import os, time, requests, yfinance as yf, pandas as pd
from threading import Thread
from flask import Flask
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
VERSION = "V36.8 STRETTO 32/68 FINAL"
SYMBOLS = ["EURUSD=X", "GBPUSD=X", "EURGBP=X"]

app = Flask(__name__)
@app.route("/")
def home():
    return f"{VERSION} LIVE - {datetime.now().strftime('%H:%M:%S')}"

def send_tg(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        print(f"TG inviato: {msg[:30]}")
    except Exception as e:
        print(f"Err TG: {e}")

def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_signal(symbol):
    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False, auto_adjust=True)
        if df.empty or len(df) < 60:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        close = df['Close']
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:,0]
        close = pd.to_numeric(close, errors='coerce').dropna()

        ema20 = close.ewm(span=20, adjust=False).mean()
        ema50 = close.ewm(span=50, adjust=False).mean()
        rsi = calc_rsi(close)

        last_close = float(close.iloc[-1])
        last_rsi = float(rsi.iloc[-1])
        last_ema20 = float(ema20.iloc[-1])
        last_ema50 = float(ema50.iloc[-1])

        return {
            "price": last_close,
            "rsi": last_rsi,
            "ema20": last_ema20,
            "ema50": last_ema50
        }
    except Exception as e:
        print(f"Errore {symbol}: {e}")
        return None

def bot_loop():
    time.sleep(5)
    send_tg(f"✅ *{VERSION} LIVE* 🟢\nBot ripartito corretto\nFiltro: BUY 32 / SELL 68 + EMA\nScansione ogni 2 min")
    print(f"{VERSION} AVVIATO")
    
    while True:
        try:
            for sym in SYMBOLS:
                data = get_signal(sym)
                if not data:
                    continue

                nome = sym.replace("=X","")
                nome = nome.replace("EURUSD","EUR/USD").replace("GBPUSD","GBP/USD").replace("EURGBP","EUR/GBP")
                
                rsi = data['rsi']
                price = data['price']
                ema20 = data['ema20']
                ema50 = data['ema50']

                # V36.8 STRETTO - SOLO QUESTO, NIENTE ALTRO
                if ema20 > ema50 and rsi <= 32:
                    msg = f"🟢 *BUY {nome}*\nRSI: {rsi:.1f} (32 stretto)\nPrezzo: {price:.5f}\nEMA20 > EMA50"
                    send_tg(msg)
                elif ema20 < ema50 and rsi >= 68:
                    msg = f"🔻 *SELL {nome}*\nRSI: {rsi:.1f} (68 stretto)\nPrezzo: {price:.5f}\nEMA20 < EMA50"
                    send_tg(msg)

                print(f"[{datetime.now().strftime('%H:%M:%S')}] {nome} RSI:{rsi:.1f} P:{price:.5f} EMA20:{'UP' if ema20>ema50 else 'DOWN'}")
                time.sleep(2)

        except Exception as e:
            print(f"Errore loop: {e}")
            time.sleep(10)
        
        print("--- Scan OK V36.8 STRETTO attendo 2m ---")
        time.sleep(120)

Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
