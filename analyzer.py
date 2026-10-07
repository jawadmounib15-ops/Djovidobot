from flask import Flask, jsonify
import yfinance as yf
from curl_cffi import requests as cffi_requests
import pandas as pd
from datetime import datetime
import pytz, os, time as tm

app = Flask(__name__)
ROMA = pytz.timezone("Europe/Rome")
_YF_SESSION = cffi_requests.Session(impersonate="chrome")
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","AUDCHF=X","CHFJPY=X","CADCHF=X","EURNZD=X","AUDNZD=X"]

STORICO1,STORICO2,STORICO3,STORICO4=[],[],[],[]
cooldown1,cooldown2,cooldown3,cooldown4={},{},{},{}
pending1,pending2,pending3,pending4=[],[],[],[]

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def atr(df,p=14):
    tr=pd.concat([df['High']-df['Low'],abs(df['High']-df['Close'].shift()),abs(df['Low']-df['Close'].shift())],axis=1).max(axis=1)
    return tr.rolling(p).mean()

def is_pin_bar(o,h,l,c):
    body=abs(c-o); rng=h-l
    if rng==0 or body==0: return None
    if body>rng*0.30: return None
    upper=h-max(o,c); lower=min(o,c)-l
    if upper>=body*2.5 and lower<=body*0.8: return "BEAR_PIN"
    if lower>=body*2.5 and upper<=body*0.8: return "BULL_PIN"
    return None
def is_engulfing(o1,c1,o2,c2):
    body1=abs(c1-o1); body2=abs(c2-o2)
    if body2<body1*1.2: return None
    if c1<o1 and c2>o2 and o2<=c1 and c2>=o1: return "BULL_ENG"
    if c1>o1 and c2<o2 and o2>=c1 and c2<=o1: return "BEAR_ENG"
    return None
def is_double_bounce(df,idx):
    if idx<10: return None
    price=float(df['Close'].iloc[idx]); e200=float(df['e200'].iloc[idx])
    if abs(price-e200)/price>0.002: return None
    lows=df['Low'].iloc[idx-10:idx].nsmallest(2).values
    highs=df['High'].iloc[idx-10:idx].nlargest(2).values
    if len(lows)>=2 and abs(lows[0]-lows[1])/lows[0]<0.0008 and price>e200: return "DOUBLE_BOTTOM"
    if len(highs)>=2 and abs(highs[0]-highs[1])/highs[0]<0.0008 and price<e200: return "DOUBLE_TOP"
    return None

def scan():
    global STORICO1,STORICO2,STORICO3,STORICO4,pending1,pending2,pending3,pending4
    now=datetime.now(ROMA)
    if now.weekday()>=5 or (now.weekday()==4 and now.hour>=23): return [],[],[],[]
    pending1=[p for p in pending1 if tm.time()-p['time']<3600]
    pending2=[p for p in pending2 if tm.time()-p['time']<3600]
    pending3=[p for p in pending3 if tm.time()-p['time']<3600]
    pending4=[p for p in pending4 if tm.time()-p['time']<7200]
    n1,n2,n3,n4=[],[],[],[]
    for sym in PAIRS:
        if len(n1)>=2 and len(n2)>=2 and len(n3)>=1 and len(n4)>=1: break
        clean=sym.replace("=X","")
        try:
            df=yf.Ticker(sym, session=_YF_SESSION).history(period="5d", interval="15m")
            df=fix_df(df)
            if len(df)<210: continue
            df['e20']=df['Close'].ewm(span=20).mean()
            df['e50']=df['Close'].ewm(span=50).mean()
            df['e200']=df['Close'].ewm(span=200).mean()
            df['rsi']=rsi(df['Close']); df['atr']=atr(df,14); df['atr_ma']=df['atr'].rolling(50).mean()
            last=df.iloc[-1]; prev=df.iloc[-2]
            price=float(last['Close']); e20=float(last['e20']); e50=float(last['e50']); e200=float(last['e200']); rsi_v=float(last['rsi'])
            o=float(last['Open']); h=float(last['High']); l=float(last['Low']); c=float(last['Close'])
            is_green=c>o

            # L1 TREND 75%
            if (clean not in cooldown1 or tm.time()-cooldown1[clean]>=5400) and not any(p['symbol']==clean for p in pending1):
                if float(last['atr'])>=float(last['atr_ma'])*0.75 and float(last['atr'])<=float(last['atr_ma'])*1.85:
                    if abs(price-e20)/price<=0.0016 and abs(price-e200)/price>=0.0012:
                        slope=float(df['e20'].iloc[-1]-df['e20'].iloc[-4])
                        sig=None
                        if e50>e200 and price>e200 and e20>e50 and slope>0 and 32<=rsi_v<=42 and is_green: sig="BUY"
                        if e50<e200 and price<e200 and e20<e50 and slope<0 and 58<=rsi_v<=68 and not is_green: sig="SELL"
                        if sig:
                            s={"coppia":clean,"dir":sig,"rsi":int(rsi_v),"entry":round(price,5),"ora":now.strftime("%H:%M:%S"),"data":now.strftime("%d/%m %H:%M"),"id":f"L1{clean}{now.strftime('%H%M%S')}","tipo":"L1 TREND"}
                            STORICO1.append(s); n1.append(s); pending1.append({"symbol":clean,"time":tm.time()}); cooldown1[clean]=tm.time()

            # L2 PIN BAR 80%
            if (clean not in cooldown2 or tm.time()-cooldown2[clean]>=5400) and not any(p['symbol']==clean for p in pending2):
                pin=is_pin_bar(o,h,l,c)
                if pin and (abs(price-e20)/price<=0.0015 or abs(price-e50)/price<=0.0018) and 35<=rsi_v<=65:
                    sig="BUY PIN" if pin=="BULL_PIN" and price>e200 else "SELL PIN" if pin=="BEAR_PIN" and price<e200 else None
                    if sig:
                        s={"coppia":clean,"dir":sig,"rsi":int(rsi_v),"entry":round(price,5),"ora":now.strftime("%H:%M:%S"),"data":now.strftime("%d/%m %H:%M"),"id":f"L2{clean}{now.strftime('%H%M%S')}","tipo":"L2 PIN"}
                        STORICO2.append(s); n2.append(s); pending2.append({"symbol":clean,"time":tm.time()}); cooldown2[clean]=tm.time()

            # L3 ENGULFING 82%
            if (clean not in cooldown3 or tm.time()-cooldown3[clean]>=5400) and not any(p['symbol']==clean for p in pending3):
                eng=is_engulfing(float(prev['Open']),float(prev['Close']),o,c)
                if eng and abs(price-e20)/price<=0.0015 and 35<=rsi_v<=65:
                    sig="BUY ENG" if eng=="BULL_ENG" and price>e200 else "SELL ENG" if eng=="BEAR_ENG" and price<e200 else None
                    if sig:
                        s={"coppia":clean,"dir":sig,"rsi":int(rsi_v),"entry":round(price,5),"ora":now.strftime("%H:%M:%S"),"data":now.strftime("%d/%m %H:%M"),"id":f"L3{clean}{now.strftime('%H%M%S')}","tipo":"L3 ENGULFING"}
                        STORICO3.append(s); n3.append(s); pending3.append({"symbol":clean,"time":tm.time()}); cooldown3[clean]=tm.time()

            # L4 DOPPIO RIMBALZO 85% PIU SICURO
            if (clean not in cooldown4 or tm.time()-cooldown4[clean]>=7200) and not any(p['symbol']==clean for p in pending4):
                dbl=is_double_bounce(df,len(df)-1)
                if dbl and 38<=rsi_v<=62:
                    sig="BUY DB" if dbl=="DOUBLE_BOTTOM" else "SELL DT"
                    s={"coppia":clean,"dir":sig,"rsi":int(rsi_v),"entry":round(price,5),"ora":now.strftime("%H:%M:%S"),"data":now.strftime("%d/%m %H:%M"),"id":f"L4{clean}{now.strftime('%H%M%S')}","tipo":"L4 DOPPIO"}
                    STORICO4.append(s); n4.append(s); pending4.append({"symbol":clean,"time":tm.time()}); cooldown4[clean]=tm.time()
        except: continue
    return n1,n2,n3,n4

@app.route('/api/signals')
def api():
    now=datetime.now(ROMA)
    if now.weekday()>=5 or (now.weekday()==4 and now.hour>=23):
        return jsonify({"ora":now.strftime("%H:%M:%S"),"storico1":STORICO1[-20:][::-1],"storico2":STORICO2[-20:][::-1],"storico3":STORICO3[-20:][::-1],"storico4":STORICO4[-20:][::-1],"nuovi1":[],"nuovi2":[],"nuovi3":[],"nuovi4":[],"status":"🔴 CHIUSO"})
    n1,n2,n3,n4=scan()
    return jsonify({"ora":now.strftime("%H:%M:%S"),"storico1":STORICO1[-30:][::-1],"storico2":STORICO2[-30:][::-1],"storico3":STORICO3[-30:][::-1],"storico4":STORICO4[-30:][::-1],"nuovi1":n1,"nuovi2":n2,"nuovi3":n3,"nuovi4":n4,"status":"🟢 4 LAVORI LIVE"})

@app.route('/')
def home():
    return """<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>4 LAVORI</title><style>body{background:#000;color:#fff;font-family:Arial;margin:0}.header{background:#111;padding:12px;border-bottom:3px solid #0f0}h2{margin:0;color:#0f0;font-size:13px}.container{padding:8px}.timer{font-size:26px;color:#ff0;text-align:center;background:#222;padding:10px;border-radius:10px;margin:6px 0}button{width:100%;padding:12px;border:none;border-radius:12px;font-weight:bold;margin:4px 0}#unlock{background:#0f0;color:#000}.card{border:2px solid #0f0;padding:8px;margin:6px 0;border-radius:10px;background:#151515}.SELL{border-color:#f33}.PIN{border-color:#ff0}.ENG{border-color:#0ff}.DB{border-color:#f0f}.row{display:flex;justify-content:space-between;font-size:10px;padding:2px 0;border-bottom:1px solid #222}.box{background:#111;padding:6px;border-radius:8px;margin:6px 0}</style></head><body><div class=header><h2>🟢 4 LAVORI - L1 75% L2 80% L3 82% L4 85%</h2></div><div class=container><div id=timer class=timer>00:00:00</div><div id=status style=text-align:center;background:#222;padding:5px;border-radius:8px;font-size:10px></div><button id=unlock onclick="unlockAudio()">🔊 SUONO</button><div id=l></div><div class=box><b>🔵 L1 TREND 75%</b><div id=s1>Vuoto</div></div><div class=box style=border:1px solid #ff0><b>🟡 L2 PIN 80%</b><div id=s2>Vuoto</div></div><div class=box style=border:1px solid #0ff><b>🔵 L3 ENGULFING 82%</b><div id=s3>Vuoto</div></div><div class=box style=border:1px solid #f0f><b>🟣 L4 DOPPIO RIMBALZO 85% PIU SICURO</b><div id=s4>Vuoto</div></div><button onclick="testAudio()" style="background:#333;color:#fff">🔔 TEST</button></div><script>let audioCtx=null,audioOn=false,seen=new Set(),first=true;function unlockAudio(){try{audioCtx=new(window.AudioContext||window.webkitAudioContext)();audioCtx.resume();audioOn=true;document.getElementById('unlock').innerText='✅ ON';}catch(e){}}function testAudio(){if(!audioOn){unlockAudio();setTimeout(testAudio,300);return;}let o=audioCtx.createOscillator();let g=audioCtx.createGain();o.connect(g);g.connect(audioCtx.destination);o.frequency.value=880;g.gain.value=0.3;o.start();setTimeout(()=>o.stop(),350);}function alarm(){if(!audioOn)return;for(let i=0;i<2;i++)setTimeout(testAudio,i*500);}async function load(){try{let r=await fetch('/api/signals');let d=await r.json();document.getElementById('timer').innerText=d.ora;document.getElementById('status').innerText=d.status;['s1','s2','s3','s4'].forEach((id,i)=>{let el=document.getElementById(id);let arr=d['storico'+(i+1)];if(!arr||arr.length==0)el.innerHTML='Vuoto';else{let html='';arr.slice(0,10).forEach(s=>{html+=`<div class=row><span>${s.data} ${s.coppia}</span><span><b>${s.dir}</b> RSI${s.rsi}</span></div>`});el.innerHTML=html;}});let all=[...(d.nuovi1||[]),...(d.nuovi2||[]),...(d.nuovi3||[]),...(d.nuovi4||[])];all.forEach(s=>{if(!seen.has(s.id)){seen.add(s.id);if(!first){document.getElementById('l').innerHTML=`<div class=card><b>${s.tipo} ${s.coppia} ${s.dir}</b> ${s.data} RSI${s.rsi} ${s.entry}</div>`+document.getElementById('l').innerHTML;alarm();}}});if(first){[1,2,3,4].forEach(i=>(d['storico'+i]||[]).forEach(s=>seen.add(s.id)));first=false;}}catch(e){}}setInterval(load,8000);load();</script></body></html>"""

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
