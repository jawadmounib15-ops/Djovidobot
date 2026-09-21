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

PAIRS = ["EURUSD=X","GBPUSD=X","GBPJPY=X","AUDJPY=X","EURJPY=X","USDCHF=X","EURCHF=X","GBPCHF=X"]

pending = []

def send(msg):
    try:
        if not TOKEN or not CHAT_ID:
            return
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
        df = fix_df(yf.download(symbol, period="5d", interval="15m", progress=False, auto_adjust=False))
        if len(df) < 250:
            return None
        close = df['Close']
        high = df['High']
        low = df['Low']
        ema20 = ta.trend.ema_indicator(close, window=20)
        ema50 = ta.trend.ema_indicator(close, window=50)
        ema200 = ta.trend.ema_indicator(close, window=200)
        rsi = ta.momentum.rsi(close, window=14)
        stoch = ta.momentum.stoch(high=high, low=low, close=close, window=14, smooth_window=3)
        atr = ta.volatility.average_true_range(high=high, low=low, close=close, window=14)
        adx = ta.trend.adx(high=high, low=low, close=close, window=14)

        price = float(close.iloc[-1])
        e20 = float(ema20.iloc[-1])
        e50 = float(ema50.iloc[-1])
        e200 = float(ema200.iloc[-1])
        r = float(rsi.iloc[-1])
        s = float(stoch.iloc[-1])
        adx_v = float(adx.iloc[-1])
        a = float(atr.iloc[-1])
        a_ma = float(atr.rolling(50).mean().iloc[-1])
        touch = abs(price - e20) / price * 100

        if adx_v < 25:
            return None
        if touch > 0.20:
            return None
        if not (0.5 * a_ma < a < 3.0 * a_ma):
            return None

        side = None
        if price > e200 and e20 > e50:
            side = "BUY"
            if not (25 < r < 60 and s < 35):
                return None
        elif price < e200 and e20 < e50:
            side = "SELL"
            if not (40 < r < 75 and s > 65):
                return None
        else:
            return None

        df4 = fix_df(yf.download(symbol, period="1mo", interval="4h", progress=False, auto_adjust=False))
        if len(df4) < 100:
            return None
        p4 = float(df4['Close'].iloc[-1])
        e200_4h = float(ta.trend.ema_indicator(df4['Close'], window=200).iloc[-1])
        if side == "BUY" and p4 < e200_4h:
            return None
        if side == "SELL" and p4 > e200_4h:
            return None

        return {"symbol": symbol, "side": side, "price": price, "rsi": r, "adx": adx_v, "touch": touch, "time": time.time()}
    except:
        return None

def scan_loop():
    send("V63 ANTI-LOSS LIVE - Tocco 0.20% + ADX25 + 8 Pairs")
    while True:
        for sym in PAIRS:
            sig = check_signal(sym)
            if sig:
                if any(p['symbol']==sig['symbol'] and time.time()-p['time']<3600 for p in pending):
                    continue
                pending.append(sig)
                name = sym.replace("=X","")
                s_side = sig['side']
                s_rsi = str(round(sig['rsi'],1))
                s_adx = str(round(sig['adx'],1))
                s_touch = str(round(sig['touch'],3))
                txt = "L4 V63 " + s_side + " " + name + " RSI " + s_rsi + " ADX " + s_adx + " TOUCH " + s_touch + "%"
                send(txt)
                time.sleep(2)
        time.sleep(90)

def check_results():
    while True:
        time.sleep(60)
        now = time.time()
        for p in pending[:]:
            if now - p['time'] < 900:
                continue
            try:
                df = fix_df(yf.download(p['symbol'], period="1d", interval="5m", progress=False, auto_adjust=False))
                if len(df)==0:
                    continue
                curr = float(df['Close'].iloc[-1])
                p_side = p['side']
                p_price = p['price']
                win = (p_side=="BUY" and curr > p_price) or (p_side=="SELL" and curr < p_price)
                name = p['symbol'].replace("=X","")
                if win:
                    send("WIN " + p_side + " " + name)
                else:
                    send("LOSS " + p_side + " " + name)
                pending.remove(p)
            except:
                pass

@app.route("/")
def home():
    return "V63 LIVE"

if __name__ == "__main__":
    threading.Thread(target=scan_loop, daemon=True).start()
    threading.Thread(target=check_results, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
