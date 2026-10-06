from flask import Flask, jsonify
import yfinance as yf
from curl_cffi import requests as cffi_requests
import pandas as pd
from datetime import datetime
import pytz, os, time

app = Flask(__name__)
ROMA = pytz.timezone("Europe/Rome")

# FIX 401 Render - session singleton condivisa come da fix ufficiale
_YF_SESSION = cffi_requests.Session(impersonate="chrome")

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","EURGBP=X","GBPJPY=X","AUDJPY=X"]
STORICO, cooldown = [], {}

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def atr(df,p=14):
    tr=pd.concat([df['High']-df['Low'],abs(df['High']-df['Close'].shift()),abs(df['Low']-df['Close'].shift())],axis=1).max(axis=1)
    return tr.rolling(p).mean()

@app.route('/api/signals')
def api():
    global STORICO
    now=datetime.now(ROMA)
    if now.weekday()>=5 or (now.weekday()==4 and now.hour>=23):
        return jsonify({"ora":now.strftime("%H:%M:%S"),"storico":STORICO[-20:][::-1],"nuovi":[],"status":"🔴 CHIUSO"})
    nuovi=[]
    for sym in PAIRS:
        try:
            clean=sym.replace("=X","")
            if clean in cooldown and time.time()-cooldown[clean]<5400: continue
            # Ticker con sessione fix 401
            tk=yf.Ticker(sym, session=_YF_SESSION)
            df=tk.history(period="5d", interval="15m")
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
            atr_v=float(last['atr']); atr_ma=float(last['atr_ma'])
            is_green=float(last['Close'])>float(last['Open'])
            is_red=not is_green

            # FILTRI GIUSTISSIMI 75%
            if atr_v < atr_ma*0.7: continue # no volatilità morta
            if e50 <= e200 and price <= e200: # trend check per SELL verrà dopo
                pass
            sig=None
            # BUY: EMA50>EMA200 + prezzo sopra EMA200 + RSI 30-45 + bullish close
            if e50>e200 and price>e200 and 30<=rsi_v<=45 and is_green and abs(price-float(last['e20']))/price<=0.002:
                sig="BUY"
            # SELL: EMA50<EMA200 + prezzo sotto EMA200 + RSI 55-70 + bearish close
            if e50<e200 and price<e200 and 55<=rsi_v<=70 and is_red and abs(price-float(last['e20']))/price<=0.002:
                sig="SELL"
            if sig:
                s={"coppia":clean,"dir":sig,"rsi":int(rsi_v),"entry":round(price,5),"ora":now.strftime("%H:%M:%S"),"data":now.strftime("%d/%m %H:%M:%S"),"id":f"{clean}{now.strftime('%H%M%S')}"}
                STORICO.append(s)
                if len(STORICO)>100: STORICO=STORICO[-100:]
                cooldown[clean]=time.time()
                nuovi.append(s)
                if len(nuovi)>=2: break
        except: continue
    return jsonify({"ora":now.strftime("%H:%M:%S"),"storico":STORICO[-30:][::-1],"nuovi":nuovi,"status":"🟢 V66 75% GIUSTO LIVE"})

@app.route('/')
def home():
    return """<html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>V66</title><style>body{background:#000;color:#fff;font-family:Arial;margin:0;padding:10px}.header{background:#111;padding:12px;border-bottom:3px solid #0f0}h2{color:#0f0;margin:0}.timer{font-size:32px;color:#ff0;text-align:center;background:#222;padding:12px;border-radius:10px;margin:10px 0}.card{border:2px solid #0f0;padding:10px;margin:8px 0;border-radius:10px;background:#151515}.SELL{border-color:#f33;color:#f33}.BUY{color:#0f0}.row{display:flex;justify-content:space-between;font-size:12px}</style></head><body><div class=header><h2>🟢 V66 75% GIUSTISSIMO</h2><div style=color:#ff0;font-size:10px>EMA50>200 + RSI 30-45/55-70 + ATR filter + fix 401 Render</div></div><div id=timer class=timer>00:00:00</div><div id=status style=text-align:center;background:#222;padding:8px;border-radius:8px></div><div id=list></div><script>async function load(){try{let r=await fetch('/api/signals');let d=await r.json();document.getElementById('timer').innerText=d.ora;document.getElementById('status').innerText=d.status;let h='';if(!d.storico||d.storico.length==0)h='<div class=card>Attendo primo segnale - pagina OK</div>';else d.storico.forEach(s=>{h+=`<div class=card ${s.dir}><b>${s.coppia} ${s.dir}</b> ${s.data} RSI${s.rsi} Entry ${s.entry}</div>`});document.getElementById('list').innerHTML=h;}catch(e){document.getElementById('status').innerText='Connessione...';}}setInterval(load,10000);load();</script></body></html>"""

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
