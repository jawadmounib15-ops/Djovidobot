from flask import Flask, jsonify
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz, time as time_module, os

app = Flask(__name__)
ROMA = pytz.timezone("Europe/Rome")
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURNZD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","GBPCAD=X","AUDJPY=X","AUDCAD=X","AUDCHF=X","CADJPY=X","CHFJPY=X","CADCHF=X"]
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
def stochastic(df):
    lo=df['Low'].rolling(14).min(); hi=df['High'].rolling(14).max()
    return 100*((df['Close']-lo)/(hi-lo))

def scan():
    global STORICO, pending
    now=datetime.now(ROMA)
    if now.weekday()>=5 or (now.weekday()==4 and now.hour>=23): return []
    pending=[p for p in pending if time_module.time()-p['time']<3600]
    nuovi=[]; c=0
    for sym in PAIRS:
        if c>=3: break
        clean=sym.replace("=X","")
        if clean in cooldown and time_module.time()-cooldown[clean]<5400: continue
        try:
            df=yf.download(sym, period="5d", interval="15m", progress=False, auto_adjust=True)
            df=fix_df(df)
            if len(df)<210: continue
            df['e20']=df['Close'].ewm(span=20).mean()
            df['e200']=df['Close'].ewm(span=200).mean()
            df['rsi']=rsi(df['Close'])
            df['atr']=atr(df,14)
            df['atr_ma50']=df['atr'].rolling(50).mean()
            df['stoch']=stochastic(df)
            last=df.iloc[-1]
            price=float(last['Close']); rsi_v=float(last['rsi']); stoch_k=float(last['stoch'])
            e20=float(last['e20']); e200=float(last['e200'])
            if last['atr'] < last['atr_ma50']*0.60 or last['atr'] > last['atr_ma50']*1.95: continue
            if abs(price-e20)/price >= 0.0022: continue
            if abs(price-e200)/price < 0.0008: continue
            e20_slope=float(df['e20'].iloc[-1]-df['e20'].iloc[-3])
            is_green=float(df['Close'].iloc[-1])>float(df['Open'].iloc[-1])
            is_red=not is_green
            sig=None
            if price>e200 and e20>e200 and e20_slope>=0 and 27<=rsi_v<=42 and 10<=stoch_k<=35 and is_green: sig="BUY"
            if price<e200 and e20<e200 and e20_slope<=0 and 58<=rsi_v<=73 and 65<=stoch_k<=90 and is_red: sig="SELL"
            if sig and not any(p['symbol']==clean for p in pending):
                s={"coppia":clean,"dir":sig,"rsi":int(rsi_v),"stoch":int(stoch_k),"entry":round(price,5),"ora":now.strftime("%H:%M:%S"),"data":now.strftime("%d/%m %H:%M:%S"),"id":f"{clean}{now.strftime('%H%M%S')}"}
                STORICO.append(s)
                if len(STORICO)>100: STORICO=STORICO[-100:]
                pending.append({"symbol":clean,"time":time_module.time()})
                cooldown[clean]=time_module.time()
                nuovi.append(s); c+=1
        except: continue
    return nuovi

@app.route('/api/signals')
def api():
    now=datetime.now(ROMA)
    if now.weekday()>=5 or (now.weekday()==4 and now.hour>=23):
        return jsonify({"ora":now.strftime("%H:%M:%S"),"storico":STORICO[-30:][::-1],"nuovi":[],"status":"🔴 CHIUSO"})
    return jsonify({"ora":now.strftime("%H:%M:%S"),"storico":STORICO[-30:][::-1],"nuovi":scan(),"status":"🟢 V64 75% LIVE"})

@app.route('/')
def home():
    return """<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>V64</title><style>body{background:#000;color:#fff;font-family:Arial;margin:0}.header{background:#111;padding:14px;border-bottom:3px solid #0f0}h2{margin:0;color:#0f0;font-size:15px}.timer{font-size:32px;color:#ff0;text-align:center;background:#222;padding:12px;border-radius:12px;margin:10px 0}button{width:100%;padding:16px;border:none;border-radius:14px;font-weight:bold;margin:6px 0}#unlock{background:#0f0;color:#000}.card{border:3px solid #0f0;padding:12px;margin:10px 0;border-radius:12px;background:#151515}.SELL{color:#f33;border-color:#f33}.BUY{color:#0f0}.row{display:flex;justify-content:space-between;font-size:11px;padding:4px 0;border-bottom:1px solid #222}.storico{background:#111;padding:8px;border-radius:10px}</style></head><body><div class=header><h2>🟢 V64 75% SBLOCCATO</h2></div><div style=padding:10px><div id=timer class=timer>00:00:00</div><div id=status style=text-align:center;font-size:12px;padding:6px;background:#222;border-radius:8px;margin:5px 0></div><button id=unlock onclick="unlockAudio()">🔊 AUDIO</button><div id=l></div><div class=storico><div id=storico>Carico...</div></div><button onclick="testAudio()" style="background:#333;color:#fff">🔔 TEST</button></div><script>let audioCtx=null,audioOn=false,seen=new Set(),first=true;function unlockAudio(){try{audioCtx=new(window.AudioContext||window.webkitAudioContext)();audioCtx.resume();audioOn=true;document.getElementById('unlock').innerText='✅ AUDIO ON';}catch(e){}}function testAudio(){if(!audioOn){unlockAudio();setTimeout(testAudio,300);return;}let o=audioCtx.createOscillator();let g=audioCtx.createGain();o.connect(g);g.connect(audioCtx.destination);o.frequency.value=880;g.gain.value=0.2;o.start();setTimeout(()=>o.stop(),300);}function alarm(){if(!audioOn)return;testAudio();}async function load(){try{let r=await fetch('/api/signals');let d=await r.json();document.getElementById('timer').innerText=d.ora;document.getElementById('status').innerText=d.status;let h=document.getElementById('storico');if(!d.storico||d.storico.length==0)h.innerHTML='Vuoto - in attesa';else{let html='';d.storico.forEach(s=>{html+=`<div class=row><span>${s.data} ${s.coppia}</span><span><b class=${s.dir}>${s.dir}</b> RSI${s.rsi}</span></div>`});h.innerHTML=html;}if(d.nuovi&&d.nuovi.length>0){d.nuovi.forEach(s=>{if(!seen.has(s.id)){seen.add(s.id);if(!first){document.getElementById('l').innerHTML=`<div class=card ${s.dir}><b>${s.coppia} ${s.dir}</b> ${s.data}<br>RSI${s.rsi} STO${s.stoch} ${s.entry}</div>`+document.getElementById('l').innerHTML;alarm();}}});}if(first){d.storico.forEach(s=>seen.add(s.id));first=false;}}catch(e){}}setInterval(load,5000);load();</script></body></html>"""

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
