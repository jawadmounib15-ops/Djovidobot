# V36.8.9 SNIPER COMPLETO FINALE - PORT FIX + LOGICA TOP
import os, time, threading, requests
import yfinance as yf
import pandas as pd
import numpy as np
from flask import Flask
from datetime import datetime

# --- FLASK FIX PER RENDER ---
app = Flask(__name__)
@app.route('/')
def home(): return "V36.8.9 SNIPER COMPLETO LIVE - VIP"
def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- TOKEN ---
BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID")

def send_tg(msg):
    try:
        if not BOT_TOKEN or not CHAT_ID:
            print("TOKEN MANCANTI")
            return
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
        print(f"TG INVIATO: {msg[:80]}")
    except Exception as e:
        print(f"Errore TG: {e}")

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- CONFIG SNIPER ---
COPPIE = ["EURUSD=X", "GBPUSD=X", "EURGBP=X"]
# Mappatura per messaggio
NOMI = {"EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "EURGBP=X": "EUR/GBP"}

def analizza_coppia(symbol):
    try:
        df = yf.download(symbol, period="2d", interval="15m", progress=False)
        if len(df) < 50: return None

        close = df['Close']
        rsi = calc_rsi(close).iloc[-1]
        prezzo = close.iloc[-1]

        # --- LOGICA L2 L5 L6 (SIMULATA CON INDICATORI) ---
        # L2 = Trend forte (EMA 20 > EMA 50)
        ema20 = close.ewm(span=20).mean().iloc[-1]
        ema50 = close.ewm(span=50).mean().iloc[-1]
        has_L2_buy = ema20 > ema50
        has_L2_sell = ema20 < ema50

        # L5 = Momentum (RSI conferma)
        has_L5 = True # gia filtrato da RSI sotto

        # L6 = Anti-crollo (non comprare se sta crollando forte)
        # Se ultimi 3 candle tutti rossi e discesa >0.5% -> crollo -> blocca BUY
        ultime = close.tail(4)
        crollo = (ultime.iloc[-1] < ultime.iloc[-2] < ultime.iloc[-3]) and ((ultime.iloc[-1]-ultime.iloc[-3])/ultime.iloc[-3] < -0.005)
        has_L6 = not crollo

        # --- FILTRO SNIPER FINALE ---
        # BUY solo se L2+L5+L6 + RSI <=35
        if has_L2_buy and has_L5 and has_L6 and rsi <= 35:
            return f"✅✅✅ V.I.P ✅✅\n💎 *BUY {NOMI[symbol]}* - SNIPER TOP\n📉 RSI: {rsi:.1f} (ipervenduto)\n💰 Prezzo: {prezzo:.5f}\n✅ L2+L5+L6 confermati\n⏰ {datetime.now().strftime('%H:%M:%S')}"

        # SELL solo se L2+L5+L6 + RSI >=65
        if has_L2_sell and has_L5 and has_L6 and rsi >= 65:
            return f"✅✅✅ V.I.P ✅✅\n🔻 *SELL {NOMI[symbol]}* - SNIPER TOP\n📈 RSI: {rsi:.1f} (ipercomprato)\n💰 Prezzo: {prezzo:.5f}\n✅ L2+L5+L6 confermati\n⏰ {datetime.now().strftime('%H:%M:%S')}"

        return None
    except Exception as e:
        print(f"Errore {symbol}: {e}")
        return None

def bot_loop():
    time.sleep(5)
    send_tg("✅✅ 💯✅✅ V.I.P ✅✅ 💯✅✅\n✅ *V36.8.9 SNIPER PORT FIX ATTIVO - COMPLETO*\n\n🟢 Bot LIVE su Render - Fix 503 ok\n🔍 Filtro: L2+L5+L6 + RSI <=35 / >=65\n🚫 Anti-crollo attivo\n💎 Solo segnali TOP VIP")

    while True:
        try:
            for coppia in COPPIE:
                segnale = analizza_coppia(coppia)
                if segnale:
                    send_tg(segnale)
                    time.sleep(5)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Scansione fatta, nessun segnale TOP, attendo...")
            time.sleep(120) # ogni 2 minuti
        except Exception as e:
            print(f"Errore loop: {e}")
            time.sleep(30)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot_loop()
