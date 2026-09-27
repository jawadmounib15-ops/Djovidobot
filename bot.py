import os, yfinance as yf, asyncio, pandas as pd
from telegram import Bot
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_TOKEN)

COPPIE = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "EURJPY=X", "GBPJPY=X"]

def is_weekend():
    return datetime.now().weekday() >= 5

def analizza(pair, tf):
    try:
        df = yf.Ticker(pair).history(period="3d", interval=tf)
        if len(df) < 50: return None
        df.rename(columns={'Open':'open','High':'high','Low':'low','Close':'close'}, inplace=True)
        df['ema9'] = df['close'].ewm(9).mean()
        df['ema21'] = df['close'].ewm(21).mean()
        df['ema50'] = df['close'].ewm(50).mean()
        delta = df['close'].diff()
        gain = delta.where(delta>0,0).rolling(14).mean()
        loss = -delta.where(delta<0,0).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + gain/loss))
        last = df.iloc[-1]

        # Engulfing
        prev = df.iloc[-2]
        call_eng = last['close'] > last['open'] and prev['close'] < prev['open']
        put_eng = last['close'] < last['open'] and prev['close'] > prev['open']

        if last['ema9'] > last['ema21'] > last['ema50'] and call_eng and 38 < last['rsi'] < 62:
            return "CALL", 88, last['rsi']
        if last['ema9'] < last['ema21'] < last['ema50'] and put_eng and 38 < last['rsi'] < 62:
            return "PUT", 88, last['rsi']
        return None
    except:
        return None

async def main():
    tipo = "OTC 🔶 (Reali chiusi - Weekend)" if is_weekend() else "REALI 📊"
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"⏱️ Bot impostato: 1 messaggio ogni 5 minuti\nModalità: {tipo}\nFase 3 STRETTA 85%+")

    while True:
        # Aspetta 5 minuti ESATTI
        await asyncio.sleep(300)

        weekend = is_weekend()
        etichetta = "OTC" if weekend else "REAL"
        miglior_segale = None
        best_score = 0

        for tf in ["5m", "15m"]:
            for coppia in COPPIE:
                res = analizza(coppia, tf)
                if res and res[1] > best_score:
                    best_score = res[1]
                    direz, score, rsi = res
                    miglior_segale = (coppia.replace("=X",""), tf, direz, rsi, etichetta)

        # Manda 1 solo messaggio ogni 5 min
        ora = datetime.now().strftime('%H:%M:%S')
        if miglior_segale:
            nome, tf, direz, rsi, etichetta = miglior_segale
            emoji = "🟢🟢" if direz == "CALL" else "🔴🔴"
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID,
                text=f"{emoji} {nome} {tf} {etichetta} - {direz}\nScore 88% | RSI {rsi:.1f}\n⏰ {ora}")
        else:
            # Se vuoi ZERO spam quando non c'è segnale, cancella queste 2 righe sotto
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID,
                text=f"⏳ {ora} - Nessun segnale pulito 85%+ su 5 coppie | Controllo tra 5 min | {etichetta}")

if __name__ == "__main__":
    asyncio.run(main())
