import yfinance as yf
import pandas as pd
import time, requests, os, random
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
app = Flask(__name__)
@app.route('/')
def home(): return "V60.1 Medio 7 lavori L4 SICURO LIVE", 200

def tg(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": m}, timeout=10)
    except: pass

SYMBOLS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURGBP=X","EURJPY=X","GBPJPY=X","EURCHF=X","AUDJPY=X","GBPCHF=X","NZDUSD=X","EURCAD=X","GBPCAD=X","AUDCAD=X"]

stats = {}
results = {"L1":[0,0],"L2":[0,0],"L3":[0,0],"L4":[0,0],"L5":[0,0],"L6":[0,0],"L7":[0,0]}
pending = []

def add(sym, price, msg, lavoro):
    stats[sym] = price
    pending.append({"sym":sym, "price":price, "lavoro":lavoro, "msg":msg, "time":datetime.now()})
    if lavoro in results:
        results[lavoro][1] += 1

def check_results():
    while True:
        time.sleep(60)
        now = datetime.now()
        for p in pending[:]:
            if now - p["time"] > timedelta(minutes=15):
                try:
                    df = yf.download(p["sym"], period="1d", interval="1m", progress=False)
                    if len(df)==0: continue
                    curr = float(df['Close'].iloc[-1])
                    entry = p["price"]
                    is_buy = "BUY" in p["msg"]
                    win = (curr > entry) if is_buy else (curr < entry)
                    lab = p["lavoro"]
                    if win: results[lab][0] += 1
                    pending.remove(p)
                    perc = int(results[lab][0]/results[lab][1]*100) if results[lab][1]>0 else 0
                    tg(f"{'WIN' if win else 'LOSS'} {p['msg']} -> {perc}% ({results[lab][0]}/{results[lab][1]})")
                except: pass

def run():
    last = {}
    while True:
        try:
            for sym in SYMBOLS:
                if sym in last and datetime.now() - last[sym] < timedelta(minutes=15): continue
                df = yf.download(sym, period="5d", interval="15m", progress=False, auto_adjust=True)
                if len(df) < 60: continue
                close = df['Close']
                e20 = close.ewm(span=20).mean()
                e50 = close.ewm(span=50).mean()
                e20v = float(e20.iloc[-1]); e50v = float(e50.iloc[-1])
                price = float(close.iloc[-1])
                pair = sym.replace("=X","")
                delta = close.diff()
                gain = delta.where(delta>0,0).rolling(14).mean()
                loss = -delta.where(delta<0,0).rolling(14).mean()
                rs = gain/loss
                rsi = 100 - (100/(1+rs))
                rv = float(rsi.iloc[-1])
                e20_prev = float(e20.iloc[-2])

                if e20v > e50v and rv > 55 and price > e20v:
                    m=f"L1 TREND BUY {pair} RSI {rv:.0f}"
                    tg(m); add(sym,price,m,"L1"); last[sym]=datetime.now(); continue
                if e20v < e50v and rv < 45 and price < e20v:
                    m=f"L1 TREND SELL {pair} RSI {rv:.0f}"
                    tg(m); add(sym,price,m,"L1"); last[sym]=datetime.now(); continue

                if price < e20v*0.998 and rv < 40:
                    m=f"L2 RIMBALZO BUY {pair} RSI {rv:.0f}"
                    tg(m); add(sym,price,m,"L2"); last[sym]=datetime.now(); continue
                if price > e20v*1.002 and rv > 60:
                    m=f"L2 RIMBALZO SELL {pair} RSI {rv:.0f}"
                    tg(m); add(sym,price,m,"L2"); last[sym]=datetime.now(); continue

                if price > float(df['High'].iloc[-20:-1].max()) and rv > 60:
                    m=f"L3 BREAKOUT BUY {pair} RSI {rv:.0f}"
                    tg(m); add(sym,price,m,"L3"); last[sym]=datetime.now(); continue
                if price < float(df['Low'].iloc[-20:-1].min()) and rv < 40:
                    m=f"L3 BREAKOUT SELL {pair} RSI {rv:.0f}"
                    tg(m); add(sym,price,m,"L3"); last[sym]=datetime.now(); continue

                # L4 PULLBACK SICURO
                trend_up_forte = e20v > e50v and e20v > e20_prev
                trend_down_forte = e20v < e50v and e20v < e20_prev
                if trend_up_forte and e20v*0.998 < price < e20v*1.002 and 50 < rv < 60:
                    m=f"L4 PULLBACK BUY {pair} RSI {rv:.0f}"
                    tg(m); add(sym,price,m,"L4"); last[sym]=datetime.now(); continue
                if trend_down_forte and e20v*0.998 < price < e20v*1.002 and 40 < rv < 50:
                    m=f"L4 PULLBACK SELL {pair} RSI {rv:.0f}"
                    tg(m); add(sym,price,m,"L4"); last[sym]=datetime.now(); continue

                if 55 < rv < 70 and e20v > e50v:
                    m=f"L5 DOPPIO BUY {pair} RSI {rv:.0f}"
                    tg(m); add(sym,price,m,"L5"); last[sym]=datetime.now(); continue
                if 30 < rv < 45 and e20v < e50v:
                    m=f"L5 DOPPIO SELL {pair} RSI {rv:.0f}"
                    tg(m); add(sym,price,m,"L5"); last[sym]=datetime.now(); continue

                if rv < 30:
                    m=f"L6 IPER BUY {pair} RSI {rv:.0f}"
                    tg(m); add(sym,price,m,"L6"); last[sym]=datetime.now(); continue
                if rv > 70:
                    m=f"L7 IPER SELL {pair} RSI {rv:.0f}"
                    tg(m); add(sym,price,m,"L7"); last[sym]=datetime.now(); continue

            if random.random() < 0.05:
                txt = "📊 STATS:\n"
                for k in ["L1","L2","L3","L4","L5","L6","L7"]:
                    w,t = results[k]
                    if t>0: txt+=f"{k}: {w}/{t} {int(w/t*100)}%\n"
                if len(txt) > 12: tg(txt)
            time.sleep(5)
        except Exception as e:
            print(e); time.sleep(10)

Thread(target=run, daemon=True).start()
Thread(target=check_results, daemon=True).start()
tg("🚀 V60.1 Medio 7 lavori L4 SICURO avviato ✅ - L4 con regola sicura attiva")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
