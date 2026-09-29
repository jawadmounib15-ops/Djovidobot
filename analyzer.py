# analyzer.py - VERSIONE LARGA SICURA - 15 SECONDI
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
        df=yf.Ticker(sym,session=session).history(period="20d",interval="15m")
        if len(df)<60: return None
        cl=df['Close']; df['EMA9']=cl.ewm(9).mean(); df['EMA21']=cl.ewm(21).mean(); df['EMA50']=cl.ewm(50).mean()
        df['ATR']=(df['High']-df['Low']).rolling(14).mean()
        d=cl.diff(); g=d.where(d>0,0).rolling(14).mean(); l=-d.where(d<0,0).rolling(14).mean()
        df['RSI']=100-(100/(1+g/l)); return df
    except: return None

def get_trend(sym):
    try:
        df=yf.Ticker(sym,session=session).history(period="20d",interval="1h")
        if len(df)<60: return None
        return "UP" if df['Close'].ewm(21).mean().iloc[-1] > df['Close'].ewm(50).mean().iloc[-1] else "DOWN"
    except: return None

def scadenza():
    now=datetime.now(ROMA); m=(now.minute//15+1)*15
    s15=now.replace(minute=0,second=0,microsecond=0)+timedelta(hours=1) if m>=60 else now.replace(minute=m,second=0,microsecond=0)
    return s15.strftime("%H:%M"), (s15+timedelta(minutes=15)).strftime("%H:%M")

def pinbar(o,h,l,c):
    b=abs(c-o); r=h-l
    if r==0 or b<r*0.10 or b>r*0.30: return None
    up=h-max(o,c); lo=min(o,c)-l
    if min(up,lo)>r*0.25: return None
    if max(up,lo)<r*0.60: return None
    if max(up,lo)<b*1.8: return None
    return (up,lo)

def analizza_tutto():
    out=[]; s15,s30=scadenza()
    for ysym,label in MAP.items():
        for suff in ["", " OTC"]:
            full=label+suff; df=get_df(ysym)
            if df is None: continue
            tr=get_trend(ysym)
            if tr is None: continue
            r=df.iloc[-1]; pb=pinbar(r['Open'],r['High'],r['Low'],r['Close'])
            if not pb: continue
            up,lo=pb; dir=None; lavoro=""

            if lo>up and r['EMA9']>r['EMA21'] and 38<=r['RSI']<=62:
                dir="CALL"; lavoro="L1 TREND LARGO"
            if up>lo and r['EMA9']<r['EMA21'] and 38<=r['RSI']<=62:
                dir="PUT"; lavoro="L1 TREND LARGO"
            
            if not dir:
                prev_low=df['Low'].iloc[-11:-1].min(); prev_high=df['High'].iloc[-11:-1].max()
                if lo>up and r['Low'] < prev_low: dir="CALL"; lavoro="L2 SPORGENZA"
                if up>lo and r['High'] > prev_high: dir="PUT"; lavoro="L2 SPORGENZA"

            if not dir: continue
            if dir=="CALL" and tr=="DOWN": continue
            if dir=="PUT" and tr=="UP": continue
            
            out.append({"coppia":full,"dir":dir,"lavoro":lavoro,"trend1h":tr,"is_otc":"OTC" in full,"scadenza":s15,"scadenza_30":s30,"rsi":round(float(r['RSI']),1),"ora":datetime.now(ROMA).strftime("%H:%M:%S")})
    return out

PAGE="""<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Pocket Largo 15s</title>
<style>body{background:#111;color:#fff;font-family:Arial;padding:15px}.card{border:2px solid #0f0;padding:12px;margin:10px 0;border-radius:8px}.CALL{color:#0f0}.PUT{color:#f44}</style></head><body>
<h2>🔓 Analyzer LARGO - 15s - Inizio Test</h2><p>Partiamo largo (8-12 segnali/giorno) - Aggiorna ogni 15s</p><button onclick=load()>Aggiorna</button><div id=l></div>
<audio id=b src=https://cdn.pixabay.com/audio/2022/03/10/audio_1c8c9a0727.mp3></audio>
<script>async function load(){let r=await fetch('/api/signals');let d=await r.json();let c=document.getElementById('l');c.innerHTML='';if(!d.length){c.innerHTML='<p>Nessun segnale in questo momento, ricontrollo ogni 15s...</p>';return} d.forEach(s=>{let e=document.createElement('div');e.className='card';e.innerHTML=`<b>${s.coppia}</b> ${s.lavoro} - ${s.ora}<br><h2 class=${s.dir}>${s.dir}</h2>Scadenza: <b>${s.scadenza}</b> | Alt ${s.scadenza_30}<br>Trend ${s.trend1h} RSI ${s.rsi}`;c.appendChild(e)});document.getElementById('b').play()}load();setInterval(load,15000)</script></body></html>"""

@app.route('/')
def home(): return PAGE
@app.route('/api/signals')
def sig():
    try: return jsonify(analizza_tutto())
    except Exception as e: return jsonify({"error":str(e)}),500
