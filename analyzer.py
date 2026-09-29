# analyzer.py - V3 PINBAR PULITA 80% - 5m - REAL+OTC - 15s
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
        df=yf.Ticker(sym,session=session).history(period="5d",interval="5m")
        return df if len(df)>=30 else None
    except: return None

def scadenza():
    now=datetime.now(ROMA)
    m = (now.minute // 5 + 1) * 5
    if m >= 60:
        s = now.replace(minute=0,second=0,microsecond=0)+timedelta(hours=1)
    else:
        s = now.replace(minute=m,second=0,microsecond=0)
    return s.strftime("%H:%M"), (s+timedelta(minutes=5)).strftime("%H:%M")

# SOLO PINBAR PULITA 80%
def pinbar_pulita(o,h,l,c):
    b=abs(c-o); r=h-l
    if r==0: return None
    if b/r < 0.12 or b/r > 0.22: return None
    up=h-max(o,c); lo=min(o,c)-l
    if lo >= b*2.8 and up <= r*0.15 and lo/r >= 0.60:
        return "CALL", round(lo/b,1)
    if up >= b*2.8 and lo <= r*0.15 and up/r >= 0.60:
        return "PUT", round(up/b,1)
    return None

def analizza():
    out=[]; s5,s10=scadenza()
    for ysym,label in MAP.items():
        df=get_df(ysym)
        if df is None: continue
        r=df.iloc[-1]
        res=pinbar_pulita(r['Open'],r['High'],r['Low'],r['Close'])
        if not res: continue
        d,ratio=res
        # MANDIAMO ENTRAMBE: REAL e OTC con stessi dati
        for tipo in [label, label+" OTC"]:
            out.append({"coppia":tipo,"dir":d,"ratio":ratio,"scadenza":s5,"scadenza_2":s10,"ora":datetime.now(ROMA).strftime("%H:%M:%S"),"tipo":"REAL" if "OTC" not in tipo else "OTC"})
    return out

PAGE="""<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width'><title>V3 PINBAR 80% 5m</title>
<style>body{background:#111;color:#fff;font-family:Arial;padding:15px}.card{border:2px solid #0f0;padding:12px;margin:8px 0;border-radius:10px}.CALL{color:#0f0;font-size:22px}.PUT{color:#f44;font-size:22px}.OTC{border-color:#ff0}</style></head><body>
<h2>🔥 V3 PINBAR PULITA 80% - 5m - REAL+OTC - 15s</h2><div id=l></div><audio id=b src=https://cdn.pixabay.com/audio/2022/03/10/audio_1c8c9a0727.mp3></audio>
<script>async function load(){let r=await fetch('/api/signals');let d=await r.json();let c=document.getElementById('l');c.innerHTML='';if(!d.length){c.innerHTML='<p>Nessun segnale pulito, controllo ogni 15s...</p>';return} d.forEach(s=>{let e=document.createElement('div');e.className='card '+(s.tipo=='OTC'?'OTC':'');e.innerHTML=`<b>${s.coppia}</b> - ${s.ora}<br><span class=${s.dir}>${s.dir}</span> - PULITA ${s.ratio}x<br>Scad: <b>${s.scadenza}</b> | Alt ${s.scadenza_2} | ${s.tipo}`;c.appendChild(e)});document.getElementById('b').play()}load();setInterval(load,15000)</script></body></html>"""

@app.route('/')
def home(): return PAGE
@app.route('/api/signals')
def sig(): return jsonify(analizza())
