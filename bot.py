import os, yfinance as yf, asyncio, threading
from flask import Flask
from telegram import Bot
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_TOKEN)

app = Flask(__name__)
@app.route('/')
def home(): return "Bot Doppio Lavoro: Engulfing + Pinbar"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

COPPIE = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDUSD=X", "USDCAD=X", "EURGBP=X", "USDCHF=X", "NZDUSD=X"]
def is_weekend(): return datetime.now().weekday() >= 5

def analizza_engulfing(pair, tf):
    try:
        df = yf.Ticker(pair).history(period="5d", interval=tf)
        if len(df) < 100: return None
        df.rename(columns={'Open':'open','High':'high','Low':'low','Close':'close'}, inplace=True)
        df['ema9'] = df['close'].ewm(9).mean()
        df['ema21'] = df['close'].ewm(21).mean()
        df['ema50'] = df['close'].ewm(50).mean()
        df['ema200'] = df['close'].ewm(200).mean()
        delta = df['close'].diff()
        gain = delta.where(delta>0,0).rolling(14).mean()
        loss = -delta.where(delta<0,0).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + gain/loss))
        df['atr'] = (df['high']-df['low']).rolling(14).mean()
        last = df.iloc[-1]; prev = df.iloc[-2]; prev2 = df.iloc[-3]
        trend_call = last['ema9'] > last['ema21'] > last['ema50'] > last['ema200']
        trend_put = last['ema9'] < last['ema21'] < last['ema50'] < last['ema200']
        rsi_ok = 48 <= last['rsi'] <= 54
        body = abs(last['close']-last['open']); range_c = last['high']-last['low']
        body_big = body > range_c * 0.6 if range_c>0 else False
        call_eng = last['close'] > last['open'] and prev['close'] < prev['open'] and last['close'] > prev['open'] and body_big
        put_eng = last['close'] < last['open'] and prev['close'] > prev['open'] and last['close'] < prev['open'] and body_big
        momentum_call = prev['close'] > prev2['close']; momentum_put = prev['close'] < prev2['close']
        dist = abs(last['close'] - last['ema50']) / last['atr'] if last['atr']>0 else 10
        if trend_call and rsi_ok and call_eng and momentum_call and dist < 1.5: return "CALL", last['rsi'], "ENGULFING 90%+"
        if trend_put and rsi_ok and put_eng and momentum_put and dist < 1.5: return "PUT", last['rsi'], "ENGULFING 90%+"
        return None
    except: return None

def analizza_pinbar(pair, tf):
    try:
        df = yf.Ticker(pair).history(period="5d", interval=tf)
        if len(df) < 100: return None
        df.rename(columns={'Open':'open','High':'high','Low':'low','Close':'close'}, inplace=True)
        df['ema21'] = df['close'].ewm(21).mean()
        df['ema50'] = df['close'].ewm(50).mean()
        delta = df['close'].diff()
        gain = delta.where(delta>0,0).rolling(14).mean()
        loss = -delta.where(delta<0,0).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + gain/loss))
        last = df.iloc[-1]; prev = df.iloc[-2]
        
        body = abs(last['close']-last['open'])
        upper_wick = last['high'] - max(last['close'], last['open'])
        lower_wick = min(last['close'], last['open']) - last['low']
        range_c = last['high']-last['low']
        if range_c == 0: return None
        
        # Pinbar pulita: corpo piccolo <30% range, stoppino lungo >2x corpo
        corpo_piccolo = body < range_c * 0.3
        is_pinbar_call = lower_wick > body * 2.5 and upper_wick < body * 0.5 and corpo_piccolo
        is_pinbar_put = upper_wick > body * 2.5 and lower_wick < body * 0.5 and corpo_piccolo
        
        # Filtri stretti pinbar
        rsi_ok = 45 <= last['rsi'] <= 55
        near_ema = abs(last['close'] - last['ema21']) < (range_c * 1.5)  # vicina a EMA21
        prev_trend_call = prev['close'] < prev['open']  # prima era ribasso, ora pinbar rialzista
        prev_trend_put = prev['close'] > prev['open']
        
        if is_pinbar_call and rsi_ok and near_ema and prev_trend_call and last['ema21'] > last['ema50']:
            return "CALL", last['rsi'], f"PINBAR PULITA 📌 Wick {lower_wick/body:.1f}x"
        if is_pinbar_put and rsi_ok and near_ema and prev_trend_put and last['ema21'] < last['ema50']:
            return "PUT", last['rsi'], f"PINBAR PULITA 📌 Wick {upper_wick/body:.1f}x"
        return None
    except: return None

async def bot_loop():
    tipo = "OTC 🔶" if is_weekend() else "REALI 📊"
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🔧 Bot DOPPIO LAVORO ON\n1) Engulfing 90%+  2) Se non trova -> Pinbar pulita\nModalità {tipo} | 10 coppie | 1 msg/5min")
    while True:
        await asyncio.sleep(300)
        etichetta = "OTC" if is_weekend() else "REAL"
        best = None
        # GIRO 1: cerca engulfing
        for tf in ["5m","15m"]:
            for coppia in COPPIE:
                res = analizza_engulfing(coppia, tf)
                if res:
                    direz, rsi, tipo_sig = res
                    best = (coppia.replace("=X",""), tf, direz, rsi, tipo_sig, etichetta); break
            if best: break
        # GIRO 2: se non trovato, cerca pinbar
        if not best:
            for tf in ["5m","15m"]:
                for coppia in COPPIE:
                    res = analizza_pinbar(coppia, tf)
                    if res:
                        direz, rsi, tipo_sig = res
                        best = (coppia.replace("=X",""), tf, direz, rsi, tipo_sig, etichetta); break
                if best: break
        
        ora = datetime.now().strftime('%H:%M:%S')
        if best:
            nome, tf, direz, rsi, tipo_sig, et = best
            emoji = "🟢" if direz=="CALL" else "🔴"
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"{emoji} {nome} {tf} {et} - {direz}\n{tipo_sig} | RSI {rsi:.1f} | {ora}")
        else:
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🔍 {ora} - Nessun Engulfing ne Pinbar pulita | {etichetta}")

def start_bot(): asyncio.run(bot_loop())
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    start_bot()
