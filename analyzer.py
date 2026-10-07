from flask import Flask, jsonify
import yfinance as yf
from curl_cffi import requests as cffi_requests
import pandas as pd
from datetime import datetime
import pytz, os, time as tm

app = Flask(__name__)
ROMA = pytz.timezone("Europe/Rome")
_YF_SESSION = cffi_requests.Session(impersonate="chrome")
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","AUDCHF=X","CHFJPY=X"]
STORICO, cooldown, pending = [], {}, []

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
    now=datetime.now(ROMA)
    if now.weekday()>=5 or (now.weekday()==4 and now.hour>=23): return []
    # SCADENZA SEGNALE: 60 min
    pending=[p for p in pending if tm.time()-p['time']<3600]
    nuovi=[]; c=0
    for sym in PAIRS:
        if c>=3: break
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
            df['rsi']=rsi(df['Close'])
            df['atr']=atr(df,14)
            df['atr_ma']=df['atr'].rolling(50).mean()
            last=df.iloc[-1]
            price=float(last['Close']); e50=float(last['e50']); e200=float(last['e200']); rsi_v=float(last['rsi'])
            if float(last['atr']) < float(last['atr_ma'])*0.65: continue
            if abs(price-float(last['e20']))/price > 0.0022: continue
            is_green=float(last['Close'])>float(last['Open'])
            sig=None
            if e50>e200 and price>e200 and 30<=rsi_v<=45 and is_green: sig="BUY"
            if e50<e200 and price<e200 and 55<=rsi_v<=70 and not is_green: sig="SELL"
            if sig:
                s={"coppia":clean,"dir":sig,"rsi":int(rsi_v),"entry":round(price,5),"ora":now.strftime("%H:%M:%S"),"data":now.strftime("%d/%m %H:%M"),"id":f"{clean}{now.strftime('%H%M%S')}"}
                STORICO.append(s)
                if len(STORICO)>100: STORICO=STORICO[-100:]
                pending.append({"symbol":clean,"time":tm.time()})
                cooldown[clean]=tm.time()
                nuovi.append(s); c+=1
        except: continue
    return nuovi

@app.route('/api/signals')
def api():
    now=datetime.now(ROMA)
    if now.weekday()>=5 or (now.weekday()==4 and now.hour>=23):
        return jsonify({"ora":now.strftime("%H:%M:%S"),"storico":STORICO[-30:][::-1],"nuovi":[],"status":"🔴 WEEKEND CHIUSO"})
    return jsonify({"ora":now.strftime("%H:%M:%S"),"storico":STORICO[-30:][::-1],"nuovi":scan(),"status":"🟢 V67 SUONO+STORICO+SCADENZA LIVE"})

@app.route('/')
def home():
    return """<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>V67</title><style>body{background:#000;color:#fff;font-family:Arial;margin:0}.header{background:#111;padding:14px;border-bottom:3px solid #0f0}h2{margin:0;color:#0f0;font-size:15px}.sub{color:#ff0;font-size:10px}.container{padding:10px}.timer{font-size:32px;color:#ff0;text-align:center;background:#222;padding:12px;border-radius:12px;margin:10px 0}button{width:100%;padding:16px;border:none;border-radius:14px;font-weight:bold;margin:6px 0}#unlock{background:#0f0;color:#000}.card{border:3px solid #0f0;padding:12px;margin:10px 0;border-radius:12px;background:#151515}.SELL{border-color:#f33;color:#f33}.BUY{color:#0f0}.row{display:flex;justify-content:space-between;font-size:11px;padding:4px 0;border-bottom:1px solid #222}.storico{background:#111;padding:8px;border-radius:10px}</style></head><body><div class=header><h2>🟢 V67 75% - SUONO+STORICO+SCADENZA</h2><div class=sub>Scadenza 60min - Cooldown 90min - Suono allarme</div></div><div class=container><div id=timer class=timer>00:00:00</div><div id=status style=text-align:center;font-size:12px;padding:6px;background:#222;border-radius:8px;margin:5px 0></div><button id=unlock onclick="unlockAudio()">🔊 ATTIVA SUONO</button><div id=l></div><div class=storico><b>STORICO:</b><div id=storico>Carico...</div></div><button onclick="testAudio()" style="background:#333;color:#fff">🔔 TEST SUONO</button></div><script>let audioCtx=null,audioOn=false,seen=new Set(),first=true;function unlockAudio(){try{audioCtx=new(window.AudioContext||window.webkitAudioContext)();audioCtx.resume();audioOn=true;document.getElementById('unlock').innerText='✅ SUONO ATTIVO';}catch(e){}}function testAudio(){if(!audioOn){unlockAudio();setTimeout(testAudio,300);return;}let o=audioCtx.createOscillator();let g=audioCtx.createGain();o.connect(g);g.connect(audioCtx.destination);o.frequency.value=880;g.gain.value=0.3;o.start();setTimeout(()=>o.stop(),400);}function alarm(){if(!audioOn)return;for(let i=0;i<3;i++){setTimeout(testAudio,i*600);}}async function load(){try{let r=await fetch('/api/signals');let d=await r.json();document.getElementById('timer').innerText=d.ora;document.getElementById('status').innerText=d.status+' | Scadenza segnale 60min';let h=document.getElementById('storico');if(!d.storico||d.storico.length==0)h.innerHTML='Vuoto - in attesa primo segnale';else{let html='';d.storico.forEach(s=>{html+=`<div class=row><span>${s.data} ${s.coppia}</span><span><b class=${s.dir}>${s.dir}</b> RSI${s.rsi} ${s.entry}</span></div>`});h.innerHTML=html;}if(d.nuovi&&d.nuovi.length>0){d.nuovi.forEach(s=>{if(!seen.has(s.id)){seen.add(s.id);if(!first){document.getElementById('l').innerHTML=`<div class=card ${s.dir}><b>🔔 ${s.coppia} ${s.dir}</b> ${s.data}<br>RSI${s.rsi} Entry ${s.entry}<br><small>Scade tra 60min</small></div>`+document.getElementById('l').innerHTML;alarm();}}});}if(first){d.storico.forEach(s=>seen.add(s.id));first=false;}}catch(e){}}setInterval(load,8000);load();</script></body></html>"""

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
