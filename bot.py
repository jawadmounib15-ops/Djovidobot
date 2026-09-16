import yfinance as yf
import pandas as pd
import time
import threading
import requests
from flask import Flask

# CONFIG
TOKEN = "TELEGRAM_TOKEN"
CHAT_ID = "6723819958"
COPPIE = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "EURJPY=X", "GBPJPY=X", "EURGBP=X", "USDCAD=X", "EURCAD=X", "AUDJPY=X", "NZDUSD=X", "CADJPY=X"]

app = Flask(__name__)
@app.route('/')
def home(): return "V2.6 ANTI-SPAM ATTIVO"

last_sent = {} # <--- ANTI SPAM

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

def check_candles(pair):
    try:
        df = yf.download(pair, period="2d", interval="15m", progress=False)
        if len(df) < 55: return None
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        c = df.iloc[-1]
        prev = df.iloc[-2]
        close = float(c['Close'])
        open_ = float(c['Open'])
        ema = float(c['EMA50'])

        # PIN BAR FORTE
        body = abs(close - open_)
        upper = float(c['High']) - max(close, open_)
        lower = min(close, open_) - float(c['Low'])

        pin_sell = lower > body*2.5 and close < open_ and close < ema
        pin_buy = upper > body*2.5 and close > open_ and close > ema

        eng_sell = close < open_ and float(prev['Close']) > float(prev['Open']) and close < ema
        eng_buy = close > open_ and float(prev['Close']) < float(prev['Open']) and close > ema

        if pin_sell: return f"🔴 PIN BAR SELL - {pair}\nPrezzo sotto EMA50 - Trend DOWN"
        if pin_buy: return f"🟢 PIN BAR BUY - {pair}\nPrezzo sopra EMA50 - Trend UP"
        if eng_sell: return f"🔴 ENGULFING SELL - {pair}\nPrezzo sotto EMA50"
        if eng_buy: return f"🟢 ENGULFING BUY - {pair}\nPrezzo sopra EMA50"
    except: return None
    return None

def bot_loop():
    send_telegram("✅ V2.6 ANTI-SPAM AVVIATO!")
    while True:
        for pair in COPPIE:
            sig = check_candles(pair)
            if sig:
                # Controllo anti-spam 30 minuti
                now = time.time()
                if pair not in last_sent or now - last_sent[pair] > 1800:
                    send_telegram(f"🚨 *SEGNALE V2.6*\n\n{sig}\nTF: 15m -> Entra 30m su Pocket\nCoppia reale: {pair.replace('=X','')}")
                    last_sent[pair] = now
        time.sleep(60)

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
