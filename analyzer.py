from flask import Flask, jsonify
import yfinance as yf
from curl_cffi import requests as cffi_requests
import pandas as pd
from datetime import datetime
import pytz, os, time as tm

app = Flask(__name__)
ROMA = pytz.timezone("Europe/Rome")
_YF_SESSION = cffi_requests.Session(impersonate="chrome")
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","AUDCHF=X","CHFJPY=X","CADCHF=X","EURNZD=X"]
STORICO1, STORICO2, cooldown1, cooldown2, pending1, pending2 = [], [], {}, {}, [], []

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def atr(df,p=14):
    tr=pd.concat([df['High']-df['Low'],abs(df['High']-df['Close'].shift()),abs(df['Low']-df['Close'].shift())],axis=1).max(axis=1)
    return tr.rolling(p).mean()

# LAVORO 2 - PIN BAR PULITA GIUSTISSIMA
def is_pin_bar(o,h,l,c):
    body = abs(c-o)
    rng = h-l
    if rng==0 or body==0: return None
    upper = h - max(o,c)
    lower = min(o,c) - l
    # PIN BAR PULITA: stoppino 2.5x il body, body < 30% del range
    if body > rng*0.30: return None
    if upper >= body*2.5 and lower <= body*0.8 and body>0: # Bearish pin (rifiuto alto)
        return "BEAR_PIN"
    if lower >= body*2.5 and upper <= body*0.8 and body>0: # Bullish pin (rifiuto basso)
        return "BULL_PIN"
    return None

def scan():
    global STORICO1, STORICO2, pending1, pending2
    now=datetime.now(ROMA)
    if now.weekday()>=5 or (now.weekday()==4 and now.hour>=23): return [], []
    pending1=[p for p in pending1 if tm.time()-p['time']<3600]
    pending2=[p for p in pending2 if tm.time()-p['time']<3600]
    nuovi1, nuovi2 = [], []

    for sym in PAIRS:
        if len(nuovi1)>=2 and len(nuovi2)>=2: break
        clean=sym.replace("=X","")
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
            last=df.iloc[-1]; prev=df.iloc[-2]
            price=float(last['Close']); e50=float(last['e50']); e200=float(last['e200']); rsi_v=float(last['rsi'])
            e20=float(last['e20'])
            o=float(last['Open']); h=float(last['High']); l=float(last['Low']); c=float(last['Close'])

            # ===== LAVORO 1 - V68 75% =====
            if clean not in cooldown1 or tm.time()-cooldown1[clean]>=5400:
                if not any(p['symbol']==clean for p in pending1):
                    if float(last['atr'])>=float(last['atr_ma'])*0.75 and float(last['atr'])<=float(last['atr_ma'])*1.85:
                        if abs(price-e20)/price<=0.0016 and abs(price-e200)/price>=0.0012:
                            e20_slope=float(df['e20'].iloc[-1]-df['e20'].iloc[-4])
                            is_green=c>o
                            sig1=None
                            if e50>e200 and price>e200 and e20>e50 and e20_slope>0 and 32<=rsi_v<=42 and is_green: sig1="BUY"
                            if e50<e200 and price<e200 and e20<e50 and e20_slope<0 and 58<=rsi_v<=68 and not is_green: sig1="SELL"
                            if sig1:
                                s={"coppia":clean,"dir":sig1,"rsi":int(rsi_v),"entry":round(price,5),"ora":now.strftime("%H:%M:%S"),"data":now.strftime("%d/%m %H:%M"),"id":f"L1{clean}{now.strftime('%H%M%S')}","tipo":"L1 TREND"}
                                STORICO1.append(s); nuovi1.append(s); pending1.append({"symbol":clean,"time":tm.time()}); cooldown1[clean]=tm.time()

            # ===== LAVORO 2 - PIN BAR PULITA =====
            if clean not in cooldown2 or tm.time()-cooldown2[clean]>=5400:
                if not any(p['symbol']==clean for p in pending2):
                    pin = is_pin_bar(o,h,l,c)
                    if pin:
                        # PIN BAR GIUSTA: deve essere su EMA200 o EMA50 + RSI non estremo
                        near_ema = abs(price-e20)/price<=0.0015 or abs(price-e50)/price<=0.0018
                        if near_ema and 35<=rsi_v<=65:
                            sig2=None
                            if pin=="BULL_PIN" and price>e200: sig2="BUY PIN"
                            if pin=="BEAR_PIN" and price<e200: sig2="SELL PIN"
                            if sig2:
                                s={"coppia":clean,"dir":sig2,"rsi":int(rsi_v),"entry":round(price,5),"ora":now.strftime("%H:%M:%S"),"data":now.strftime("%d/%m %H:%M"),"id":f"L2{clean}{now.strftime('%H%M%S')}","tipo":"L2 PIN"}
                                STORICO2.append(s); nuovi2.append(s); pending2.append({"symbol":clean,"time":tm.time()}); cooldown2[clean]=tm.time()

        except: continue
    return nuovi1, nuovi2

@app.route('/api/signals')
def api():
    now=datetime.now(ROMA)
    if now.weekday()>=5 or (now.weekday()==4 and now.hour>=23):
        return jsonify({"ora":now.strftime("%H:%M:%S"),"storico1":STORICO1[-20:][::-1],"storico2":STORICO2[-20:][::-1],"nuovi1":[],"nuovi2":[],"status":"🔴 CHIUSO"})
    n1,n2=scan()
    return jsonify({"ora":now.strftime("%H:%M:%S"),"storico1":STORICO1[-30:][::-1],"storico2":STORICO2[-30:][::-1],"nuovi1":n1,"nuovi2":n2,"status":"🟢 DOPPIO LAVORO LIVE"})

@app.route('/')
def home():
    return """<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>DOPPIO</title><style>body{background:#000;color:#fff;font-family:Arial;margin:0}.header{background:#111;padding:12px;border-bottom:3px solid #0f0}h2{margin:0;color:#0f0;font-size:14px}.container{padding:10px}.timer{font-size:28px;color:#ff0;text-align:center;background:#222;padding:10px;border-radius:10px;margin:8px 0}button{width:100%;padding:14px;border:none;border-radius:12px;font-weight:bold;margin:5px 0}#unlock{background:#0f0;color:#000}.card{border:2px solid #0f0;padding:10px;margin:6px 0;border-radius:10px;background:#151515}.SELL{border-color:#f33;color:#f88}.BUY{color:#0f0}.PIN{border-color:#ff0}.row{display:flex;justify-content:space-between;font-size:11px;padding:3px 0;border-bottom:1px solid #222}.box{background:#111;padding:8px;border-radius:10px;margin:8px 0}</style></head><body><div class=header><h2>🟢 DOPPIO LAVORO - L1 TREND 75% + L2 PIN BAR</h2></div><div class=container><div id=timer class=timer>00:00:00</div><div id=status style=text-align:center;background:#222;padding:6px;border-radius:8px;font-size:11px></div><button id=unlock onclick="unlockAudio()">🔊 SUONO</button><div id=l></div><div class=box><b>🔵 LAVORO 1 - TREND 75%</b><div id=storico1>Vuoto</div></div><div class=box style=border:1px solid #ff0><b>🟡 LAVORO 2 - PIN BAR PULITA</b><div id=storico2>Vuoto</div></div><button onclick="testAudio()" style="background:#333;color:#fff">🔔 TEST</button></div><script>let audioCtx=null,audioOn=false,seen=new Set(),first=true;function unlockAudio(){try{audioCtx=new(window.AudioContext||window.webkitAudioContext)();audioCtx.resume();audioOn=true;document.getElementById('unlock').innerText='✅ SUONO ON';}catch(e){}}function testAudio(){if(!audioOn){unlockAudio();setTimeout(testAudio,300);return;}let o=audioCtx.createOscillator();let g=audioCtx.createGain();o.connect(g);g.connect(audioCtx.destination);o.frequency.value=880;g.gain.value=0.3;o.start();setTimeout(()=>o.stop(),400);}function alarm(){if(!audioOn)return;for(let i=0;i<2;i++)setTimeout(testAudio,i*500);}async function load(){try{let r=await fetch('/api/signals');let d=await r.json();document.getElementById('timer').innerText=d.ora;document.getElementById('status').innerText=d.status;let h1=document.getElementById('storico1');if(!d.storico1||d.storico1.length==0)h1.innerHTML='Vuoto L1';else{let html='';d.storico1.forEach(s=>{html+=`<div class=row><span>${s.data} ${s.coppia}</span><span><b>${s.dir}</b> RSI${s.rsi}</span></div>`});h1.innerHTML=html;}let h2=document.getElementById('storico2');if(!d.storico2||d.storico2.length==0)h2.innerHTML='Vuoto L2 - attendo pin pulita';else{let html='';d.storico2.forEach(s=>{html+=`<div class=row><span>${s.data} ${s.coppia}</span><span><b>${s.dir}</b> RSI${s.rsi}</span></div>`});h2.innerHTML=html;}let all=[...(d.nuovi1||[]),...(d.nuovi2||[])];all.forEach(s=>{if(!seen.has(s.id)){seen.add(s.id);if(!first){document.getElementById('l').innerHTML=`<div class=card ${s.dir.includes('PIN')?'PIN':s.dir}><b>${s.tipo} ${s.coppia} ${s.dir}</b><br>${s.data} RSI${s.rsi} ${s.entry}</div>`+document.getElementById('l').innerHTML;alarm();}}});if(first){[...(d.storico1||[]),...(d.storico2||[])].forEach(s=>seen.add(s.id));first=false;}}catch(e){}}setInterval(load,8000);load();</script></body></html>"""

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
