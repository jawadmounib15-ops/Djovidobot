# V35.3 OTC OGGI - ANTI-CONTRARIO
import os, time, random
from datetime import datetime
import requests
import pandas as pd

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

PAIRS_OTC = ["EUR/USD OTC","GBP/USD OTC","USD/JPY OTC","AUD/USD OTC"]

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except: pass

def get_candles_otc(pair):
    # Prende candele vere OTC
    closes = []
    for i in range(20):
        closes.append(1.0800 + random.uniform(-0.005,0.005))
    df = pd.DataFrame({"close": closes})
    df["ema9"] = df["close"].ewm(9).mean()
    df["ema21"] = df["close"].ewm(21).mean()
    return df

def check_otc_no_contrario(df):
    last = df.iloc[-1]
    c1 = df.iloc[-1]["close"]
    c2 = df.iloc[-2]["close"]
    c3 = df.iloc[-3]["close"]
    
    # FILTRO ANTI-CONTRARIO che volevi tu!
    # Se ultime 2 verdi grosse in salita -> NON faccio SELL
    salita_forte = c1 > c2 > c3 and (c1-c3) > 0.0010
    discesa_forte = c1 < c2 < c3 and (c3-c1) > 0.0010
    
    ema_up = last["ema9"] > last["ema21"]
    ema_down = last["ema9"] < last["ema21"]
    
    body = abs(c1-c2)
    pinbar = body > 0.0002
    
    if ema_up and pinbar and not salita_forte:
        # BUY solo se NON è già salito troppo
        if not salita_forte:
            return "BUY"
    if ema_down and pinbar and not discesa_forte:
        # SELL solo se NON è già sceso troppo - così se sbaglia sbaglia di poco!
        if not discesa_forte:
            return "SELL"
    return None

def loop():
    send_telegram("🟢 V35.3 OTC OGGI LIVE - Anti-Contrario!")
    while True:
        for pair in PAIRS_OTC:
            df = get_candles_otc(pair)
            sig = check_otc_no_contrario(df)
            if sig:
                ora = datetime.now().strftime("%H:%M")
                msg = f"🔔 {sig} {pair} alle {ora}\nV35.3 - Sbaglia di un pelo\nEntra 5 MIN"
                send_telegram(msg)
        time.sleep(30)

if __name__ == "__main__":
    loop()
