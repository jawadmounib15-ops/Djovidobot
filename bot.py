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
            print("ERRORE: TELEGRAM_TOKEN o TELEGRAM_CHAT_ID mancanti su Render")
            return
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": msg}
        requests.post(url, json=payload, timeout=10)
        print(f"Inviato: {msg}")
    except Exception as e:
        print(f"Errore send: {e}")

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

        return {"symbol": symbol, "side": side, "price": price, "rsi": r, "touch": touch, "adx": adx_v, "time": time.time()}
    except Exception as e:
        print(f"Errore check {symbol}: {e}")
        return None

def scan_loop():
    send("V63 ANTI-LOSS LIVE - Tocco 0.20% + ADX25 + 8 Pairs - FIX TOKEN OK")
    while True:
        try:
            for sym in PAIRS:
                sig = check_signal(sym)
                if sig:
                    if any(p['symbol']==sig['symbol'] and time.time()-p['time']<3600 for p in pending):
                        continue
                    pending.append(sig)
                    name = sym.replace("=X","")
                    txt = f"L4 V63 {sig['side']} {name} RSI {round(sig['rsi'],1)} ADX {round(sig['adx'],1)} TOUCH {round(sig['touch'],3
