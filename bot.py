import time, threading, requests, yfinance as yf, pandas as pd, os
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")

SYMBOLS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCHF=X","EURGBP=X","AUDJPY=X","EURNZD=X"]
PAIRS_OTC = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","EUR/JPY-OTC","GBP/JPY-OTC","USD/CHF-OTC","EUR/GBP-OTC","AUD/JPY-OTC","EUR/NZD-OTC"]

app = Flask(__name__)
@app.route('/')
def home(): return "TEST STRETTO M1 OTC ONLINE"

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"}, timeout=10)
    except: pass

def fix_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df.dropna()

def loop():
    send("🔒 *TEST STRETTO M1 OTC ONLINE*\nFiltri: wick >65% + body <25%\nSolo segnali forti")
    while True:
        for sym, pair in zip(SYMBOLS, PAIRS_OTC):
            try:
                df = fix_df(yf.download(sym, period="1d", interval="1m", progress=False, auto_adjust=True))
                if len(df) < 30: 
                    time.sleep(1.5)
                    continue
                
                # Ultima candela chiusa
                o = float(df["Open"].values[-2])
                h = float(df["High"].values[-2])
                l = float(df["Low"].values[-2])
                c = float(df["Close"].values[-2])
                
                rng = h - l
                if rng == 0: 
                    time.sleep(1.5)
                    continue
                
                body = abs(c - o)
                body_perc = (body / rng) * 100
                upper = ((h - max(o,c)) / rng) * 100
                lower = ((min(o,c) - l) / rng) * 100

                # --- FILTRO STRETTO ---
                # Body piccolo <25% + stoppino lungo >65%
                sig = None
                if lower >= 65 and body_perc <= 25 and c > o:
                    sig = f"📌 *BUY STRETTO {pair} M1*\nWick basso: {lower:.0f}% | Body: {body_perc:.0f}%"
                elif upper >= 65 and body_perc <= 25 and c < o:
                    sig = f"📌 *SELL STRETTO {pair} M1*\nWick alto: {upper:.0f}% | Body: {body_perc:.0f}%"

                if sig:
                    send(sig + "\n👉 *POCKET OTC*")
                
                time.sleep(1.5) # anti-429
            except:
                time.sleep(1.5)
                continue
        time.sleep(5)

threading.Thread(target=loop, daemon=True).start()
app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
