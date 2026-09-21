import os, time, requests, yfinance as yf, pandas as pd
from threading import Thread
from flask import Flask
from datetime import datetime, timedelta

TOKEN=os.getenv("TELEGRAM_TOKEN")
CHAT=os.getenv("TELEGRAM_CHAT_ID")
app=Flask(__name__)
@app.route("/")
def home(): return "V60 LIVE"

def tg(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id":CHAT,"text":m}, timeout=10)
    except: pass

def rsi(c):
    d=c.diff()
    g=d.where(d>0,0).rolling(14).mean()
    l=-d.where(d<0,0).rolling(14).mean()
    return 100-(100/(1+g/l))

blk={}
def run():
    time.sleep(4)
    tg("V60 PARTITO 7 lavori")
    while True:
        for sym in ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X"]:
            try:
                df=yf.download(sym, period="5d", interval="15m", progress=False, auto_adjust=True)
                if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
                c=df["Close"]; e20=c.ewm(20).mean(); e50=c.ewm(50).mean(); r=rsi(c)
                price=float(c.iloc[-1]); e20v=float(e20.iloc[-1]); e50v=float(e50.iloc[-1]); rv=float(r.iloc[-1])
                if sym in blk and datetime.now()-blk[sym] < timedelta(minutes=40): continue
                if e20v>e50v and price>e20v and 55<rv<68:
                    tg(f"L1 TREND BUY {sym} RSI {rv:.0f}"); blk[sym]=datetime.now()
                elif e20v<e50v and price<e20v and 32<rv<45:
                    tg(f"L1 TREND SELL {sym} RSI {rv:.0f}"); blk[sym]=datetime.now()
            except Exception as e: print(e)
            time.sleep(4)
        time.sleep(120)

Thread(target=run, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
