import os
import yfinance as yf
import pandas as pd
import asyncio
from telegram import Bot
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TELEGRAM_TOKEN)

COPPIE_REALI = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDUSD=X"]
COPPIE_OTC = ["EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "EURJPY_otc", "GBPJPY_otc", "AUDUSD_otc"]

def analizza_largo(pair_yf, tf):
    try:
        interval = "5m" if tf == "5m" else "15m"
        df = yf.Ticker(pair_yf).history(period="1d", interval=interval)
        if len(df) < 30: return None
        df.rename(columns={'Open':'open','High':'high','Low':'low','Close':'close'}, inplace=True)
        
        # Solo 2 EMA, più largo
        df['ema9'] = df['close'].ewm(9).mean()
        df['ema21'] = df['close'].ewm(21).mean()
        
        delta = df['close'].diff()
        gain = delta.where(delta>0,0).rolling(14).mean()
        loss = -delta.where(delta<0,0).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + gain/loss))
        last = df.iloc[-1]
        
        score = 0
        # LARGO: basta incrocio ema9/ema21
        if last['ema9'] > last['ema21']:
            score += 50
            direzione = "CALL"
        else:
            score += 50
            direzione = "PUT"

        # RSI largo 25-75
        if 25 < last['rsi'] < 75:
            score += 30
        else:
            score += 10

        # Un po' di corpo candela
        corpo = abs(last['close']-last['open']) / (last['high']-last['low']+0.00001)
        if corpo > 0.3:
            score += 20

        if score < 60: # LARGO = soglia bassa
            return None
            
        return direzione, score, last['close'], last['rsi']
    except:
        return None

async def main():
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="🟢 FASE 1 - LARGO attiva\n6 REALI + 6 OTC | 5m + 15m | Soglia 60/100\nVediamo quanti ne manda")
    while True:
        for tf in ["5m", "15m"]:
            for coppia in COPPIE_REALI:
                res = analizza_largo(coppia, tf)
                if res:
                    dir, score, prezzo, rsi = res
                    nome = coppia.replace("=X","")
                    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, 
                        text=f"📊 {nome} {tf} REAL - {dir} | Score {score} | RSI {rsi:.1f}")

            for coppia in COPPIE_OTC:
                base = coppia.replace("_otc","=X")
                res = analizza_largo(base, tf)
                if res:
                    dir, score, prezzo, rsi = res
                    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, 
                        text=f"🔶 {coppia} {tf} OTC - {dir} | Score {score} | RSI {rsi:.1f}")
        await asyncio.sleep(90)

if __name__ == "__main__":
    asyncio.run(main())
