# V35.7 FINAL - SOLO EUR/USD OTC - 1 SEGNALE / 5 MIN
# REGOLE: segue il trend, mai contro
import time
import requests
import pandas as pd
from datetime import datetime

# --- CONFIG ---
PAIR = "EUR/USD OTC"
TIMEFRAME = 60  # M1
COOLDOWN = 300  # 5 minuti
TELEGRAM_TOKEN = "INSERISCI_QUI_TOKEN"
CHAT_ID = "INSERISCI_QUI_CHAT_ID"

ultimo_segale_time = 0

# --- TELEGRAM ---
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except:
        pass

# --- INDICATORI SERI ---
def calcola_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/period, adjust=False).mean()
    loss = -delta.where(delta < 0, 0).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analizza_trend(df):
    global ultimo_segale_time

    # REGOLA 1: COOLDOWN 5 MIN - BLOCCO TOTALE
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

    # REGOLA 2: EMA DEVONO ESSERE LARGHE (no laterale)
    distanza_ema = abs(ema9 - ema21)
    if distanza_ema < 0.0005:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] EMA vicine {distanza_ema:.5f} -> NO TRADE")
        return None

    # REGOLA 3: CEDERE IL TREND - FORZA
    salita_3_candele = c1["close"] - c3["close"]
    discesa_3_candele = c3["close"] - c1["close"]
    salita_forte =
