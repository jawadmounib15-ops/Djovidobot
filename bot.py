import os, time, requests, yfinance as yf, threading, pandas as pd, random
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V131 ULTRA LARGO 2% ONLINE"

TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("BOT_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("CHAT_ID")

# SOLO OTC PER SABATO - 15 COPPIE
SYMBOLS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCHF=X","EURGBP=X","AUDJPY=X","EURNZD=X","GBPCHF=X","EURCAD=X","AUDCAD=X","CHFJPY=X","NZDUSD=X"]
PAIRS = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","EUR/JPY-OTC","GBP/JPY-OTC","USD/CHF-OTC","EUR/GBP-OTC","AUD/JPY-OTC","EUR/NZD-OTC","GBP/CHF-OTC","EUR/CAD-OTC","AUD/CAD-OTC","CHF/JPY-OTC","NZD/USD-OTC"]

COOLDOWN, LAST_PRICE, LAST_SIGNAL = {}, {}, {}

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass
def fix_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df.dropna()
def pinbar(o,h,l,c):
    rng=h-l
    if rng==0: return 0,0,100
    body=abs(o-c); bp=(body/rng)*100
    buy=((min(o,c)-l)/rng)*100; sell=((h-max(o,c))/rng)*100
    return buy,sell,bp

def bot():
    time.sleep(2)
    send("🔥🔥 *V131 ULTRA LARGO 2% ONLINE*\nFiltri 2-3% = MASSIMA OPPORTUNITA\n15 lavori - Test sabato")
    while True:
        for idx, (yahoo, pair) in enumerate(zip(SYMBOLS, PAIRS)):
            try:
                if idx % 5 == 0 and idx!=0: time.sleep(4)
                if pair in COOLDOWN and time.time()-COOLDOWN[pair] < 30: continue # 30sec solo
                time.sleep(random.uniform(0.7,1.1))

                df1=fix_df(yf.download(yahoo, period="1d", interval="1m", progress=False, auto_adjust=True))
                if len(df1)<6: continue
                df5=df1.resample('5min').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()

                o1=float(df1["Open"].values[-2]); h1=float(df1["High"].values[-2]); l1=float(df1["Low"].values[-2]); c1=float(df1["Close"].values[-2])
                o1p=float(df1["Open"].values[-3]); c1p=float(df1["Close"].values[-3])
                o1p2=float(df1["Open"].values[-4]) if len(df1)>4 else o1p; c1p2=float(df1["Close"].values[-4]) if len(df1)>4 else c1p
                o5=float(df5["Open"].values[-2]) if len(df5)>=2 else o1; c5=float(df5["Close"].values[-2]) if len(df5)>=2 else c1
                h5=float(df5["High"].values[-2]) if len(df5)>=2 else h1; l5=float(df5["Low"].values[-2]) if len(df5)>=2 else l1
                b1,s1,bd1=pinbar(o1,h1,l1,c1); b5,s5,bd5=pinbar(o5,h5,l5,c5)
                b1p,s1p,bd1p=pinbar(o1p,float(df1["High"].values[-3]),float(df1["Low"].values[-3]),c1p)

                price_key = f"{c1:.5f}"
                if LAST_PRICE.get(pair) == price_key: continue
                LAST_PRICE[pair]=price_key

                sig=None

                # === 15 LAVORI ULTRA LARGHI 2-5% ===
                if b1>=2 and b5>=2 and bd1<80 and c1>o1: sig=f"📌 *L1 DOPPIA BUY {pair}* M1:{b1:.0f}% M5:{b5:.0f}%"
                elif s1>=2 and s5>=2 and bd1<80 and c1<o1: sig=f"📌 *L2 DOPPIA SELL {pair}* M1:{s1:.0f}% M5:{s5:.0f}%"
                elif not sig and b1>=3 and bd1<80 and c1>o1: sig=f"⚡ *L3 MEDIA BUY {pair}* {b1:.0f}%"
                elif not sig and s1>=3 and bd1<80 and c1<o1: sig=f"⚡ *L4 MEDIA SELL {pair}* {s1:.0f}%"
                elif not sig and c1>o1 and c1p<o1p: sig=f"🔄 *L5 ENGULF BUY {pair}*"
                elif not sig and c1<o1 and c1p>o1p: sig=f"🔄 *L6 ENGULF SELL {pair}*"
                elif not sig and b5>=2 and c1>o1: sig=f"📊 *L7 M5 BUY {pair}* M5:{b5:.0f}%"
                elif not sig and s5>=2 and c1<o1: sig=f"📊 *L8 M5 SELL {pair}* M5:{s5:.0f}%"
                elif not sig and b1>=5 and bd1<70 and c1>o1: sig=f"🔨 *L9 HAMMER BUY {pair}* {b1:.0f}%"
                elif not sig and s1>=5 and bd1<70 and c1<o1: sig=f"💫 *L10 SHOOT SELL {pair}* {s1:.0f}%"
                elif not sig and c1>o1 and c1p>o1p: sig=f"📈 *L11 2x BUY {pair}*"
                elif not sig and c1<o1 and c1p<o1p: sig=f"📉 *L12 2x SELL {pair}*"
                elif not sig and bd1p<30 and b1>=2: sig=f"⭐ *L13 DOJI BUY {pair}*"
                elif not sig and bd1p<30 and s1>=2: sig=f"⭐ *L14 DOJI SELL {pair}*"
                elif not sig and b1>=1 and c1>o1: sig=f"💡 *L15 ULTRA BUY {pair}* {b1:.0f}%"
                elif not sig and s1>=1 and c1<o1: sig=f"💡 *L15 ULTRA SELL {pair}* {s1:.0f}%"

                if sig and LAST_SIGNAL.get(pair)!=sig:
                    LAST_SIGNAL[pair]=sig
                    COOLDOWN[pair]=time.time()
                    send(sig+f"\n{c1:.5f}\n👉 *POCKET*")
            except: continue
        time.sleep(2)

threading.Thread(target=bot, daemon=True).start()
app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
