import os, time, requests, yfinance as yf, threading, pandas as pd
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V143 SCALP + SWING"

TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("BOT_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("CHAT_ID")

SYMBOLS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCHF=X","EURGBP=X","AUDJPY=X","EURNZD=X","GBPCHF=X","EURCAD=X","AUDCAD=X","CHFJPY=X","NZDUSD=X"]
PAIRS = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","EUR/JPY-OTC","GBP/JPY-OTC","USD/CHF-OTC","EUR/GBP-OTC","AUD/JPY-OTC","EUR/NZD-OTC","GBP/CHF-OTC","EUR/CAD-OTC","AUD/CAD-OTC","CHF/JPY-OTC","NZD/USD-OTC"]

LAST_SCALP = 0
LAST_SWING = 0

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass
def wick(o,h,l,c):
    rng=h-l
    if rng==0: return 0,0,100
    return ((min(o,c)-l)/rng)*100, ((h-max(o,c))/rng)*100, (abs(o-c)/rng)*100

def bot():
    global LAST_SCALP, LAST_SWING
    time.sleep(2)
    send("⚖️ *V143 SCALP + SWING ONLINE*\nScalp: M1/M5 ogni 10 min | Swing: 1H/4H ogni 15 min\nNon solo 1 ora!")
    while True:
        try:
            best_scalp = None; score_scalp = 0
            best_swing = None; score_swing = 0
            
            for yahoo, pair in zip(SYMBOLS, PAIRS):
                time.sleep(0.8)
                df1 = yf.download(yahoo, period="5d", interval="1m", progress=False, auto_adjust=True)
                if df1.empty: continue
                if isinstance(df1.columns, pd.MultiIndex): df1.columns = df1.columns.get_level_values(0)
                df1 = df1.dropna()
                if len(df1)<20: continue
                df5 = df1.resample('5min').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
                df1h = df1.resample('1h').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
                df4h = df1.resample('4h').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()

                o1=float(df1["Open"].values[-2]); h1=float(df1["High"].values[-2]); l1=float(df1["Low"].values[-2]); c1=float(df1["Close"].values[-2])
                o5=float(df5["Open"].values[-2]) if len(df5)>=2 else o1; h5=float(df5["High"].values[-2]) if len(df5)>=2 else h1; l5=float(df5["Low"].values[-2]) if len(df5)>=2 else l1; c5=float(df5["Close"].values[-2]) if len(df5)>=2 else c1
                o1h=float(df1h["Open"].values[-2]) if len(df1h)>=2 else o1; h1h=float(df1h["High"].values[-2]) if len(df1h)>=2 else h1; l1h=float(df1h["Low"].values[-2]) if len(df1h)>=2 else l1; c1h=float(df1h["Close"].values[-2]) if len(df1h)>=2 else c1
                o4h=float(df4h["Open"].values[-2]) if len(df4h)>=2 else o1h; h4h=float(df4h["High"].values[-2]) if len(df4h)>=2 else h1h; l4h=float(df4h["Low"].values[-2]) if len(df4h)>=2 else l1h; c4h=float(df4h["Close"].values[-2]) if len(df4h)>=2 else c1h

                wb1,ws1,bd1=wick(o1,h1,l1,c1); wb5,ws5,bd5=wick(o5,h5,l5,c5); wb1h,ws1h,bd1h=wick(o1h,h1h,l1h,c1h); wb4h,ws4h,bd4h=wick(o4h,h4h,l4h,c4h)

                # SCALP: M1/M5 - soglia più bassa 40% così entra più facile
                if wb1>=40 and bd1<25 and wb1>score_scalp:
                    score_scalp=wb1; best_scalp=f"⚡ *SCALP L1 (M1) BUY {pair}*\n⏰ TF: M1 | Wick:{wb1:.0f}% | Body:{bd1:.0f}%\n⏳ *SCADENZA: 2 MIN* | {c1:.5f}"
                if ws1>=40 and bd1<25 and ws1>score_scalp:
                    score_scalp=ws1; best_scalp=f"⚡ *SCALP L2 (M1) SELL {pair}*\n⏰ TF: M1 | Wick:{ws1:.0f}% | Body:{bd1:.0f}%\n⏳ *SCADENZA: 2 MIN* | {c1:.5f}"
                if wb5>=40 and bd5<25 and wb5>score_scalp:
                    score_scalp=wb5; best_scalp=f"📌 *SCALP L9 (M5) BUY {pair}*\n⏰ TF: M5 | Wick:{wb5:.0f}% | Body:{bd5:.0f}%\n⏳ *SCADENZA: 5 MIN* | {c1:.5f}"
                if ws5>=40 and bd5<25 and ws5>score_scalp:
                    score_scalp=ws5; best_scalp=f"📌 *SCALP L10 (M5) SELL {pair}*\n⏰ TF: M5 | Wick:{ws5:.0f}% | Body:{bd5:.0f}%\n⏳ *SCADENZA: 5 MIN* | {c1:.5f}"

                # SWING: 1H/4H - soglia 50%+
                if wb1h>=50 and bd1h<30 and wb1h>score_swing:
                    score_swing=wb1h; best_swing=f"🕐 *SWING L13 (1H) BUY {pair}*\n⏰ TF: 1H | Wick:{wb1h:.0f}%\n⏳ *SCADENZA: 15 MIN* | {c1:.5f}"
                if ws1h>=50 and bd1h<30 and ws1h>score_swing:
                    score_swing=ws1h; best_swing=f"🕐 *SWING L14 (1H) SELL {pair}*\n⏰ TF: 1H | Wick:{ws1h:.0f}%\n⏳ *SCADENZA: 15 MIN* | {c1:.5f}"
                if wb4h>=50 and bd4h<30 and wb4h>score_swing:
                    score_swing=wb4h; best_swing=f"🏛️ *SWING L15 (4H) BUY {pair}*\n⏰ TF: 4H | Wick:{wb4h:.0f}%\n⏳ *SCADENZA: 1 ORA* | {c1:.5f}"
                if ws4h>=50 and bd4h<30 and ws4h>score_swing:
                    score_swing=ws4h; best_swing=f"🏛️ *SWING L15 (4H) SELL {pair}*\n⏰ TF: 4H | Wick:{ws4h:.0f}%\n⏳ *SCADENZA: 1 ORA* | {c1:.5f}"

            # Invia 1 scalp ogni 10 min + 1 swing ogni 15 min separati!
            if best_scalp and time.time()-LAST_SCALP > 600:
                send(best_scalp); LAST_SCALP=time.time()
            if best_swing and time.time()-LAST_SWING > 900:
                send(best_swing); LAST_SWING=time.time()

            time.sleep(10)
        except:
            time.sleep(5); continue

threading.Thread(target=bot, daemon=True).start()
app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
