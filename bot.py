# bot.py - V9.6 FORTE - COMPLETO E CORRETTO
import os
import time
import requests
import yfinance as yf
from datetime import datetime
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

RSI_BUY_MIN = 30
RSI_BUY_MAX = 45
RSI_SELL_MIN = 55
RSI_SELL_MAX = 70
COOLDOWN = 30 * 60
ultimo_segnale = 0

PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "EURJPY=X"]

def is_strong_signal(rsi, price, ema):
    if rsi < 25 or rsi > 75:
        return False, None
    if RSI_BUY_MIN <= rsi <= RSI_BUY_MAX and price > ema:
        return True, f"🟢 BUY FORTE RSI {rsi:.1f} + EMA50 OK - 30m"
    if RSI_SELL_MIN <= rsi <= RSI_SELL_MAX and price < ema:
        return True, f"🔴 SELL FORTE RSI {rsi:.1f} + EMA50 OK - 30m"
    return False, None

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print(e)

def is_orario_forte():
    ora = datetime.now().hour
    return 6 <= ora <= 9  # solo 06-09 come quando hai vinto

print("Bot V9.6 avviato")
send_telegram("✅ Bot V9.6 FORTE attivo - Solo 06:00-09:00")

while True:
    try:
        if not is_orario_forte():
            print("Fuori orario forte, pausa")
            time.sleep(300)
            continue

        if time.time() - ultimo_segnale < COOLDOWN:
            time.sleep(30)
            continue

        for pair in PAIRS:
            try:
                df = yf.download(pair, period="2d", interval="5m", progress=False, auto_adjust=True)
                if len(df) < 60: continue
                close = df['Close']
                rsi = float(RSIIndicator(close, window=14).rsi().iloc[-1])
                ema = float(EMAIndicator(close, window=50).ema_indicator().iloc[-1])
                price = float(close.iloc[-1])

                forte, messaggio = is_strong_signal(rsi, price, ema)
                if forte:
                    send_telegram(f"{messaggio}\nPair: {pair}\nOra: {datetime.now().strftime('%H:%M')}")
                    ultimo_segnale = time.time()
                    print(f"INVIATO {pair} {messaggio}")
                    break
            except Exception as e:
                print(f"Err {pair}: {e}")
                continue
        
        time.sleep(60)
    except Exception as e:
        print(f"Err loop: {e}")
        time.sleep(60)
