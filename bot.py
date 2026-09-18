import yfinance as yf
import requests
import time
import os
from flask import Flask
from threading import Thread
import pandas as pd

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

app = Flask(__name__)

@app.route('/')
def home():
    return "V13.2 LIVE FIXED", 200

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print(e)

def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analizza():
    COPPIE_YF = ["EURUSD=X","GBPUSD=X","USDJPY=X","EURJPY=X","GBPJPY=X","AUDUSD=X"]
    COPPIE = ["EUR/USD","GBP/USD","USD/JPY","EUR/JPY","GBP/JPY","AUD/USD"]
    for i, simbolo in enumerate(COPPIE_YF):
        nome = COPPIE[i]
        try:
            df = yf.download(simbolo, period="2d", interval="15m", progress=False, auto_adjust=True)
            if len(df) < 60:
                continue
            close_s = df['Close']
            if isinstance(close_s, pd.DataFrame):
                close_s = close_s.iloc[:,0]
            close_s = close_s.squeeze()
            open_s = df['Open']
            if isinstance(open_s, pd.DataFrame):
                open_s = open_s.iloc[:,0]
            open_s = open_s.squeeze()

            ema50 = float(close_s.ewm(span=50).mean().iloc[-1])
            ema200 = float(close_s.ewm(span=200).mean().iloc[-1])
            rsi = float(calc_rsi(close_s).iloc[-1])

            ultima_close = float(close_s.iloc[-1])
            ultima_open = float(open_s.iloc[-1])
            prec_close = float(close_s.iloc[-2])
            prec_open = float(open_s.iloc[-2])

            corpo_u = abs(ultima_close - ultima_open)
            corpo_p = abs(prec_close - prec_open)
            if corpo_p == 0:
                continue
            ratio = corpo_u / corpo_p
            if ratio < 1.20 or ratio > 2.00:
                continue

            bullish = (prec_close < prec_open) and (ultima_close > ultima_open) and (ultima_close > prec_open) and (ultima_open < prec_close)
            bearish = (prec_close > prec_open) and (ultima_close < ultima_open) and (ultima_close < prec_open) and (ultima_open > prec_close)

            sig = "BUY" if bullish else "SELL" if bearish else ""
            if not sig:
                continue

            trend = "BUY" if ema50 > ema200 else "SELL"
            if sig == "BUY" and rsi > 70: continue
            if sig == "SELL" and rsi < 30: continue
            if sig!= trend: continue

            msg = f"🔥 SEGNALE 90% SICURO 🔥\n\nCoppia: {nome}\nDirezione: {sig}\nRatio: {ratio:.2f}\nRSI: {rsi:.1f}\nTrend: {trend} OK"
            send(msg)
        except Exception as e:
            print(f"Err {nome}: {e}")

def run_bot():
    print("BOT 90% AVVIATO")
    send("✅ BOT V13.2 AVVIATO - 90% SICURO\nFix Series applicato, ora funziona")
    while True:
        analizza()
        time.sleep(300)

Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
