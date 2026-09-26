import os, time, requests, yfinance as yf, threading, pandas as pd
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V138 FINALE 15 LAVORI TF + 15 OTC"

TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("BOT_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("CHAT_ID")

# 15 COPPIE OTC
SYMBOLS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCHF=X","EURGBP=X","AUDJPY=X","EURNZD=X","GBPCHF=X","EURCAD=X","AUDCAD=X","CHFJPY=X","NZDUSD=X"]
PAIRS = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","EUR/JPY-OTC","GBP/JPY-OTC","USD/CHF-OTC","EUR/GBP-OTC","AUD/JPY-OTC","EUR/NZD-OTC","GBP/CHF-OTC","EUR/CAD-OTC","AUD/CAD-OTC","CHF/JPY-OTC","NZD/USD-OTC"]

COOLDOWN = {}
def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass
def ok(pair, lavoro, sec=60):
    k=f"{pair}_{lavoro}"
    if k in COOLDOWN and time.time()-COOLDOWN[k] < sec: return False
    COOLDOWN[k]=time.time()
    return True
def wick(o,h,l,c):
    rng=h-l
    if rng==0: return 0,0,100
    return ((min(o,c)-l)/rng)*100, ((h-max(o,c))/rng)*100, (abs(o-c)/rng)*100

def bot():
    time.sleep(2)
    send("🔥 *V138 FINALE ONLINE*\n15 Lavori + TF per ogni lavoro + 15 Coppie OTC\nSABATO MODE 2% per far lavorare tutte le coppie")
    while True:
        for yahoo, pair in zip(SYMBOLS, PAIRS):
            try:
                time.sleep(1.0)
                df1 = yf.download(yahoo, period="5d", interval="1m", progress=False, auto_adjust=True)
                if df1.empty: continue
                if isinstance(df1.columns, pd.MultiIndex): df1.columns = df1.columns.get_level_values(0)
                df1 = df1.dropna()
                if len(df1)<20: continue
                df5 = df1.resample('5min').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
                df1h = df1.resample('1h').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
                df4h = df1.resample('4h').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()

                o1=float(df1["Open"].values[-2]); h1=float(df1["High"].values[-2]); l1=float(df1["Low"].values[-2]); c1=float(df1["Close"].values[-2])
                op=float(df1["Open"].values[-3]); cp=float(df1["Close"].values[-3])
                o5=float(df5["Open"].values[-2]) if len(df5)>=2 else o1; h5=float(df5["High"].values[-2]) if len(df5)>=2 else h1; l5=float(df5["Low"].values[-2]) if len(df5)>=2 else l1; c5=float(df5["Close"].values[-2]) if len(df5)>=2 else c1
                o1h=float(df1h["Open"].values[-2]) if len(df1h)>=2 else o1; h1h=float(df1h["High"].values[-2]) if len(df1h)>=2 else h1; l1h=float(df1h["Low"].values[-2]) if len(df1h)>=2 else l1; c1h=float(df1h["Close"].values[-2]) if len(df1h)>=2 else c1
                o4h=float(df4h["Open"].values[-2]) if len(df4h)>=2 else o1h; h4h=float(df4h["High"].values[-2]) if len(df4h)>=2 else h1h; l4h=float(df4h["Low"].values[-2]) if len(df4h)>=2 else l1h; c4h=float(df4h["Close"].values[-2]) if len(df4h)>=2 else c1h

                wb1,ws1,bd1=wick(o1,h1,l1,c1); wb5,ws5,bd5=wick(o5,h5,l5,c5); wb1h,ws1h,bd1h=wick(o1h,h1h,l1h,c1h); wb4h,ws4h,bd4h=wick(o4h,h4h,l4h,c4h)

                # SABATO MODE: soglia bassa per far suonare tutte le 15 coppie
                # Lunedì cambi 2 -> 10

                # === 15 LAVORI TUTTI CON TF ===

                # L1 (M1) 30%
                if wb1>=25 and bd1<35 and c1>o1 and ok(pair,"L1"):
                    send(f"🔨 *L1 (M1) HAMMER BUY {pair}*\n⏰ TF: M1 | Wick:{wb1:.0f}% | {c1:.5f}\n👉 POCKET M1")
                # L2 (M1) 30%
                if ws1>=25 and bd1<35 and c1<o1 and ok(pair,"L2"):
                    send(f"💫 *L2 (M1) SHOOT SELL {pair}*\n⏰ TF: M1 | Wick:{ws1:.0f}% | {c1:.5f}\n👉 POCKET M1")
                # L3 (M1) ENGULF
                if c1>o1 and cp<op and ok(pair,"L3"):
                    send(f"🔄 *L3 (M1) ENGULF BUY {pair}*\n⏰ TF: M1 | {c1:.5f}\n👉 POCKET M1")
                # L4 (M1) ENGULF
                if c1<o1 and cp>op and ok(pair,"L4"):
                    send(f"🔄 *L4 (M1) ENGULF SELL {pair}*\n⏰ TF: M1 | {c1:.5f}\n👉 POCKET M1")
                # L5 (M1) 2x TREND
                if c1>o1 and cp>op and ok(pair,"L5"):
                    send(f"📈 *L5 (M1) 2x BUY {pair}*\n⏰ TF: M1 | {c1:.5f}\n👉 POCKET M1")
                # L6 (M1) 2x TREND
                if c1<o1 and cp<op and ok(pair,"L6"):
                    send(f"📉 *L6 (M1) 2x SELL {pair}*\n⏰ TF: M1 | {c1:.5f}\n👉 POCKET M1")
                # L7 (M1) 15%
                if wb1>=15 and bd1<45 and c1>o1 and ok(pair,"L7"):
                    send(f"⚡ *L7 (M1) PIN BUY {pair}*\n⏰ TF: M1 | Wick:{wb1:.0f}% | {c1:.5f}\n👉 POCKET M1")
                # L8 (M1) 15%
                if ws1>=15 and bd1<45 and c1<o1 and ok(pair,"L8"):
                    send(f"⚡ *L8 (M1) PIN SELL {pair}*\n⏰ TF: M1 | Wick:{ws1:.0f}% | {c1:.5f}\n👉 POCKET M1")
                # L9 (M5) 15% - SABATO 2% per far lavorare tutte
                if wb5>=2 and bd5<60 and c5>o5 and ok(pair,"L9"):
                    send(f"📌 *L9 (M5) PIN BUY {pair}*\n⏰ TF: M5 | Wick M5:{wb5:.0f}% | {c1:.5f}\n👉 POCKET M5")
                # L10 (M5) 15%
                if ws5>=2 and bd5<60 and c5<o5 and ok(pair,"L10"):
                    send(f"📌 *L10 (M5) PIN SELL {pair}*\n⏰ TF: M5 | Wick M5:{ws5:.0f}% | {c1:.5f}\n👉 POCKET M5")
                # L11 (M1) 5% LEGGERO
                if wb1>=2 and c1>o1 and ok(pair,"L11"):
                    send(f"💡 *L11 (M1) LEGGERO BUY {pair}*\n⏰ TF: M1 | Wick:{wb1:.0f}% | {c1:.5f}\n👉 POCKET M1")
                # L12 (M1) 5% LEGGERO
                if ws1>=2 and c1<o1 and ok(pair,"L12"):
                    send(f"💡 *L12 (M1) LEGGERO SELL {pair}*\n⏰ TF: M1 | Wick:{ws1:.0f}% | {c1:.5f}\n👉 POCKET M1")
                # L13 (1H) 15%
                if wb1h>=2 and c1h>o1h and ok(pair,"L13", 100):
                    send(f"🕐 *L13 (1H) BUY {pair}*\n⏰ TF: 1H | Wick 1H:{wb1h:.0f}% | {c1:.5f}\n👉 POCKET 1H")
                # L14 (1H) 15%
                if ws1h>=2 and c1h<o1h and ok(pair,"L14", 100):
                    send(f"🕐 *L14 (1H) SELL {pair}*\n⏰ TF: 1H | Wick 1H:{ws1h:.0f}% | {c1:.5f}\n👉 POCKET 1H")
                # L15 (4H) 15%
                if wb4h>=2 and c4h>o4h and ok(pair,"L15", 150):
                    send(f"🏛️ *L15 (4H) BUY {pair}*\n⏰ TF: 4H | Wick 4H:{wb4h:.0f}% | {c1:.5f}\n👉 POCKET 4H")
                if ws4h>=2 and c4h<o4h and ok(pair,"L15S", 150):
                    send(f"🏛️ *L15 (4H) SELL {pair}*\n⏰ TF: 4H | Wick 4H:{ws4h:.0f}% | {c1:.5f}\n👉 POCKET 4H")

            except: continue
        time.sleep(3)

threading.Thread(target=bot, daemon=True).start()
app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
