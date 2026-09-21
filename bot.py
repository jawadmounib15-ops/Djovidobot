import os, time, requests, yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"]
WIN = 0
LOSS = 0

pending = {}
last_check = 0

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        print(f"Errore send: {e}")

send("🚀 *V66 ULTRA LARGO AUTO ATTIVO*\nScansione 60sec | Calcolo AUTO 15min\nSenza bottoni - Regole LARGHISSIME")

print("Bot V66 ULTRA AUTO avviato")

while True:
    try:
        # 1. CALCOLO AUTO DOPO 15 MIN
        now = datetime.now()
        to_remove = []
        for pair, (signal, entry_price, entry_time) in list(pending.items()):
            if now - entry_time >= timedelta(minutes=15):
                try:
                    df = yf.download(pair, period="1d", interval="1m", progress=False)
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    curr_price = float(df["Close"].iloc[-1])

                    win = False
                    if signal == "BUY" and curr_price > entry_price:
                        win = True
                    if signal == "SELL" and curr_price < entry_price:
                        win = True

                    if win:
                        WIN += 1
                        result = "✅ WIN AUTO"
                    else:
                        LOSS += 1
                        result = "❌ LOSS AUTO"

                    tot = WIN + LOSS
                    wr = (WIN / tot * 100) if tot > 0 else 0
                    clean_pair = pair.replace("=X","")
                    send(f"{result} *{clean_pair} {signal}*\nEntrata: {entry_price:.5f}\nOra: {curr_price:.5f}\n📊 STATS: WIN {WIN} | LOSS {LOSS} | WR {wr:.1f}%")
                    to_remove.append(pair)
                except Exception as e:
                    print(f"Errore calc {pair}: {e}")

        for p in to_remove:
            if p in pending:
                del pending[p]

        # 2. SCANSIONE ULTRA LARGA OGNI 60 SEC
        if time.time() - last_check > 60:
            last_check = time.time()
            print(f"[{now}] Scansione ULTRA LARGA...")
            for pair in PAIRS:
                if pair in pending:
                    continue
                try:
                    df = yf.download(pair, period="1d", interval="5m", progress=False)
                    if len(df) < 25:
                        continue
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)

                    df["ema20"] = df["Close"].ewm(span=20).mean()
                    delta = df["Close"].diff()
                    gain = (delta.where(delta>0,0)).rolling(14).mean()
                    loss = (-delta.where(delta<0,0)).rolling(14).mean()
                    rs = gain / loss
                    df["rsi"] = 100 - (100/(1+rs))

                    last = df.iloc[-1]

                    signal = None
                    # ULTRA LARGO - uguale a V65
                    if last["Close"] > last["ema20"] and last["rsi"] > 50:
                        signal = "BUY"
                    elif last["Close"] < last["ema20"] and last["rsi"] < 50:
                        signal = "SELL"

                    if signal:
                        clean_pair = pair.replace("=X","")
                        pending[pair] = (signal, float(last["Close"]), now)
                        send(f"🔔 *V66 ULTRA {signal} {clean_pair}*\nPrice: {last['Close']:.5f}\nEMA20: {last['ema20']:.5f}\nRSI: {last['rsi']:.1f}\n\n⏳ Calcolo AUTO tra 15 min...")
                        print(f"SEGNALE {signal} {clean_pair}")
                except Exception as e:
                    print(f"Errore {pair}: {e}")

    except Exception as e:
        print(f"Errore loop: {e}")

    time.sleep(3)
