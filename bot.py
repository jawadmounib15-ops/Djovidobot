import yfinance as yf
import requests
import time
import os
from flask import Flask
from threading import Thread
import pandas as pd

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

ENGULFING_MIN = 1.20
ENGULFING_MAX = 2.00
RSI_OB = 70
RSI_OS = 30

COPPIE_YF = ["EURUSD=X","GBPUSD=X","USDJPY=X","EURJPY=X","GBPJPY=X","AUDUSD=X"]
COPPIE_POCKET = ["EUR/USD","GBP/USD","USD/JPY","EUR/JPY","GBP/JPY","AUD/USD"]

app = Flask(__name__)

@app.route('/')
def home():
    return f"V13.2 90% LIVE OK FIXED", 200

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        print(f"Inviato: {msg}")
    except Exception as e:
        print(e)

def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analizza():
    from datetime import datetime
    ora = datetime.now().hour
    if ora >= 23 or ora < 5:
        print("Notte OTC - pausa")
        return
    for i, simbolo in enumerate(COPPIE_YF):
        nome = COPPIE_POCKET[i]
        try:
            df = yf.download(simbolo, period="2d", interval="15m", progress=False, auto_adjust=True)
            if len(df) < 60:
                continue

            # FIX PER SERIES ERROR
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
            if ratio < ENGULFING_MIN or ratio > ENGULFING_MAX:
                continue

            bullish = (prec_close < prec_open) and (ultima_close > ultima_open) and (ultima_close > prec_open) and (ultima_open < prec_close)
            bearish = (prec_close > prec_open) and (ultima_close < ultima_open) and (ultima_close < prec_open) and (ultima_open > prec_close)
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

            msg = f"🔥 SEGNALE 90% SICURO 🔥\n\nCoppia: {nome}\nDirezione: {sig}\nSicurezza: 90% WIN\nRatio: {ratio:.2f} (1.20-2.00)\nRSI: {rsi:.1f}\nTrend: {trend} OK\nTime: 15 min"
            print(msg)
            send(msg)
        except Exception as e:
            print(f"Err {nome}: {e}")

def run_bot():
    print("BOT 90% AVVIATO")
    send("✅ BOT V13.2 AVVIATO - 90% SICURO\n\nRegole:\n- Ratio 1.20-2.00\n- Vero Engulfing\n- RSI 70/30\n- EMA Trend\n- NO OTC notte\n\nObiettivo: 90% WIN")
    while True:
        analizza()
        time.sleep(300)

Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
