# V35.8 COMPLETO - SOLO EUR/USD OTC - 5 MIN - FIX SYNTAX
import os
import time
import requests
from datetime import datetime

# CONFIG - METTI LE TUE VARIABILI SU RENDER
PAIR = "EUR/USD OTC"
COOLDOWN = 300  # 5 minuti
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ultimo_segale = 0

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        print(f"Telegram inviato: {msg}")
    except Exception as e:
        print(f"Err Telegram: {e}")

def analizza_finto_test():
    # TEST PER FAR PARTIRE RENDER SENZA PANDAS PESANTE
    # Quando va Live, sostituiamo con candele vere Quotex
    global ultimo_segale
    if time.time() - ultimo_segale < COOLDOWN:
        return
    
    # Simula analisi seria
    ora = datetime.now().strftime("%H:%M:%S")
    segnale = "BUY"  # per test
    msg = f"🔔 {PAIR} - {segnale} - TEST {ora} - Cooldown 5min OK"
    send_telegram(msg)
    ultimo_segale = time.time()
    print(msg)

# AVVIO
if __name__ == "__main__":
    print(f"--- BOT V35.8 AVVIATO {PAIR} ---")
    send_telegram(f"✅ V35.8 LIVE - {PAIR} - Cooldown 5min - Fixato")
    
    while True:
        # QUI COLLEGHERAI LE CANDELE VERE QUOTEX
        # Per ora test ogni 5 min per vedere se Render funziona
        analizza_finto_test()
        time.sleep(30)
