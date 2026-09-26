import os, time, requests, yfinance as yf, threading, pandas as pd
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V134 15 LAVORI TUTTI VIVI"

TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("BOT_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("CHAT_ID")

SYMBOLS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCHF=X","EURGBP=X","AUDJPY=X","EURNZD=X","GBPCHF=X","EURCAD=X","AUDCAD=X","CHFJPY=X","NZDUSD=X"]
PAIRS = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","EUR/JPY-OTC","GBP/JPY-OTC","USD/CHF-OTC","EUR/GBP-OTC","AUD/JPY-OTC","EUR/NZD-OTC","GBP/CHF-OTC","EUR/CAD-OTC","AUD/CAD-OTC","CHF/JPY-OTC","NZD/USD-OTC"]

COOLDOWN = {}

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass

def ok(pair, lavoro, sec=50):
    key = f"{pair}_{lavoro}"
    if key in COOLDOWN and time.time() - COOLDOWN[key] < sec: return False
    COOLDOWN[key] = time.time()
    return True

def bot():
    time.sleep(3)
    send("🔥 *V134 15 LAVORI TUTTI VIVI*\nOgni lavoro ha timer suo - ORA FUNZIONANO TUTTI!")
    while True:
        for yahoo, pair in zip(SYMBOLS, PAIRS):
            try:
                time.sleep(1.2)
                df = yf.download(yahoo, period="1d", interval="1m", progress=False, auto_adjust=True)
                if df.empty: continue
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                df = df.dropna()
                if len(df) < 4: continue

                o = float(df["Open"].values[-2]); h = float(df["High"].values[-2]); l = float(df["Low"].values[-2]); c = float(df["Close"].values[-2])
                op = float(df["Open"].values[-3]); cp = float(df["Close"].values[-3])
                rng = h - l
                if rng == 0: continue
                wick_buy = ((min(o,c)-l)/rng)*100
                wick_sell = ((h-max(o,c))/rng)*100

                # 15 LAVORI - TUTTI IF SEPARATI - NESSUN ELIF!

                # L1
                if wick_buy >= 30 and c > o and ok(pair,"L1"):
                    send(f"🔨 *L1 HAMMER BUY {pair}* {wick_buy:.0f}% {c:.5f}")
                # L2
                if wick_sell >= 30 and c < o and ok(pair,"L2"):
                    send(f"💫 *L2 SHOOT SELL {pair}* {wick_sell:.0f}% {c:.5f}")
                # L3
                if c > o and cp < op and c > op and ok(pair,"L3"):
                    send(f"🔄 *L3 ENGULF BUY {pair}* {c:.5f}")
                # L4
                if c < o and cp > op and c < op and ok(pair,"L4"):
                    send(f"🔄 *L4 ENGULF SELL {pair}* {c:.5f}")
                # L5
                if c > o and cp > op and ok(pair,"L5"):
                    send(f"📈 *L5 2x BUY {pair}* {c:.5f}")
                # L6
                if c < o and cp < op and ok(pair,"L6"):
                    send(f"📉 *L6 2x SELL {pair}* {c:.5f}")
                # L7
                if wick_buy >= 15 and c > o and ok(pair,"L7"):
                    send(f"⚡ *L7 PIN BUY {pair}* {wick_buy:.0f}% {c:.5f}")
                # L8
                if wick_sell >= 15 and c < o and ok(pair,"L8"):
                    send(f"⚡ *L8 PIN SELL {pair}* {wick_sell:.0f}% {c:.5f}")
                # L9
                if wick_buy >= 8 and c > o and ok(pair,"L9"):
                    send(f"📌 *L9 DOPPIA BUY {pair}* {wick_buy:.0f}% {c:.5f}")
                # L10
                if wick_sell >= 8 and c < o and ok(pair,"L10"):
                    send(f"📌 *L10 DOPPIA SELL {pair}* {wick_sell:.0f}% {c:.5f}")
                # L11
                if wick_buy >= 3 and c > o and ok(pair,"L11"):
                    send(f"💡 *L11 LEGGERO BUY {pair}* {wick_buy:.0f}% {c:.5f}")
                # L12
                if wick_sell >= 3 and c < o and ok(pair,"L12"):
                    send(f"💡 *L12 LEGGERO SELL {pair}* {wick_sell:.0f}% {c:.5f}")
                # L13
                if wick_buy >= 50 and c > o and ok(pair,"L13", 80):
                    send(f"⭐ *L13 SUPER BUY {pair}* {wick_buy:.0f}% {c:.5f}")
                # L14
                if wick_sell >= 50 and c < o and ok(pair,"L14", 80):
                    send(f"⭐ *L14 SUPER SELL {pair}* {wick_sell:.0f}% {c:.5f}")
                # L15
                if c > o and ok(pair,"L15", 30):
                    send(f"🔥 *L15 TREND BUY {pair}* {c:.5f}")

            except Exception as e:
                continue
        time.sleep(2)

threading.Thread(target=bot, daemon=True).start()
app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
