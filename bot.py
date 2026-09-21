import os
import time
import threading
from flask import Flask
import yfinance as yf
import pandas as pd
import requests

# FIX TOKEN
TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", "7819696377:AAH2yW1u7Su1TeKkBNM09n-Ww2T5N1rbn5M"))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", "6129723979"))

PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "EURJPY=X", "GBPJPY=X", "EURGBP=X", "USDCHF=X", "NZDUSD=X", "EURCHF=X", "AUDJPY=X", "GBPCHF=X", "EURCAD=X", "AUDCAD=X", "NZDJPY=X"]

app = Flask(__name__)
@app.route('/')
def home():
    return f"V61 LOOSE LIVE - TOKEN OK: {TOKEN[:5]}... CHAT: {CHAT_ID}"

pending = []

def send(msg):
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except: pass

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta>0, 0).rolling(period).mean()
    loss = -delta.where(delta<0, 0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100/(1+rs))

def atr(df, period=14):
    hl = df['High'] - df['Low']
    hc = abs(df['High'] - df['Close'].shift())
    lc = abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def stochastic(df, k=14, d=3):
    low_min = df['Low'].rolling(k).min()
    high_max = df['High'].rolling(k).max()
    k_percent = 100 * ((df['Close'] - low_min) / (high_max - low_min))
    d_percent = k_percent.rolling(d).mean()
    return k_percent, d_percent

def scan():
    for symbol in PAIRS:
        try:
            df = yf.download(symbol, period="5d", interval="15m", progress=False)
            if len(df) < 210: continue
            df['e20'] = df['Close'].ewm(span=20).mean()
            df['e200'] = df['Close'].ewm(span=200).mean()
            df['rsi'] = rsi(df['Close'])
            df['atr'] = atr(df, 14)
            df['atr_ma50'] = df['atr'].rolling(50).mean()
            k, d = stochastic(df)
            df['stoch_k'] = k
            
            last = df.iloc[-1]
            clean = symbol.replace("=X","")
            price = float(last['Close'])
            rsi_val = float(last['rsi'])
            stoch_k = float(last['stoch_k'])

            if last['atr'] < last['atr_ma50'] * 0.4: continue
            if last['atr'] > last['atr_ma50'] * 3.5: continue

            signal = None
            tocco_e20 = abs(price - float(last['e20'])) / price < 0.005

            if price > float(last['e200']) and tocco_e20 and 20 <= rsi_val <= 60 and stoch_k < 35:
                signal = "BUY"
            if price < float(last['e200']) and tocco_e20 and 40 <= rsi_val <= 80 and stoch_k > 65:
                signal = "SELL"

            if signal:
                if any(p['symbol']==clean for p in pending): continue
                send(f"🎯 L4 LOOSE {signal} {clean} RSI {rsi_val:.1f} Stoch {stoch_k:.1f} Entry {price:.5f}")
                pending.append({"symbol": clean, "signal": signal, "entry": price, "time": time.time()})
        except: continue

def check_results():
    now = time.time()
    for p in pending[:]:
        if now - p['time'] < 900: continue
        try:
            df = yf.download(p['symbol']+"=X", period="1d", interval="1m", progress=False)
            if len(df)==0: continue
            curr = float(df['Close'].iloc[-1])
            win = (p['signal']=="BUY" and curr > p['entry']) or (p['signal']=="SELL" and curr < p['entry'])
            send(f"{'WIN' if win else 'LOSS'} L4 LOOSE {p['signal']} {p['symbol']}")
            pending.remove(p)
        except: pass

def loop():
    send(f"🚀 V61 LOOSE avviato OK\nTOKEN: {TOKEN[:10]}...\nCHAT_ID: {CHAT_ID}")
    while True:
        try:
            scan()
            check_results()
        except: pass
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
