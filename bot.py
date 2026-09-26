import time, threading, requests, yfinance as yf, pandas as pd
from flask import Flask
import os

# --- USA I TUOI NOMI GIUSTI ---
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")

SYMBOLS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCHF=X","EURGBP=X","AUDJPY=X","EURNZD=X"]
PAIRS_OTC = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","EUR/JPY-OTC","GBP/JPY-OTC","USD/CHF-OTC","EUR/GBP-OTC","AUD/JPY-OTC","EUR/NZD-OTC"]

app = Flask(__name__)
@app.route('/')
def home(): return "TEST WIDE M1 OTC ONLINE"
@app.route('/ping')
def ping(): return "OK"

def send(msg):
    try:
        print(f"Invio Telegram...", flush=True)
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown", timeout=15)
    except Exception as e:
        print(f"Errore send: {e}", flush=True)

def get_m1(symbol):
    try:
        df = yf.download(symbol, period="1d", interval="1m", progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.dropna()
        return df.tail(5)
    except:
        return None

def check_pinbar_wide(df):
    if df is None or len(df) < 2: return None
    last = df.iloc[-1]
    o, h, l, c = last['Open'], last['High'], last['Low'], last['Close']
    body = abs(c - o)
    if body == 0: body = 0.00001
    upper = h - max(o,c)
    lower = min(o,c) - l
    total = h - l
    if total == 0: return None
    if upper > total*0.4 or lower > total*0.4:
        direction = "CALL 📈" if c > o else "PUT 📉"
        return direction
    return None

def loop():
    time.sleep(2)
    send("🧪 *TEST WIDE M1 OTC ONLINE*\nSolo 1m + Solo OTC + Segnali larghissimi\nPython 3.11.11")
    while True:
        for sym, pair in zip(SYMBOLS, PAIRS_OTC):
            df = get_m1(sym)
            sig = check_pinbar_wide(df)
            if sig:
                send(f"🧪 *TEST {pair} - M1*\n{sig}\nPrezzo: {df.iloc[-1]['Close']:.5f}")
            time.sleep(1.5)
        time.sleep(10)

threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
