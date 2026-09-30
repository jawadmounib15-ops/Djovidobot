# V4 ORO LIGHT 00-23 - 15m REAL - 30M SCADENZA
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
    now=datetime.now(ROMA)
    return (now + timedelta(minutes=30)).strftime("%H:%M")

def pinbar_oro(o,h,l,c, df):
    b=abs(c-o); r=h-l
    if r==0: return None
    up=h-max(o,c); lo=min(o,c)-l
    # LIGHT: 60% invece di 70%
    if up/r < 0.60 and lo/r < 0.60: return None
    if b/r > 0.35 or b/r < 0.03: return None
    if up/r >= 0.60 and lo/r > 0.20: return None
    if lo/r >= 0.60 and up/r > 0.20: return None
    max10 = df['High'].iloc[-11:-1].max(); min10 = df['Low'].iloc[-11:-1].min()
    fakeout_alto = h >= max10*0.999 and c < max10
    fakeout_basso = l <= min10*1.001 and c > min10
    if up/r >= 0.60 and fakeout_alto: return "PUT", int(up/r*100), round(up/b,1)
    if lo/r >= 0.60 and fakeout_basso: return "CALL", int(lo/r*100), round(lo/b,1)
    return None

def analizza():
    now_roma = datetime.now(ROMA)
    if not (0 <= now_roma.hour < 23): return []
    out=[]; sc=scadenza()
    for ysym,label in MAP.items():
        df=get_df(ysym)
        if df is None: continue
        r=df.iloc[-1]
        res=pinbar_oro(r['Open'],r['High'],r['Low'],r['Close'], df)
        if not res: continue
        d, perc, ratio=res
        out.append({"coppia":label,"dir":d,"perc":perc,"ratio":ratio,"scadenza":sc,"ora":now_roma.strftime("%H:%M:%S")})
    return out

PAGE="""<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width'><title>V4 ORO 00-23</title>
<style>body{background:#111;color:#fff;font-family:Arial;padding:15px}.card{border:2px solid #0f0;padding:12px;margin:8px 0;border-radius:10px}.PUT{color:#f44;font-size:20px}.CALL{color:#0f0;font-size:20px}</style></head><body>
<h2>🔥 V4 ORO LIGHT - 15m REAL 00-23 - Scad 30M</h2><div id=l></div><audio id=b src=https://cdn.pixabay.com/audio/2022/03/10/audio_1c8c9a0727.mp3></audio>
<script>async function load(){let r=await fetch('/api/signals');let d=await r.json();let c=document.getElementById('l');c.innerHTML=d.length?'': '<p>00-23 LIGHT attivo, nessun fakeout ora, controllo ogni 15s... Scadenza 30M sicura</p>'; d.forEach(s=>{let e=document.createElement('div');e.className='card';e.innerHTML=`<b>${s.coppia}</b> ${s.ora}<br><span class=${s.dir}>${s.dir}</span> - Ombra ${s.perc}% ${s.ratio}x<br>Scad <b>${s.scadenza} (30M)</b>`;c.appendChild(e)}); if(d.length) document.getElementById('b').play()}load();setInterval(load,15000)</script></body></html>"""
@app.route('/')
def home(): return PAGE
@app.route('/api/signals')
def sig(): return jsonify(analizza())
