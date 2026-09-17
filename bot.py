import threading, time, requests, os
from flask import Flask
import yfinance as yf

app = Flask(__name__)

# FIX NOME VARIABILI - legge sia CHAT_ID che CHAT
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_CHAT")

print(f"TOKEN presente? {bool(TELEGRAM_TOKEN)} CHAT presente? {bool(TELEGRAM_CHAT)}", flush=True)

def send_telegram(msg):
    try:
        if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
            print("MANCA TOKEN O CHAT ID!", flush=True)
            return
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        r = requests.post(url, data={"chat_id": TELEGRAM_CHAT, "text": msg}, timeout=10)
        print(f"TELEGRAM RISPOSTA: {r.status_code} - {r.text[:100]}", flush=True)
        print(f"INVIATO: {msg}", flush=True)
    except Exception as e:
        print(f"ERRORE TELEGRAM: {e}", flush=True)

def get_price(data):
    try:
        val = data['Close'].iloc[-1]
        if hasattr(val, 'iloc'): val = val.iloc[0]
        if hasattr(val, 'item'): val = val.item()
        return float(val)
    except:
        return float(data['Close'].values[-1])

def check_pair(symbol):
    try:
        data = yf.download(symbol+"=X", period="1d", interval="5m", progress=False, auto_adjust=True)
        if len(data) < 50: return None
        close = data['Close']
        if hasattr(close, 'iloc') and hasattr(close.iloc[-1], 'iloc'):
             close = close.iloc[:,0]
        delta = close.diff()
        gain = delta.where(delta>0,0).rolling(14).mean()
        loss = -delta.where(delta<0,0).rolling(14).mean()
        rs = gain/loss
        rsi = 100 - (100/(1+rs))
        last_rsi_raw = rsi.iloc[-1]
        if hasattr(last_rsi_raw, 'iloc'): last_rsi_raw = last_rsi_raw.iloc[0]
        last_rsi = float(last_rsi_raw)
        price = get_price(data)
        print(f"CHECK {symbol} RSI={last_rsi:.1f} PRICE={price}", flush=True)
        if last_rsi > 60: return f"🟢 BUY SICURO {symbol} RSI {last_rsi:.1f}"
        if last_rsi < 40: return f"🔴 SELL SICURO {symbol} RSI {last_rsi:.1f}"
        return None
    except Exception as e:
        print(f"ERRORE {symbol}: {e}", flush=True)
        return None

def run_bot():
    print("MOTORE AVVIATO V9.5 FIX CHAT_ID...", flush=True)
    send_telegram("V9.5 ONLINE - FIXATO! Ora arrivano i segnali Pa!")
    pairs = ["EURUSD","GBPUSD","USDJPY","EURGBP","EURJPY","GBPJPY","AUDUSD","USDCHF"]
    while True:
        try:
            print("--- NUOVA SCANSIONE ---", flush=True)
            for p in pairs:
                signal = check_pair(p)
                if signal:
                    send_telegram(signal)
                    time.sleep(900)
                    break
            time.sleep(60)
        except Exception as e:
            print(f"ERRORE LOOP: {e}", flush=True)
            time.sleep(30)

@app.route("/")
def home():
    return "V9.5 ONLINE - FIX CHAT_ID"

threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
