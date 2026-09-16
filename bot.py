import os, gc, time, requests, yfinance as yf, pandas as pd
from flask import Flask
from threading import Thread
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "AUDUSD": "AUDUSD=X",
    "AUDJPY": "AUDJPY=X",
    "GBPJPY": "GBPJPY=X",
    "USDCAD": "USDCAD=X",
    "NZDUSD": "NZDUSD=X",
    "EURJPY": "EURJPY=X",
    "EURGBP": "EURGBP=X",
    "GBPCHF": "GBPCHF=X",
    "CADJPY": "CADJPY=X"
}

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot V3.2 POCKET LIVE - Filtri ULTRA LEGGERI - 12 mercati reali"

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        print(f"Inviato Telegram: {msg[:30]}")
    except Exception as e:
        print(f"Errore Telegram: {e}")

def is_pin_bar(o,h,l,c):
    body = abs(c-o)
    if body==0: return False
    up = h - max(o,c)
    low = min(o,c) - l
    if low > body*1.8 and up < body*1.2 and body < (h-l)*0.5:
        return "BUY"
    if up > body*1.8 and low < body*1.2 and body < (h-l)*0.5:
        return "SELL"
    return False

def is_engulfing(po,pc,o,c):
    if pc<po and c>o and c>po and o<pc and abs(c-o)>abs(pc-po)*1.0:
        return "BUY"
    if pc>po and c<o and c<po and o>pc and abs(c-o)>abs(pc-po)*1.0:
        return "SELL"
    return False

def scan():
    send_telegram("✅ *V3.2 POCKET AVVIATO!* 12 mercati reali + Pin+Engulfing + filtri ULTRA leggeri! Ora manda EURUSD!")
    print("BOT V3.2 AVVIATO!")
    while True:
        for name, ticker in SYMBOLS.items():
            try:
                df = yf.download(ticker, period="5d", interval="15m", progress=False, auto_adjust=True)
                if len(df)<60:
                    del df
                    continue
                df = df.tail(80)
                df['EMA50'] = df['Close'].ewm(span=50).mean()
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14).mean()
                loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14).mean()
                df['RSI'] = 100 - (100 / (1 + gain/loss))
                
                prev, last = df.iloc[-2], df.iloc[-1]
                o,h,l,c = float(last['Open']), float(last['High']), float(last['Low']), float(last['Close'])
                po,pc = float(prev['Open']), float(prev['Close'])
                ema50 = float(df['EMA50'].iloc[-1])
                rsi = float(df['RSI'].iloc[-1])
                
                if pd.isna(rsi):
                    rsi = 50

                sig = is_pin_bar(o,h,l,c)
                pat = "Pin Bar"
                if not sig:
                    sig = is_engulfing(po,pc,o,c)
                    pat = "Engulfing"
                
                if sig:
                    # FILTRO ULTRA LEGGERO - SOLO TREND + RSI
                    trend_ok = (sig=="BUY" and c>ema50 and 20<rsi<80) or (sig=="SELL" and c<ema50 and 20<rsi<80)
                    if trend_ok:
                        msg = f"🚨 *{sig} {name}* {pat} 15m\nPrezzo: {c:.5f} | RSI {rsi:.0f}\nOra: {datetime.now().strftime('%H:%M')} | Pocket 30m"
                        send_telegram(msg)
                
                del df
                gc.collect()
                time.sleep(1)
            except Exception as e:
                print(f"Errore {name}: {e}")
                gc.collect()
                continue
        print(f"Scansione completa {datetime.now().strftime('%H:%M:%S')} - pausa 90s")
        gc.collect()
        time.sleep(90)

if __name__ == "__main__":
    Thread(target=scan, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
