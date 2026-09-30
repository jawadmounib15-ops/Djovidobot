import os, time, threading, yfinance as yf, pandas as pd, requests
from flask import Flask
from datetime import datetime
import pytz

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))

MODE = "LENTO"
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","GBPJPY=X","EURGBP=X","EURCHF=X","AUDJPY=X","GBPCHF=X","NZDJPY=X","EURAUD=X","GBPAUD=X","CADJPY=X","CHFJPY=X","NZDCAD=X"]
SETTINGS = {
    "LENTO": {"rsi_buy": (20,42), "rsi_sell": (58,80), "sto_buy": 26, "sto_sell": 74, "tocco": 0.0022, "ratio": 1.8, "cooldown": 5400},
    "MEDIO": {"rsi_buy": (24,38), "rsi_sell": (62,76), "sto_buy": 18, "sto_sell": 82, "tocco": 0.0015, "ratio": 2.2, "cooldown": 9000},
}
CFG = SETTINGS[MODE]

app = Flask(__name__)
@app.route('/')
def home():
    tz = pytz.timezone('Europe/Rome')
    now = datetime.now(tz).strftime('%H:%M:%S IT')
    return f"V64 {MODE} LIVE - {now} - scan 60s"

pending=[]; cooldown={}

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def atr(df,p=14):
    hl=df['High']-df['Low']; hc=abs(df['High']-df['Close'].shift()); lc=abs(df['Low']-df['Close'].shift())
    tr=pd.concat([hl,hc,lc],axis=1).max(axis=1); return tr.rolling(p).mean()
def stoch(df,k=14): return 100*((df['Close']-df['Low'].rolling(k).min())/(df['High'].rolling(k).max()-df['Low'].rolling(k).min()))

def send_alarm(msg):
    # ALLARME CHE SUONA - Telegram con suono + notifica forte
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        params={"chat_id": CHAT_ID, "text": f"🔔🔔🔔 ALLARME 🔔🔔🔔\n{msg}", "disable_notification": False}, timeout=10)
    except: pass

def ora_italia():
    tz = pytz.timezone('Europe/Rome')
    return datetime.now(tz).strftime('%H:%M:%S %d/%m')

def scan():
    sent=0
    for symbol in PAIRS:
        if sent>=2: break
        clean=symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < CFG["cooldown"]: continue
        try:
            df15=yf.download(symbol, period="5d", interval="15m", progress=False); df15=fix_df(df15)
            if len(df15)<210: continue
            df15['e20']=df15['Close'].ewm(span=20).mean(); df15['e200']=df15['Close'].ewm(span=200).mean()
            df15['rsi']=rsi(df15['Close']); df15['atr']=atr(df15,14); df15['atr_ma']=df15['atr'].rolling(50).mean(); df15['sto']=stoch(df15,14)
            df60=yf.download(symbol, period="20d", interval="60m", progress=False); df60=fix_df(df60); df60['e200']=df60['Close'].ewm(span=200).mean()
            last=df15.iloc[-1]; last60=df60.iloc[-1]
            price=float(last['Close']); rsi_v=float(last['rsi']); sto_v=float(last['sto'])
            e20=float(last['e20']); e200=float(last['e200']); e200_60=float(last60['e200'])
            if not ((price>e200_60 and price>e200) or (price<e200_60 and price<e200)): continue
            if last['atr'] < last['atr_ma']*0.70 or last['atr'] > last['atr_ma']*2.0: continue
            if abs(price-e20)/price > CFG["tocco"]: continue
            o=float(last['Open']); h=float(last['High']); l=float(last['Low']); c=float(last['Close'])
            body=abs(c-o); rng=h-l
            if rng==0 or body < rng*0.07 or body > rng*0.30: continue
            up=h-max(o,c); down=min(o,c)-l; ratio=max(up,down)/body if body>0 else 0
            if ratio < CFG["ratio"] or min(up,down) > rng*0.22: continue
            sig=None
            if price>e200 and down>up and CFG["rsi_buy"][0] <= rsi_v <= CFG["rsi_buy"][1] and sto_v < CFG["sto_buy"]: sig="BUY"
            if price<e200 and up>down and CFG["rsi_sell"][0] <= rsi_v <= CFG["rsi_sell"][1] and sto_v > CFG["sto_sell"]: sig="SELL"
            if sig and not any(p['symbol']==clean for p in pending):
                send_alarm(f"🎯 {sig} {clean}\n⏰ {ora_italia()}\nRSI {rsi_v:.0f} STO {sto_v:.0f} {ratio:.1f}x\nEntry {price:.5f}\nMODE {MODE}")
                pending.append({"symbol":clean,"signal":sig,"entry":price,"time":time.time()}); cooldown[clean]=time.time(); sent+=1
        except: continue

def check():
    for p in pending[:]:
        if time.time()-p['time'] < 900: continue
        try:
            df=yf.download(p['symbol']+"=X", period="1d", interval="1m", progress=False); df=fix_df(df)
            curr=float(df['Close'].iloc[-1])
            win=(p['signal']=="BUY" and curr>p['entry']) or (p['signal']=="SELL" and curr<p['entry'])
            send_alarm(f"{'WIN ✅' if win else 'LOSS ❌'} {p['signal']} {p['symbol']}\n⏰ {ora_italia()}\n{abs(curr-p['entry'])*10000:.1f} pip")
            pending.remove(p)
        except: pass

def loop():
    send_alarm(f"🚀 V64 {MODE} PARTITO\n⏰ {ora_italia()}\nScan automatico ogni 60 sec\n18 coppie")
    while True:
        try: scan(); check()
        except: pass
        time.sleep(60) # CERCA OGNI 60 SEC

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
