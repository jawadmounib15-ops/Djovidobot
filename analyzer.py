import os, asyncio, threading, random, time
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
def home(): return "Bot PHOTO PINBAR 5m ON"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

REAL_MAP = {
 "EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","AUDUSD=X":"AUD/USD",
 "USDJPY=X":"USD/JPY","EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY",
 "AUDJPY=X":"AUD/JPY","EURGBP=X":"EUR/GBP","AUDCAD=X":"AUD/CAD","AUDCHF=X":"AUD/CHF"
}
OTC_MAP = {k: v+" OTC" for k,v in REAL_MAP.items()}
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")

# PARAMETRI FOTO - COME IN SCREENSHOT
BODY_MIN, BODY_MAX = 0.05, 0.30
RATIO_MIN, RATIO_MAX = 2.8, 10.0
WICK_MAX = 0.40
COOLDOWN = 180
ultimo_segnali = {}

def get_rsi(close_s):
    delta = close_s.diff()
    gain = delta.where(delta>0,0).rolling(14).mean()
    loss = -delta.where(delta<0,0).rolling(14).mean()
    return 100 - (100/(1+gain/loss))

def is_pinbar_foto(o,h,l,c, ema9, ema21, rsi, prev_lows):
    body = abs(c - o); rng = h - l
    if rng == 0: return None
    up = h - max(o,c); low = min(o,c) - l
    close_pos = (c - l) / rng
    if not (rng*BODY_MIN <= body <= rng*BODY_MAX): return None

    # Deve essere minimo degli ultimi 5 come in foto
    if l > min(prev_lows) * 1.0015:
        return None

    # CALL HAMMER come tuo cerchio arancione
    if low >= body * RATIO_MIN:
        ratio = low/body
        if not (RATIO_MIN <= ratio <= RATIO_MAX): return None
        if up > rng*WICK_MAX: return None
        if close_pos < 0.60: return None
        if low < rng*0.50: return None # wick deve essere 50% della candela
        if not (20 <= rsi <= 75): return None
        if not (ema9 > ema21 or rsi < 45):
            return None
        return "CALL", round(ratio,1), int(close_pos*100)

    # PUT opposto
    if up >= body * RATIO_MIN:
        ratio = up/body
        if not (RATIO_MIN <= ratio <= RATIO_MAX): return None
        if low > rng*WICK_MAX: return None
        if close_pos > 0.40: return None
        if up < rng*0.50: return None
        if not (20 <= rsi <= 75): return None
        return "PUT", round(ratio,1), int(close_pos*100)
    return None

def analizza():
    now = datetime.now().timestamp()
    pool = [(t,"REAL",REAL_MAP[t]) for t in REAL_MAP] + [(t,"OTC",OTC_MAP[t]) for t in OTC_MAP]
    random.shuffle(pool)
    for ticker, tipo, nome in pool:
        key = f"{ticker}_{tipo}"
        if key in ultimo_segnali and now - ultimo_segnali[key] < COOLDOWN: continue
        try:
            time.sleep(0.4)
            df = yf.Ticker(ticker, session=session).history(period="2d", interval="5m")
            if len(df) < 60: continue
            cl = df['Close']
            ema9 = cl.ewm(span=9).mean().iloc[-1]
            ema21 = cl.ewm(span=21).mean().iloc[-1]
            rsi_s = get_rsi(cl)
            rsi_last = float(rsi_s.iloc[-1])
            row = df.iloc[-1]
            prev_lows = df['Low'].iloc[-6:-1].tolist()
            res = is_pinbar_foto(row['Open'],row['High'],row['Low'],row['Close'], ema9, ema21, rsi_last, prev_lows)
            if res:
                d, ratio, cp = res
                ultimo_segnali[key] = now
                return nome, tipo, d, rsi_last, ratio, cp
        except: continue
    return None

async def bot_loop():
    ora = datetime.now(ROMA).strftime('%H:%M:%S')
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"✅ BOT FOTO PINBAR 5m ON\nSolo Hammer come GBP/JPY foto\nWick >2.8x | Body 5-30% | Swing Low | {ora} IT")
    while True:
        await asyncio.sleep(45)
        res = analizza()
        ora = datetime.now(ROMA).strftime('%H:%M:%S')
        if res:
            nome, tipo, direz, rsi, ratio, cp = res
            emoji = "🟢" if direz=="CALL" else "🔴"
            tag = "🏦 REAL" if tipo=="REAL" else "🔶 OTC"
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"{emoji} {nome} 5m - {direz} {tag}\n📸 PINBAR FOTO | {ratio}x | Close {cp}% | RSI {rsi:.0f} | {ora} IT\n🎯 Come in foto GBP/JPY")

def start_bot(): asyncio.run(bot_loop())
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    start_bot()
