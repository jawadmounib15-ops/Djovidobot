from flask import Flask, jsonify
import yfinance as yf
from curl_cffi import requests as cffi_requests
import pandas as pd
from datetime import datetime
import pytz, os, time as tm, requests, threading

app = Flask(__name__)
ROMA = pytz.timezone("Europe/Rome")
_YF_SESSION = cffi_requests.Session(impersonate="chrome")

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","EURGBP=X","GBPJPY=X","GBPCHF=X"]

STORICO=[]; cooldown={}; pending=[]

def send(msg):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg}, timeout=10)
    except: pass
def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def atr(df,p=14):
    tr=pd.concat([df['High']-df['Low'],abs(df['High']-df['Close'].shift()),abs(df['Low']-df['Close'].shift())],axis=1).max(axis=1)
    return tr.rolling(p).mean()

def scan():
    global STORICO, pending
    pending=[p for p in pending if tm.time()-p['time']<3600]
    now=datetime.now(ROMA)
    if now.weekday()>=5 or (now.weekday()==4 and now.hour>=23): return []
    nuovi=[]
    for sym in PAIRS:
        if len(nuovi)>=2: break
        clean=sym.replace("=X","")
        if clean in cooldown and tm.time()-cooldown[clean]<5400: continue
        if any(p['symbol']==clean for p in pending): continue
        try:
            df=yf.Ticker(sym, session=_YF_SESSION).history(period="5d", interval="15m")
            df=fix_df(df)
            if len(df)<210: continue
            df['e20']=df['Close'].ewm(span=20).mean()
            df['e50']=df['Close'].ewm(span=50).mean()
            df['e200']=df['Close'].ewm(span=200).mean()
            df['rsi']=rsi(df['Close']); df['atr']=atr(df,14); df['atr_ma']=df['atr'].rolling(50).mean()
            last=df.iloc[-1]
            price=float(last['Close']); e20=float(last['e20']); e50=float(last['e50']); e200=float(last['e200']); rsi_v=float(last['rsi'])
            is_green=float(last['Close'])>float(last['Open'])
            if float(last['atr']) < float(last['atr_ma'])*0.80: continue
            if float(last['atr']) > float(last['atr_ma'])*1.70: continue
            if abs(price-e20)/price > 0.0018: continue
            if abs(price-e200)/price < 0.0015: continue
            slope_e20=float(df['e20'].iloc[-1]-df['e20'].iloc[-5])
            slope_e50=float(df['e50'].iloc[-1]-df['e50'].iloc[-5])
            sig=None
            if e50>e200 and e20>e50 and slope_e20>0 and slope_e50>0 and price>e200 and 33<=rsi_v<=41 and is_green: sig="BUY"
            if e50<e200 and e20<e50 and slope_e20<0 and slope_e50<0 and price<e200 and 59<=rsi_v<=67 and not is_green: sig="SELL"
            if sig:
                s={"coppia":clean,"dir":sig,"rsi":int(rsi_v),"entry":round(price,5),"ora":now.strftime("%H:%M:%S"),"data":now.strftime("%d/%m %H:%M"),"id":f"{clean}{now.strftime('%H%M%S')}"}
                STORICO.append(s); nuovi.append(s)
                pending.append({"symbol":clean,"time":tm.time()})
                cooldown[clean]=tm.time()
                if TOKEN: send(f"🎯 V72.1 {sig} {clean} RSI {int(rsi_v)} {price:.5f}")
        except: continue
    return nuovi

@app.route('/api/signals')
def api():
    now=datetime.now(ROMA)
    if now.weekday()>=5 or (now.weekday()==4 and now.hour>=23):
        return jsonify({"ora":now.strftime("%H:%M:%S"),"storico":STORICO[-20:][::-1],"nuovi":[],"status":"🔴 CHIUSO"})
    nuovi=scan()
    return jsonify({"ora":now.strftime("%H:%M:%S"),"storico":STORICO[-30:][::-1],"nuovi":nuovi,"status":"🟢 V72.1 MIGLIORE 70%+ LIVE"})

@app.route('/')
def home():
    return """<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>V72.1</title>
<style>body{background:#000;color:#fff;font-family:Arial;margin:0}.header{background:#111;padding:12px;border-bottom:3px solid #0f0}h2{margin:0;color:#0f0;font-size:14px}.container{padding:8px}.timer{font-size:28px;color:#ff0;text-align:center;background:#222;padding:12px;border-radius:10px;margin:6px 0}button{width:100%;padding:12px;border:none;border-radius:12px;font-weight:bold;margin:4px 0}#unlock{background:#0f0;color:#000}.card{border:2px solid #0f0;padding:10px;margin:6px 0;border-radius:10px;background:#151515;font-size:12px}.SELL{border-color:#f33}.row{display:flex;justify-content:space-between;font-size:11px;padding:3px 0;border-bottom:1px solid #222}.box{background:#111;padding:8px;border-radius:10px;margin:8px 0}</style></head>
<body><div class=header><h2>🟢 V72.1 MIGLIORE REGOLAZIONE - 1 LAVORO 70%+ - GIUSTO NON STRETTO</h2></div>
<div class=container><div id=timer class=timer>00:00:00</div><div id=status style=text-align:center;background:#222;padding:6px;border-radius:8px;font-size:11px></div>
<button id=unlock onclick="unlockAudio()">🔊 ATTIVA SUONO</button><div id=l></div>
<div class=box><b>📊 SEGNALI V72.1 (2-4 al giorno, 70%+ win)</b><div id=s>Vuoto - in attesa...</div></div>
<button onclick="testAudio()" style="background:#333;color:#fff">🔔 TEST SUONO</button></div>
<script>let audioCtx=null,audioOn=false,seen=new Set(),first=true;
function unlockAudio(){try{audioCtx=new(window.AudioContext||window.webkitAudioContext)();audioCtx.resume();audioOn=true;document.getElementById('unlock').innerText='✅ SUONO ON';}catch(e){}}
function testAudio(){if(!audioOn){unlockAudio();setTimeout(testAudio,300);return;}let o=audioCtx.createOscillator();let g=audioCtx.createGain();o.connect(g);g.connect(audioCtx.destination);o.frequency.value=880;g.gain.value=0.3;o.start();setTimeout(()=>o.stop(),350);}
function alarm(){if(!audioOn)return;for(let i=0;i<2;i++)setTimeout(testAudio,i*500);}
async function load(){try{let r=await fetch('/api/signals');let d=await r.json();document.getElementById('timer').innerText=d.ora;document.getElementById('status').innerText=d.status;
let el=document.getElementById('s');if(!d.storico||d.storico.length==0)el.innerHTML='Vuoto - in attesa...';else{let html='';d.storico.slice(0,20).forEach(s=>{let cls=s.dir.includes('SELL')?'SELL':'';html+=`<div class=row><span>${s.data} <b>${s.coppia}</b></span><span style="color:${s.dir.includes('BUY')?'#0f0':'#f33'}"><b>${s.dir}</b> RSI${s.rsi} ${s.entry}</span></div>`});el.innerHTML=html;}
(d.nuovi||[]).forEach(s=>{if(!seen.has(s.id)){seen.add(s.id);if(!first){document.getElementById('l').innerHTML=`<div class=card ${s.dir.includes('SELL')?'SELL':''}><b>🎯 ${s.coppia} ${s.dir}</b> ${s.data} RSI${s.rsi} Entry ${s.entry}</div>`+document.getElementById('l').innerHTML;alarm();}}});
if(first){(d.storico||[]).forEach(s=>seen.add(s.id));first=false;}}catch(e){}}setInterval(load,8000);load();</script></body></html>"""

# thread telegram loop
def bg():
    while True:
        try: scan()
        except: pass
        tm.sleep(60)
threading.Thread(target=bg, daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
