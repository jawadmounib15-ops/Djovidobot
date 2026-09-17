import yfinance as yf
import time
import requests
import os
import threading
from flask import Flask

# --- PER RENDER - SITO FITTO COSI NON SI SPEGNE ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🟢 V12 75% LIVE - 21 coppie attive - Pa!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web, daemon=True).start()
# --- FINE FIX RENDER ---

# --- DATI TELEGRAM - METTI I TUOI QUI PA ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
# --- 21 COPPIE REALI TUE ---
COPPIE_POCKET = [
    "USD/JPY", "AUD/JPY", "AUD/CHF", "GBP/USD", "CAD/JPY",
    "CHF/JPY", "AUD/USD", "GBP/CAD", "USD/CHF", "EUR/JPY",
    "USD/CAD", "EUR/CHF", "EUR/GBP", "AUD/CAD", "GBP/CHF",
    "GBP/AUD", "EUR/USD", "GBP/JPY", "EUR/CAD", "CAD/CHF", "EUR/AUD"
]

def converti(nome):
    return nome.replace("/", "") + "=X"

COPPIE_YF = [converti(c) for c in COPPIE_POCKET]
ENGULFING = 0.75

def manda_telegram(messaggio):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": messaggio}, timeout=10)
    except Exception as e:
        print(f"Telegram errore: {e}")

def analizza():
    print(">>> Inizio giro 21 coppie...")
    for i, simbolo_yf in enumerate(COPPIE_YF):
        nome_pocket = COPPIE_POCKET[i]
        try:
            df = yf.download(simbolo_yf, period="3d", interval="15m", progress=False, auto_adjust=True)
            if len(df) < 200:
                continue

            # LAVORO 1 - TREND EMA 50/200
            ema50 = df['Close'].ewm(span=50).mean().iloc[-1].item()
            ema200 = df['Close'].ewm(span=200).mean().iloc[-1].item()
            trend = "BUY" if ema50 > ema200 else "SELL"

            # LAVORO 2 - ENGULFING 75%
            ultima = df.iloc[-1]
            prec = df.iloc[-2]
            corpo_ult = abs(float(ultima['Close'].iloc[0] if hasattr(ultima['Close'], 'iloc') else ultima['Close']) - float(ultima['Open'].iloc[0] if hasattr(ultima['Open'], 'iloc') else ultima['Open']))
            corpo_prec = abs(float(prec['Close'].iloc[0] if hasattr(prec['Close'], 'iloc') else prec['Close']) - float(prec['Open'].iloc[0] if hasattr(prec['Open'], 'iloc') else prec['Open']))
            if corpo_prec == 0:
                continue
            rapporto = corpo_ult / corpo_prec

            engulf = None
            close_u = float(ultima['Close'].iloc[0] if hasattr(ultima['Close'], 'iloc') else ultima['Close'])
            open_u = float(ultima['Open'].iloc[0] if hasattr(ultima['Open'], 'iloc') else ultima['Open'])
            if rapporto >= ENGULFING:
                engulf = "BUY" if close_u > open_u else "SELL"

            # LAVORO 3 - SICURO
            if engulf and trend == engulf:
                msg = f"🟢 SEGNALE SICURO 75% - {nome_pocket} - {trend}\n3 LAVORI OK - Ratio: {rapporto:.2f}"
                print(msg)
                manda_telegram(msg)

        except Exception as e:
            print(f"Errore {nome_pocket}: {e}")

print("V12 75% AVVIATO - 21 COPPIE REALI - FIX RENDER")
manda_telegram("🟢 V12 75% AVVIATO - FIX RENDER\n21 coppie attive\nNon si spegne più!")

while True:
    analizza()
    print("Giro finito, aspetto 15 min...")
    time.sleep(900)
