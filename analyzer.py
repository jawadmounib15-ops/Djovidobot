from flask import Flask, jsonify
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
import time as time_module
import os
from curl_cffi import requests as cffi_requests

app = Flask(__name__)
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X",
         "EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURNZD=X",
         "GBPJPY=X","GBPCHF=X","GBPAUD=X","GBPCAD=X",
         "AUDJPY=X","AUDCAD=X","AUDCHF=X",
         "CADJPY=X","CHFJPY=X","CADCHF=X"]

STORICO, cooldown, pending = [], {}, []

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

def stochastic(df):
    lo=df['Low'].rolling(14).min(); hi=df['High'].rolling(14).max()
    return 100*((df['Close']-lo)/(hi-lo))

def get_df(s):
    try:
        df=yf.Ticker(s, session=session).history(period="5d", interval="15m")
        df=fix_df(df)
        return df if len(df)>=210 else None
    except: return None

def scan():
    global STORICO, pending
    now=datetime.now(ROMA)
    # FIX 23:00
    if now.weekday()==5 or now.weekday()==6 or (now.weekday()==4 and now.hour>=23):
        return []
    pending = [p for p in pending if time_module.time()-p['time']<3600]
    nuovi=[]; c=0
    for sym in PAIRS:
        if c>=4: break
        clean=sym.replace("=X","")
        if clean in cooldown and time_module.time()-cooldown[clean]<5400: continue
        try:
            df=get_df(sym)
            if df is None: continue
            df['e20']=df['Close'].ewm(span=20).mean()
            df['e200']=df['Close'].ewm(span=200).mean()
            df['rsi']=rsi(df['Close'])
            df['atr']=atr(df,14)
            df['atr_ma50']=df['atr'].rolling(50).mean()
            df['stoch']=stochastic(df)
            last=df.iloc[-1]
            price=float(last['Close']); rsi_v=float(last['rsi']); stoch_k=float(last['stoch'])
            e20=float(last['e20']); e200=float(last['e200'])

            # EQUILIBRATO 10W 4L
            if last['atr'] < last['atr_ma50']*0.65 or last['atr'] > last['atr_ma50']*1.85: continue
            if abs(price-e20)/price >= 0.0018: continue
            if abs(price-e200)/price < 0.0010: continue
            e20_slope = float(df['e20'].iloc[-1] - df['e20'].iloc[-3])
            if abs(e20_slope) < 0.00001: continue

            sig=None
            if price>e200 and e20>e200 and 28<=rsi_v<=40 and 12<=stoch_k<=32 and e20_slope>0:
                sig="BUY"
            if price<e200 and e20<e200 and 60<=rsi_v<=72 and 68<=stoch_k<=88 and e20_slope<0:
                sig="SELL"

            if sig and not any(p['symbol']==clean for p in pending):
                s={"coppia":clean,"dir":sig,"rsi":int(rsi_v),"stoch":int(stoch_k),"entry":round(price,5),"ora":now.strftime("%H:%M:%S"),"data":now.strftime("%d/%m %H:%M:%S"),"id":f"{clean}{now.strftime('%H%M%S')}"}
                STORICO.append(s)
                if len(STORICO)>100: STORICO=STORICO[-100:]
                pending.append({"symbol":clean,"time":time_module.time()})
                cooldown[clean]=time_module.time()
                nuovi.append(s)
                c+=1
        except: continue
    return nuovi

@app.route('/api/signals')
def api():
    now=datetime.now(ROMA)
    if now.weekday() in [5,6] or (now.weekday()==4 and now.hour>=23):
        return jsonify({"ora":now.strftime("%H:%M:%S"),"storico":STORICO[-30:][::-1],"nuovi":[],"status":"🔴 CHIUSO"})
    return jsonify({"ora":now.strftime("%H:%M:%S"),"storico":STORICO[-30:][::-1],"nuovi":scan(),"status":"🟢 V62.5 10W-4L"})

HTML="""<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>V62.5 10W-4L</title><style>body{background:#000;color:#fff;font-family:Arial;margin:0}.header{background:#111;padding:14px;border-bottom:3px solid #0f0}h2{margin:0;color:#0f0;font-size:15px}.sub{color:#ff0;font-size:11px}.container{padding:10px}.timer{font-size:32px;color:#ff0;text-align:center;background:#222;padding:12px;border-radius:12px;margin:10px 0}button{width:100%;padding:16px;border:none;border-radius:14px;font-weight:bold;margin:6px 0}#unlock{background:#0f0;color:#000}.card{border:3px solid #0f0;padding:12px;margin:10px 0;border-radius:12px;background:#151515}.SELL{color:#f33;border-color:#f33}.BUY{color:#0f0}.row{display:flex;justify-content:space-between;font-size:11px;padding:4px 0;border-bottom:1px solid #222}.storico{background:#111;padding:8px;border-radius:10px}</style></head><body><div class=header><h2>🟢 V62.5 EQUILIBRATO 10W-4L</h2><div class=sub>RSI 28-40/60-72 STO 12-32/68-88 + slope + fix 23:00</div></div><div class=container><div id=timer class=timer>00:00:00</div><div id=status style=text-align:center;font-size:12px;padding:6px;background:#222;border-radius:8px;margin:5px 0></div><button id=unlock onclick="unlockAudio()">🔊 AUDIO</button><div id=l></div><div class=storico><div id=storico>Vuoto</div></div><button onclick="testAudio()" style="background:#333;color:#fff">🔔 TEST</button></div><script>let audioCtx=null,audioOn=false,seen=new Set(),first=true;function unlockAudio(){try{audioCtx=new(window.AudioContext||window.webkitAudioContext)();audioCtx.resume();audioOn=true;document.getElementById('unlock').innerText='✅ AUDIO ON';}catch(e){}}function testAudio(){if(!audioOn){unlockAudio();setTimeout(testAudio,300);return;}let o=audioCtx.createOscillator();let g=audioCtx.createGain();o.connect(g);g.connect(audioCtx.destination);o.frequency.value=880;g.gain.value=0.2;o.start();setTimeout(()=>o.stop(),300);}function alarm(){if(!audioOn)return;testAudio();}async function load(){try{let r=await fetch('/api/signals');let d=await r.json();document.getElementById('timer').innerText=d.ora;document.getElementById('status').innerText=d.status;let h=document.getElementById('storico');if(!d.storico||d.storico.length==0)h.innerHTML='Vuoto - in attesa segnali';else{let html='';d.storico.forEach(s=>{html+=`<div class=row><span>${s.data} ${s.coppia}</span><span><b class=${s.dir}>${s.dir}</b> RSI${s.rsi} STO${s.stoch}</span></div>`});h.innerHTML=html;}if(d.nuovi&&d.nuovi.length>0){d.nuovi.forEach(s=>{if(!seen.has(s.id)){seen.add(s.id);if(!first){document.getElementById('l').innerHTML=`<div class=card ${s.dir}><b>${s.coppia} ${s.dir}</b> ${s.data}<br>RSI${s.rsi} STO${s.stoch} ${s.entry}</div>`+document.getElementById('l').innerHTML;alarm();}}});}if(first){d.storico.forEach(s=>seen.add(s.id));first=false;}}catch(e){}}setInterval(load,5000);load();</script></body></html>"""
@app.route('/')
def home(): return HTML
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
