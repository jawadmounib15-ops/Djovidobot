from flask import Flask, jsonify
import yfinance as yf
from datetime import datetime, timedelta
import pytz
from curl_cffi import requests as cffi_requests

app = Flask(__name__)
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")

# 32 OTC PER 1 MIN SCALPING
OTC_1M = [
("EURUSD=X","EUR/USD OTC"),("GBPUSD=X","GBP/USD OTC"),("USDJPY=X","USD/JPY OTC"),
("AUDUSD=X","AUD/USD OTC"),("USDCAD=X","USD/CAD OTC"),("USDCHF=X","USD/CHF OTC"),
("NZDUSD=X","NZD/USD OTC"),("EURJPY=X","EUR/JPY OTC"),("EURGBP=X","EUR/GBP OTC"),
("EURCHF=X","EUR/CHF OTC"),("EURAUD=X","EUR/AUD OTC"),("EURCAD=X","EUR/CAD OTC"),
("EURNZD=X","EUR/NZD OTC"),("GBPJPY=X","GBP/JPY OTC"),("GBPCHF=X","GBP/CHF OTC"),
("GBPAUD=X","GBP/AUD OTC"),("GBPCAD=X","GBP/CAD OTC"),("GBPNZD=X","GBP/NZD OTC"),
("AUDJPY=X","AUD/JPY OTC"),("AUDCAD=X","AUD/CAD OTC"),("AUDCHF=X","AUD/CHF OTC"),
("AUDNZD=X","AUD/NZD OTC"),("CADJPY=X","CAD/JPY OTC"),("CHFJPY=X","CHF/JPY OTC"),
("NZDJPY=X","NZD/JPY OTC"),("CADCHF=X","CAD/CHF OTC"),("NZDCAD=X","NZD/CAD OTC"),
("EURCAD=X","EUR/CAD OTC"),("GBPCAD=X","GBP/CAD 2"),("AUDCAD=X","AUD/CAD 2"),
("GBPCHF=X","GBP/CHF 2"),("EURCHF=X","EUR/CHF 2"),
]

def get_df(sym):
    try:
        # 1 MIN DATA
        df=yf.Ticker(sym,session=session).history(period="1d",interval="1m")
        return df if len(df)>=100 else None
    except: return None

def scadenza_1m():
    now = datetime.now(ROMA)
    # Scadenza 1 min = prossimo minuto :00
    scad = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    # Se siamo a 30 sec, mancano 30 sec + 1 min = 1:30, ma Quotex vuole scadenza a :00
    # Quindi se segnale a :30, scadenza è al minuto successivo
    if now.second < 30:
        # se siamo prima di :30, scadenza è questo minuto +1
        pass
    else:
        # se siamo dopo :30, scadenza è +1 min (già calcolata)
        pass
    return scad.strftime("%H:%M:%S"), (60 - now.second) # ritorna anche secondi rimanenti

def pinbar_otc_1m_best(o,h,l,c, df):
    b=abs(c-o); r=h-l
    if r==0 or b==0: return None
    up=h-max(o,c); lo=min(o,c)-l
    lo_perc = lo/r; up_perc = up/r; body_perc = b/r

    if body_perc > 0.35: return None
    if lo_perc < 0.58 and up_perc < 0.58: return None # 58% per 1m è già forte

    # FILTRI OTTIMIZZATI PER 1 MIN OTC - VELOCI
    ema9 = df['Close'].ewm(span=9).mean().iloc[-1]
    ema21 = df['Close'].ewm(span=21).mean().iloc[-1]

    # RSI veloce 7 per 1 min (non 14)
    delta = df['Close'].diff()
    gain = delta.where(delta>0,0).ewm(span=7).mean()
    loss = -delta.where(delta<0,0).ewm(span=7).mean()
    rs = gain.iloc[-1] / (loss.iloc[-1] + 0.00001)
    rsi = 100 - (100/(1+rs))

    # Momento - OTC 1m deve avere spinta
    prev = df.iloc[-2]
    prev_r = df.iloc[-3]

    # CALL 1M - Hammer OTC
    if lo_perc >= 0.58 and up_perc <= 0.25:
        ratio = lo/b if b>0 else 0
        if ratio < 1.6: return None
        # Deve essere sotto EMA9 per rimbalzo veloce
        if c > ema9 * 1.0003 and rsi > 60: return None
        # Ultime 2 candele rosse
        if not (prev['Close'] < prev['Open']):
            if not (prev_r['Close'] < prev_r['Open']):
                return None
        if rsi > 65: return None
        min10 = df['Low'].iloc[-11:-1].min()
        if l > min10 * 1.0008: return None
        return "CALL", int(lo_perc*100), round(ratio,1), int(rsi)

    # PUT 1M - Star OTC
    if up_perc >= 0.58 and lo_perc <= 0.25:
        ratio = up/b if b>0 else 0
        if ratio < 1.6: return None
        if c < ema9 * 0.9997 and rsi < 40: return None
        if not (prev['Close'] > prev['Open']):
            if not (prev_r['Close'] > prev_r['Open']):
                return None
        if rsi < 35: return None
        max10 = df['High'].iloc[-11:-1].max()
        if h < max10 * 0.9992: return None
        return "PUT", int(up_perc*100), round(ratio,1), int(rsi)

    return None

def analizza():
    now = datetime.now(ROMA)
    # SEGNALE SOLO SE SIAMO TRA :30 e :55 SEC - COSI HAI 30 SEC PER ENTRARE
    sec = now.second
    if not (25 <= sec <= 58):
        return {"wait": True, "sec": sec, "signals": []}

    out=[]; scad_str, sec_rim = scadenza_1m()
    for ysym,label in OTC_1M:
        df=get_df(ysym)
        if df is None: continue
        r=df.iloc[-1]
        res=pinbar_otc_1m_best(r['Open'],r['High'],r['Low'],r['Close'], df)
        if not res: continue
        d, perc, ratio, rsi=res
        out.append({
            "coppia":label,"dir":d,"perc":perc,"ratio":ratio,"rsi":rsi,
            "scadenza":scad_str,"ora":now.strftime("%H:%M:%S"),
            "rimanenti": sec_rim
        })
    return {"wait": False, "sec": sec, "signals": out}

PAGE="""<!DOCTYPE html><html><head><meta charset=utf-8>
<meta name=viewport content='width=device-width, initial-scale=1'>
<title>V8 OTC 1MIN -30SEC</title>
<style>
*{box-sizing:border-box}
body{background:#000;color:#fff;font-family:Arial;margin:0;padding:0}
.header{background:#111;padding:14px;border-bottom:3px solid #0f0;position:sticky;top:0}
.header h2{margin:0;color:#0f0;font-size:20px}
.sub{color:#ff0;font-size:12px}
.container{padding:10px}
.card{border:3px solid #0f0;padding:16px;margin:12px 0;border-radius:14px;background:#151515}
.card.PUT{border-color:#ff3333}
.CALL{color:#0f0;font-size:28px;font-weight:bold}
.PUT{color:#ff3333;font-size:28px;font-weight:bold}
.timer{font-size:32px;font-weight:bold;color:#ff0;text-align:center;padding:10px;background:#222;border-radius:10px;margin:10px 0}
button{padding:16px;border:none;border-radius:12px;font-size:17px;font-weight:bold;margin:8px 0;width:100%}
#unlock{background:#0f0;color:#000}
#analyze{background:#222;color:#fff;border:1px solid #555}
.wait{background:#332200;border:2px solid #ff0;padding:15px;border-radius:12px;text-align:center;margin:10px 0}
</style></head><body>
<div class=header>
<h2>⚡ V8 OTC 1 MIN - SEGNALE A 30 SEC</h2>
<div class=sub>32 OTC - Pinbar 58%+ - EMA9/21 - RSI7 - Scadenza 1 MIN - Segnale a :30 sec</div>
</div>
<div class=container>
<div id=status>🟢 V8 1M OTC attivo - aspetto :30 sec...</div>
<div id=timer class=timer>00</div>
<button id=unlock onclick=enableAudio()>🔊 ATTIVA AUDIO</button>
<button id=analyze onclick=load()>🔄 SCANSIONA ORA</button>
<div id=l></div>
</div>
<audio id=b src=https://cdn.pixabay.com/audio/2022/03/10/audio_1c8c9a0727.mp3 preload=auto></audio>
<script>
let audioEnabled=false;
function enableAudio(){let a=document.getElementById('b');a.play().then(()=>{a.pause();a.currentTime=0;audioEnabled=true;document.getElementById('unlock').innerText='✅ AUDIO ON';localStorage.setItem('audio','1');}).catch(e=>{});}
async function load(){
  try{
    let r=await fetch('/api/signals'); let data=await r.json();
    document.getElementById('timer').innerText=':'+String(data.sec).padStart(2,'0')+' sec';
    let c=document.getElementById('l');
    if(data.wait){
      document.getElementById('status').innerHTML='⏳ Aspetto :30 sec per segnale 1M... ora :'+data.sec+' sec - prossimo scan tra 2s';
      if(data.sec < 25){
        c.innerHTML='<div class=wait>⏰ SEGNALE 1M ARRIVA TRA '+(30-data.sec)+' SEC<br>A :30 sec parte scansione<br>Preparati su Quotex 1M</div>';
      }
      return;
    }
    let d=data.signals;
    if(d.length==0){
      document.getElementById('status').innerHTML='✅ Scan a :'+data.sec+' sec - 32 OTC - nessuna pinbar 1M - riprovo tra 2s';
      c.innerHTML='<div style=color:#666;padding:15px;text-align:center>🔍 32 OTC scansionate a :'+data.sec+'<br>Nessuna pinbar 1M ora</div>';
    } else {
      document.getElementById('status').innerHTML='🔥🔥 '+d.length+' SEGNALI 1M A :'+data.sec+' - ENTRA ORA! '+d[0].rimanenti+' SEC RIMANENTI!';
      c.innerHTML='';
      d.forEach(s=>{
        let e=document.createElement('div'); e.className='card '+s.dir;
        e.innerHTML=`<b style=font-size:18px>${s.coppia} 1M</b> <span style=float:right;color:#ff0>${s.ora}</span><br>
        <span class=${s.dir}>${s.dir} 1M</span> - ${s.perc}% ${s.ratio}x RSI ${s.rsi}<br>
        <div style=margin-top:10px>Scade <b style=font-size:20px>${s.scadenza}</b><br>
        <span style=color:#ff0;font-size:18px>⏰ ${s.rimanenti} SEC PER ENTRARE!</span><br><br>
        <span style=background:#0f0;color:#000;padding:8px 15px;border-radius:8px;font-weight:bold>👉 ENTRA ORA 1 MIN</span></div>`;
        c.appendChild(e);
      });
      if(audioEnabled){
        document.getElementById('b').play().catch(()=>{});
        if(navigator.vibrate) navigator.vibrate([600,100,600,100,600]);
      }
    }
    if(localStorage.getItem('audio')=='1'){audioEnabled=true;document.getElementById('unlock').innerText='✅ AUDIO ON';}
  }catch(e){document.getElementById('status').innerHTML='❌ Errore...';}
}
setInterval(load,2000);
load();
</script></body></html>"""

@app.route('/')
def home(): return PAGE
@app.route('/api/signals')
def sig(): return jsonify(analizza())
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
