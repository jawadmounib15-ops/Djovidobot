# V35.8 FINAL FIX - SOLO EUR/USD OTC - 5 MIN - NO ERROR
import time
import requests
import pandas as pd
from datetime import datetime
import os

PAIR = "EUR/USD OTC"
COOLDOWN = 300
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "INSERISCI_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "INSERISCI_CHAT")

ultimo_segale_time = 0

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def calcola_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/period, adjust=False).mean()
    loss = -delta.where(delta < 0, 0).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analizza_trend(df):
    global ultimo_segale_time
    if time.time() - ultimo_segale_time < COOLDOWN:
        return None
    if len(df) < 30:
        return None

    c1 = df.iloc[-1]
    c2 = df.iloc[-2]
    c3 = df.iloc[-3]

    ema9 = df["close"].ewm(span=9, adjust=False).mean().iloc[-1]
    ema21 = df["close"].ewm(span=21, adjust=False).mean().iloc[-1]
    rsi = calcola_rsi(df["close"]).iloc[-1]

    distanza = abs(ema9 - ema21)
    if distanza < 0.0005:
        return None

    salita = c1["close"] - c3["close"]
    discesa = c3["close"] - c1["close"]
    salita_forte = salita > 0.0009
    discesa_forte = discesa > 0.0009

    segnale = None
    if ema9 > ema21 and rsi < 47 and not discesa_forte:
        segnale = "BUY"
    elif ema9 < ema21 and rsi > 53 and not salita_forte:
        segnale = "SELL"

    if segnale:
        ultimo_segale_time = time.time()
        msg = f"{PAIR} - {segnale} - {datetime.now().strftime('%H:%M:%S')} RSI {rsi:.1f}"
        send_telegram(msg)
        print(msg)
        return segnale
    return None

# COLLEGA QUI LE TUE CANDELE VERE QUOTEX
# Esempio:
# from quotexapi import Quotex
# q = Quotex("email","pass")
# q.connect()
# while True:
#     df = pd.DataFrame(q.get_candles(PAIR, 60, 50))
#     analizza_trend(df)
#     time.sleep(10)

if __name__ == "__main__":
    print(f"BOT V35.8 AVVIATO - {PAIR}")
    send_telegram(f"Bot V35.8 avviato - {PAIR} - 5min cooldown")
    while True:
        time.sleep(10)
