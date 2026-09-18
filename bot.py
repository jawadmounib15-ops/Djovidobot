import yfinance as yf
import requests, time, os
from flask import Flask
from threading import Thread
import pandas as pd

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

app = Flask(__name__)
@app.route('/')
def home():
    return "V13.3 FIXED LIVE", 200

def send(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except: pass

def to_float(x):
    # converte qualsiasi cosa (DataFrame, Series) in float
    if isinstance(x, pd.DataFrame):
        x = x.iloc[:,0]
    if isinstance(x, pd.Series):
        x = x.iloc[-1]
        if isinstance(x, pd.Series):
            x = x.iloc[0]
    return float(x)

def calc_rsi(close, period=14):
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:,0]
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analizza():
    coppie = [("EURUSD=X","EUR/USD"),("GBPUSD=X","GBP/USD"),("USDJPY=X","USD/JPY"),("EURJPY=X","EUR/JPY"),("GBPJPY=X","GBP/JPY"),("AUDUSD=X","AUD/USD")]
    for simbolo, nome in coppie:
        try:
            df = yf.download(simbolo, period="2d", interval="15m", progress=False, auto_adjust=True)
            if len(df) < 60: continue

            close = df['Close']
            open_ = df['Open']
            ema50 = to_float(close.ewm(span=50).mean())
            ema200 = to_float(close.ewm(span=200).mean())
            rsi = to_float(calc_rsi(close))

            uc = to_float(close.iloc[-1:])
            uo = to_float(open_.iloc[-1:])
            pc = to_float(close.iloc[-2:-1])
            po = to_float(open_.iloc[-2:-1])

            corpo_u = abs(uc - uo)
            corpo_p = abs(pc - po)
            if corpo_p == 0: continue
            ratio = corpo_u / corpo_p
            if ratio < 1.20 or ratio > 2.00: continue

            bullish = (pc < po) and (uc > uo) and (uc > po) and (uo < pc)
            bearish = (pc > po) and (uc < uo) and (uc < po) and (uo > pc)
            sig = "BUY" if bullish else "SELL" if bearish else ""
            if not sig: continue
            trend = "BUY" if ema50 > ema200 else "SELL"
            if sig=="BUY" and rsi>70: continue
            if sig=="SELL" and rsi<30: continue
            if sig!= trend: continue

            send(f"🔥 SEGNALE 90% 🔥\nCoppia: {nome}\nDirezione: {sig}\nRatio: {ratio:.2f}\nRSI: {rsi:.1f}\nTrend: {trend}")
        except Exception as e:
            print(f"Err {nome}: {e}")

def run_bot():
    print("BOT 90% AVVIATO")
    send("✅ BOT V13.3 AVVIATO - Fix Series OK")
    while True:
        analizza()
        time.sleep(300)

Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
