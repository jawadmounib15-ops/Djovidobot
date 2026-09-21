import os, time, requests, yfinance as yf, pandas as pd
from threading import Thread
from flask import Flask
from datetime import datetime, timedelta

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
VERSION = "V40 FIX"
SYMBOLS = ["EURUSD=X", "GBPUSD=X", "EURGBP=X", "USDJPY=X"]

app = Flask(__name__)
@app.route("/")
def home(): return f"{VERSION} LIVE - {datetime.now()}"

def send_tg(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": m, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def calc_rsi(c, p=14):
    d=c.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

last_block = {}

def get_signal(sym):
    try:
        df=yf.download(sym, period="4d", interval="15m", progress=False, auto_adjust=True)
        if len(df)<80: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        c=df['Close'].dropna(); o=df['Open'].dropna()
        if len(c)<80: return None
        e9=c.ewm(span=9).mean(); e20=c.ewm(span=20).mean(); e50=c.ewm(span=50).mean()
        rsi=calc_rsi(c); macd=c.ewm(span=12).mean()-c.ewm(span=26).mean(); sig=macd.ewm(span=9).mean(); hist=macd-sig

        price=float(c.iloc[-1]); curr_o=float(o.iloc[-1]); prev=float(c.iloc[-2]); prev_o=float(o.iloc[-2]); prev2=float(c.iloc[-3])
        e9v=float(e9.iloc[-1]); e20v=float(e20.iloc[-1]); e50v=float(e50.iloc[-1]); rv=float(rsi.iloc[-1]); hv=float(hist.iloc[-1]); hv2=float(hist.iloc[-2])

        if sym in last_block and datetime.now() - last_block[sym] < timedelta(minutes=30): return None

        dist=abs(price-e20v)/e20v*100
        if dist>0.18 or dist<0.02: return None # REGOLA 2

        green = (1 if price>curr_o else 0) + (1 if prev>prev_o else 0)
        red = (1 if price<curr_o else 0) + (1 if prev<prev_o else 0)

        # Crollo precedente? Se candela prima lunga >0.12% blocca contrario - REGOLA 4
        body_prev = abs(prev - prev_o)/prev*100
        if body_prev > 0.12:
            return None

        if e9v>e20v>e50v and 52<=rv<=62 and hv>0 and hv>hv2 and green<=2 and price>curr_o and price>e20v:
            last_block[sym]=datetime.now()
            return f"🟢 BUY {sym.replace('=X','')} | vicino {dist:.2f}% RSI {rv:.0f} | {price:.5f}"

        if e9v<e20v<e50v and 38<=rv<=48 and hv<0 and hv<hv2 and red<=2 and price<curr_o and price<e20v:
            last_block[sym]=datetime.now()
            return f"🔻 SELL {sym.replace('=X','')} | vicino {dist:.2f}% RSI {rv:.0f} | {price:.5f}"

        return None
    except Exception as e:
        print(f"Err {sym}: {e}")
        return None

def loop():
    time.sleep(5)
    send_tg(f"✅ *{VERSION} PARTITO*\nRegole buone attive: no RSI 71, no 3 verdi, no dopo crollo")
    while True:
        for s in SYMBOLS:
            sig=get_signal(s)
            if sig: send_tg(sig)
            time.sleep(8)
        time.sleep(180)

Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
