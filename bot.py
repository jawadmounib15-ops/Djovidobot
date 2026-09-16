import os, gc, time, requests, yfinance as yf
from flask import Flask
from threading import Thread
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = {
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X", "AUDUSD": "AUDUSD=X",
    "AUDJPY": "AUDJPY=X", "GBPJPY": "GBPJPY=X",
    "USDCAD": "USDCAD=X", "NZDUSD": "NZDUSD=X",
    "ORO": "GC=F", "BTC": "BTC-USD",
    "NAS100": "^NDX", "EURJPY": "EURJPY=X",
    "EURGBP": "EURGBP=X", "GBPCHF": "GBPCHF=X",
}

app = Flask(__name__)
@app.route('/')
def home(): return "Bot V2 LIGHT LIVE 24/7 - DjovidoBot"

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def is_pin_bar(o,h,l,c):
    body = abs(c-o)
    if body==0: return False
    up = h - max(o,c); low = min(o,c) - l
    if low > body*2.5 and up < body*0.8 and body < (h-l)*0.4: return "BUY"
    if up > body*2.5 and low < body*0.8 and body < (h-l)*0.4: return "SELL"
    return False

def is_engulfing(po,pc,o,c):
    if pc<po and c>o and c>po and o<pc and abs(c-o)>abs(pc-po)*1.2: return "BUY"
    if pc>po and c<o and c<po and o>pc and abs(c-o)>abs(pc-po)*1.2: return "SELL"
    return False

def scan():
    send_telegram("✅ *V2 LIGHT avviato!* 14 mercati + Pin+Engulfing FORTE. Zero crash!")
    while True:
        for name, ticker in SYMBOLS.items():
            try:
                df = yf.download(ticker, period="5d", interval="1h", progress=False, auto_adjust=True)
                if len(df)<10: 
                    del df; continue
                df = df.tail(50)
                prev, last = df.iloc[-2], df.iloc[-1]
                o,h,l,c = float(last['Open']), float(last['High']), float(last['Low']), float(last['Close'])
                po,pc = float(prev['Open']), float(prev['Close'])
                sig = is_pin_bar(o,h,l,c); pat = "Pin Bar FORTE" if sig else None
                if not sig:
                    sig = is_engulfing(po,pc,o,c); pat = "Engulfing FORTE" if sig else None
                if sig:
                    send_telegram(f"🚨 *{sig} {name}* | {pat}\nPrezzo: {c}\nOra: {datetime.now().strftime('%H:%M')}")
                del df; gc.collect(); time.sleep(2)
            except: gc.collect(); continue
        gc.collect(); time.sleep(300)

if __name__ == "__main__":
    Thread(target=scan, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
