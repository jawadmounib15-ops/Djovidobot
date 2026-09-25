import os, time, threading, requests, json, gc, statistics
from flask import Flask
import websocket

app = Flask(__name__)
@app.route('/')
def home(): return "V14.2 ULTRA LIGHT AUTO-READER LIVE"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POCKET_SSID = os.getenv("POCKET_SSID")

PAIRS_ALL = ["EURUSD","EURUSD_otc","GBPUSD","GBPUSD_otc","USDJPY","USDJPY_otc","AUDUSD","AUDUSD_otc","USDCAD","USDCAD_otc","EURJPY","EURJPY_otc","GBPJPY","GBPJPY_otc","EURGBP","EURGBP_otc","AUDJPY","AUDJPY_otc","NZDUSD","NZDUSD_otc","USDCHF","USDCHF_otc","EURCHF","EURCHF_otc","CADJPY","CADJPY_otc"]
PAIRS_REAL_ONLY = ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","EURJPY","GBPJPY","EURGBP","AUDJPY","NZDUSD","USDCHF","EURCHF","CADJPY"]

sent = {}

def send_tg(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode":"Markdown"}, timeout=8)
    except: pass

def rsi(closes, p=14):
    if len(closes)<p+1: return 50
    gains=[]; losses=[]
    for i in range(1,len(closes)):
        d=closes[i]-closes[i-1]
        gains.append(max(d,0)); losses.append(max(-d,0))
    ag=sum(gains[-p:])/p; al=sum(losses[-p:])/p
    if al==0: return 70
    return 100-(100/(1+ag/al))

def bollinger(closes, p=20, std=2):
    if len(closes)<p: return None,None,None,None
    ma=statistics.mean(closes[-p:])
    st=statistics.stdev(closes[-p:]) if len(closes[-p:])>1 else 0
    return ma+std*st, ma-std*st, ma, (2*std*st)/ma if ma!=0 else 0

def get_candles_one(pair):
    # LETTURA AUTOMATICA SINGOLA - si apre e si chiude subito - NO LEAK
    candles=[]
    ws=None
    try:
        def on_message(w, msg):
            if msg.startswith('42'):
                try:
                    d=json.loads(msg[2:])
                    if len(d)>1 and isinstance(d[1], dict) and 'candles' in str(d[1]):
                        for c in d[1].get('candles', []):
                            candles.append(c)
                except: pass

        ws = websocket.WebSocketApp("wss://api-eu.po.market/socket.io/?EIO=3&transport=websocket", on_message=on_message)

        def run():
            time.sleep(0.5)
            try:
                ws.send("40")
                time.sleep(0.3)
                ws.send(f'42["auth",{{"session":"{POCKET_SSID}"}}]')
                time.sleep(0.5)
                clean=pair.replace("_otc","").replace("_","").upper()
                ws.send(f'42["changeSymbol",{{"asset":"{clean}","period":300}}]')
                if "_otc" in pair.lower():
                    time.sleep(0.2)
                    ws.send(f'42["changeSymbol",{{"asset":"{clean}_otc","period":300}}]')
                time.sleep(1.5)
                ws.close()
            except:
                try: ws.close()
                except: pass

        t=threading.Thread(target=run, daemon=True)
        t.start()
        ws.run_forever(ping_timeout=3)
        t.join(timeout=2)
    except: pass
    finally:
        try:
            if ws: ws.close()
        except: pass
        gc.collect()

    return candles[-30:] if len(candles)>=10 else []

def check_pinbar(candles):
    if len(candles)<5: return None
    last=candles[-2]
    try:
        if isinstance(last, dict): o=float(last.get('open',0)); c=float(last.get('close',0)); h=float(last.get('high',0)); l=float(last.get('low',0))
        else: o=float(last[1]); c=float(last[2]); h=float(last[3]); l=float(last[4])
        body=abs(c-o) or 0.00001; up=h-max(o,c); low=min(o,c)-l
        closes=[float(x.get('close',0)) if isinstance(x,dict) else float(x[2]) for x in candles[-20:] if (isinstance(x,dict) or len(x)>=3)]
        r=rsi(closes)
        if low/body>=2.0 and low>up*1.5 and 22<=r<=38: return "BUY", f"PINBAR BUY coda {low/body:.1f}x RSI {r:.0f}"
        if up/body>=2.0 and up>low*1.5 and 58<=r<=82: return "SELL", f"PINBAR SELL coda {up/body:.1f}x RSI {r:.0f}"
    except: pass
    return None

def check_squeeze(candles):
    if len(candles)<21: return None
    closes=[float(x.get('close',0)) if isinstance(x,dict) else float(x[2]) for x in candles[-22:] if (isinstance(x,dict) or len(x)>=3)]
    if len(closes)<21: return None
    up,low,ma,w=bollinger(closes)
    if up is None: return None
    r=rsi(closes)
    avg_w=0.002
    if w is not None and w<0.0035:
        if closes[-1]>up and 52<=r<=68: return "BUY", f"SQUEEZE BREAK UP banda {w:.4f} RSI {r:.0f}"
        if closes[-1]<low and 32<=r<=48: return "SELL", f"SQUEEZE BREAK DOWN banda {w:.4f} RSI {r:.0f}"
    return None

def bot_loop():
    time.sleep(2)
    send_tg("✅ *V14.2 ULTRA LIGHT AUTO-READER ONLINE*\n📌 PINBAR 26 coppie\n🚀 SQUEEZE 13 REALI\n🧹 No memory leak - No lag")
    while True:
        try:
            for pair in PAIRS_ALL:
                # Pulisci sent vecchi per liberare memoria
                if len(sent)>40:
                    oldest=min(sent, key=sent.get)
                    del sent[oldest]

                if pair in sent and time.time()-sent[pair]<600: continue

                candles=get_candles_one(pair) # 1 alla volta - LEGGERO
                if len(candles)<10:
                    time.sleep(1)
                    continue

                res=check_pinbar(candles)
                tipo="📌 PINBAR"
                if not res and pair in PAIRS_REAL_ONLY:
                    res=check_squeeze(candles)
                    tipo="🚀 SQUEEZE"

                if res:
                    d,det=res
                    e="🔵" if d=="BUY" else "🔴"
                    send_tg(f"{tipo} {e} *{pair.upper()} {d} 5m*\n{det}\n⏰ Entra 5 min {d}")
                    sent[pair]=time.time()

                time.sleep(2.5) # pausa per non spammare RAM
                gc.collect()

        except Exception as e:
            print(e)
            time.sleep(10)
            gc.collect()
        time.sleep(25)

def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))

if __name__=="__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot_loop()
