import os, time, threading, requests, json, gc
from flask import Flask
import websocket
app = Flask(__name__)
@app.route('/')
def home(): return "V15.9 TURBO 30% LIVE"
@app.route('/ping')
def ping(): return "OK"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POCKET_SSID = os.getenv("POCKET_SSID")
PAIRS = ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","EURJPY","GBPJPY","EURGBP","AUDJPY","NZDUSD","USDCHF","EURCHF","CADJPY","AUDCAD","NZDJPY","EURNZD","EURUSD_otc","GBPUSD_otc","USDJPY_otc","AUDUSD_otc","EURJPY_otc","GBPJPY_otc","AUDJPY_otc","BTCUSD_otc","ETHUSD_otc","EURGBP_otc","USDCHF_otc","EURCHF_otc","GBPCHF_otc","AUDCHF_otc","CADCHF_otc"]
sent={}
def send_tg(msg):
 try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=8)
 except: pass
def rsi(closes, p=14):
 if len(closes)<p+1: return 50
 gains=[]; losses=[]
 for i in range(1,len(closes)):
  d=closes[i]-closes[i-1]; gains.append(max(d,0)); losses.append(max(-d,0))
 ag=sum(gains[-p:])/p; al=sum(losses[-p:])/p
 if al==0: return 70
 return 100-(100/(1+ag/al))
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
def is_perfect(candles):
 if len(candles)<10: return None
 last=candles[-2]
 try:
  if isinstance(last, dict): o=float(last.get('open',0)); c=float(last.get('close',0)); h=float(last.get('high',0)); l=float(last.get('low',0))
  else: o=float(last[1]); c=float(last[2]); h=float(last[3]); l=float(last[4])
  total=h-l
  if total==0: return None
  body=abs(c-o); up=h-max(o,c); low=min(o,c)-l
  closes=[float(x.get('close',0)) if isinstance(x,dict) else float(x[2]) for x in candles[-20:]]
  r=rsi(closes)
  # TURBO 30% - SPARA TUTTO
  if low/total>=0.30 and body/total<=0.60 and r<=70:
   return "BUY", f"TURBO PINBAR Coda {low/total*100:.0f}% RSI {r:.0f}"
  if up/total>=0.30 and body/total<=0.60 and r>=30:
   return "SELL", f"TURBO PINBAR Coda {up/total*100:.0f}% RSI {r:.0f}"
 except: pass
 return None
def process(pair, period, label):
 try:
  key=f"{pair}_{label}"
  if key in sent and time.time()-sent[key]<60: return
  candles=get_candles(pair, period)
  if not candles: return
  sm={"M5":"5 MINUTI","M15":"15 MINUTI","H1":"1 ORA","H4":"4 ORE"}
  scad=sm.get(label,label)
  res=is_perfect(candles)
  if res:
   d,det=res; e="🔵" if d=="BUY" else "🔴"
   send_tg(f"💎 *{label} {e} {pair.upper()} {d}*\n{det}\n⏰ {scad}")
   sent[key]=time.time()
 except: pass
def bot_loop():
 send_tg("✅ *V15.9 TURBO 30% ONLINE*\n💥 LARGATISSIMO - 1 segnale in 10min!")
 while True:
  try:
   for period,label in [(300,"M5"),(900,"M15"),(3600,"H1")]:
    for i in range(0, len(PAIRS), 6):
     batch=PAIRS[i:i+6]
     ths=[]
     for p in batch:
      th=threading.Thread(target=process, args=(p,period,label), daemon=True)
      th.start(); ths.append(th)
     for th in ths: th.join(timeout=8)
     time.sleep(1)
  except: time.sleep(10)
  time.sleep(5)
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
if __name__=="__main__":
 threading.Thread(target=run_flask, daemon=True).start()
 bot_loop()
