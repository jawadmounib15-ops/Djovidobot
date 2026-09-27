import os, time, requests, yfinance as yf, threading, pandas as pd
from datetime import datetime, timedelta
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V105 LARGATO OTC+REALI ONLINE"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")

SYMBOLS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","NZDUSD=X","USDCHF=X","USDCAD=X","EURJPY=X","GBPJPY=X","EURGBP=X","AUDJPY=X","CADJPY=X","NZDJPY=X","CHFJPY=X","EURCHF=X","GBPCHF=X","AUDCHF=X","EURAUD=X","GBPAUD=X","EURCAD=X","AUDCAD=X","NZDCAD=X","AUDNZD=X","CADCHF=X","EURNZD=X"]
PAIRS_REAL = ["EUR/USD","GBP/USD","USD/JPY","AUD/USD","NZD/USD","USD/CHF","USD/CAD","EUR/JPY","GBP/JPY","EUR/GBP","AUD/JPY","CAD/JPY","NZD/JPY","CHF/JPY","EUR/CHF","GBP/CHF","AUD/CHF","EUR/AUD","GBP/AUD","EUR/CAD","AUD/CAD","NZD/CAD","AUD/NZD","CAD/CHF","EUR/NZD"]
PAIRS_OTC = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","NZD/USD-OTC","USD/CHF-OTC","USD/CAD-OTC","EUR/JPY-OTC","GBP/JPY-OTC","EUR/GBP-OTC","AUD/JPY-OTC","CAD/JPY-OTC","NZD/JPY-OTC","CHF/JPY-OTC","EUR/CHF-OTC","GBP/CHF-OTC","AUD/CHF-OTC","EUR/AUD-OTC","GBP/AUD-OTC","EUR/CAD-OTC","AUD/CAD-OTC","NZD/CAD-OTC","AUD/NZD-OTC","CAD/CHF-OTC","EUR/NZD-OTC"]

WIN=0; LOSS=0; PEND={}; CHECK=0; LAST={}

def is_otc():
    now = datetime.utcnow()
    if now.weekday()>=5: return True
    if now.hour<7 or now.hour>21: return True
    return False

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0); l=-d.where(d<0,0)
    ag=g.ewm(alpha=1/p).mean(); al=l.ewm(alpha=1/p).mean()
    return 100-(100/(1+ag/al))

def bot():
    global WIN,LOSS,CHECK
    send("💀 *V105 LARGATO ONLINE*\nRSI 60/40 + BB 25% + EMA largo\n25 REALI + 25 OTC")
    while True:
        try:
            now=datetime.now()
            otc_mode = is_otc()
            MERCATO = "OTC" if otc_mode else "REALI"
            PAIRS_LABEL = PAIRS_OTC if otc_mode else PAIRS_REAL

            for k in list(PEND.keys()):
                s,p,t,label,merc = PEND[k]
                if now-t >= timedelta(minutes=5):
                    try:
                        df=yf.download(k,period="1d",interval="1m",progress=False)
                        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
                        c=float(df["Close"].iloc[-1])
                        w=(s=="BUY" and c>p) or (s=="SELL" and c<p)
                        if w: WIN+=1; R="✅ WIN"
                        else: LOSS+=1; R="❌ LOSS"
                        tot=WIN+LOSS; wr=WIN/tot*100 if tot>0 else 0
                        send(f"{R} *{label} {s} {merc}* {p:.5f}->{c:.5f} WR {wr:.0f}% ({WIN}W/{LOSS}L)\n👉 Pocket fai *{'SELL' if s=='BUY' else 'BUY'}*")
                        del PEND[k]
                    except: pass

            if time.time()-CHECK >= 30:
                CHECK=time.time()
                for yahoo, label in zip(SYMBOLS, PAIRS_LABEL):
                    if yahoo in PEND: continue
                    if yahoo in LAST and time.time()-LAST[yahoo]<1800: continue
                    try:
                        df=yf.download(yahoo,period="10d",interval="5m",progress=False)
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
                        ora_now = now.strftime("%H:%M:%S")
                        ora_scad = (now + timedelta(minutes=5)).strftime("%H:%M:%S")
                        sig=None
                        toll=(up-low)*0.20 # LARGATO DA 0.15 A 0.20
                        if r>=60 and c>=up-toll and c<ema*1.0003: sig="BUY" # LARGATO DA 63 A 60
                        elif r<=40 and c<=low+toll and c>ema*0.9997: sig="SELL" # LARGATO DA 37 A 40
                        if sig:
                            PEND[yahoo]=(sig,c,now,label,MERCATO)
                            LAST[yahoo]=time.time()
                            send(f"💀 *5M {sig} {label} LARGATO {MERCATO} {ora_now}*\n📊 RSI:{r:.0f} (60/40) BB toll 25%\n💰 {c:.5f} EMA:{ema:.5f}\n⏰ {ora_now} → {ora_scad} (5 MIN)\n👉 POCKET: *{'SELL' if sig=='BUY' else 'BUY'}*")
                    except: pass
        except: pass
        time.sleep(1)

threading.Thread(target=bot,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
