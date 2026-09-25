import os, time, threading, requests, json, gc
from flask import Flask
import websocket
app = Flask(__name__)
@app.route('/')
def home(): return "V15.9 DEBUG LIVE"
@app.route('/ping')
def ping(): return "OK"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POCKET_SSID = os.getenv("POCKET_SSID")
PAIRS = ["EURUSD","GBPUSD","USDJPY","AUDUSD","EURJPY","BTCUSD_otc","ETHUSD_otc"]
sent={}
def send_tg(msg):
 try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=8)
 except: pass
def get_candles(pair, period):
 candles=[]; ws=None
 try:
  def on_message(w, msg):
   if msg.startswith('42'):
    try:
     d=json.loads(msg[2:])
     if len(d)>1 and isinstance(d[1], dict):
      for c in d[1].get('candles', []): candles.append(c)
    except: pass
  ws=websocket.WebSocketApp("wss://api-eu.po.market/socket.io/?EIO=3&transport=websocket", on_message=on_message)
  def run():
   time.sleep(0.2)
   try:
    ws.send("40"); time.sleep(0.2)
    ws.send(f'42["auth",{{"session":"{POCKET_SSID}"}}]'); time.sleep(0.3)
    clean=pair.replace("_otc","").upper()
    ws.send(f'42["changeSymbol",{{"asset":"{clean}","period":{period}}}]')
    if "_otc" in pair.lower():
     time.sleep(0.2); ws.send(f'42["changeSymbol",{{"asset":"{clean}_otc","period":{period}}}]')
    time.sleep(1.2); ws.close()
   except:
    try: ws.close()
    except: pass
  t=threading.Thread(target=run, daemon=True); t.start()
  ws.run_forever(ping_timeout=3); t.join(timeout=2)
 except: pass
 finally:
  try:
   if ws: ws.close()
  except: pass
  gc.collect()
 return candles[-30:] if len(candles)>=10 else []
def bot_loop():
 send_tg("✅ *V15.9 DEBUG ONLINE*\n🧪 Test ogni 2 min!")
 cnt=0
 while True:
  try:
   cnt+=1
   # TEST FAKE OGNI 2 MIN
   send_tg(f"🧪 *TEST {cnt} DEBUG*\n💎 EURUSD BUY TEST\n⏰ 5 MINUTI\nSSID OK: {POCKET_SSID[:10]}...")
   # POI PROVA VERO
   for pair in PAIRS[:2]:
    c=get_candles(pair, 300)
    if c: send_tg(f"📊 *{pair} M5* Candele prese: {len(c)} OK")
   time.sleep(120)
  except Exception as e:
   send_tg(f"❌ Errore debug: {e}")
   time.sleep(30)
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
if __name__=="__main__":
 threading.Thread(target=run_flask, daemon=True).start()
 bot_loop()
