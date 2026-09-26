import os, time, requests, yfinance as yf, threading, pandas as pd
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V141 ULTRA STRETTO 35%"

TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("BOT_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("CHAT_ID")

SYMBOLS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCHF=X","EURGBP=X","AUDJPY=X","EURNZD=X","GBPCHF=X","EURCAD=X","AUDCAD=X","CHFJPY=X","NZDUSD=X"]
PAIRS = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","EUR/JPY-OTC","GBP/JPY-OTC","USD/CHF-OTC","EUR/GBP-OTC","AUD/JPY-OTC","EUR/NZD-OTC","GBP/CHF-OTC","EUR/CAD-OTC","AUD/CAD-OTC","CHF/JPY-OTC","NZD/USD-OTC"]

COOLDOWN = {}
LAST_PAIR = {} # 1 segnale ogni 5 min per coppia
def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass
def ok(pair, lavoro, sec=300): # 5 MINUTI cooldown
    k=f"{pair}_{lavoro}"
    if pair in LAST_PAIR and time.time()-LAST_PAIR[pair] < 300: return False # 1 ogni 5 min max per coppia
    if k in COOLDOWN and time.time()-COOLDOWN[k] < sec: return False
    COOLDOWN[k]=time.time()
    LAST_PAIR[pair]=time.time()
    return True
def wick(o,h,l,c):
    rng=h-l
    if rng==0: return 0,0,100
    return ((min(o,c)-l)/rng)*100, ((h-max(o,c))/rng)*100, (abs(o-c)/rng)*100

def bot():
    time.sleep(2)
    send("🔒 *V141 ULTRA STRETTO 35% ONLINE*\nSolo wick 35%+ e 1 segnale ogni 5 min per coppia - ZERO SPAM!")
    while True:
        for yahoo, pair in zip(SYMBOLS, PAIRS):
            try:
                time.sleep(1.2)
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

                # ULTRA STRETTO 35-45%

                if wb1>=45 and bd1<25 and c1>o1 and ok(pair,"L1",300):
                    send(f"🔨 *L1 (M1) BUY {pair}*\n⏰ TF: M1 | Wick:{wb1:.0f}%\n⏳ *SCADENZA: 2 MIN* | {c1:.5f}")
                    continue
                if ws1>=45 and bd1<25 and c1<o1 and ok(pair,"L2",300):
                    send(f"💫 *L2 (M1) SELL {pair}*\n⏰ TF: M1 | Wick:{ws1:.0f}%\n⏳ *SCADENZA: 2 MIN* | {c1:.5f}")
                    continue

                if wb5>=35 and bd5<30 and c5>o5 and ok(pair,"L9",300):
                    send(f"📌 *L9 (M5) BUY {pair}*\n⏰ TF: M5 | Wick:{wb5:.0f}%\n⏳ *SCADENZA: 5 MIN* | {c1:.5f}")
                    continue
                if ws5>=35 and bd5<30 and c5<o5 and ok(pair,"L10",300):
                    send(f"📌 *L10 (M5) SELL {pair}*\n⏰ TF: M5 | Wick:{ws5:.0f}%\n⏳ *SCADENZA: 5 MIN* | {c1:.5f}")
                    continue

                if wb1h>=35 and bd1h<30 and c1h>o1h and ok(pair,"L13",400):
                    send(f"🕐 *L13 (1H) BUY {pair}*\n⏰ TF: 1H | Wick:{wb1h:.0f}%\n⏳ *SCADENZA: 15 MIN* | {c1:.5f}")
                    continue
                if ws1h>=35 and bd1h<30 and c1h<o1h and ok(pair,"L14",400):
                    send(f"🕐 *L14 (1H) SELL {pair}*\n⏰ TF: 1H | Wick:{ws1h:.0f}%\n⏳ *SCADENZA: 15 MIN* | {c1:.5f}")
                    continue

                if wb4h>=35 and bd4h<35 and c4h>o4h and ok(pair,"L15",500):
                    send(f"🏛️ *L15 (4H) BUY {pair}*\n⏰ TF: 4H | Wick:{wb4h:.0f}%\n⏳ *SCADENZA: 1 ORA* | {c1:.5f}")
                    continue
                if ws4h>=35 and bd4h<35 and c4h<o4h and ok(pair,"L15S",500):
                    send(f"🏛️ *L15 (4H) SELL {pair}*\n⏰ TF: 4H | Wick:{ws4h:.0f}%\n⏳ *SCADENZA: 1 ORA* | {c1:.5f}")
                    continue

            except: continue
        time.sleep(5)

threading.Thread(target=bot, daemon=True).start()
app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
