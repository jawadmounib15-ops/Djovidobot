import os, time, threading
from flask import Flask
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from curl_cffi import requests as cffi_requests

# ========== CONFIG ==========
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","GBPJPY=X","EURJPY=X","AUDJPY=X","EURGBP=X","USDCHF=X","AUDUSD=X","USDCAD=X","NZDJPY=X","CADJPY=X","GBPCHF=X","AUDCAD=X","EURAUD=X","CHFJPY=X"]
ITALY = ZoneInfo("Europe/Rome")
_YF = cffi_requests.Session(impersonate="chrome", timeout=15)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
cooldown = {}

app = Flask(__name__)

def send_tg(text):
    print(text)
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Manca TOKEN o CHAT_ID nelle env")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print("TG error", e)

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# ========== PINBAR PERFETTA 70-80% ==========
def pinbar_perfetta(o,h,l,c):
    rng = h - l
    if rng == 0: return None, 0
    if rng / c < 0.00008: return None, 0

    body = abs(c - o)
    upper = h - max(o,c)
    lower = min(o,c) - l

    tail = max(upper, lower)
    opp = min(upper, lower)

    if tail / rng < 0.70: return None, 0
    if body / rng > 0.25: return None, 0
    if opp / rng > 0.15: return None, 0

    if lower > upper:
        return "BUY", tail / rng
    else:
        return "SELL", tail / rng

def scan_pair(sym):
    try:
        if sym in cooldown and time.time() - cooldown[sym] < 300:
            return None

        name = sym.replace("=X","")
        pair = name[:3]+"/"+name[3:]

        df = fix_df(yf.Ticker(sym, session=_YF).history(period="2d", interval="1m"))
        if len(df) < 20: return None

        candle = df.iloc[-2] # ultima chiusa
        o = float(candle['Open'])
        h = float(candle['High'])
        l = float(candle['Low'])
        c = float(candle['Close'])

        side, forza = pinbar_perfetta(o,h,l,c)
        if not side: return None

        cooldown[sym] = time.time()
        ora = datetime.now(ITALY).strftime("%H:%M:%S")

        msg = (
            f"🎯 *PINBAR PERFETTA M1*\n\n"
            f"💰 *{pair} {side}*\n"
            f"📏 Ombra {forza*100:.0f}% | Corpo {abs(c-o)/(h-l)*100:.0f}%\n"
            f"💵 {c:.5f}\n"
            f"⏰ {ora} IT | ⏳ *5 MIN*\n"
            f"✅ Entra chiusura M1"
        )
        return msg
    except Exception as e:
        print(f"Err {sym}: {e}")
        return None

def bot_loop():
    time.sleep(3)
    send_tg("✅ *BOT PINBAR PERFETTA ONLINE*\nOmbra 70-80% | Scadenza 5m | M1")
    print("BOT AVVIATO")
    while True:
        try:
            for sym in PAIRS:
                msg = scan_pair(sym)
                if msg: send_tg(msg)
                time.sleep(1)
            time.sleep(10)
        except Exception as e:
            print("Loop error", e)
            time.sleep(20)

@app.route('/')
def home():
    return f"BOT ONLINE {datetime.now(ITALY).strftime('%H:%M:%S')}"

@app.route('/test')
def test():
    for sym in PAIRS:
        m = scan_pair(sym)
        if m:
            send_tg(m)
            return m
    return "Nessuna pinbar ora - bot in attesa"

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
