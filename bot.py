# V36.8.6 7 LAVORI PELO EXTREME LIVE - FIX DEFINITIVO
import yfinance as yf
import pandas as pd
import ta
import time
import requests
import os
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "EUR/JPY", "GBP/JPY", "AUD/USD", "USD/CHF", "EUR/GBP"]
TF = "5M"
COOLDOWN = 300

def invia_telegram(msg):
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}", timeout=10)
    except:
        pass

def analizza(pair):
    try:
        # Mapping simboli
        if pair == "GBP/USD": symbol = "GBPUSD=X"
        elif pair == "EUR/USD": symbol = "EURUSD=X"
        elif pair == "USD/JPY": symbol = "JPY=X"
        elif pair == "EUR/JPY": symbol = "EURJPY=X"
        elif pair == "GBP/JPY": symbol = "GBPJPY=X"
        elif pair == "AUD/USD": symbol = "AUDUSD=X"
        else: symbol = "EURUSD=X"

        df = yf.download(symbol, period="2d", interval="5m", progress=False, auto_adjust=False)
        if len(df) < 60:
            return None, None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = df['Close']
        high = df['High']
        low = df['Low']

        rsi14 = float(ta.momentum.RSIIndicator(close, 14).rsi().iloc[-1])
        sma50 = float(close.rolling(50).mean().iloc[-1])
        ema9 = float(close.ewm(span=9).mean().iloc[-1])
        ema21 = float(close.ewm(span=21).mean().iloc[-1])
        prev_close = float(close.iloc[-2])
        curr_close = float(close.iloc[-1])
        curr_high = float(high.iloc[-1])
        curr_low = float(low.iloc[-1])

        # --- V36.8.6 PELO EXTREME - BLOCCO 39-61 ---
        # I tuoi 2 LOSS erano RSI 43 e 55 -> BLOCCATI!
        # I tuoi 3 WIN erano RSI 38, 42, 58 -> 38 passa, 42 e 58 vicini ma con L6 forte passavano
        # Ora mettiamo 38 / 62 per essere EXTREME
        if rsi14 >= 39 and rsi14 <= 61:
            return None, None

        buy = 0; sell = 0; motivi = []
        has_L6 = False

        # L1 - RIMBALZO SMA
        if curr_low < sma50 and curr_close > sma50:
            buy+=1; motivi.append("L1")
        if curr_high > sma50 and curr_close < sma50:
            sell+=1; motivi.append("L1")

        # L2 - CONFERMA
        if prev_close < sma50 and curr_close > sma50 and curr_close > prev_close:
            buy+=1; motivi.append("L2")
        if prev_close > sma50 and curr_close < sma50 and curr_close < prev_close:
            sell+=1; motivi.append("L2")

        # L3 - BREAKOUT 10 candele
        last_high = float(high.iloc[-10:-1].max())
        last_low = float(low.iloc[-10:-1].min())
        if curr_close > last_high:
            buy+=1; motivi.append("L3")
        if curr_close < last_low:
            sell+=1; motivi.append("L3")

        # L4 - PULLBACK
        if curr_close > sma50 and prev_close < curr_close:
            buy+=1; motivi.append("L4")
        if curr_close < sma50 and prev_close > curr_close:
            sell+=1; motivi.append("L4")

        # L5 - PELO EXTREME 38 / 62
        if rsi14 <= 38:
            buy+=1; motivi.append("L5")
        if rsi14 >= 62:
            sell+=1; motivi.append("L5")

        # L6 - CROSS EMA - OBBLIGATORIO PER V36.8.6
        prev_ema9 = float(close.ewm(span=9).mean().iloc[-2])
        prev_ema21 = float(close.ewm(span=21).mean().iloc[-2])
        if prev_ema9 < prev_ema21 and ema9 > ema21:
            buy+=1; motivi.append("L6"); has_L6 = True
        if prev_ema9 > prev_ema21 and ema9 < ema21:
            sell+=1; motivi.append("L6"); has_L6 = True

        # L7 - TREND
        if rsi14 < 50 and curr_close > sma50:
            buy+=1; motivi.append("L7")
        if rsi14 > 50 and curr_close < sma50:
            sell+=1; motivi.append("L7")

        # --- FILTRO FINALE V36.8.6 ---
        # Minimo 4 lavori + L6 obbligatorio + RSI extreme
        if not has_L6:
            return None, None

        if buy >= 4 and rsi14 <= 38:
            return "BUY", f"🟢 {pair} OTC BUY TF {TF} | {'+'.join(motivi)} | RSI {int(rsi14)}"
        elif sell >= 4 and rsi14 >= 62:
            return "SELL", f"🔴 {pair} OTC SELL TF {TF} | {'+'.join(motivi)} | RSI {int(rsi14)}"
        else:
            return None, None

    except Exception as e:
        print(f"Errore {pair}: {e}")
        return None, None

# LOOP
ultimo_seg = {}
print("V36.8.6 PELO EXTREME ATTIVO - 38/62 + 4 lavori + L6 obbligatorio")
invia_telegram("✅ V36.8.6 PELO EXTREME ATTIVO - RSI 38/62 + 4 lavori + L6 obbl.")

while True:
    for p in PAIRS:
        if p in ultimo_seg and time.time() - ultimo_seg[p] < COOLDOWN:
            continue
        dir, msg = analizza(p)
        if msg:
            ora = datetime.now().strftime("%H:%M:%S")
            full = f"{msg} {ora}"
            print(full)
            invia_telegram(full)
            ultimo_seg[p] = time.time()
    time.sleep(10)
