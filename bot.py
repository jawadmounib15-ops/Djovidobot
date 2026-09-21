import yfinance as yf
import pandas as pd
import ta
import time
import threading
import os
import requests
from flask import Flask

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","EURJPY=X","GBPJPY=X","EURGBP=X","USDCHF=X","NZDUSD=X","EURCHF=X","AUDJPY=X","GBPCHF=X","EURCAD=X","AUDCAD=X","NZDJPY=X"]

pending = []

def send(msg):
    try:
        url = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except:
        pass

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.copy()
    for c in ['Open','High','Low','Close']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    return df.dropna()

def check_signal(symbol):
    try:
        df = fix_df(yf.download(symbol, period="5d", interval="15m", progress=False))
        if len(df) < 250:
            return None
        close = df['Close']
        high = df['High']
        low = df['Low']

        ema20 = ta.trend.ema_indicator(close, 20).iloc[-1]
        ema200 = ta.trend.ema_indicator(close, 200).iloc[-1]
        rsi = ta.momentum.rsi(close, 14).iloc[-1]
        stoch = ta.momentum.stoch(close, high, low, 14, 3).iloc[-1]
        atr = ta.volatility.average_true_range(high, low, close, 14)

        price = float(close.iloc[-1])
        touch = abs(price - float(ema20)) / price * 100
        a_ma = float(atr.rolling(50).mean().iloc[-1])
        a = float(atr.iloc[-1])

        if price > ema200:
            side = "BUY"
        elif price < ema200:
            side = "SELL"
        else:
            return None

        if touch > 0.35:
            return None
        if side == "BUY" and not (20 < rsi < 60 and stoch < 35):
            return None
        if side == "SELL" and not (40 < rsi < 80 and stoch > 65):
            return None
        if not (0.4 * a_ma < a < 3.5 * a_ma):
            return None

        df4 = fix_df(yf.download(symbol, period="1mo", interval="4h", progress=False))
        if len(df4) < 100:
            return None
        p4 = float(df4['Close'].iloc[-1])
        e200_4h = float(ta.trend.ema_indicator(df4['Close'], 200).iloc[-1])
        if side == "BUY" and p4 < e200_4h:
            return None
        if side == "SELL" and p4 > e200_4h:
            return None

        return {"symbol": symbol, "side": side, "price": price, "rsi": float(rsi), "touch": touch, "time": time.time()}
    except:
        return None

def scan_loop():
    send("V62 STEP 2 LIVE - Tocco 0.35% + 4H")
    while True:
        for sym in PAIRS:
            sig = check_signal(sym)
            if sig:
                if any(p['symbol']==sig['symbol'] and time.time()-p['time']<1800 for p in pending):
                    continue
                pending.append(sig)
                name = sym.replace("=X","")
                txt = "L4 V62 " + sig['side'] + " " + name + " RSI " + str(round(sig['rsi'],1)) + " Tocco " + str(round(sig['touch'],2)) + "%"
                send(txt)
                time.sleep(2)
        time.sleep(60)

def check_results():
    while True:
        time.sleep(60)
        now = time.time()
        for p in pending[:]:
            if now - p['time'] < 900:
                continue
            try:
                df = fix_df(yf.download(p['symbol'], period="1d", interval="5m", progress=False))
                if len(df)==0:
                    continue
                curr = float(df['Close'].iloc[-1])
                win = False
                if p['side']=="BUY" and curr > p['price']:
                    win = True
                if p['side']=="SELL" and curr < p['price']:
                    win = True
                name = p['symbol'].replace("=X","")
                if win:
                    send("WIN " + p['side'] + " " + name)
                else:
                    send("LOSS " + p['side'] + " " + name)
                pending.remove(p)
            except:
                pass

@app.route("/")
def home():
    return "V62 LIVE"

if __name__ == "__main__":
    threading.Thread(target=scan_loop, daemon=True).start()
    threading.Thread(target=check_results, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
