from flask import Flask, jsonify
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz, time
from curl_cffi import requests as cffi_requests

app = Flask(__name__)
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X",
         "EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X","EURNZD=X",
         "GBPJPY=X","GBPCHF=X","GBPAUD=X","GBPCAD=X","GBPNZD=X",
         "AUDJPY=X","AUDCAD=X","AUDCHF=X","AUDNZD=X",
         "CADJPY=X","CHFJPY=X","NZDJPY=X","CADCHF=X","NZDCAD=X","NZDCHF=X"]

STORICO = []
cooldown = {}
pending = []

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
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
    return 100*((df['Close']-lo)/(hi-lo))
def get_df_safe(sym):
    try:
        df=yf.Ticker(sym, session=session).history(period="5d", interval="15m")
        df=fix_df(df)
        return df if len(df)>=210 else None
    except: return None

def scan_v61():
    global STORICO
    now = datetime.now(ROMA)
    results=[]
    count=0
    for symbol in PAIRS:
        if count>=5: break
        clean=symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 3600: continue
        try:
            df=get_df_safe(symbol)
            if df is None: continue
            df['e20']=df['Close'].ewm(span=20).mean()
            df['e200']=df['Close'].ewm(span=200).mean()
            df['rsi']=rsi(df['Close'])
            df['atr']=atr(df,14)
            df['atr_ma50']=df['atr'].rolling(50).mean()
            df['stoch_k']=stochastic(df)
            last=df.iloc[-1]
            price=float(last['Close']); rsi_v=float(last['rsi']); stoch_k=float(last['stoch_k'])
            if last['atr'] < last['atr_ma50']*0.60: continue
            if last['atr'] > last['atr_ma50']*2.0: continue
            tocco_e20=abs(price-float(last['e20']))/price < 0.0028
            if abs(price-float(last['e200']))/price < 0.001: continue
            signal=None
            if price>float(last['e200']) and tocco_e20 and 18<=rsi_v<=33 and stoch_k<20: signal="BUY"
            if price<float(last['e200']) and tocco_e20 and 62<=rsi_v<=75 and stoch_k>80: signal="SELL"
            if signal:
                if any(p['symbol']==clean for p in pending): continue
                s={"coppia":clean,"dir":signal,"rsi":int(rsi_v),"stoch":int(stoch_k),"entry":round(price,5),"ora":now.strftime("%H:%M:%S"),"data":now.strftime("%d/%m %H:%M:%S"),"id":f"{clean}{now.strftime('%H%M')}"}
                STORICO.append(s)
                if len(STORICO)>100: STORICO=STORICO[-100:]
                pending.append({"symbol":clean,"time":time.time()})
                cooldown[clean]=time.time()
                results.append(s)
                count+=1
        except: continue
    return results

@app.route('/api/signals')
def api():
    now=datetime.now(ROMA)
    nuovi=scan_v61()
    return jsonify({"ora":now.strftime("%H:%M:%S"),"storico":STORICO[-30:][::-1],"nuovi":nuovi})

PAGE="""<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width, initial-scale=1'>
<title>V61.2 FIX SUONO</title>
<style>
body{background:#000;color:#fff;font-family:Arial;margin:0}.header{background:#111;padding:14px;border-bottom:3px solid #0f0;position:sticky;top:0}
.header h2{margin:0;color:#0f0;font-size:18px}.sub{color:#ff0;font-size:11px}
.container{padding:10px}.card{border:3px solid #0f0;padding:14px;margin:12px 0;border-radius:14px;background:#151515;animation:pop.5s}
.card.SELL{border-color:#f33}.BUY{color:#0f0;font-size:26px;font-weight:bold}.SELL{color:#f33;font-size:26px;font-weight:bold}
@keyframes pop{0%{transform:scale(.8)}100%{transform:scale(1)}}
.timer{font-size:42px;color:#ff0;text-align:center;background:#222;padding:14px;border-radius:12px;margin:10px 0}
button{padding:16px;width:100%;border:none;border-radius:12px;font-weight:bold;margin:6px 0;font-size:16px}
#unlock{background:#ff0;color:#000;font-size:18px;border:3px solid #0f0}
#unlock.on{background:#0f0;color:#000}
.storico{background:#111;border:1px solid #444;border-radius:12px;padding:10px;margin:15px 0}
.row{display:flex;justify-content:space-between;font-size:12px;padding:6px 0;border-bottom:1px solid #222}
.row.BUY b{color:#0f0}.row.SELL b{color:#f33}
</style></head><body>
<div class=header><h2>🔊 V61.2 FIX SUONO - BILANCIATO 28 PAIRS</h2>
<div class=sub>FIX: Suono ora suona sempre + Vibrazione + Notifica popup</div></div>
<div class=container>
<div id=timer class=timer>00:00:00</div>
<div id=status style=text-align:center;color:#0f0>🔊 CLICCA AUDIO ON SOTTO - OBBLIGATORIO PER SUONO</div>
<button id=unlock onclick=enableAudio()>🔊 CLICCA QUI PER ATTIVARE SUONO 🔊</button>
<div id=l></div>
<div class=storico><h3 style=color:#ff0>📜 STORICO</h3><div id=storico>Vuoto</div></div>
<button onclick=testSound()>🔔 TEST SUONO - PROVA ORA</button>
</div>
<audio id=b src=https://cdn.pixabay.com/audio/2022/03/10/audio_1c8c9a0727.mp3 preload=auto></audio>
<audio id=b2 src=https://cdn.pixabay.com/audio/2021/08/04/audio_0625c1539c.mp3 preload=auto></audio>
<script>
let audioEnabled=false;
let seenIds=new Set();
let firstLoad=true;

function enableAudio(){
 let a=document.getElementById('b');
 a.volume=1;
 a.play().then(()=>{
   a.pause(); a.currentTime=0;
   audioEnabled=true;
   document.getElementById('unlock').innerText='✅ AUDIO ON - SUONA ATTIVO';
   document.getElementById('unlock').classList.add('on');
   document.getElementById('status').innerText='✅ AUDIO ATTIVO - Ora suonerà ad ogni segnale';
   localStorage.setItem('audio','1');
   // vibra per confermare
   if(navigator.vibrate) navigator.vibrate(200);
 }).catch(e=>{
   alert('Clicca di nuovo - il browser ha bloccato');
 });
}

function testSound(){
 if(!audioEnabled){ alert('Prima clicca AUDIO ON sopra!'); return; }
 document.getElementById('b').currentTime=0;
 document.getElementById('b').play();
 if(navigator.vibrate) navigator.vibrate([500,100,500]);
 alert('🔊 Se hai sentito suono, ora funziona!');
}

function playAlarm(s){
 if(!audioEnabled) return;
 let a=document.getElementById('b');
 let a2=document.getElementById('b2');
 a.currentTime=0; a.play().catch(()=>{});
 setTimeout(()=>{a2.currentTime=0; a2.play().catch(()=>{});},400);
 setTimeout(()=>{a.currentTime=0; a.play().catch(()=>{});},900);
 if(navigator.vibrate) navigator.vibrate([600,150,600,150,1000]);
 // Notifica visiva
 if('Notification' in window && Notification.permission==='granted'){
   new Notification(`🎯 ${s.dir} ${s.coppia}`, {body:`RSI ${s.rsi} STO ${s.stoch} Entry ${s.entry}`});
 }
}

async function load(){
 try{
  let r=await fetch('/api/signals'); let data=await r.json();
  document.getElementById('timer').innerText=data.ora;
  // storico
  let h=document.getElementById('storico');
  if(!data.storico||data.storico.length==0){h.innerHTML='Vuoto - 28 pairs scan';}
  else{
   let html=''; data.storico.forEach(s=>{html+=`<div class=row ${s.dir}><span>${s.data} - ${s.coppia}</span><span><b>${s.dir}</b> RSI${s.rsi} ${s.entry}</span></div>`;}); h.innerHTML=html;
  }
  // controlla nuovi segnali
  if(data.nuovi && data.nuovi.length>0){
    data.nuovi.forEach(s=>{
      if(!seenIds.has(s.id)){
        seenIds.add(s.id);
        if(!firstLoad){
          // NUOVO SEGNALE -> SUONA!
          document.getElementById('l').innerHTML=`<div class=card ${s.dir}><b>🚨 ${s.coppia} 15M NUOVO!</b> ${s.data}<br><span class=${s.dir}>${s.dir}</span> RSI ${s.rsi} STO ${s.stoch} Entry ${s.entry}<br><div style=margin-top:8px;background:#ff0;color:#000;padding:8px;border-radius:8px;text-align:center;font-weight:bold>👉 SEGNALE APPENA ARRIVATO - ${s.ora}</div></div>`+document.getElementById('l').innerHTML;
          playAlarm(s);
        }
      }
    });
  }
  // al primo giro, memorizza id esistenti senza suonare
  if(firstLoad){
    data.storico.forEach(s=>seenIds.add(s.id));
    firstLoad=false;
  }
  if(localStorage.getItem('audio')=='1' &&!audioEnabled){
    document.getElementById('unlock').innerText='✅ AUDIO ON (riattivato)';
    document.getElementById('unlock').classList.add('on');
    audioEnabled=true;
  }
 }catch(e){}
}
setInterval(load,5000); load();
// chiedi permesso notifiche
if('Notification' in window && Notification.permission!=='granted'){Notification.requestPermission();}
</script></body></html>"""

@app.route('/')
def home(): return PAGE

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
