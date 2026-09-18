import os, time, requests, pandas as pd, yfinance as yf
from flask import Flask
from threading import Thread

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
app = Flask(__name__)

@app.route('/')
def home(): return "OK", 200

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": m}, timeout=10)
    except: pass

def to_float(v):
    if isinstance(v, pd.DataFrame): v = v.iloc[:,0]
    if isinstance(v, pd.Series):
        v = v.dropna()
        if len(v)>0: v = v.iloc[-1]
        else: return 0.0
        if isinstance(v, pd.Series): v = v.iloc[0]
    try: return float(v)
    except: return 0.0

def analizza():
    for sym, name in [("EURUSD=X","EUR/USD"),("GBPUSD=X","GBP/USD"),("USDJPY=X","USD/JPY"),("EURJPY=X","EUR/JPY"),("GBPJPY=X","GBP/JPY"),("AUDUSD=X","AUD/USD")]:
        try:
            df = yf.download(sym, period="3d", interval="15m", progress=False, auto_adjust=True)
            if df is None or len(df) < 60: continue
            close = df['Close']; open_ = df['Open']
            ema50 = to_float(close.ewm(span=50).mean())
            ema200 = to_float(close.ewm(span=200).mean())
            delta = close.diff()
            gain = delta.where(delta>0,0).rolling(14).mean()
            loss = -delta.where(delta<0,0).rolling(14).mean()
            rsi = to_float(100 - (100/(1+gain/loss)))
            uc = to_float(close.iloc[-1]); uo = to_float(open_.iloc[-1])
            pc = to_float(close.iloc[-2]); po = to_float(open_.iloc[-2])
            cp = abs(pc-po)
            if cp==0: continue
            ratio = abs(uc-uo)/cp
            if ratio<1.2 or ratio>2.0: continue
            bull = pc<po and uc>uo and uc>po and uo<pc
            bear = pc>po and uc<uo and uc<po and uo>pc
            sig = "BUY" if bull else "SELL" if bear else ""
            if not sig: continue
            trend = "BUY" if ema50>ema200 else "SELL"
            if sig!=trend: continue
            if sig=="BUY" and rsi>70: continue
            if sig=="SELL" and rsi<30: continue
            send(f"🔥 {name} {sig} Ratio {ratio:.2f} RSI {rsi:.1f}")
        except Exception as e:
            print(f"Err {name}: {e}")

def loop():
    send("✅ BOT V13.5 AVVIATO - Fix finale")
    while True:
        analizza()
        time.sleep(300)

Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
