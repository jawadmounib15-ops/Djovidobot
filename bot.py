import os, time, threading, requests, json
from flask import Flask
import websocket
import statistics
app = Flask(__name__)
@app.route('/')
def home(): return "V14 PINBAR 26 + SQUEEZE 13 REALI LIVE"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POCKET_SSID = os.getenv("POCKET_SSID")

PAIRS_ALL = ["EURUSD","EURUSD_otc","GBPUSD","GBPUSD_otc","USDJPY","USDJPY_otc","AUDUSD","AUDUSD_otc","USDCAD","USDCAD_otc","EURJPY","EURJPY_otc","GBPJPY","GBPJPY_otc","EURGBP","EURGBP_otc","AUDJPY","AUDJPY_otc","NZDUSD","NZDUSD_otc","USDCHF","USDCHF_otc","EURCHF","EURCHF_otc","CADJPY","CADJPY_otc"]
PAIRS_REAL_ONLY = ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","EURJPY","GBPJPY","EURGBP","AUDJPY","NZDUSD","USDCHF","EURCHF","CADJPY"]

sent = {}
def send_tg(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode":"Markdown"}, timeout=10)
    except: pass

def get_candles_pocket(pair, period=300, count=30):
    candles=[]
    try:
        def on_message(ws, message):
            if message.startswith('42'):
                try:
                    d=json.loads(message[2:])
                    if isinstance(d,list) and len(d)>1 and 'candles' in str(d):
                        for c in d[1].get('candles',[]): candles.append(c)
                except: pass
        ws=websocket.WebSocketApp(f"wss://api-eu.po.market/socket.io/?EIO=3&transport=websocket", on_message=on_message)
        def run():
            time.sleep(1)
            try:
                ws.send("40"); time.sleep(0.5)
                ws.send(f'42["auth",{{"session":"{POCKET_SSID}"}}]'); time.sleep(0.8)
                clean=pair.replace("_otc","").replace("_","").upper()
                ws.send(f'42["changeSymbol",{{"asset":"{clean}","period":{period}}}]')
                if "_otc" in pair.lower():
                    time.sleep(0.3); ws.send(f'42["changeSymbol",{{"asset":"{clean}_otc","period":{period}}}]')
                time.sleep(2); ws.close()
            except: pass
        t=threading.Thread(target=run, daemon=True); t.start()
        ws.run_forever(ping_timeout=5); t.join(timeout=4)
    except: pass
    return candles[-30:] if len(candles)>=10 else []

def rsi(closes, period=14):
    if len(closes)<period+1: return 50
    gains=[]; losses=[]
    for i in range(1,len(closes)):
        d=closes[i]-closes[i-1]; gains.append(max(d,0)); losses.append(max(-d,0))
    avg_g=sum(gains[-period:])/period; avg_l=sum(losses[-period:])/period
    if avg_l==0: return 70 if avg_g>0 else 50
    return 100-(100/(1+avg_g/avg_l))

def bollinger(closes, period=20, std=2):
    if len(closes)<period: return None,None,None,None
    ma=statistics.mean(closes[-period:]); st=statistics.stdev(closes[-period:]) if len(closes[-period:])>1 else 0
    return ma+std*st, ma-std*st, ma, (2*std*st)/ma if ma!=0 else 0

def check_pinbar(candles):
    if len(candles)<5: return None
    last=candles[-2] if len(candles)>=2 else candles[-1]
    try:
        if isinstance(last, dict): o=float(last.get('open',0)); c=float(last.get('close',0)); h=float(last.get('high',0)); l=float(last.get('low',0))
        elif isinstance(last,(list,tuple)) and len(last)>=5: o=float(last[1]); c=float(last[2]); h=float(last[3]); l=float(last[4])
        else: return None
        body=abs(c-o) or 0.00001; up_w=h-max(o,c); lw=min(o,c)-l
        closes=[];
        for x in candles[-20:]:
            try:
                if isinstance(x,dict): closes.append(float(x.get('close',0)))
                elif isinstance(x,(list,tuple)): closes.append(float(x[2]))
            except: pass
        r=rsi(closes)
        if lw/body>=2.0 and lw>up_w*1.5 and 22<=r<=38: return "BUY", f"Pinbar BUY coda sotto {lw/body:.1f}x RSI {r:.0f}"
        if up_w/body>=2.0 and up_w>lw*1.5 and 58<=r<=82: return "SELL", f"Pinbar SELL coda sopra {up_w/body:.1f}x RSI {r:.0f}"
    except: pass
    return None

def check_squeeze(candles):
    if len(candles)<22: return None
    closes=[]
    for x in candles[-22:]:
        try:
            if isinstance(x,dict): closes.append(float(x.get('close',0)))
            elif isinstance(x,(list,tuple)): closes.append(float(x[2]))
        except: pass
    if len(closes)<21: return None
    widths=[]
    for i in range(len(closes)-8, len(closes)):
        up,low,ma,w=bollinger(closes[:i+1])
        if w is not None: widths.append(w)
    if len(widths)<6: return None
    avg_w=statistics.mean(widths[:-2]); last_w=widths[-1]
    up,low,ma,w=bollinger(closes)
    if up is None: return None
    r=rsi(closes); last_close=closes[-1]
    if avg_w<0.0025 and last_w<0.0035:
        if last_close>up and 52<=r<=68: return "BUY", f"SQUEEZE BREAKOUT UP banda {last_w:.4f} RSI {r:.0f}"
        if last_close<low and 32<=r<=48: return "SELL", f"SQUEEZE BREAKOUT DOWN banda {last_w:.4f} RSI {r:.0f}"
    return None

def bot_loop():
    time.sleep(3)
    send_tg("✅ *V14 ONLINE*\n📌 PINBAR su 26 REALI+OTC\n🚀 SQUEEZE solo su 13 REALI\nCandele VERE Pocket")
    while True:
        try:
            for pair in PAIRS_ALL:
                if pair in sent and time.time()-sent[pair]<600: continue
                candles=get_candles_pocket(pair, period=300, count=30)
                if len(candles)<15: continue
                res=check_pinbar(candles); tipo="📌 PINBAR"
                if not res and pair in PAIRS_REAL_ONLY:
                    res=check_squeeze(candles); tipo="🚀 SQUEEZE REALI"
                if res:
                    direction,detail=res; emoji="🔵" if direction=="BUY" else "🔴"
                    send_tg(f"{tipo} {emoji} *{pair.upper()} {direction} 5m* - VERE ✅\n{detail}\n⏰ Entra 5 min {direction}")
                    sent[pair]=time.time()
                time.sleep(1.2)
        except Exception as e:
            print(f"err {e}")
        time.sleep(30)

def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
if __name__=="__main__":
    threading.Thread(target=run_flask, daemon=True).start(); bot_loop()
