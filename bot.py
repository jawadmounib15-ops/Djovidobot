import os, gc, time, requests, yfinance as yf, pandas as pd
from flask import Flask
from threading import Thread
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X",
    "AUDUSD": "AUDUSD=X", "AUDJPY": "AUDJPY=X", "GBPJPY": "GBPJPY=X",
    "USDCAD": "USDCAD=X", "NZDUSD": "NZDUSD=X", "ORO": "GC=F",
    "BTC": "BTC-USD", "NAS100": "^NDX", "EURJPY": "EURJPY=X",
    "EURGBP": "EURGBP=X", "GBPCHF": "GBPCHF=X"
}

app = Flask(__name__)
@app.route('/')
def home(): return "Bot V3.1 POCKET LIVE 24/7 - DjovidoBot - Filtri Leggeri"

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def is_pin_bar(o,h,l,c):
    body = abs(c-o)
    if body==0: return False
    up = h - max(o,c); low = min(o,c) - l
    if low > body*2.5 and up < body*0.8 and body < (h-l)*0.4:
        return "BUY"
    if up > body*2.5 and low < body*0.8 and body < (h-l)*0.4:
        return "SELL"
    return False

def is_engulfing(po,pc,o,c):
    if pc<po and c>o and c>po and o<pc and abs(c-o)>abs(pc-po)*1.2: return "BUY"
    if pc>po and c<o and c<po and o>pc and abs(c-o)>abs(pc-po)*1.2: return "SELL"
    return False

def scan():
    send_telegram("✅ *V3.1 POCKET AVVIATO!* 14 mercati + Pin+Engulfing + filtri leggeri. Zero crash!")
    while True:
        for name, ticker in SYMBOLS.items():
            try:
                df = yf.download(ticker, period="5d", interval="15m", progress=False, auto_adjust=True)
                if len(df)<100:
                    del df; continue
                df = df.tail(100)
                df['EMA50'] = df['Close'].ewm(span=50).mean()
                df['EMA200'] = df['Close'].ewm(span=200).mean()
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14).mean()
                loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14).mean()
                df['RSI'] = 100 - (100 / (1 + gain/loss))
                tr = pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift()).abs(), (df['Low']-df['Close'].shift()).abs()], axis=1).max(axis=1)
                df['ATR'] = tr.ewm(alpha=1/14).mean()

                prev, last = df.iloc[-2], df.iloc[-1]
                o,h,l,c = float(last['Open']), float(last['High']), float(last['Low']), float(last['Close'])
                po,pc = float(prev['Open']), float(prev['Close'])
                ema50, ema200, rsi, atr = float(df['EMA50'].iloc[-1]), float(df['EMA200'].iloc[-1]), float(df['RSI'].iloc[-1]), float(df['ATR'].iloc[-1])

                # REGOLA 1: ATR - CORRETTA PIU LEGGERA
                if atr/c < 0.00015:
                    del df; gc.collect(); continue

                # REGOLA 2: Vicino a S/R - CORRETTA PIU LEGGERA 0.35%
                recent_high = df['High'].iloc[-20:-1].max()
                recent_low = df['Low'].iloc[-20:-1].min()
                near_sr = abs(c-recent_high)/c < 0.0035 or abs(c-recent_low)/c < 0.0035
                if not near_sr:
                    del df; gc.collect(); continue

                sig = is_pin_bar(o,h,l,c); pat = "Pin Bar FORTE" if sig else None
                if not sig:
                    sig = is_engulfing(po,pc,o,c); pat = "Engulfing FORTE" if sig else None

                if sig:
                    # REGOLA 3+4: Trend + RSI - CORRETTA PIU LEGGERA PER POCKET
                    trend_ok = (sig=="BUY" and c>ema50 and 30<rsi<75) or (sig=="SELL" and c<ema50 and 30<rsi<75)
                    if trend_ok:
                        send_telegram(f"🚨 *{sig} {name}* | {pat}\nPrezzo: {c}\nRSI: {rsi:.1f} | EMA Trend | S/R | ATR OK\nOra: {datetime.now().strftime('%H:%M')} - TF 15m")

                del df; gc.collect(); time.sleep(2)
            except:
                gc.collect(); continue
        gc.collect(); time.sleep(180)

if __name__ == "__main__":
    Thread(target=scan, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
