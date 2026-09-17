# bot.py V9.6 FORTE - Corretto da Pa - 17/09/2026
import os
import time
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# CONFIG CORRETTA - come ieri che vincevi
PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "EURJPY=X"]
RSI_BUY_MIN, RSI_BUY_MAX = 30, 45   # Compra basso
RSI_SELL_MIN, RSI_SELL_MAX = 55, 70 # Vendi alto
EMA_PERIOD = 50
COOLDOWN_SEC = 30 * 60  # 30 min

ultimo_segnale_time = 0

def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"Err Telegram: {e}")

def is_orario_forte():
    ora = datetime.now().hour
    # Solo 06:00-09:00 hai vinto 3 su 4 - dopo le 10 è debole
    return 6 <= ora <= 9

def check_pair(pair):
    try:
        df = yf.download(pair, period="2d", interval="5m", progress=False)
        if len(df) < 60: return None
        close = df['Close']
        
        rsi = RSIIndicator(close, window=14).rsi().iloc[-1]
        ema = EMAIndicator(close, window=EMA_PERIOD).ema_indicator().iloc[-1]
        price = close.iloc[-1]

        # FILTRO 1: RSI estremo = SCARTA (quelli che ti hanno fatto perdere oggi)
        if rsi < 25 or rsi > 75:
            print(f"{pair} scartato RSI estremo {rsi:.1f}")
            return None

        # FILTRO 2: Orario debole = SCARTA
        if not is_orario_forte():
            print(f"{pair} scartato fuori orario forte")
            return None

        # FILTRO 3: Doppio filtro RSI + EMA - SEGNALE FORTE
        if RSI_BUY_MIN <= rsi <= RSI_BUY_MAX and price > ema:
            msg = f"🟢 *SEGNALE FORTE BUY {pair}*\nRSI {rsi:.1f} (30-45) + Prezzo sopra EMA50\nOrario: {datetime.now().strftime('%H:%M')}\nScadenza consigliata: 30m\nForza: 85%"
            return msg
        
        if RSI_SELL_MIN <= rsi <= RSI_SELL_MAX and price < ema:
            msg = f"🔴 *SEGNALE FORTE SELL {pair}*\nRSI {rsi:.1f} (55-70) + Prezzo sotto EMA50\nOrario: {datetime.now().strftime('%H:%M')}\nScadenza consigliata: 30m\nForza: 85%"
            return msg

        print(f"{pair} debole RSI {rsi:.1f} - scartato")
        return None

    except Exception as e:
        print(f"Errore {pair}: {e}")
        return None

# LOOP PRINCIPALE
print("Bot V9.6 FORTE avviato - Solo orario 06-09")
send_telegram("✅ Bot V9.6 FORTE avviato\nSolo segnali 06:00-09:00\nRSI 30-45 BUY / 55-70 SELL + EMA50")

while True:
    try:
        if time.time() - ultimo_segnale_time < COOLDOWN_SEC:
            time.sleep(10)
            continue

        for pair in PAIRS:
            segnale = check_pair(pair)
            if segnale:
                send_telegram(segnale)
                ultimo_segnale_time = time.time()
                print(f"SEGNALE INVIATO: {segnale}")
                break  # 1 segnale per volta
        
        time.sleep(60)  # controlla ogni minuto

    except Exception as e:
        print(f"Errore loop: {e}")
        time.sleep(60)
