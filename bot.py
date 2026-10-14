import os, time, threading
from flask import Flask
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from curl_cffi import requests as cffi_requests

PAIRS = ["EURUSD=X","GBPUSD=X","EURGBP=X","USDJPY=X","GBPJPY=X","EURJPY=X","AUDJPY=X","USDCHF=X","AUDUSD=X","USDCAD=X","NZDJPY=X","CADJPY=X","GBPCHF=X","EURAUD=X","CHFJPY=X","GBPAUD=X"]
ITALY = ZoneInfo("Europe/Rome")
_YF = cffi_requests.Session(impersonate="chrome", timeout=15)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
cooldown = {}

app = Flask(__name__)

def send_tg(text):
    print(text)
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print("TG err", e)

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# ========== PINBAR PERFETTA V3 - COME LE TUE FOTO ==========
def pinbar_perfetta(o,h,l,c):
    rng = h - l
    if rng == 0: return None, 0
    body = abs(c - o)
    upper = h - max(o,c)
    lower = min(o,c) - l
    tail = max(upper, lower)
    opp = min(upper, lower)

    # 1. Ombra 72%+ (le tue erano 75-80)
    if tail / rng < 0.72: return None, 0
    # 2. Corpo piccolo 22% max
    if body / rng > 0.22: return None, 0
    # 3. Ombra opposta max 10% - quasi nulla
    if opp / rng > 0.10: return None, 0
    # 4. Colore giusto obbligatorio
    if lower > upper and c <= o: return None, 0 # BUY deve essere verde
    if upper > lower and c >= o: return None, 0 # SELL deve essere rosso

    if lower > upper:
        return "BUY", tail / rng
    else:
        return "SELL", tail / rng

def scan_pair(sym):
    try:
        if sym in cooldown and time.time() - cooldown[sym] < 1800: # 30 min stop per coppia
            return None

        name = sym.replace("=X","")
        pair = name[:3]+"/"+name[3:]

        # M5 - NON M1! M1 sono tutti falsi come hai visto
        df = fix_df(yf.Ticker(sym, session=_YF).history(period="5d", interval="5m"))
        if len(df) < 100: return None

        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        # RSI 7 come da tua regola
        delta = df['Close'].diff()
        gain = delta.where(delta>0,0).ewm(alpha=1/7, adjust=False).mean()
        loss = -delta.where(delta<0,0).ewm(alpha=1/7, adjust=False).mean()
        df['RSI'] = 100 - (100/(1+gain/loss))

        c = df.iloc[-2] # ultima chiusa
        o = float(c['Open']); h = float(c['High']); l = float(c['Low']); close = float(c['Close'])
        ema = float(c['EMA20']); rsi = float(df.iloc[-2]['RSI'])

        side, forza = pinbar_perfetta(o,h,l,close)
        if not side: return None

        # ========== FILTRO LIVELLO - FONDAMENTALE ==========
        # Deve essere su supporto/resistenza o tocco EMA20
        lowest_20 = float(df['Low'].iloc[-20:].min())
        highest_20 = float(df['High'].iloc[-20:].max())

        is_support = (l <= lowest_20 * 1.0005) or (abs(l - ema) / close < 0.001)
        is_resist = (h >= highest_20 * 0.9995) or (abs(h - ema) / close < 0.001)

        if side == "BUY":
            if not is_support: return None # scarta se non è su supporto
            if rsi > 42: return None # RSI deve essere basso, uscita da <30
        else: # SELL
            if not is_resist: return None
            if rsi < 58: return None # RSI deve essere alto

        cooldown[sym] = time.time()
        ora = datetime.now(ITALY).strftime("%H:%M:%S")

        msg = (
            f"🎯 *PINBAR VERA M5*\n\n"
            f"💰 *{pair} {side}*\n"
            f"📏 Ombra {forza*100:.0f}% | Corpo {abs(close-o)/(h-l)*100:.0f}% | RSI {rsi:.0f}\n"
            f"📍 {'Supporto' if side=='BUY' else 'Resistenza'} + EMA20\n"
            f"💵 {close:.5f}\n"
            f"⏰ {ora} IT | ⏳ *5 MIN*\n"
            f"✅ Scadenza prossima M5"
        )
        return msg
    except Exception as e:
        print(f"Err {sym} {e}")
        return None

def bot_loop():
    time.sleep(5)
    send_tg("✅ *BOT V3 PINBAR VERA ONLINE*\nM5 | Ombra 72%+ | Solo su supporto/resistenza | RSI 7 | Max 1 ogni 30m")
    print("BOT V3 AVVIATO")
    while True:
        try:
            for sym in PAIRS:
                m = scan_pair(sym)
                if m:
                    send_tg(m)
                time.sleep(1.2)
            time.sleep(30)
        except Exception as e:
            print("Loop err", e)
            time.sleep(30)

@app.route('/')
def home():
    return f"BOT V3 ONLINE {datetime.now(ITALY).strftime('%H:%M:%S')}"

@app.route('/test')
def test():
    for sym in PAIRS:
        m = scan_pair(sym)
        if m:
            send_tg(m)
            return m
    return "Nessuna pinbar vera ora - aspetta livello giusto"

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
