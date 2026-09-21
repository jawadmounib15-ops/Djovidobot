# V36.8.9 SNIPER COMPLETO - FIX TypeError Series - FINALE
import os, time, threading, requests
import yfinance as yf
import pandas as pd
from flask import Flask
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return "V36.8.9 FIX Series LIVE"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

print(f"AVVIO - TOKEN:{bool(BOT_TOKEN)} CHAT:{bool(CHAT_ID)}", flush=True)

def send_tg(msg):
    try:
        if not BOT_TOKEN or not CHAT_ID:
            print("TOKEN MANCANTI", flush=True)
            return
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
    except Exception as e:
        print(f"Errore TG:{e}", flush=True)

def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

COPPIE = {"EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "EURGBP=X": "EUR/GBP"}

def bot_loop():
    time.sleep(5)
    print("LOOP PARTITO - FIX Series", flush=True)
    send_tg("✅ *V36.8.9 FIX Series LIVE*\n🟢 Bot ripartito dopo fix errore Series\n🔍 Scansione ogni 2 min")

    while True:
        try:
            for symbol, nome in COPPIE.items():
                df = yf.download(symbol, period="2d", interval="15m", progress=False, auto_adjust=True)
                if df is None or len(df) < 55:
                    print(f"{nome} no data {len(df) if df is not None else 0}", flush=True)
                    continue

                # --- FIX PER ERRORE SERIES ---
                close_raw = df['Close']
                # Se è DataFrame, prendi prima colonna
                if isinstance(close_raw, pd.DataFrame):
                    close = close_raw.iloc[:, 0]
                else:
                    close = close_raw
                # Squeeze per sicurezza
                close = pd.Series(close).squeeze()
                # --------------------------------

                rsi_series = calc_rsi(close)
                rsi = float(rsi_series.iloc[-1])
                prezzo = float(close.iloc[-1])
                ema20 = float(close.ewm(span=20).mean().iloc[-1])
                ema50 = float(close.ewm(span=50).mean().iloc[-1])

                c1 = float(close.iloc[-1])
                c2 = float(close.iloc[-2])
                c3 = float(close.iloc[-3])
                crollo = (c1 < c2 and c2 < c3 and (c1 - c3) / c3 < -0.005)

                print(f"[{datetime.now().strftime('%H:%M:%S')}] {nome} RSI:{rsi:.1f} P:{prezzo:.5f} Buy:{ema20>ema50} Crollo:{crollo}", flush=True)

                if ema20 > ema50 and not crollo and rsi <= 35:
                    send_tg(f"✅ *BUY {nome}* RSI {rsi:.1f} - {prezzo:.5f}")
                if ema20 < ema50 and not crollo and rsi >= 65:
                    send_tg(f"🔻 *SELL {nome}* RSI {rsi:.1f} - {prezzo:.5f}")

            print("--- Scan OK attendo 2m ---", flush=True)
            time.sleep(120)

        except Exception as e:
            print(f"ERRORE LOOP: {e}", flush=True)
            import traceback
            traceback.print_exc()
            time.sleep(30)

threading.Thread(target=run_flask, daemon=True).start()
threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    while True:
        time.sleep(3600)
