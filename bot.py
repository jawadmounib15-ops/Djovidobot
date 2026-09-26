import os, time, requests, yfinance as yf, threading, pandas as pd, random
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V130 15 LAVORI LARGHI ONLINE"

TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("BOT_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("CHAT_ID")

SYMBOLS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCHF=X","EURGBP=X","AUDJPY=X","EURNZD=X","GBPCHF=X","EURCAD=X","AUDCAD=X","CHFJPY=X","NZDUSD=X"]
PAIRS = ["EUR/USD","GBP/USD","USD/JPY-OTC","AUD/USD","EUR/JPY-OTC","GBP/JPY-OTC","USD/CHF-OTC","EUR/GBP-OTC","AUD/JPY-OTC","EUR/NZD-OTC","GBP/CHF-OTC","EUR/CAD-OTC","AUD/CAD-OTC","CHF/JPY-OTC","NZD/USD-OTC"]

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
    send("🔥 *V130 15 LAVORI LARGHI ONLINE*\nFiltri larghi 8-15% = tanti segnali\nPoi stringiamo piano!")
    while True:
        for idx, (yahoo, pair) in enumerate(zip(SYMBOLS, PAIRS)):
            try:
                # ANTILAG
                if idx % 5 == 0 and idx!=0: time.sleep(5)
                if pair in COOLDOWN and time.time()-COOLDOWN[pair] < 60: continue
                time.sleep(random.uniform(0.8,1.3))

                df1=fix_df(yf.download(yahoo, period="1d", interval="1m", progress=False, auto_adjust=True))
                if len(df1)<10: continue
                df5=df1.resample('5min').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()

                o1=float(df1["Open"].values[-2]); h1=float(df1["High"].values[-2]); l1=float(df1["Low"].values[-2]); c1=float(df1["Close"].values[-2])
                o1p=float(df1["Open"].values[-3]); c1p=float(df1["Close"].values[-3])
                o1p2=float(df1["Open"].values[-4]) if len(df1)>4 else o1p; c1p2=float(df1["Close"].values[-4]) if len(df1)>4 else c1p
                o5=float(df5["Open"].values[-2]) if len(df5)>=2 else o1; c5=float(df5["Close"].values[-2]) if len(df5)>=2 else c1
                h5=float(df5["High"].values[-2]) if len(df5)>=2 else h1; l5=float(df5["Low"].values[-2]) if len(df5)>=2 else l1
                b1,s1,bd1=pinbar(o1,h1,l1,c1); b5,s5,bd5=pinbar(o5,h5,l5,c5)
                b1p,s1p,bd1p=pinbar(o1p,float(df1["High"].values[-3]),float(df1["Low"].values[-3]),c1p)

                # ANTIDUPLICATO
                price_key = f"{c1:.5f}"
                if LAST_PRICE.get(pair) == price_key: continue
                LAST_PRICE[pair]=price_key

                sig=None

                # === 15 LAVORI LARGHI ===
                # L1-2 DOPPIA LARGA: wick 8% + body 50% (prima era 15%)
                if b1>=8 and b5>=8 and bd1<50 and c1>o1: sig=f"📌 *L1 DOPPIA BUY {pair}* M1:{b1:.0f}%"
                elif s1>=8 and s5>=8 and bd1<50 and c1<o1: sig=f"📌 *L2 DOPPIA SELL {pair}* M1:{s1:.0f}%"
                # L3-4 PINBAR MEDIA LARGA: wick 15% body 45% (prima 40%)
                elif not sig and b1>=15 and bd1<45 and c1>o1: sig=f"⚡ *L3 MEDIA BUY {pair}* {b1:.0f}%"
                elif not sig and s1>=15 and bd1<45 and c1<o1: sig=f"⚡ *L4 MEDIA SELL {pair}* {s1:.0f}%"
                # L5-6 ENGULFING LARGO: qualsiasi engulfing
                elif not sig and c1>o1 and c1p<o1p and c1>=o1p: sig=f"🔄 *L5 ENGULF BUY {pair}*"
                elif not sig and c1<o1 and c1p>o1p and c1<=o1p: sig=f"🔄 *L6 ENGULF SELL {pair}*"
                # L7-8 M5 LARGO: wick 10% body 50%
                elif not sig and b5>=10 and bd5<50 and c1>o1: sig=f"📊 *L7 M5 BUY {pair}* {b5:.0f}%"
                elif not sig and s5>=10 and bd5<50 and c1<o1: sig=f"📊 *L8 M5 SELL {pair}* {s5:.0f}%"
                # L9-10 HAMMER LARGO: wick 30% body 30% (prima 60%)
                elif not sig and b1>=30 and bd1<30 and c1>o1: sig=f"🔨 *L9 HAMMER BUY {pair}* {b1:.0f}%"
                elif not sig and s1>=30 and bd1<30 and c1<o1: sig=f"💫 *L10 SHOOT SELL {pair}* {s1:.0f}%"
                # L11-12 2 CANDELE (non 3) = più largo
                elif not sig and c1>o1 and c1p>o1p: sig=f"📈 *L11 2x BUY {pair}*"
                elif not sig and c1<o1 and c1p<o1p: sig=f"📉 *L12 2x SELL {pair}*"
                # L13-14 DOJI LARGO: body <20% poi pinbar 10%
                elif not sig and bd1p<20 and b1>=10: sig=f"⭐ *L13 DOJI BUY {pair}*"
                elif not sig and bd1p<20 and s1>=10: sig=f"⭐ *L14 DOJI SELL {pair}*"
                # L15 LEGGERISSIMO: wick 8% body 60% = max opportunità
                elif not sig and b1>=8 and bd1<60 and c1>o1: sig=f"💡 *L15 LEGGERO BUY {pair}* {b1:.0f}%"
                elif not sig and s1>=8 and bd1<60 and c1<o1: sig=f"💡 *L15 LEGGERO SELL {pair}* {s1:.0f}%"

                if sig and LAST_SIGNAL.get(pair)!=sig:
                    LAST_SIGNAL[pair]=sig
                    COOLDOWN[pair]=time.time()
                    send(sig+f"\n{c1:.5f}\n👉 *POCKET*")
            except:
                if "429" in str(Exception): time.sleep(25)
                continue
        time.sleep(3)

threading.Thread(target=bot, daemon=True).start()
app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
