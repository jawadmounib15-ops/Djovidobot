# bot.py - V9.6 ULTRA FORTE - TUTTO IL GIORNO
import os
import time
import requests
import yfinance as yf
from datetime import datetime
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# CONFIG ULTRA FORTE
PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "EURJPY=X", "GBPJPY=X"]
RSI_BUY_MIN = 30
RSI_BUY_MAX = 42  # più stretto = più forte
RSI_SELL_MIN = 58 # più stretto = più forte
RSI_SELL_MAX = 70
EMA_PERIOD = 50
EMA_TREND = 200
COOLDOWN = 20 * 60  # 20 min tra segnali

ultimo_segnale = 0

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"Err telegram: {e}")

def is_strong_signal(rsi, price, ema50, ema200):
    # FILTRO 1: Scarta RSI estremi - troppo pericoloso
    if rsi < 28 or rsi > 72:
        return False, f"Scartato RSI estremo {rsi:.1f}"

    # FILTRO 2: Scarta zona neutra 42-58 - troppo debole
    if 42 < rsi < 58:
        return False, f"Scartato zona neutra {rsi:.1f}"

    # FILTRO 3: BUY ULTRA FORTE - 3 conferme insieme
    # RSI 30-42 + prezzo > EMA50 + EMA50 > EMA200 (trend su forte)
    if RSI_BUY_MIN <= rsi <= RSI_BUY_MAX:
        if price > ema50 and ema50 > ema200:
            forza = 90 if rsi < 35 else 85
            return True, f"🟢 *BUY ULTRA FORTE*\nRSI {rsi:.1f} + EMA50>EMA200\nForza: {forza}%\nScadenza: 30m"
    
    # FILTRO 4: SELL ULTRA FORTE - 3 conferme insieme
    # RSI 58-70 + prezzo < EMA50 + EMA50 < EMA200 (trend giù forte)
    if RSI_SELL_MIN <= rsi <= RSI_SELL_MAX:
        if price < ema50 and ema50 < ema200:
            forza = 90 if rsi > 65 else 85
            return True, f"🔴 *SELL ULTRA FORTE*\nRSI {rsi:.1f} + EMA50<EMA200\nForza: {forza}%\nScadenza: 30m"

    return False, f"Debole scartato RSI {rsi:.1f}"

print("Bot V9.6 ULTRA FORTE avviato - TUTTO IL GIORNO")
send_telegram("✅ *Bot V9.6 ULTRA FORTE attivo*\nTutto il giorno\nSolo segnali 85-90%\nRSI 30-42 BUY / 58-70 SELL + Doppia EMA")

while True:
    try:
        # Tutto il giorno - nessun filtro orario
        if time.time() - ultimo_segnale < COOLDOWN:
            time.sleep(30)
            continue

        for pair in PAIRS:
            try:
                df = yf.download(pair, period="3d", interval="5m", progress=False, auto_adjust=True)
                if len(df) < 210:
                    continue
                
                close = df['Close']
                rsi = float(RSIIndicator(close, window=14).rsi().iloc[-1])
                ema50 = float(EMAIndicator(close, window=EMA_PERIOD).ema_indicator().iloc[-1])
                ema200 = float(EMAIndicator(close, window=EMA_TREND).ema_indicator().iloc[-1])
                price = float(close.iloc[-1])

                forte, msg = is_strong_signal(rsi, price, ema50, ema200)
                
                if forte:
                    testo = f"{msg}\nPair: {pair}\nPrezzo: {price:.5f}\nOra: {datetime.now().strftime('%H:%M:%S')}"
                    send_telegram(testo)
                    print(f"SEGNALE FORTE INVIATO: {pair} - {msg}")
                    ultimo_segnale = time.time()
                    break
                else:
                    print(f"{pair} {msg}")

            except Exception as e:
                print(f"Errore {pair}: {e}")
                continue
        
        time.sleep(60)

    except Exception as e:
        print(f"Errore loop principale: {e}")
        time.sleep(60)
