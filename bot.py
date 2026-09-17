import yfinance as yf
import os, time, threading, requests
import pandas as pd
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print("--- V9.3 SICURO - POCHI MA BUONISSIMI ---")

COPPIE = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "EURJPY=X",
    "EURCAD=X", "USDCHF=X", "AUDUSD=X", "EURGBP=X"
]

app = Flask(__name__)

@app.route('/')
def home():
    return "V9.3 ONLINE - SICURO"

last_global = 0

def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except:
        pass

def loop():
    global last_global
    print("Loop V9.3 avviato")
    send("✅ V9.3 SICURO ONLINE - 8 coppie, max 1 ogni 15min, RSI 60/40")
    while True:
        if time.time() - last_global < 900:
            time.sleep(60)
            continue

        candidati = []
        for pair in COPPIE:
            try:
                df = yf.download(pair, period="5d", interval="15m", progress=False, auto_adjust=True)
                if len(df) < 210:
                    continue

                c = df['Close']
                if isinstance(c, pd.DataFrame):
                    c = c.iloc[:, 0]

                close = float(c.iloc[-1])
                prev = float(c.iloc[-2])

                o = df['Open']
                if isinstance(o, pd.DataFrame):
                    o = o.iloc[:, 0]
                open_price = float(o.iloc[-1])

                ema50 = float(c.ewm(span=50).mean().iloc[-1])
                ema200 = float(c.ewm(span=200).mean().iloc[-1])

                delta = c.diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = -delta.where(delta < 0, 0).rolling(14).mean()
                rsi = float(100 - (100 / (1 + gain.iloc[-1] / loss.iloc[-1])))

                corpo = abs(close - open_price) / close * 100
                if corpo < 0.02:
                    continue

                score = abs(close - ema50) / close * 100 + abs(rsi - 50) / 10 + corpo

                if prev < ema50 and close > ema50 and close > ema200 and rsi >= 60:
                    candidati.append((score, f"🟢 BUY SICURO {pair.replace('=X','')} @ {close:.5f} RSI:{rsi:.0f}"))
                elif prev > ema50 and close < ema50 and close < ema200 and rsi <= 40:
                    candidati.append((score, f"🔴 SELL SICURO {pair.replace('=X','')} @ {close:.5f} RSI:{rsi:.0f}"))
            except:
                continue

        if candidati:
            candidati.sort(reverse=True)
            send(candidati[0][1])
            last_global = time.time()
            print(f"Inviato: {candidati[0][1]}")

        time.sleep(120)

threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
