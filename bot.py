import os
import time
import requests
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PAIR = "EUR/USD OTC"
COOLDOWN = 300

ultimo = 0
prezzi = []

def tg(m):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": m}, timeout=10)
        print(m)
    except Exception as e:
        print(f"Errore: {e}")

def get_price():
    try:
        r = requests.get("https://api.frankfurter.app/latest?from=EUR&to=USD", timeout=10)
        data = r.json()
        return float(data["rates"]["USD"])
    except:
        return None

def rsi(data):
    if len(data) < 15:
        return 50
    g = 0
    l = 0
    for i in range(-14, 0):
        d = data[i] - data[i-1]
        if d > 0:
            g += d
        else:
            l += -d
    if l == 0:
        return 100
    rs = (g / 14) / (l / 14)
    return 100 - (100 / (1 + rs))

def analizza():
    global ultimo, prezzi
    if time.time() - ultimo < COOLDOWN:
        return
    p = get_price()
    if not p:
        return
    prezzi.append(p)
    if len(prezzi) > 50:
        prezzi.pop(0)
    if len(prezzi) < 20:
        print(f"Raccolgo {len(prezzi)}/20 prezzo {p}")
        return
    ema9 = sum(prezzi[-9:]) / 9
    ema21 = sum(prezzi[-21:]) / 21
    rsi14 = rsi(prezzi)
    buy = 0
    sell = 0
    mot = []
    if ema9 > ema21:
        buy += 1
        mot.append("EMA BUY")
    else:
        sell += 1
        mot.append("EMA SELL")
    if rsi14 < 35:
        buy += 1
        mot.append(f"RSI {rsi14:.0f} BUY")
    elif rsi14 > 65:
        sell += 1
        mot.append(f"RSI {rsi14:.0f} SELL")
    if prezzi[-1] > prezzi[-5]:
        buy += 1
        mot.append("Trend UP")
    else:
        sell += 1
        mot.append("Trend DOWN")
    if buy >= 2:
        tg(f"BUY {PAIR} {datetime.now().strftime('%H:%M:%S')} {' | '.join(mot)}")
        ultimo = time.time()
    elif sell >= 2:
        tg(f"SELL {PAIR} {datetime.now().strftime('%H:%M:%S')} {' | '.join(mot)}")
        ultimo = time.time()
    else:
        print(f"Neutro B{buy} S{sell}")

tg("V36 LIVE SENZA QUOTEX - AVVIATO")
print("V36 AVVIATO CORRETTO")

while True:
    analizza()
    time.sleep(30)
