import time, threading, requests, yfinance as yf, pandas as pd, os
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")

SYMBOLS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCHF=X","EURGBP=X","AUDJPY=X","EURNZD=X"]
PAIRS_OTC = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","EUR/JPY-OTC","GBP/JPY-OTC","USD/CHF-OTC","EUR/GBP-OTC","AUD/JPY-OTC","EUR/NZD-OTC"]

LAST_PRICE, COOLDOWN = {}, {}

app = Flask(__name__)
@app.route('/')
def home(): return "TEST MEDIO-STRETTO M1 ONLINE"

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"}, timeout=10)
    except: pass

def fix_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df.dropna()

def loop():
    send("⚖️ *TEST MEDIO-STRETTO M1 OTC ONLINE*\nFiltri: wick >50% + body <35% = 5-8 segnali/ora")
    while True:
        for sym, pair in zip(SYMBOLS, PAIRS_OTC):
            try:
                if pair in COOLDOWN and time.time() - COOLDOWN[pair] < 120: continue
                df = fix_df(yf.download(sym, period="1d", interval="1m", progress=False, auto_adjust=True))
                if len(df) < 5: time.sleep(1.5); continue

                key = f"{float(df['Close'].values[-2]):.5f}"
                if LAST_PRICE.get(pair) == key: time.sleep(1.5); continue
                LAST_PRICE[pair] = key

                o=float(df["Open"].values[-2]); h=float(df["High"].values[-2]); l=float(df["Low"].values[-2]); c=float(df["Close"].values[-2])
                rng=h-l
                if rng==0: time.sleep(1.5); continue
                body=(abs(c-o)/rng)*100
                upper=((h-max(o,c))/rng)*100
                lower=((min(o,c)-l)/rng)*100

                sig=None
                # MEDIO-STRETTO: 50% wick + 35% body
                if lower>=50 and body<=35 and c>o:
                    sig=f"📌 *BUY {pair} M1*\nWick {lower:.0f}% Body {body:.0f}%"
                elif upper>=50 and body<=35 and c<o:
                    sig=f"📌 *SELL {pair} M1*\nWick {upper:.0f}% Body {body:.0f}%"

                if sig:
                    COOLDOWN[pair]=time.time()
                    send(sig+f"\nPrezzo: {c:.5f}\n👉 *POCKET OTC*")
                time.sleep(1.5)
            except: time.sleep(1.5); continue
        time.sleep(5)

threading.Thread(target=loop, daemon=True).start()
app.run(host='0.0.0.0', port=int(os.environ.get("PO RT",10000)))
