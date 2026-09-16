import os, time, threading, requests, yfinance as yf, pandas as pd
from flask import Flask

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","EURJPY=X","GBPJPY=X","CADJPY=X","EURGBP=X","AUDJPY=X","GBPCHF=X","EURCAD=X"]
TIMEFRAME = "15m"

app = Flask(__name__)
@app.route('/')
def home(): return "Bot V2.5 REAL LIVE - DjovidoBot"

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def check_signals(df, pair):
    if len(df) < 60: return None
    df['EMA50'] = df['Close'].ewm(span=50).mean()
    i = -2
    close = df['Close'].iloc[i]; open_ = df['Open'].iloc[i]; high = df['High'].iloc[i]; low = df['Low'].iloc[i]
    ema50 = df['EMA50'].iloc[i]
    body = abs(close-open_); upper = high-max(close,open_); lower = min(close,open_)-low
    prev_open = df['Open'].iloc[i-1]; prev_close = df['Close'].iloc[i-1]

    is_pin_bull = lower > body*2.0 and upper < body*0.6
    is_pin_bear = upper > body*2.0 and lower < body*0.6
    is_bull_eng = close>open_ and prev_close<prev_open and close>prev_open and open_<prev_close
    is_bear_eng = close<open_ and prev_close>prev_open and close<prev_open and open_>prev_close

    if is_pin_bull and close > ema50: return f"🟢 PIN BAR BUY - {pair}\nPrezzo sopra EMA50 - Trend UP"
    if is_pin_bear and close < ema50: return f"🔴 PIN BAR SELL - {pair}\nPrezzo sotto EMA50 - Trend DOWN"
    if is_bull_eng and close > ema50: return f"🟢 ENGULFING BUY - {pair}\nPrezzo sopra EMA50"
    if is_bear_eng and close < ema50: return f"🔴 ENGULFING SELL - {pair}\nPrezzo sotto EMA50"
    return None

def bot_loop():
    send_telegram("✅ *V2.5 REAL AVVIATO!*\n12 coppie - Pin FORTE + EMA50 - Sicuro ma spara!")
    while True:
        for pair in PAIRS:
            try:
                df = yf.download(pair, period="2d", interval=TIMEFRAME, progress=False)
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                sig = check_signals(df, pair)
                if sig: send_telegram(f"🚨 *SEGNALE V2.5*\n\n{sig}\nTF: 15m -> Entra 30m su Pocket\nCoppia reale: {pair.replace('=X','')}")
                time.sleep(1)
            except: pass
        time.sleep(60)

threading.Thread(target=bot_loop, daemon=True).start()
if __name__ == "__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
