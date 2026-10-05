import os, time, threading
from flask import Flask, jsonify
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
from curl_cffi import requests as cffi_requests

app = Flask(__name__)
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")

# TUTTE LE COPPIE REALI - 28 invece di 21
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X",
         "EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X","EURNZD=X",
         "GBPJPY=X","GBPCHF=X","GBPAUD=X","GBPCAD=X","GBPNZD=X",
         "AUDJPY=X","AUDCAD=X","AUDCHF=X","AUDNZD=X",
         "CADJPY=X","CHFJPY=X","NZDJPY=X","CADCHF=X","NZDCAD=X","NZDCHF=X"]

STORICO = []
cooldown = {}
pending = []

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns=df.columns.get_level_values(0)
    return df

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

def atr(df,p=14):
    hl=df['High']-df['Low']; hc=abs(df['High']-df['Close'].shift()); lc=abs(df['Low']-df['Close'].shift())
    tr=pd.concat([hl,hc,lc],axis=1).max(axis=1)
    return tr.rolling(p).mean()

def stochastic(df,k=14,d=3):
    lo=df['Low'].rolling(k).min(); hi=df['High'].rolling(k).max()
    k_perc=100*((df['Close']-lo)/(hi-lo))
    return k_perc, k_perc.rolling(d).mean()

def get_df_safe(symbol):
    try:
        df=yf.Ticker(symbol, session=session).history(period="5d", interval="15m")
        df=fix_df(df)
        return df if len(df)>=210 else None
    except: return None

def scan_v61():
    global STORICO
    now = datetime.now(ROMA)
    results = []
    count_this_scan = 0

    for symbol in PAIRS:
        if count_this_scan>=5: break
        clean=symbol.replace("=X","")
        # COOLDOWN 60 min invece di 90 - così gira più segnali
        if clean in cooldown and time.time()-cooldown[clean] < 3600:
            continue
        try:
            df=get_df_safe(symbol)
            if df is None: continue
            df['e20']=df['Close'].ewm(span=20).mean()
            df['e200']=df['Close'].ewm(span=200).mean()
            df['rsi']=rsi(df['Close'])
            df['atr']=atr(df,14)
            df['atr_ma50']=df['atr'].rolling(50).mean()
            df['stoch_k'],_ = stochastic(df)
            last=df.iloc[-1]
            price=float(last['Close']); rsi_v=float(last['rsi']); stoch_k=float(last['stoch_k'])

            # TUE REGOLE ORIGINALI V61.1 MA ALLARGATE UN PELO:
            # Prima: ATR 0.70-1.8 -> Ora 0.60-2.0 (+30% più largo)
            if last['atr'] < last['atr_ma50']*0.60: continue
            if last['atr'] > last['atr_ma50']*2.0: continue

            # Prima: tocco 0.002 (0.2%) -> Ora 0.0028 (0.28%)
            tocco_e20=abs(price-float(last['e20']))/price < 0.0028

            dist_e200=abs(price-float(last['e200']))/price
            if dist_e200 < 0.001: continue

            signal=None
            # Prima: BUY 20-30 STO<15 / SELL 64-70 STO>85 (troppo stretto = 0 segnali)
            # Ora: BUY 18-33 STO<20 / SELL 62-75 STO>80 (trova 2-3 al giorno in più)
            if price>float(last['e200']) and tocco_e20 and 18<=rsi_v<=33 and stoch_k<20:
                signal="BUY"
            if price<float(last['e200']) and tocco_e20 and 62<=rsi_v<=75 and stoch_k>80:
                signal="SELL"

            if signal:
                if any(p['symbol']==clean for p in pending): continue
                segnale={
                    "coppia":clean,"dir":signal,"rsi":int(rsi_v),"stoch":int(stoch_k),
                    "entry":round(price,5),"ora":now.strftime("%H:%M:%S"),
                    "data":now.strftime("%d/%m %H:%M:%S"),"e20":round(float(last['e20']),5)
                }
                results.append(segnale)
                STORICO.append(segnale)
                if len(STORICO)>100: STORICO=STORICO[-100:]
                pending.append({"symbol":clean,"signal":signal,"entry":price,"time":time.time()})
                cooldown[clean]=time.time()
                count_this_scan+=1
        except: continue
    return results

@app.route('/api/signals')
def api():
    now=datetime.now(ROMA)
    # scansiona ogni chiamata
    scan_v61()
    return jsonify({"ora":now.strftime("%H:%M:%S"),"sec":now.second,"storico":STORICO[-30:][::-1],"pending":len(pending)})

PAGE="""<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width, initial-scale=1'>
<title>V61.2 SCANNER APP - 28 PAIRS</title>
<style>
*{box-sizing:border-box}body{background:#000;color:#fff;font-family:Arial;margin:0}
.header{background:#111;padding:14px;border-bottom:3px solid #0f0;position:sticky;top:0}
.header h2{margin:0;color:#0f0;font-size:18px}.sub{color:#ff0;font-size:11px}
.container{padding:10px}.card{border:3px solid #0f0;padding:14px;margin:12px 0;border-radius:14px;background:#151515}
.card.SELL{border-color:#f33}.BUY{color:#0f0;font-size:24px;font-weight:bold}.SELL{color:#f33;font-size:24px;font-weight:bold}
.timer{font-size:42px;font-weight:bold;color:#ff0;text-align:center;padding:14px;background:#222;border-radius:12px;margin:10px 0}
button{padding:16px;border:none;border-radius:12px;font-size:16px;font-weight:bold;margin:6px 0;width:100%}
#unlock{background:#0f0;color:#000}
.storico{background:#111;border:1px solid #444;border-radius:12px;padding:10px;margin:15px 0}
.row{display:flex;justify-content:space-between;font-size:12px;padding:6px 0;border-bottom:1px solid #222}
.row.BUY b{color:#0f0}.row.SELL b{color:#f33}
</style></head><body>
<div class=header><h2>🟡 V61.2 BILANCIATO - SCANNER APP - 28 PAIRS REALI</h2>
<div class=sub>STESSE REGOLE V61 L4 PELO - MA ALLARGATO UN PELO: EMA20 0.28% + RSI 18-33/62-75 + STO 20/80 + ATR 0.6-2.0 + 60min cooldown + STORICO + SUONO</div></div>
<div class=container>
<div id=status>🟢 V61.2 SCANNER - 28 coppie reali</div>
<div id=timer class=timer>00:00:00</div>
<button id=unlock onclick=enableAudio()>🔊 AUDIO ON - BILANCIATO</button>
<button onclick=load()>🔄 SCANSIONA 28 PAIRS ORA</button>
<div id=l></div>
<div class=storico><h3 style=color:#ff0>📜 STORICO ULTIMI 30 - BILANCIATO</h3><div id=storico>Nessun segnale - storico vuoto - 28 coppie in scan ogni 60 sec</div></div>
</div>
<audio id=b src=https://cdn.pixabay.com/audio/2022/03/10/audio_1c8c9a0727.mp3 preload=auto></audio>
<script>
let audioEnabled=false, lastLen=0;
function enableAudio(){let a=document.getElementById('b');a.play().then(()=>{a.pause();a.currentTime=0;audioEnabled=true;document.getElementById('unlock').innerText='✅ AUDIO ON - 28 PAIRS';localStorage.setItem('audio','1');}).catch(e=>{});}
function render(list){
 let h=document.getElementById('storico');
 if(!list||list.length==0){h.innerHTML='Nessun segnale - storico vuoto';return;}
 let html=''; list.forEach(s=>{html+=`<div class=row ${s.dir}><span>${s.data} - ${s.coppia}</span><span><b>${s.dir}</b> RSI${s.rsi} STO${s.stoch} Entry ${s.entry}</span></div>`;}); h.innerHTML=html;
}
async function load(){
 try{
  let r=await fetch('/api/signals'); let data=await r.json();
  document.getElementById('timer').innerText=data.ora;
  document.getElementById('status').innerHTML=`🟢 V61.2 - ${data.storico.length} segnali storico - Pending ${data.pending}`;
  render(data.storico);
  if(data.storico.length>lastLen && lastLen!=0){
    let s=data.storico[0];
    document.getElementById('l').innerHTML=`<div class=card ${s.dir}><b>${s.coppia} 15M</b> ${s.data}<br><span class=${s.dir}>${s.dir}</span> RSI ${s.rsi} STO ${s.stoch} Entry ${s.entry}</div>`;
    if(audioEnabled){document.getElementById('b').play().catch(()=>{}); if(navigator.vibrate) navigator.vibrate([600,100,600]);}
  }
  lastLen=data.storico.length;
  if(localStorage.getItem('audio')=='1'){audioEnabled=true;document.getElementById('unlock').innerText='✅ AUDIO ON - 28 PAIRS';}
 }catch(e){document.getElementById('status').innerHTML='❌ '+e.message;}
}
setInterval(load,60000); load();
</script></body></html>"""

@app.route('/')
def home(): return PAGE

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
