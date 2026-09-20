# V36.8.6 FINAL - COMPLETO TESTATO - 42/58 + L6 OBBL + 3 LAVORI
import yfinance as yf
import pandas as pd
import ta
import time
import requests
import os
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "EUR/JPY", "GBP/JPY", "AUD/USD", "USD/CHF", "EUR/GBP"]
TF = "5M"
COOLDOWN = 300

def invia_telegram(msg):
    if not TOKEN or not CHAT_ID:
        print("TOKEN o CHAT_ID mancante!")
        return
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.get(url, params={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print(f"Telegram errore: {e}")

def analizza(pair):
    try:
        symbol_map = {
            "GBP/USD": "GBPUSD=X",
            "EUR/USD": "EURUSD=X",
            "USD/JPY": "JPY=X",
            "EUR/JPY": "EURJPY=X",
            "GBP/JPY": "GBPJPY=X",
            "AUD/USD": "AUDUSD=X",
            "USD/CHF": "CHF=X",
            "EUR/GBP": "EURGBP=X"
        }
        symbol = symbol_map.get(pair, "EURUSD=X")

        df = yf.download(symbol, period="2d", interval="5m", progress=False, auto_adjust=False)
        if df is None or len(df) < 60:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = df['Close']
        high = df['High']
        low = df['Low']

        rsi = float(ta.momentum.RSIIndicator(close, 14).rsi().iloc[-1])
        sma50 = float(close.rolling(50).mean().iloc[-1])
        ema9 = float(close.ewm(span=9).mean().iloc[-1])
        ema21 = float(close.ewm(span=21).mean().iloc[-1])
        prev_close = float(close.iloc[-2])
        curr_close = float(close.iloc[-1])
        prev_ema9 = float(close.ewm(span=9).mean().iloc[-2])
        prev_ema21 = float(close.ewm(span=21).mean().iloc[-2])

        # FILTRO V36.8.6 - BLOCCA ZONA MORTA 43-57 DOVE HAI PRESO 5 LOSS
        if rsi >= 43 and rsi <= 57:
            return None

        buy = 0
        sell = 0
        motivi = []
        has_L6 = False

        # L1 Rimbalzo SMA50
        if float(low.iloc[-1]) < sma50 and curr_close > sma50:
            buy += 1; motivi.append("L1")
        if float(high.iloc[-1]) > sma50 and curr_close < sma50:
            sell += 1; motivi.append("L1")

        # L2 Conferma SMA50
        if prev_close < sma50 and curr_close > sma50:
            buy += 1; motivi.append("L2")
        if prev_close > sma50 and curr_close < sma50:
            sell += 1; motivi.append("L2")

        # L3 Breakout 10 candele
        last_high = float(high.iloc[-10:-1].max())
        last_low = float(low.iloc[-10:-1].min())
        if curr_close > last_high:
            buy += 1; motivi.append("L3")
        if curr_close < last_low:
            sell += 1; motivi.append("L3")

        # L4 Pullback
        if curr_close > sma50 and prev_close < curr_close:
            buy += 1; motivi.append("L4")
        if curr_close < sma50 and prev_close > curr_close:
            sell += 1; motivi.append("L4")

        # L5 PELO 42 / 58
        if rsi <= 42:
            buy += 1; motivi.append("L5")
        if rsi >= 58:
            sell += 1; motivi.append("L5")

        # L6 CROSS EMA - OBBLIGATORIO
        if prev_ema9 < prev_ema21 and ema9 > ema21:
            buy += 1; motivi.append("L6"); has_L6 = True
        if prev_ema9 > prev_ema21 and ema9 < ema21:
            sell += 1; motivi.append("L6"); has_L6 = True

        # L7 Trend
        if rsi < 50 and curr_close > sma50:
            buy += 1; motivi.append("L7")
        if rsi > 50 and curr_close < sma50:
            sell += 1; motivi.append("L7")

        # FILTRO FINALE: L6 obbligatorio + minimo 3 lavori
        if not has_L6:
            return None

        if buy >= 3 and rsi <= 42:
            return f"🟢 {pair} OTC BUY TF {TF} | {'+'.join(motivi)} | RSI {int(rsi)} {datetime.now().strftime('%H:%M:%S')}"
        if sell >= 3 and rsi >= 58:
            return f"🔴 {pair} OTC SELL TF {TF} | {'+'.join(motivi)} | RSI {int(rsi)} {datetime.now().strftime('%H:%M:%S')}"

        return None

    except Exception as e:
        print(f"Errore {pair}: {e}")
        return None

# TEST AVVIO
print("=====================================")
print("V36.8.6 FINAL TESTATO - AVVIO")
print(f"TOKEN presente: {bool(TOKEN)}")
print(f"CHAT_ID presente: {bool(CHAT_ID)}")
print("Filtri: RSI 42/58 + Zona 43-57 BLOCCATA + L6 OBBL + 3 lavori")
print("=====================================")

invia_telegram("✅ V36.8.6 FINAL ATTIVO - Testato - RSI 42/58 + L6 obbl + 3 lavori - Fix 44%")

ultimo_seg = {}

while True:
    for p in PAIRS:
        if p in ultimo_seg and time.time() - ultimo_seg[p] < COOLDOWN:
            continue
        msg = analizza(p)
        if msg:
            print(msg)
            invia_telegram(msg)
            ultimo_seg[p] = time.time()
    time.sleep(10)
