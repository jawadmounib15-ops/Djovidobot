import os, asyncio, threading
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
def home(): return "Bot V3 ULTIMATE 70%"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

YAHOO_MAP = {"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","AUDUSD=X":"AUD/USD","USDJPY=X":"USD/JPY","EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY","AUDJPY=X":"AUD/JPY","EURGBP=X":"EUR/GBP","AUDCAD=X":"AUD/CAD","AUDCHF=X":"AUD/CHF"}
COPPIE = list(YAHOO_MAP.keys())
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")
ultimo = {}

def analizza_ultimate():
    now = datetime.now(ROMA)
    if not (8 <= now.hour <= 22): return None
    ts = now.timestamp()

    for cp in COPPIE:
        if cp in ultimo and ts-ultimo[cp] < 600: continue
        try:
            df5 = yf.Ticker(cp, session=session).history(period="5d", interval="5m")
            df15 = yf.Ticker(cp, session=session).history(period="5d", interval="15m")
            if len(df5)<70 or len(df15)<50: continue

            cl5 = df5['Close']; cl15 = df15['Close']
            e9_5 = cl5.ewm(span=9).mean(); e21_5 = cl5.ewm(span=21).mean(); e50_5 = cl5.ewm(span=50).mean()
            e9_15 = cl15.ewm(span=9).mean(); e21_15 = cl15.ewm(span=21).mean()

            ema9 = e9_5.iloc[-1]; ema9p = e9_5.iloc[-2]
            ema21 = e21_5.iloc[-1]; ema50 = e50_5.iloc[-1]
            ema9_15 = e9_15.iloc[-1]; ema21_15 = e21_15.iloc[-1]

            delta = cl5.diff(); g = delta.where(delta>0,0).rolling(14).mean()
            l = -delta.where(delta<0,0).rolling(14).mean()
            rsi_s = 100-(100/(1+g/l))
            rsi = float(rsi_s.iloc[-1]); rsip = float(rsi_s.iloc[-2])

            row = df5.iloc[-1]; prev = df5.iloc[-2]; prev2 = df5.iloc[-3]
            avg = (df5['High']-df5['Low']).rolling(20).mean().iloc[-1]
            rng = row['High']-row['Low']; body = abs(row['Close']-row['Open'])
            if rng==0 or rng < avg*0.65: continue

            up = row['High']-max(row['Open'],row['Close'])
            low = min(row['Open'],row['Close'])-row['Low']
            closes = cl5.iloc[-5:].tolist()
            trend_su_forte = closes[-1]>closes[-2]>closes[-3] and closes[-1]>closes[-3]*1.001
            trend_giu_forte = closes[-1]<closes[-2]<closes[-3] and closes[-1]<closes[-3]*0.999

            # 1 - PINBAR ULTIMATE 2.5-8x (bilanciato)
            if body>=rng*0.10 and body<=rng*0.28:
                if low >= body*2.5 and up <= rng*0.25 and 2.5<=low/body<=8.0:
                    if ema9>ema21 and ema9>ema9p and ema9_15>ema21_15 and not trend_giu_forte and 40<=rsi<=57:
                        ultimo[cp]=ts; return YAHOO_MAP[cp], "CALL", rsi, round(low/body,1), "PINBAR ⭐"
                if up >= body*2.5 and low <= rng*0.25 and 2.5<=up/body<=8.0:
                    if ema9<ema21 and ema9<ema9p and ema9_15<ema21_15 and not trend_su_forte and 43<=rsi<=60:
                        ultimo[cp]=ts; return YAHOO_MAP[cp], "PUT", rsi, round(up/body,1), "PINBAR ⭐"

            # 2 - ENGULFING ULTIMATE 1.5x
            b1 = abs(prev['Close']-prev['Open'])
            if b1>0 and body>=b1*1.5 and body<=b1*5.0:
                if prev['Close']<prev['Open'] and row['Close']>row['Open'] and row['Close']>prev['Open']*0.9995:
                    if ema9>ema21 and ema9_15>ema21_15 and 38<=rsi<=56:
                        ultimo[cp]=ts; return YAHOO_MAP[cp], "CALL", rsi, round(body/b1,1), "ENGULF 🔥"
                if prev['Close']>prev['Open'] and row['Close']<row['Open'] and row['Close']<prev['Open']*1.0005:
                    if ema9<ema21 and ema9_15<ema21_15 and 44<=rsi<=62:
                        ultimo[cp]=ts; return YAHOO_MAP[cp], "PUT", rsi, round(body/b1,1), "ENGULF 🔥"

            # 3 - EMA RETEST ULTIMATE
            if abs(row['Close']-ema9)/row['Close'] < 0.00030:
                if prev['Close']<ema9 and row['Close']>ema9 and ema9>ema21 and ema9_15>ema21_15 and 38<=rsi<=54:
                    ultimo[cp]=ts; return YAHOO_MAP[cp], "CALL", rsi, 2.0, "RETEST ♻️"
                if prev['Close']>ema9 and row['Close']<ema9 and ema9<ema21 and ema9_15<ema21_15 and 46<=rsi<=62:
                    ultimo[cp]=ts; return YAHOO_MAP[cp], "PUT", rsi, 2.0, "RETEST ♻️"

            # 4 - INSIDE BAR ULTIMATE 1.5x + breakout
            mother = prev['High']-prev['Low']; child = rng
            if mother>0 and child>0 and mother/child >= 1.5 and row['High']<prev['High'] and row['Low']>prev['Low']:
                pass # inside, aspetta breakout prossima candela
            # breakout della inside precedente
            if prev2['High']>prev['High'] and prev2['Low']<prev['Low']: # prev era inside
                if row['Close']>prev2['High'] and ema9>ema21 and ema9_15>ema21_15 and 40<=rsi<=56:
                    ultimo[cp]=ts; return YAHOO_MAP[cp], "CALL", rsi, round((prev2['High']-prev2['Low'])/(prev['High']-prev['Low']),1), "INSIDE 📦"
                if row['Close']<prev2['Low'] and ema9<ema21 and ema9_15<ema21_15 and 44<=rsi<=60:
                    ultimo[cp]=ts; return YAHOO_MAP[cp], "PUT", rsi, round((prev2['High']-prev2['Low'])/(prev['High']-prev['Low']),1), "INSIDE 📦"

            # 5 - RSI REVERSAL ULTIMATE
            if rsip<42 and 42<=rsi<=52 and ema9>ema21 and ema9_15>ema21_15:
                ultimo[cp]=ts; return YAHOO_MAP[cp], "CALL", rsi, 1.8, "RSI 💎"
            if rsip>58 and 48<=rsi<=58 and ema9<ema21 and ema9_15<ema21_15:
                ultimo[cp]=ts; return YAHOO_MAP[cp], "PUT", rsi, 1.8, "RSI 💎"

        except: continue
    return None

async def bot_loop():
    ora = datetime.now(ROMA).strftime('%H:%M:%S')
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"✅ V3.0 ULTIMATE 70% ON\n5 Lavori Bilanciati + Doppia Conferma 5m/15m\nPINBAR|ENGULF|RETEST|INSIDE|RSI | {ora} IT")
    while True:
        await asyncio.sleep(28)
        r = analizza_ultimate()
        ora = datetime.now(ROMA).strftime('%H:%M:%S')
        if r:
            nome, direz, rsi, ratio, job = r
            emoji = "🟢" if direz=="CALL" else "🔴"
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"{emoji} {nome} 5m - {direz} | {job}\n70% {ratio}x | RSI {rsi:.0f} | {ora} IT")

def start_bot(): asyncio.run(bot_loop())
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    start_bot()
