from flask import Flask, jsonify
import yfinance as yf
from datetime import datetime, timedelta
import pytz
from curl_cffi import requests as cffi_requests

app = Flask(__name__)
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")
MAP = {"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","AUDUSD=X":"AUD/USD","USDJPY=X":"USD/JPY","EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY","AUDJPY=X":"AUD/JPY","EURGBP=X":"EUR/GBP"}

def get_df(sym):
    try:
        df=yf.Ticker(sym,session=session).history(period="5d",interval="15m")
        return df if len(df)>=30 else None
    except: return None

def scadenza():
    return (datetime.now(ROMA) + timedelta(minutes=30)).strftime("%H:%M")

def pinbar_oro(o,h,l,c, df):
    b=abs(c-o); r=h-l
    if r==0: return None
    up=h-max(o,c); lo=min(o,c)-l
    ema21 = df['Close'].ewm(span=21).mean().iloc[-1]
    if b/r == 0: return None
    ratio_up = up/b if b>0 else 0
    ratio_lo = lo/b if b>0 else 0
    # V4.2.1 UN PELO 62% + TREND
    if up/r < 0.62 and lo/r < 0.62: return None
    if b/r > 0.32 or b/r < 0.04: return None
    if up/r >= 0.62 and lo/r > 0.18: return None
    if lo/r >= 0.62 and up/r > 0.18: return None
    if up/r >= 0.62 and ratio_up < 1.8: return None
    if lo/r >= 0.62 and ratio_lo < 1.8: return None
    max10 = df['High'].iloc[-11:-1].max(); min10 = df['Low'].iloc[-11:-1].min()
    fakeout_alto = h >= max10*0.999 and c < max10
    fakeout_basso = l <= min10*1.001 and c > min10
    if up/r >= 0.62 and fakeout_alto:
        if c < ema21: return "PUT", int(up/r*100), round(ratio_up,1)
        else: return None
    if lo/r >= 0.62 and fakeout_basso:
        if c > ema21: return "CALL", int(lo/r*100), round(ratio_lo,1)
        else: return None
    return None

def analizza():
    if not (0 <= datetime.now(ROMA).hour < 23): return []
    out=[]; sc=scadenza()
    for ysym,label in MAP.items():
        df=get_df(ysym)
        if df is None: continue
        r=df.iloc[-1]
        res=pinbar_oro(r['Open'],r['High'],r['Low'],r['Close'], df)
        if not res: continue
        d, perc, ratio=res
        out.append({"coppia":label,"dir":d,"perc":perc,"ratio":ratio,"scadenza":sc,"ora":datetime.now(ROMA).strftime("%H:%M:%S")})
    return out

PAGE="""<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width'><title>V4.2.1 62%</title>
<style>body{background:#111;color:#fff;font-family:Arial;padding:15px}.card{border:2px solid #0f0;padding:12px;margin:8px 0;border-radius:10px}.PUT{color:#f44;font-size:22px}.CALL{color:#0f0;font-size:22px}button{padding:14px;border:none;border-radius:10px;font-size:16px;font-weight:bold;margin:6px 0;width:100%}#unlock{background:#0f0;color:#000}#analyze{background:#222;color:#fff;border:1px solid #555}</style></head><body>
<h2>🔥 V4.2.1 ORO 62% TREND 00-23 30M</h2>
<div id=status style=color:#aaa>V4.2.1 62% attivo - Trend ON - Scad 30M - controllo ogni 15s</div>
<button id=unlock onclick=enableAudio()>🔊 CLICCA PER ATTIVARE AUDIO</button>
<button id=analyze onclick=load()>🔄 ANALIZZA ORA</button>
<div id=l style=margin-top:10px></div>
<audio id=b src=https://cdn.pixabay.com/audio/2022/03/10/audio_1c8c9a0727.mp3 preload=auto></audio>
<script>
let audioEnabled=false;
function enableAudio(){
  let a=document.getElementById('b');
  a.play().then(()=>{a.pause(); a.currentTime=0; audioEnabled=true; document.getElementById('unlock').innerText='✅ AUDIO ATTIVO'; localStorage.setItem('audio','1');}).catch(e=>{});
}
async function load(){
  document.getElementById('status').innerText='⏳ Analizzo 8 coppie...';
  try{
    let r=await fetch('/api/signals'); let d=await r.json();
    let c=document.getElementById('l');
    if(d.length==0){
      document.getElementById('status').innerText='✅ V4.2.1 62% attivo 00-23 - Nessun fakeout trend OK ora - prossimo check 15s';
      c.innerHTML='<p style=color:#666>00-23 attivo, nessun segnale valido ora.<br>Ultimo check: '+new Date().toLocaleTimeString()+'</p>';
    } else {
      document.getElementById('status').innerText='🔥 '+d.length+' SEGNALE TROVATO!';
      c.innerHTML='';
      d.forEach(s=>{
        let e=document.createElement('div'); e.className='card';
        e.innerHTML=`<b>${s.coppia}</b> ${s.ora}<br><span class=${s.dir}>${s.dir}</span> - Ombra ${s.perc}% ${s.ratio}x<br>Scad <b>${s.scadenza} (30M)</b>`;
        c.appendChild(e);
      });
      if(audioEnabled){ document.getElementById('b').play().catch(()=>{}); if(navigator.vibrate) navigator.vibrate([300,100,300]); }
    }
    if(localStorage.getItem('audio')=='1'){ audioEnabled=true; document.getElementById('unlock').innerText='✅ AUDIO ATTIVO'; }
  }catch(e){ document.getElementById('status').innerText='❌ Errore connessione, riprovo...'; }
}
load(); setInterval(load,15000);
</script></body></html>"""

@app.route('/')
def home(): return PAGE
@app.route('/api/signals')
def sig(): return jsonify(analizza())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
