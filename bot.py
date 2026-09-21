import os, time, requests, yfinance as yf, pandas as pd
from threading import Thread
from flask import Flask
from datetime import datetime, timedelta

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
VERSION = "V36.5 FINALE 15m 5min"
SYMBOLS = ["EURUSD=X", "GBPUSD=X", "EURGBP=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "EURJPY=X", "GBPJPY=X"]

app = Flask(__name__)

@app.route("/")
def home():
    return f"{VERSION} LIVE"

def send_tg(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except:
        pass

def calc_rsi(close, p=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(p).mean()
    loss = -delta.where(delta < 0, 0).rolling(p).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

last_sent = {}

def get_data(sym):
    try:
        df = yf.download(sym, period="5d", interval="15m", progress=False, auto_adjust=True)
        if len(df) < 80:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        c = pd.to_numeric(df['Close'], errors='coerce').dropna()
        h = df['High']
        l = df['Low']
        o = df['Open']
        ema20 = c.ewm(span=20).mean()
        ema50 = c.ewm(span=50).mean()
        sma50 = c.rolling(50).mean()
        rsi = calc_rsi(c)
        bb_mid = c.rolling(20).mean()
        bb_std = c.rolling(20).std()
        bb_u = bb_mid + 2 * bb_std
        bb_l = bb_mid - 2 * bb_std
        price = float(c.iloc[-1])
        r = float(rsi.iloc[-1])
        e20 = float(ema20.iloc[-1])
        e50 = float(ema50.iloc[-1])
        bu = float(bb_u.iloc[-1])
        bl = float(bb_l.iloc[-1])
        s50 = float(sma50.iloc[-1])
        prev_c = float(c.iloc[-2])
        prev_e20 = float(ema20.iloc[-2])
        prev_e50 = float(ema50.iloc[-2])
        max20 = float(h.rolling(20).max().iloc[-2])
        min20 = float(l.rolling(20).min().iloc[-2])
        bb_width = (bu - bl) / bb_mid.iloc[-1]

        lavoro = None
        side = None

        if e20 > e50 and r >= 52 and r <= 55 and price > e20 and price > prev_c and price > s50:
            side = "BUY"
            lavoro = "L1 TREND STRETTO"
        elif e20 < e50 and r >= 45 and r <= 48 and price < e20 and price < prev_c and price < s50:
            side = "SELL"
            lavoro = "L1 TREND STRETTO"

        if not lavoro:
            if c.iloc[-1] <= bl and r <= 32:
                side = "BUY"
                lavoro = "L2 RIMBALZO 32/68"
            elif c.iloc[-1] >= bu and r >= 68:
                side = "SELL"
                lavoro = "L2 RIMBALZO 32/68"

        if not lavoro:
            if price > max20 and r >= 55 and r <= 62 and e20 > e50 and price > s50:
                side = "BUY"
                lavoro = "L3 BREAKOUT REGOLATO"
            elif price < min20 and r >= 38 and r <= 45 and e20 < e50 and price < s50:
                side = "SELL"
                lavoro = "L3 BREAKOUT REGOLATO"

        if not lavoro:
            if price > s50 and prev_c < s50 and e20 > e50 and r > 48 and r < 55:
                side = "BUY"
                lavoro = "L4 PULLBACK"
            elif price < s50 and prev_c > s50 and e20 < e50 and r > 45 and r < 52:
                side = "SELL"
                lavoro = "L4 PULLBACK"

        if not lavoro:
            if prev_e20 < prev_e50 and e20 > e50 and r > 50 and r < 60:
                side = "BUY"
                lavoro = "L5 EMA CROSS"
            elif prev_e20 > prev_e50 and e20 < e50 and r > 40 and r < 50:
                side = "SELL"
                lavoro = "L5 EMA CROSS"

        if not lavoro:
            body = abs(float(c.iloc[-1]) - float(o.iloc[-1]))
            lower_wick = float(min(c.iloc[-1], o.iloc[-1]) - l.iloc[-1])
            upper_wick = float(h.iloc[-1] - max(c.iloc[-1], o.iloc[-1]))
            if lower_wick > body * 1.5 and r >= 35 and r <= 45:
                side = "BUY"
                lavoro = "L6 REVERSAL"
            elif upper_wick > body * 1.5 and r >= 55 and r <= 65:
                side = "SELL"
                lavoro = "L6 REVERSAL"

        if not lavoro:
            if bb_width < 0.004 and r >= 50 and r <= 56 and price > e20 and e20 > e50:
                side = "BUY"
                lavoro = "L7 SQUEEZE"
            elif bb_width < 0.004 and r >= 44 and r <= 50 and price < e20 and e20 < e50:
                side = "SELL"
                lavoro = "L7 SQUEEZE"

        if side:
            key = f"{sym}_{side}_{lavoro}"
            now = datetime.now()
            if sym in last_sent and last_sent[sym]['key'] == key and now - last_sent[sym]['time'] < timedelta(minutes=5):
                return {"skip": True}
            last_sent[sym] = {'key': key, 'time': now}
            return {"price": price, "rsi": r, "side": side, "lavoro": lavoro}
        return None
    except:
        return None

def bot_loop():
    time.sleep(3)
    send_tg(f"✅ *{VERSION} LIVE*\nTimeframe: 15m\nAnalisi: ogni 5 min\nTra segnali: 10 sec\nAnti-doppio: 5 min\n7 Lavori attivi")
    while True:
        for sym in SYMBOLS:
            d = get_data(sym)
            if not d or d.get("skip"):
                continue
            if d.get("side"):
                nome = sym.replace("=X", "")
                emoji = "🟢" if d['side'] == 'BUY' else "🔻"
                msg = f"{emoji} *{d['side']} {nome} - {d['lavoro']}*\nRSI: {d['rsi']:.1f} | 15m\nPrezzo: {d['price']:.5f}"
                send_tg(msg)
            time.sleep(10)
        time.sleep(300)

Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
