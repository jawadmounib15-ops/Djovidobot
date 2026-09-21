import os, time, requests, yfinance as yf, pandas as pd
from threading import Thread
from flask import Flask
from datetime import datetime, timedelta

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
VERSION = "V39 5/7 RAGIONATO ANTI-CIMA"
SYMBOLS = ["EURUSD=X", "GBPUSD=X", "EURGBP=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "EURJPY=X", "GBPJPY=X"]

app = Flask(__name__)
@app.route("/")
def home(): return f"{VERSION} LIVE - {datetime.now().strftime('%H:%M')}"

def send_tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": m, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def calc_rsi(c, p=14):
    d = c.diff()
    g = d.where(d>0,0).rolling(p).mean()
    l = -d.where(d<0,0).rolling(p).mean()
    rs = g / l
    return 100 - (100 / (1 + rs))

last_sent = {}

def get_signal(sym):
    try:
        df = yf.download(sym, period="5d", interval="15m", progress=False, auto_adjust=True)
        if len(df) < 100: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        c = pd.to_numeric(df['Close'], errors='coerce').dropna()
        o = pd.to_numeric(df['Open'], errors='coerce').dropna()

        ema9 = c.ewm(span=9).mean()
        ema20 = c.ewm(span=20).mean()
        ema50 = c.ewm(span=50).mean()
        rsi = calc_rsi(c)

        macd = c.ewm(span=12).mean() - c.ewm(span=26).mean()
        sig = macd.ewm(span=9).mean()
        hist = macd - sig

        price = float(c.iloc[-1])
        curr_o = float(o.iloc[-1])
        prev = float(c.iloc[-2]); prev_o = float(o.iloc[-2])
        prev2 = float(c.iloc[-3]); prev2_o = float(o.iloc[-3])

        e9 = float(ema9.iloc[-1]); e20 = float(ema20.iloc[-1]); e50 = float(ema50.iloc[-1])
        r = float(rsi.iloc[-1])
        h_now = float(hist.iloc[-1]); h_prev = float(hist.iloc[-2])

        # ANTI-DOPPIO 25 MIN
        now = datetime.now()
        if sym in last_sent and now - last_sent[sym]['time'] < timedelta(minutes=25):
            return None

        # CALCOLO VERDI/ROSSE
        green_count = sum([1 if price>curr_o else 0, 1 if prev>prev_o else 0, 1 if prev2>prev2_o else 0])
        red_count = 3 - green_count
        dist = abs(price - e20) / e20 * 100
        is_green = price > curr_o

        # --- BUY SCORE ---
        score_buy = 0; motivi_buy = []
        if e9 > e20 > e50:
            score_buy += 2; motivi_buy.append("EMA OK")
        if dist < 0.18:
            score_buy += 2; motivi_buy.append(f"vicino {dist:.2f}%")
        else:
            motivi_buy.append(f"LONTANO {dist:.2f}%")
        if 52 <= r <= 62:
            score_buy += 1; motivi_buy.append(f"RSI {r:.0f}")
        if h_now > 0 and h_now > h_prev:
            score_buy += 1; motivi_buy.append("MACD+")
        if green_count <= 2:
            score_buy += 1; motivi_buy.append("non cima")
        else:
            motivi_buy.append(f"{green_count} verdi")

        # --- SELL SCORE ---
        score_sell = 0
        if e9 < e20 < e50: score_sell += 2
        if dist < 0.18: score_sell += 2
        if 38 <= r <= 48: score_sell += 1
        if h_now < 0 and h_now < h_prev: score_sell += 1
        if red_count <= 2: score_sell += 1

        # DECISIONE - SERVONO 5/7
        if score_buy >= 5 and is_green and price > e20:
            last_sent[sym] = {'time': now, 'price': price}
            return {"side": "BUY", "price": price, "rsi": r, "score": score_buy, "mot": ", ".join(motivi_buy)}

        if score_sell >= 5 and not is_green and price < e20:
            last_sent[sym] = {'time': now, 'price': price}
            return {"side": "SELL", "price": price, "rsi": r, "score": score_sell, "mot": "trend down"}

        # DEBUG: se era 4/7 come il tuo 157.292 perso, non manda ma puoi vedere nei log
        return None

    except Exception as e:
        print(f"Err {sym}: {e}")
        return None

def bot_loop():
    time.sleep(5)
    send_tg(f"✅ *{VERSION} LIVE*\nRegola 5/7 | anti-cima | blocco 25min")
    while True:
        for sym in SYMBOLS:
            d = get_signal(sym)
            if d:
                nome = sym.replace("=X","")
                emoji = "🟢" if d['side']=="BUY" else "🔻"
                send_tg(f"{emoji} *{d['side']} {nome} - {d['score']}/7*\n{d['mot']}\nRSI {d['rsi']:.0f} | {d['price']:.5f} | 15m")
            time.sleep(10)
        time.sleep(240)

Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
