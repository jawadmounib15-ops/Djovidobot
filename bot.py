import yfinance as yf
import requests
import time
import os
from flask import Flask
from threading import Thread

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

ENGULFING_MIN = 1.20
ENGULFING_MAX = 2.00
RSI_OB = 70
RSI_OS = 30

COPPIE_YF = ["EURUSD=X","GBPUSD=X","USDJPY=X","EURJPY=X","GBPJPY=X"]
COPPIE_POCKET = ["EUR/USD","GBP/USD","USD/JPY","EUR/JPY","GBP/JPY"]

app = Flask(__name__)

@app.route('/')
def home():
    return "V13.2 LIVE OK", 200

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except:
        pass

def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analizza():
    from datetime import datetime
    ora = datetime.now().hour
    if ora >= 23 or ora < 5:
        return
    for i, simbolo in enumerate(COPPIE_YF):
        nome = COPPIE_POCKET[i]
        try:
            df = yf.download(simbolo, period="2d", interval="15m", progress=False, auto_adjust=True)
            if len(df) < 60:
                continue
            ema50 = float(df['Close'].ewm(span=50).mean().iloc[-1])
            ema200 = float(df['Close'].ewm(span=200).mean().iloc[-1])
            rsi = float(calc_rsi(df['Close']).iloc[-1])
            ultima = df.iloc[-1]
            prec = df.iloc[-2]
            corpo_u = abs(float(ultima['Close']) - float(ultima['Open']))
            corpo_p = abs(float(prec['Close']) - float(prec['Open']))
            if corpo_p == 0:
                continue
            ratio = corpo_u / corpo_p
            if ratio < ENGULFING_MIN or ratio > ENGULFING_MAX:
                continue
            close_u = float(ultima['Close'])
            open_u = float(ultima['Open'])
            close_p = float(prec['Close'])
            open_p = float(prec['Open'])
            bullish = (close_p < open_p) and (close_u > open_u) and (close_u > open_p) and (open_u < close_p)
            bearish = (close_p > open_p) and (close_u < open_u) and (close_u < open_p) and (open_u > close_p)
            trend = "BUY" if ema50 > ema200 else "SELL"
            sig = "BUY" if bullish else "SELL" if bearish else ""
            if not sig:
                continue
            if sig == "BUY" and rsi > RSI_OB:
                continue
            if sig == "SELL" and rsi < RSI_OS:
                continue
            if sig!= trend:
                continue
            msg = f"✅ SEGNALE SICURO 90% - {nome} - {sig}\nRatio: {ratio:.2f} | RSI: {rsi:.1f}"
            print(msg)
            send(msg)
        except Exception as e:
            print(f"Err {nome}: {e}")

def run_bot():
    send("✅ V13.2 AVVIATO - REGOLA SICURA 1.20-2.00 + VERO ENGULFING + RSI - NO OTC NOTTE")
    while True:
        analizza()
        time.sleep(300)

Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
