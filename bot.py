# bot.py - V9.6 FORTE - Logica Invertita + Doppio Filtro
import os
import time
import requests
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

RSI_BUY_MIN = 30
RSI_BUY_MAX = 45
RSI_SELL_MIN = 55
RSI_SELL_MAX = 70
COOLDOWN = 30 * 60  # 30 min in secondi

ultimo_segnale = 0

def is_strong_signal(rsi, price, ema):
    if rsi < 25 or rsi > 75:
        return False, None
    
    # BUY FORTE: RSI basso + sopra EMA50
    if RSI_BUY_MIN <= rsi <= RSI_BUY_MAX and price > ema:
        return True, f"🟢 BUY FORTE {rsi} - RSI {rsi} + EMA50 OK - 30m"
    
    # SELL FORTE: RSI alto + sotto EMA50
    if RSI_SELL_MIN <= rsi <= RSI_SELL_MAX and price < ema:
        return True, f"🔴 SELL FORTE {rsi} - RSI {rsi} + EMA50 OK - 30m"
    
    return False, None

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# Qui dentro metti il tuo loop che calcola rsi, price, ema
# Esempio:
# forte, messaggio = is_strong_signal(rsi, price, ema)
# if forte:
#     send_telegram(messaggio)
