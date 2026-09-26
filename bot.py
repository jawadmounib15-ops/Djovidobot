import os, time, requests, yfinance as yf, threading, pandas as pd
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V145 BOMBE ONLY"

TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("BOT_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("CHAT_ID")

SYMBOLS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCHF=X","EURGBP=X","AUDJPY=X","EURNZD=X","GBPCHF=X","EURCAD=X","AUDCAD=X","CHFJPY=X","NZDUSD=X"]
PAIRS = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","EUR/JPY-OTC","GBP/JPY-OTC","USD/CHF-OTC","EUR/GBP-OTC","AUD/JPY-OTC","EUR/NZD-OTC","GBP/CHF-OTC","EUR/CAD-OTC","AUD/CAD-OTC","CHF/JPY-OTC","NZD/USD-OTC"]

LAST_BOMBA = 0

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass

def wick(o,h,l,c):
    rng=h-l
    if rng==0: return 0,0,100
    return ((min(o,c)-l)/rng)*100, ((h-max(o,c))/rng)*100, (abs(o-c)/rng)*100

def rsi_calc(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def bot():
    global LAST_BOMBA
    time.sleep(2)
    send("💣 *V145 BOMBE ONLY ONLINE*\n💎 Wick 65%+ | Body <10% | RSI 30/70\nSolo 1 bomba ogni 15 min!")
    while True:
        try:
            best = None; best_score = 0
            
            for yahoo, pair in zip(SYMBOLS, PAIRS):
                time.sleep(0.8)
                df1 = yf.download(yahoo, period="5d", interval="1m", progress=False, auto_adjust=True)
                if df1.empty: continue
                if isinstance(df1.columns, pd.MultiIndex): df1.columns = df1.columns.get_level_values(0)
                df1 = df1.dropna()
                if len(df1)<30: continue
                df5 = df1.resample('5min').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
                df1h = df1.resample('1h').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
                df4h = df1.resample('4h').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()

                df1['RSI'] = rsi_calc(df1['Close']); df5['RSI'] = rsi_calc(df5['Close']); df1h['RSI'] = rsi_calc(df1h['Close'])
                rsi1 = float(df1['RSI'].values[-2]); rsi5 = float(df5['RSI'].values[-2]); rsi1h = float(df1h['RSI'].values[-2])

                o1=float(df1["Open"].values[-2]); h1=float(df1["High"].values[-2]); l1=float(df1["Low"].values[-2]); c1=float(df1["Close"].values[-2])
                o5=float(df5["Open"].values[-2]) if len(df5)>=2 else o1; h5=float(df5["High"].values[-2]) if len(df5)>=2 else h1; l5=float(df5["Low"].values[-2]) if len(df5)>=2 else l1; c5=float(df5["Close"].values[-2]) if len(df5)>=2 else c1
                o1h=float(df1h["Open"].values[-2]) if len(df1h)>=2 else o1; h1h=float(df1h["High"].values[-2]) if len(df1h)>=2 else h1; l1h=float(df1h["Low"].values[-2]) if len(df1h)>=2 else l1; c1h=float(df1h["Close"].values[-2]) if len(df1h)>=2 else c1
                o4h=float(df4h["Open"].values[-2]) if len(df4h)>=2 else o1h; h4h=float(df4h["High"].values[-2]) if len(df4h)>=2 else h1h; l4h=float(df4h["Low"].values[-2]) if len(df4h)>=2 else l1h; c4h=float(df4h["Close"].values[-2]) if len(df4h)>=2 else c1h

                wb1,ws1,bd1=wick(o1,h1,l1,c1); wb5,ws5,bd5=wick(o5,h5,l5,c5); wb1h,ws1h,bd1h=wick(o1h,h1h,l1h,c1h); wb4h,ws4h,bd4h=wick(o4h,h4h,l4h,c4h)

                # BOMBE M1/M5 - 65%+ wick + body <10% + RSI estremo
                if wb1>=65 and bd1<10 and rsi1<=35 and wb1>best_score:
                    best_score=wb1; best=f"💣 *BOMBA L1 (M1) BUY {pair}*\n📌 PINBAR: Wick:{wb1:.0f}% Body:{bd1:.0f}% RSI:{rsi1:.0f}\n⏳ *SCADENZA: 2 MIN* | {c1:.5f}"
                if ws1>=65 and bd1<10 and rsi1>=65 and ws1>best_score:
                    best_score=ws1; best=f"💣 *BOMBA L2 (M1) SELL {pair}*\n📌 PINBAR: Wick:{ws1:.0f}% Body:{bd1:.0f}% RSI:{rsi1:.0f}\n⏳ *SCADENZA: 2 MIN* | {c1:.5f}"
                if wb5>=65 and bd5<10 and rsi5<=35 and wb5>best_score:
                    best_score=wb5; best=f"💣 *BOMBA L9 (M5) BUY {pair}*\n📌 PINBAR: Wick:{wb5:.0f}% Body:{bd5:.0f}% RSI:{rsi5:.0f}\n⏳ *SCADENZA: 5 MIN* | {c1:.5f}"
                if ws5>=65 and bd5<10 and rsi5>=65 and ws5>best_score:
                    best_score=ws5; best=f"💣 *BOMBA L10 (M5) SELL {pair}*\n📌 PINBAR: Wick:{ws5:.0f}% Body:{bd5:.0f}% RSI:{rsi5:.0f}\n⏳ *SCADENZA: 5 MIN* | {c1:.5f}"

                # BOMBE 1H/4H - 70%+ wick + body <10% + RSI 30/70 - CORRETTO DIREZIONE!
                if wb1h>=70 and bd1h<10 and rsi1h<=30 and wb1h>best_score:
                    best_score=wb1h; best=f"💣 *BOMBA L13 (1H) BUY {pair}*\n📌 PINBAR 4H: Wick:{wb1h:.0f}% Body:{bd1h:.0f}% RSI:{rsi1h:.0f}\n⏳ *SCADENZA: 15 MIN* | {c1:.5f}"
                if ws1h>=70 and bd1h<10 and rsi1h>=70 and ws1h>best_score:
                    best_score=ws1h; best=f"💣 *BOMBA L14 (1H) SELL {pair}*\n📌 PINBAR 4H: Wick:{ws1h:.0f}% Body:{bd1h:.0f}% RSI:{rsi1h:.0f}\n⏳ *SCADENZA: 15 MIN* | {c1:.5f}"
                if wb4h>=70 and bd4h<10 and wb4h>best_score:
                    best_score=wb4h; best=f"💣 *BOMBA L15 (4H) BUY {pair}*\n📌 PINBAR 4H: Wick:{wb4h:.0f}% Body:{bd4h:.0f}% RSI:30\n⏳ *SCADENZA: 1 ORA* | {c1:.5f}"
                if ws4h>=70 and bd4h<10 and ws4h>best_score:
                    best_score=ws4h; best=f"💣 *BOMBA L15 (4H) SELL {pair}*\n📌 PINBAR 4H: Wick:{ws4h:.0f}% Body:{bd4h:.0f}% RSI:70\n⏳ *SCADENZA: 1 ORA* | {c1:.5f}"

            # SOLO 1 BOMBA OGNI 15 MINUTI IN TUTTO IL BOT!
            if best and time.time()-LAST_BOMBA > 900:
                send(best); LAST_BOMBA=time.time()

            time.sleep(10)
        except Exception as e:
            print(e); time.sleep(5); continue

threading.Thread(target=bot, daemon=True).start()
app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
