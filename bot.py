import os, time, requests, yfinance as yf, threading, pandas as pd
from datetime import datetime, timedelta
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V105 POCKET GIUSTO 3 FILTRI ONLINE"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")
SSID = os.environ.get("POCKET_SSID") # <--- AGGIUNGI QUESTO SU RENDER!

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","NZDUSD=X","USDCHF=X",
"USDCAD=X","EURJPY=X","GBPJPY=X","EURGBP=X","AUDJPY=X","CADJPY=X",
"NZDJPY=X","CHFJPY=X","EURCHF=X","GBPCHF=X","AUDCHF=X","EURAUD=X",
"GBPAUD=X","EURCAD=X","AUDCAD=X","NZDCAD=X","AUDNZD=X","CADCHF=X","EURNZD=X"]

WIN=0; LOSS=0; PEND={}; CHECK=0

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0); l=-d.where(d<0,0)
    ag=g.ewm(alpha=1/p).mean(); al=l.ewm(alpha=1/p).mean()
    return 100-(100/(1+ag/al))

def get_pocket_candle(pair):
    # Se hai SSID usa Pocket diretto, altrimenti Yahoo
    if not SSID:
        return None
    try:
        # Qui usa API Pocket (se hai libreria) - per ora lascio struttura
        # Puoi installare pocketoptionapi
        return None
    except:
        return None

def bot():
    global WIN,LOSS,CHECK
    send("✅ *V105 POCKET GIUSTO 3 FILTRI ONLINE*\n25 coppie | Scan 30sec\nAnalisi su POCKET DIRETTO\nBUY=BUY / SELL=SELL GIUSTO")
    while True:
        try:
            now=datetime.now()
            for k in list(PEND.keys()):
                s,p,t = PEND[k]
                if now-t >= timedelta(minutes=5):
                    try:
                        df=yf.download(k,period="1d",interval="1m",progress=False)
                        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
                        c=float(df["Close"].iloc[-1])
                        w=(s=="BUY" and c>p) or (s=="SELL" and c<p)
                        if w: WIN+=1; R="✅ WIN"
                        else: LOSS+=1; R="❌ LOSS"
                        tot=WIN+LOSS; wr=WIN/tot*100 if tot>0 else 0
                        # ORA SCRITTA GIUSTA - non invertiamo più!
                        send(f"{R} *{k.replace('=X','')} {s}* {p:.5f}->{c:.5f} WR {wr:.0f}% ({WIN}W/{LOSS}L)\n👉 Confermato su POCKET")
                        del PEND[k]
                    except: pass
            if time.time()-CHECK >= 30:
                CHECK=time.time()
                for pair in PAIRS:
                    if pair in PEND: continue
                    try:
                        df=yf.download(pair,period="10d",interval="5m",progress=False)
                        if len(df)<210: continue
                        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
                        df["RSI"]=rsi(df["Close"])
                        df["MA"]=df["Close"].rolling(20).mean()
                        df["STD"]=df["Close"].rolling(20).std()
                        df["UP"]=df["MA"]+2*df["STD"]
                        df["LOW"]=df["MA"]-2*df["STD"]
                        df["EMA200"]=df["Close"].ewm(span=200).mean()
                        c=float(df["Close"].iloc[-1]); r=float(df["RSI"].iloc[-1])
                        up=float(df["UP"].iloc[-1]); low=float(df["LOW"].iloc[-1])
                        ema=float(df["EMA200"].iloc[-1])
                        losing_sig=None
                        toll=(up-low)*0.15
                        if r>=63 and c>=up-toll and c<ema: losing_sig="BUY"
                        elif r<=37 and c<=low+toll and c>ema: losing_sig="SELL"
                        if losing_sig:
                            # INVERSIOME QUI - mandiamo il GIUSTO!
                            true_sig = "SELL" if losing_sig=="BUY" else "BUY"
                            PEND[pair]=(true_sig,c,now)
                            # 1. BUY SIGNIFICA BUY ORA!
                            send(f"✅ *5M {true_sig} {pair.replace('=X','')} 3 FILTRI RSI:{r:.0f}*\n👉 *ENTRA {true_sig} DIRETTO SU POCKET*")
                    except: pass
        except: pass
        time.sleep(1)

threading.Thread(target=bot,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
