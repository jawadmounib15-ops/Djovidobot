import os, time, threading, requests, json, gc, random
from flask import Flask
import websocket
app = Flask(__name__)
@app.route('/')
def home(): return "TEST LARGHISSIMO LIVE"
@app.route('/ping')
def ping(): return "OK"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POCKET_SSID = os.getenv("POCKET_SSID")
PAIRS = ["EURUSD_otc","GBPUSD_otc","AUDUSD_otc","EURJPY_otc","BTCUSD_otc","ETHUSD_otc"]

def send_tg(msg):
 try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=8)
 except: pass

def get_candles_mock(pair):
 # SIMULAZIONE CANDELE PER TEST - così siamo sicuri che manda
 o = 1.0 + random.random()*0.01
 c = o + random.uniform(-0.005, 0.005)
 h = max(o,c) + random.uniform(0.001, 0.008)
 l = min(o,c) - random.uniform(0.001, 0.008)
 return [{'open':o,'close':c,'high':h,'low':l} for _ in range(20)] + [{'open':o,'close':c,'high':h,'low':l}]

def bot_loop():
 send_tg("✅ *TEST LARGHISSIMO ONLINE*\n🧪 Mando segnali ogni 30sec per prova!")
 c=0
 while True:
  try:
   c+=1
   pair = random.choice(PAIRS)
   label = random.choice(["M5","M15"])
   direction = random.choice(["BUY","SELL"])
   emoji = "🔵" if direction=="BUY" else "🔴"
   # SEGNALE LARGHISSIMO - qualsiasi cosa
   send_tg(f"💎 *{label} {emoji} {pair.upper()} {direction} - TEST*\n📊 Prova segnale {c}\n⏰ 5 MINUTI\n🔥 Se vedi questo, Telegram OK!")
   if c==3:
    send_tg(f"✅ *CONFERMA: Telegram funziona perfetto!*\nOra ti preparo il TURBO vero che prende candele reali!")
   time.sleep(35)
  except:
   time.sleep(10)

def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
if __name__=="__main__":
 threading.Thread(target=run_flask, daemon=True).start()
 bot_loop()
