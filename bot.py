import yfinance as yf
import requests
import time
import os
import pandas as pd
from flask import Flask
from threading import Thread

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

app = Flask(__name__)
@app.route('/')
def home():
    return "BOT V13.4 COMPLETO LIVE", 200

def send(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": msg}, timeout=15)
    except Exception as e:
        print(f"Send error: {e}")

def to_float(val):
    """Converte qualsiasi cosa (DataFrame, Series, float) in float puro"""
    try:
        if isinstance(val, pd.DataFrame):
            val = val.iloc[:,0]
        if isinstance(val, pd.Series):
            # prendi ultimo valore non-NaN
            val = val.dropna().iloc[-1] if not val.dropna().empty else val.iloc[-1]
            # se è ancora Series (raro)
            while isinstance(val, pd.Series):
                val = val.iloc[0]
        return float(val)
    except:
        return 0.0

def calc_rsi(close, period=14):
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:,0]
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def analizza():
    coppie = [
        ("EURUSD=X", "EUR/USD"),
        ("GBPUSD=X", "GBP/USD"),
        ("USDJPY=X", "USD/JPY"),
        ("EURJPY=X", "EUR/JPY"),
        ("GBPJPY=X", "GBP/JPY"),
        ("AUDUSD=X", "AUD/USD")
    ]

    for simbolo, nome in coppie:
        try:
            df = yf.download(simbolo, period="3d", interval="15m", progress=False, auto_adjust=True)
            if df is None or len(df) < 60:
                continue

            close = df['Close']
            open_ = df['Open']

            # Calcola indicatori e converti subito in float
            ema50_s = close.ewm(span=50).mean()
            ema200_s = close.ewm(span=200).mean()
            rsi_s = calc_rsi(close)

            ema50 = to_float(ema50_s)
            ema200 = to_float(ema200_s)
            rsi = to_float(rsi_s)

            if ema50 == 0 or ema200 == 0 or rsi == 0:
                continue

            uc = to_float(close.iloc[-1:])
            uo = to_float(open_.iloc[-1:])
            pc = to_float(close.iloc[-2:-1])
            po = to_float(open_.iloc[-2:-1])

            # Filtro engulfing
            corpo_u = abs(uc - uo)
            corpo_p = abs(pc - po)
            if corpo_p == 0:
                continue
            ratio = corpo_u / corpo_p
            if ratio < 1.20 or ratio > 2.00:
                continue

            bullish = (pc < po) and (uc > uo) and (uc > po) and (uo < pc)
            bearish = (pc > po) and (uc < uo) and (uc < po) and (uo > pc)

            sig = ""
            if bullish:
                sig = "BUY"
            elif bearish:
                sig = "SELL"

            if not sig:
                continue

            trend = "BUY" if ema50 > ema200 else "SELL"

            if sig == "BUY" and rsi > 70:
                continue
            if sig == "SELL" and rsi < 30:
                continue
            if sig!= trend:
                continue

            msg = f"🔥 SEGNALE 90% 🔥\nCoppia: {nome}\nDirezione: {sig}\nRatio: {ratio:.2f}\nRSI: {rsi:.1f}\nTrend: {trend}\nEMA50: {ema50:.5f}\nEMA200: {ema200:.5f}"
            send(msg)
