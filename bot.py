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
    # LIGHT 60%
    if up/r < 0.60 and lo/r < 0.60: return None
    if b/r > 0.35 or b/r < 0.03: return None
    if up/r >= 0.60 and lo/r > 0.20: return None
    if lo/r >= 0.60 and up/r > 0.20: return None
    max10 = df['High'].iloc[-11:-1].max(); min10 = df['Low'].iloc[-11:-1].min()
    fakeout_alto = h >= max10*0.999 and c < max10
    fakeout_basso = l <= min10*1.001 and c > min10
    # FILTRO TREND V4.1 - blocca contrari
    if up/r >= 0.60 and fakeout_alto:
        if c < ema21: # PUT solo in trend ribassista
            return "PUT", int(up/r*100), round(up/b,1)
        else: return None
    if lo/r >= 0.60 and fakeout_basso:
        if c > ema21: # CALL solo in trend rialzista
            return "CALL", int(lo/r*100), round(lo/b,1)
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

PAGE="""<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width'><title>V4.1 ORO TREND</title>
<style>body{background:#111;color:#fff;font-family:Arial;padding:15px}.card{border:2px solid #0f0;padding:12px;margin:8px 0;border-radius:10px}.PUT{color:#f44;font-size:22px}.CALL{color:#0f0;font-size:22px}#unlock{padding:16px;background:#0f0;color:#000;border:none;border-radius:10px;font-size:18px;font-weight:bold;width:100%;margin:10px 0}</style></head><body>
<h2>🔥 V4.1 ORO TREND FILTER 00-23 30M</h2><div id=l></div>
<audio id=b src=https://cdn.pixabay.com/audio/2022/03/10/audio_1c8c9a0727.mp3 preload=auto></audio>
<script>
let audioEnabled=false;
function enableAudio(){
  let a=document.getElementById('b');
  a.play().then(()=>{a.pause(); a.currentTime=0; audioEnabled=true; document.getElementById('unlock').style.display='none'; localStorage.setItem('audio','1');}).catch(e=>{});
}
async function load(){
  let r=await fetch('/api/signals'); let d=await r.json();
  let c=document.getElementById('l');
  if(d.length==0){
    c.innerHTML=`<p>V4.1 TREND FILTER attivo 00-23<br>Blocca segnali contrari - Scad 30M</p><button id=unlock onclick=enableAudio()>🔊 CLICCA PER ATTIVARE AUDIO</button>`;
    if(localStorage.getItem('audio')=='1') audioEnabled=true;
  } else {
    c.innerHTML='';
    d.forEach(s=>{
      let e=document.createElement('div'); e.className='card';
      e.innerHTML=`<b>${s.coppia}</b> ${s.ora}<br><span class=${s.dir}>${s.dir}</span> - Ombra ${s.perc}% ${s.ratio}x<br>Scad <b>${s.scadenza} (30M)</b>`;
      c.appendChild(e);
    });
    if(audioEnabled){ document.getElementById('b').play().catch(()=>{}); if(navigator.vibrate) navigator.vibrate([300,100,300]); }
  }
}
load(); setInterval(load,15000);
</script></body></html>"""

@app.route('/')
def home(): return PAGE
@app.route('/api/signals')
def sig(): return jsonify(analizza())
