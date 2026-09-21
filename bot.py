import os, time, requests, yfinance as yf, pandas as pd
from threading import Thread
from flask import Flask
from datetime import datetime, timedelta

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
VERSION = "V37.2 REALE 5m + 5min ANTI-DOPPIO"
SYMBOLS = ["EURUSD=X", "GBPUSD=X", "EURGBP=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "EURJPY=X", "GBPJPY=X"]

app = Flask(__name__)
@app.route("/")
def home(): return f"{VERSION} LIVE - 7 LAVORI"

def send_tg(msg):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def calc_rsi(close, p=14):
    delta=close.diff(); gain=delta.where(delta>0,0).rolling(p).mean(); loss=-delta.where(delta<0,0).rolling(p).mean(); rs=gain/loss; return 100-(100/(1+rs))

last_sent = {}

def get_data(sym):
    try:
        # TIMEFRAME 5 MINUTI
        df=yf.download(sym, period="2d", interval="5m", progress=False, auto_adjust=True)
        if len(df)<60: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        c=pd.to_numeric(df['Close'], errors='coerce').dropna(); h=df['High']; l=df['Low']
        ema20=c.ewm(span=20).mean(); ema50=c.ewm(span=50).mean(); ema5=c.ewm(span=5).mean(); sma50=c.rolling(50).mean()
        rsi=calc_rsi(c); bb_mid=c.rolling(20).mean(); bb_std=c.rolling(20).std(); bb_u=bb_mid+2*bb_std; bb_l=bb_mid-2*bb_std
        price=float(c.iloc[-1]); r=float(rsi.iloc[-1]); e20=float(ema20.iloc[-1]); e50=float(ema50.iloc[-1])
        bu=float(bb_u.iloc[-1]); bl=float(bb_l.iloc[-1]); s50=float(sma50.iloc[-1])

        lavoro=None; side=None
        if c.iloc[-1]<=bl and r<=32: side="BUY"; lavoro="L2 RIMBALZO 32/68"
        elif c.iloc[-1]>=bu and r>=68: side="SELL"; lavoro="L2 RIMBALZO 32/68"
        if not lavoro:
            if e20>e50 and r>50 and r<65 and price>e20: side="BUY"; lavoro="L1 TREND"
            elif e20<e50 and r<50 and r>35 and price<e20: side="SELL"; lavoro="L1 TREND"
        if not lavoro:
            if price>float(h.rolling(20).max().iloc[-2]): side="BUY"; lavoro="L3 BREAKOUT"
            elif price<float(l.rolling(20).min().iloc[-2]): side="SELL"; lavoro="L3 BREAKOUT"
        if not lavoro:
            if price>s50 and float(c.iloc[-2])<s50 and e20>e50: side="BUY"; lavoro="L4 PULLBACK"
            elif price<s50 and float(c.iloc[-2])>s50 and e20<e50: side="SELL"; lavoro="L4 PULLBACK"

        if side:
            key=f"{sym}_{side}_{lavoro}"
            now=datetime.now()
            # ANTI-DOPPIO OGNI 5 MINUTI - TUA MODIFICA
            if sym in last_sent and last_sent[sym]['key']==key and now - last_sent[sym]['time'] < timedelta(minutes=5):
                return {"skip":True}
            last_sent[sym]={'key':key, 'time':now}
            return {"price":price,"rsi":r,"ema20":e20,"ema50":e50,"side":side,"lavoro":lavoro}
        return {"price":price,"rsi":r,"ema20":e20,"ema50":e50,"side":None}
    except: return None

def bot_loop():
    time.sleep(3)
    send_tg(f"✅ *{VERSION} LIVE*\nTimeframe: 5m\nAnti-doppio: 5 min\n7 Lavori attivi 🟢")
    while True:
        for sym in SYMBOLS:
            d=get_data(sym)
            if not d or d.get("skip"): continue
            if d.get("side"):
                nome=sym.replace("=X","").replace("EURUSD","EUR/USD").replace("GBPUSD","GBP/USD").replace("EURGBP","EUR/GBP").replace("USDJPY","USD/JPY").replace("AUDUSD","AUD/USD").replace("USDCAD","USD/CAD").replace("EURJPY","EUR/JPY").replace("GBPJPY","GBP/JPY")
                msg=f"{'🟢' if d['side']=='BUY' else '🔻'} *{d['side']} {nome} - {d['lavoro']}*\nRSI: {d['rsi']:.1f} | 5m\nPrezzo: {d['price']:.5f}"
                send_tg(msg)
            time.sleep(1)
        time.sleep(120)

Thread(target=bot_loop, daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
