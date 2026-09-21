import os, time, requests, yfinance as yf
import pandas as pd
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"]
WIN = 0
LOSS = 0
last_check = 0

def send(msg, reply_markup=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        if reply_markup:
            data["reply_markup"] = reply_markup
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        print(f"Errore send: {e}")

# MESSAGGIO AVVIO - così sai che è partito
send("🚀 *V65 ULTRA LARGO ATTIVO*\nScansione ogni 60sec\nRegole LARGHISSIME\nIn attesa segnali...")

print("Bot V65 avviato...")

while True:
    try:
        # Check bottoni WIN/LOSS
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            r = requests.get(url, timeout=10).json()
            if r.get("result"):
                for upd in r["result"][-5:]:
                    if "callback_query" in upd:
                        cq = upd["callback_query"]
                        data = cq["data"]
                        if "|" in data:
                            _, pair, d = data.split("|")
                            if "WIN" in data:
                                WIN += 1
                            else:
                                LOSS += 1
                            tot = WIN+LOSS
                            wr = (WIN/tot*100) if tot>0 else 0
                            send(f"✅ *{data.split('|')[0]}* {pair} {d}\n📊 STATS: WIN {WIN} | LOSS {LOSS}\nWinrate: {wr:.1f}%")
                            # cancella update
                            requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={upd['update_id']+1}", timeout=5)
        except:
            pass

        # SCANSIONE OGNI 60 SEC
        if time.time() - last_check > 60:
            last_check = time.time()
            print(f"[{datetime.now()}] Scansione...")
            for pair in PAIRS:
                try:
                    df = yf.download(pair, period="1d", interval="5m", progress=False)
                    if len(df) < 25: continue
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    df["ema20"] = df["Close"].ewm(span=20).mean()
                    # RSI semplice
                    delta = df["Close"].diff()
                    gain = (delta.where(delta>0,0)).rolling(14).mean()
                    loss = (-delta.where(delta<0,0)).rolling(14).mean()
                    rs = gain / loss
                    df["rsi"] = 100 - (100/(1+rs))
                    last = df.iloc[-1]

                    signal = None
                    # REGOLE ULTRA LARGHE - senza incrocio, solo posizione!
                    if last["Close"] > last["ema20"] and last["rsi"] > 50:
                        signal = "BUY"
                    elif last["Close"] < last["ema20"] and last["rsi"] < 50:
                        signal = "SELL"

                    if signal:
                        clean_pair = pair.replace("=X","")
                        msg = f"🔔 *V65 ULTRA LARGO {signal} {clean_pair}*\nPrice: {last['Close']:.5f}\nEMA20: {last['ema20']:.5f}\nRSI: {last['rsi']:.1f}"
                        kb = {"inline_keyboard": [[{"text":"✅ WIN","callback_data":f"WIN|{clean_pair}|{signal}"},{"text":"❌ LOSS","callback_data":f"LOSS|{clean_pair}|{signal}"}]]}
                        send(msg, kb)
                        print(f"SEGNALE {signal} {clean_pair}")
                except Exception as e:
                    print(f"Errore {pair}: {e}")

    except Exception as e:
        print(f"Errore loop: {e}")

    time.sleep(3)
