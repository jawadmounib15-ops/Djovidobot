# app.py - 5 MIN FIX 60% - FUNZIONA
import os, time, threading
from flask import Flask, jsonify
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
from curl_cffi import requests as cffi_requests

PAIRS = ["EURUSD=X","GBPUSD=X","EURGBP=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCAD=X"]
ITALY = ZoneInfo("Europe/Rome")
app = Flask(__name__)
pins_live, pins_storico, cooldown = [], [], {}

def ema(s,p): return s.ewm(span=p).mean()
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def atr(df,p=14):
    hl=df['High']-df['Low']; hc=abs(df['High']-df['Close'].shift()); lc=abs(df['Low']-df['Close'].shift())
    tr=pd.concat([hl,hc,lc],axis=1).max(axis=1)
    return tr.rolling(p).mean()

def get_df(sym):
    try:
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=5m&range=5d"
        r=cffi_requests.get(url, impersonate="chrome120", timeout=10)
        q=r.json()['chart']['result'][0]['indicators']['quote'][0]
        df=pd.DataFrame({'Open':q['open'],'High':q['high'],'Low':q['low'],'Close':q['close']}).dropna()
        return df.tail(400)
    except: return pd.DataFrame()

def scan_5m():
    global pins_live, pins_storico
    for sym in PAIRS:
        clean=sym.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean]<600: continue # 10 min
        df=get_df(sym)
        if len(df)<100: continue
        try:
            df['ema20']=ema(df['Close'],20); df['ema200']=ema(df['Close'],200)
            df['rsi']=rsi(df['Close']); df['atr']=atr(df,14); df['atr_ma']=df['atr'].rolling(50).mean()
            c=df.iloc[-2]; conf=df.iloc[-1]
            O,H,L,C=float(c['Open']),float(c['High']),float(c['Low']),float(c['Close'])
            total=H-L
            if total<0.00003: continue # era 0.00007 -> 0.00003
            if float(c['atr']) < float(c['atr_ma'])*0.50: continue # era 0.75 -> 0.50
            
            corpo=abs(O-C) or total*0.05; inf=min(O,C)-L; sup=H-max(O,C)
            forza=max(inf,sup)/total*100
            
            # FIX 60% - era 2.0/0.55/0.20
            hammer=inf>=corpo*1.5 and inf>=total*0.45 and sup<=total*0.30 and corpo<=total*0.40
            star=sup>=corpo*1.5 and sup>=total*0.45 and inf<=total*0.30 and corpo<=total*0.40
            if not ((hammer or star) and 60<=forza<=92): continue # era 70 -> 60
            
            e20=float(c['ema20']); e200=float(c['ema200']); rv=float(c['rsi'])
            # RSI largo era 22-40 -> 20-45
            if hammer and not (20 <= rv <= 45): continue
            if star and not (55 <= rv <= 80): continue
            if abs(C-e20)/C > 0.006: continue # era 0.004 -> 0.006
            
            # Rimosso filtro low30/high30 killer e ema200 stretto
            conf_c=float(conf['Close'])
            # Conferma leggera
            if hammer and conf_c < C*0.9995: continue
            if star and conf_c > C*1.0005: continue
            
            signal="BUY" if hammer else "SELL"
            pin={
                "asset":clean, "dir":"CALL SU 📈 5M" if signal=="BUY" else "PUT GIÙ 📉 5M",
                "signal":signal, "entry":round((H+L)/2,5), "price":round(C,5),
                "rsi":round(rv), "forza":round(forza), "ema20":round(e20,5),
                "ora":datetime.now(ITALY).strftime("%H:%M:%S"),
                "data":datetime.now(ITALY).strftime("%d/%m %H:%M:%S"),
                "scadenza":(datetime.now(ITALY)+timedelta(minutes=5)).strftime("%H:%M:%S"),
                "scad_label":"5M", "id":f"{clean}{time.time()}"
            }
            pins_live.insert(0,pin); pins_storico.insert(0,pin)
            pins_live=pins_live[:20]; pins_storico=pins_storico[:500]
            cooldown[clean]=time.time()
            print(f"SIGNALE {clean} {signal} {forza:.0f}%", flush=True)
        except Exception as e:
            print(f"ERR {clean} {e}", flush=True)
            continue

def loop():
    while True:
        try: scan_5m()
        except: pass
        time.sleep(25)

@app.route('/')
def home():
    return f"5M FIX 60% | LIVE {len(pins_live)} | Storico {len(pins_storico)} | {datetime.now(ITALY).strftime('%H:%M:%S')}"

@app.route('/api/pins')
def api_pins(): return jsonify(pins_live)
@app.route('/api/storico')
def api_storico(): return jsonify(pins_storico)

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
