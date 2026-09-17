import threading, time, requests, os
from flask import Flask
import yfinance as yf

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT")

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT, "text": msg}, timeout=10)
        print(f"INVIATO: {msg}", flush=True)
    except Exception as e:
        print(f"ERRORE TELEGRAM: {e}", flush=True)

def get_price(data):
    # Fix per errore 'Series'
    try:
        val = data['Close'].iloc[-1]
        # se è ancora una Series (yfinance nuovo), prendi il primo valore
        if hasattr(val, 'iloc'):
            val = val.iloc[0]
        if hasattr(val, 'item'):
            val = val.item()
        return float(val)
    except:
        return float(data['Close'].values[-1])

def check_pair(symbol):
    try:
        data = yf.download(symbol+"=X", period="1d", interval="5m", progress=False, auto_adjust=True)
        if len(data) < 50:
            print(f"{symbol} pochi dati", flush=True)
            return None

        close = data['Close']
        if hasattr(close, 'iloc') and hasattr(close.iloc[-1], 'iloc'):
             close = close.iloc[:,0] # prende prima colonna se è tabella

        delta = close.diff()
        gain = delta.where(delta>0,0).rolling(14).mean()
        loss = -delta.where(delta<0,0).rolling(14).mean()
        rs = gain/loss
        rsi = 100 - (100/(1+rs))

        last_rsi_raw = rsi.iloc[-1]
        if hasattr(last_rsi_raw, 'iloc'):
            last_rsi_raw = last_rsi_raw.iloc[0]
        last_rsi = float(last_rsi_raw)

        price = get_price(data)

        print(f"CHECK {symbol} RSI={last_rsi:.1f} PRICE={price}", flush=True)

        if last_rsi > 60:
            return f"🟢 BUY SICURO {symbol} RSI {last_rsi:.1f} PRICE {price:.5f}"
        if last_rsi < 40:
            return f"🔴 SELL SICURO {symbol} RSI {last_rsi:.1f} PRICE {price:.5f}"
        return None
    except Exception as e:
        print(f"ERRORE {symbol}: {e}", flush=True)
        return None

def run_bot():
    print("MOTORE AVVIATO V9.4 FIX SERIES...", flush=True)
    send_telegram("V9.4 ONLINE - FIX ERRORE SERIES")
    pairs = ["EURUSD","GBPUSD","USDJPY","EURGBP","EURJPY","GBPJPY","AUDUSD","USDCHF"]
    while True:
        try:
            print("--- NUOVA SCANSIONE ---", flush=True)
            for p in pairs:
                signal = check_pair(p)
                if signal:
                    send_telegram(signal)
                    print(f"SEGNALE TROVATO {p}, PAUSA 15 MIN", flush=True)
                    time.sleep(900)
                    break
            time.sleep(60)
        except Exception as e:
            print(f"ERRORE LOOP: {e}", flush=True)
            time.sleep(30)

@app.route("/")
def home():
    return "V9.4 ONLINE - FIX SERIES"

threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
