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
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","EURGBP=X","GBPJPY=X","GBPCHF=X","EURAUD=X","AUDJPY=X"]

STORICO=[]; cooldown={}; pending=[]

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
    nuovi=[]
    for sym in PAIRS:
        if len(nuovi)>=2: break
        clean=sym.replace("=X","")
        if clean in cooldown and tm.time()-cooldown[clean]<3600: continue # prima 5400 -> 3600 più segnali
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
            if float(last['atr']) < float(last['atr_ma'])*0.75: continue
            if float(last['atr']) > float(last['atr_ma'])*1.85: continue # più largo
            if abs(price-e20)/price > 0.0022: continue # prima 0.0018 -> 0.0022 più segnali
            if abs(price-e200)/price < 0.0010: continue # prima 0.0015 -> 0.0010
            slope_e20=float(df['e20'].iloc[-1]-df['e20'].iloc[-5])
            sig=None
            if e50>e200 and price>e200 and slope_e20>0 and 32<=rsi_v<=44 and is_green: sig="BUY" # RSI 33-41 -> 32-44 più aperto
            if e50<e200 and price<e200 and slope_e20<0 and 56<=rsi_v<=68 and not is_green: sig="SELL" # 59-67 -> 56-68
            if sig:
                s={"coppia":clean,"dir":sig,"rsi":int(rsi_v),"entry":round(price,5),"ora":now.strftime("%H:%M:%S"),"data":now.strftime("%d/%m %H:%M"),"id":f"{clean}{now.strftime('%H%M%S')}"}
                STORICO.append(s); nuovi.append(s)
                pending.append({"symbol":clean,"time":tm.time()})
                cooldown[clean]=tm.time()
                try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":f"🎯 V72.2 {sig} {clean} RSI {int(rsi_v)}"}, timeout=5)
                except: pass
        except: continue
    return nuovi

@app.route('/api/signals')
def api():
    now=datetime.now(ROMA)
    nuovi=scan()
    return jsonify({"ora":now.strftime("%H:%M:%S"),"storico":STORICO[-30:][::-1],"nuovi":nuovi,"status":f"🟢 V72.2 LIVE - {len(STORICO)} totali"})

@app.route('/')
def home():
    return """<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>V72.2</title>
<style>body{background:#000;color:#fff;font-family:Arial;margin:0}.header{background:#111;padding:12px;border-bottom:3px solid #0f0}h2{margin:0;color:#0f0;font-size:13px}.container{padding:8px}.timer{font-size:30px;color:#ff0;text-align:center;background:#222;padding:12px;border-radius:10px;margin:6px 0}button{width:100%;padding:13px;border:none;border-radius:12px;font-weight:bold;margin:4px 0}#unlock{background:#0f0;color:#000}.card{border:2px solid #0f0;padding:10px;margin:6px 0;border-radius:10px;background:#151515;font-size:12px}.row{display:flex;justify-content:space-between;font-size:11px;padding:4px 0;border-bottom:1px solid #222}.box{background:#111;padding:8px;border-radius:10px;margin:8px 0}</style></head>
<body><div class=header><h2>🟢 V72.2 FIX - TIMER OK - GIUSTO APERTO</h2></div>
<div class=container><div id=timer class=timer>12:44:00</div><div id=status style=text-align:center;background:#222;padding:6px;border-radius:8px;font-size:11px>Caricamento...</div>
<button id=unlock onclick="unlockAudio()">🔊 SUONO ON</button><div id=l></div>
<div class=box><b>📊 SEGNALI V72.2 (3-6 al giorno)</b><div id=s>Vuoto - in attesa...</div></div>
<button onclick="testAudio()" style="background:#333;color:#fff">🔔 TEST SUONO</button></div>
<script>
let audioCtx=null,audioOn=false,seen=new Set(),first=true;
// TIMER LOCALE FIX - non dipende più dal server
setInterval(()=>{let n=new Date();let h=String(n.getHours()).padStart(2,'0');let m=String(n.getMinutes()).padStart(2,'0');let s=String(n.getSeconds()).padStart(2,'0');document.getElementById('timer').innerText=h+':'+m+':'+s;},1000);
function unlockAudio(){try{audioCtx=new(window.AudioContext||window.webkitAudioContext)();audioCtx.resume();audioOn=true;document.getElementById('unlock').innerText='✅ SUONO ON';document.getElementById('unlock').style.background='#0f0';}catch(e){}}
function testAudio(){if(!audioOn){unlockAudio();setTimeout(testAudio,300);return;}let o=audioCtx.createOscillator();let g=audioCtx.createGain();o.connect(g);g.connect(audioCtx.destination);o.frequency.value=880;g.gain.value=0.3;o.start();setTimeout(()=>o.stop(),350);}
function alarm(){if(!audioOn)return;for(let i=0;i<2;i++)setTimeout(testAudio,i*500);}
async function load(){try{let r=await fetch('/api/signals');let d=await r.json();document.getElementById('status').innerText=d.status;
let el=document.getElementById('s');if(!d.storico||d.storico.length==0)el.innerHTML='Vuoto - in attesa... primi segnali entro 15 min';else{let html='';d.storico.slice(0,20).forEach(s=>{html+=`<div class=row><span>${s.data} <b>${s.coppia}</b></span><span style="color:${s.dir.includes('BUY')?'#0f0':'#f33'}"><b>${s.dir}</b> RSI${s.rsi} ${s.entry}</span></div>`});el.innerHTML=html;}
(d.nuovi||[]).forEach(s=>{if(!seen.has(s.id)){seen.add(s.id);if(!first){document.getElementById('l').innerHTML=`<div class=card><b>🎯 ${s.coppia} ${s.dir}</b> ${s.data} RSI${s.rsi} Entry ${s.entry}</div>`+document.getElementById('l').innerHTML;alarm();}}});
if(first){(d.storico||[]).forEach(s=>seen.add(s.id));first=false;}}catch(e){document.getElementById('status').innerText='⏳ Connessione...';}}setInterval(load,10000);load();</script></body></html>"""

threading.Thread(target=lambda: [tm.sleep(60) or scan() for _ in iter(int,1)], daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
