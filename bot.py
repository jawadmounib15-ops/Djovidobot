import os, time, requests, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import yfinance as yf
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")

def keep_alive():
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        def log_message(self, *a):
            return
    HTTPServer(('0.0.0.0', int(os.getenv("PORT","10000"))), H).serve_forever()
threading.Thread(target=keep_alive, daemon=True).start()

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","USDCHF=X","EURJPY=X","GBPJPY=X"]

def send(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id":CHAT,"text":m})
    except: pass

send("BOT V12 - 3 LAVORI - 15 MIN - PARTITO!")

while True:
    try:
        for p in PAIRS:
            df = yf.download(p, period="5d", interval="15m", progress=False, auto_adjust=True)
            if len(df) < 210: continue
            c = df['Close']
            o = df['Open']
            ema50 = float(EMAIndicator(c, 50).ema_indicator().iloc[-1])
            ema200 = float(EMAIndicator(c, 200).ema_indicator().iloc[-1])
            rsi = float(RSIIndicator(c, 14).rsi().iloc[-1])
            price = float(c.iloc[-1])
            
            # Lavoro 2 - candele
            prev_close = float(c.iloc[-2])
            prev_open = float(o.iloc[-2])
            curr_open = float(o.iloc[-1])
            curr_close = float(c.iloc[-1])
            # Engulfing
            bull_eng = curr_close > curr_open and prev_close < prev_open and curr_close > prev_open and curr_open < prev_close
            bear_eng = curr_close < curr_open and prev_close > prev_open and curr_close < prev_open and curr_open > prev_close
            
            signal = None
            # Lavoro 3 - SICURO (tutti insieme)
            if price > ema50 and ema50 > ema200 and 25 < rsi < 70 and bull_eng:
                signal = f"🟢 BUY SICURO 80% {p} - 3 LAVORI OK - 15 MIN"
            elif price < ema50 and ema50 < ema200 and 30 < rsi < 75 and bear_eng:
                signal = f"🔴 SELL SICURO 80% {p} - 3 LAVORI OK - 15 MIN"
            # Lavoro 1 - Trend
            elif price > ema50 and ema50 > ema200 and 30 < rsi < 68:
                signal = f"BUY Trend {p} RSI {rsi:.0f} 15MIN"
            elif price < ema50 and ema50 < ema200 and 32 < rsi < 70:
                signal = f"SELL Trend {p} RSI {rsi:.0f} 15MIN"
            # Lavoro 2 - Solo candela forte
            elif bull_eng and 30 < rsi < 70:
                signal = f"BUY Candela 80% {p} Engulfing 15MIN"
            elif bear_eng and 30 < rsi < 70:
                signal = f"SELL Candela 80% {p} Engulfing 15MIN"

            if signal: send(signal)
            time.sleep(3)
        time.sleep(900)
    except:
        time.sleep(60)
