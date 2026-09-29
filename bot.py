import os, asyncio, threading, random
from flask import Flask
from telegram import Bot
from datetime import datetime
import pytz
import yfinance as yf
from curl_cffi import requests as cffi_requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot POCKET 5m V2.2 LARGO 1 FILTRO ON - 15s"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

YAHOO_MAP = {
    "EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","AUDUSD=X":"AUD/USD",
    "USDJPY=X":"USD/JPY","EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY",
    "AUDJPY=X":"AUD/JPY","EURGBP=X":"EUR/GBP","AUDCAD=X":"AUD/CAD","AUDCHF=X":"AUD/CHF"
}
COPPIE = list(YAHOO_MAP.keys())
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")
ultimo_segnali = {}

def is_pinbar_filtrata(o,h,l,c, ema9, ema21, ema50, rsi, df):
    body = abs(c - o)
    rng = h - l
    if rng==0: return None
    up = h - max(o,c)
    low = min(o,c) - l

    # --- V2.2 LARGO: era 12-25% ora 10-30% ---
    if body < rng * 0.10: return None
    if body > rng * 0.30: return None
    if min(up,low) > rng * 0.28: return None # era 0.18 stretto, ora 0.28 largo

    # --- UNICO FILTRO: SPORGENZA (allargato) ---
    prev_low = df['Low'].iloc[-11:-1].min()
    prev_high = df['High'].iloc[-11:-1].max()
    sporge_bull = l < prev_low * 0.9995 # era 0.999 ora 0.9995 più facile
    sporge_bear = h > prev_high * 1.0005
    if not (sporge_bull or sporge_bear): return None

    if low >= body*2.0: # era 2.6 ora 2.0 più largo
        ratio = low/body
        if ratio > 8.0: return None # era 6.5x ora 8.0x LARGO
        if up > rng*0.35: return None # era 0.20 ora 0.35
        if not (ema9 > ema21): return None # tolto c>ema50 per allargare
        if not (38 <= rsi <= 62): return None # era 42-58 ora 38-62
        return "CALL", round(ratio,1)

    if up >= body*2.0:
        ratio = up/body
        if ratio > 8.0: return None
        if low > rng*0.35: return None
        if not (ema9 < ema21): return None
        if not (38 <= rsi <= 62): return None
        return "PUT", round(ratio,1)

    return None

def analizza():
    now_ts = datetime.now().timestamp()
    for coppia in random.sample(COPPIE, len(COPPIE)):
        if coppia in ultimo_segnali and now_ts - ultimo_segnali[coppia] < 600: # era 900 ora 600 = 10 min
            continue
        try:
            df = yf.Ticker(coppia, session=session).history(period="5d", interval="5m")
            if len(df) < 60: continue
            cl = df['Close']
            ema9 = cl.ewm(span=9).mean().iloc[-1]
            ema21 = cl.ewm(span=21).mean().iloc[-1]
            ema50 = cl.ewm(span=50).mean().iloc[-1]
            delta = cl.diff()
            gain = delta.where(delta>0,0).rolling(14).mean()
            loss = -delta.where(delta<0,0).rolling(14).mean()
            rsi = 100 - (100/(1+gain/loss))
            last_rsi = float(rsi.iloc[-1])
            row = df.iloc[-1]
            avg_rng = (df['High'] - df['Low']).rolling(20).mean().iloc[-1]
            if (row['High'] - row['Low']) < avg_rng * 0.60: continue # era 0.80 ora 0.60 più largo
            res = is_pinbar_filtrata(row['Open'],row['High'],row['Low'],row['Close'], ema9, ema21, ema50, last_rsi, df)
            if res:
                d, ratio = res
                ultimo_segnali[coppia] = now_ts
                return YAHOO_MAP[coppia], d, last_rsi, ratio
        except: continue
    return None

async def bot_loop():
    ora = datetime.now(ROMA).strftime('%H:%M:%S')
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"✅ POCKET 5m V2.2 LARGO 1 FILTRO\nBody 10-30% Ratio max 8.0x + Sporgenza\n15s CHECK - {ora} IT")
    while True:
        await asyncio.sleep(15) # ERA 90 ORA 15 SECONDI COME VOLEVI TU
        res = analizza()
        ora = datetime.now(ROMA).strftime('%H:%M:%S')
        if res:
            nome, direz, rsi, ratio = res
            emoji = "🟢" if direz=="CALL" else "🔴"
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"{emoji} {nome} 5m - {direz}\nREAL: {nome} | OTC: {nome} OTC\nV2.2 LARGO {ratio}x | RSI {rsi:.0f} | Sporgenza OK | {ora} IT")

def start_bot():
    asyncio.run(bot_loop())

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    start_bot()
