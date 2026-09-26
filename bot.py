import os, time, threading, requests, json, gc
from flask import Flask
import websocket

app = Flask(__name__)
@app.route('/')
def home(): return "V17 FINAL 15%"
@app.route('/ping')
def ping(): return "OK"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POCKET_SSID = os.getenv("POCKET_SSID")

PAIRS = ["EURUSD_otc","GBPUSD_otc","BTCUSD_otc","ETHUSD_otc","EURJPY_otc","GBPJPY_otc"]
sent = {}
fail_count = 0

def send_tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id":TELEGRAM_CHAT_ID,"text":m,"parse_mode":"Markdown"}, timeout=10)
    except: pass

def rsi(closes,p=14):
    if len(closes)<p+1: return 50
    g=[]; l=[]
    for i in range(1,len(closes)):
        d=closes[i]-closes[i-1]
        g.append(max(d,0)); l.append(max(-d,0))
    ag=sum(g[-p:])/p; al=sum(l[-p:])/p
    if al==0: return 70
    return 100-(100/(1+ag/al))

def get_candles(pair,period):
    global fail_count
    candles=[]
    try:
        def on_msg(ws,msg):
            try:
                if '42' in msg and ('candles' in msg or 'history' in msg):
                    j=json.loads(msg[2:])
                    if len(j)>1 and isinstance(j[1],dict):
                        if 'candles' in j[1]: candles.extend(j[1]['candles'])
                        if 'history' in j[1]: candles.extend(j[1]['history'])
                        if 'data' in j[1] and isinstance(j[1]['data'],list): candles.extend(j[1]['data'])
            except: pass

        ws=websocket.WebSocketApp("wss://api-eu.po.market/socket.io/?EIO=3&transport=websocket", on_message=on_msg, on_error=lambda w,e:None)
        def run():
            time.sleep(0.5)
            try:
                ws.send("2::"); time.sleep(0.3)
                ws.send("40"); time.sleep(0.5)
                ws.send(f'42["auth",{{"session":"{POCKET_SSID}","isDemo":1}}]'); time.sleep(1.5)
                asset=pair.replace("_otc","").upper()
                otc="_otc" in pair.lower()
                ws.send(f'42["loadHistory",{{"asset":"{asset}","period":{period},"isOtc":{str(otc).lower()}}}]')
                time.sleep(4)
                ws.close()
            except:
                try: ws.close()
                except: pass
        t=threading.Thread(target=run,daemon=True); t.start()
        ws.run_forever(ping_timeout=10); t.join(timeout=6)
    except: pass
    gc.collect()
    if len(candles)>=5:
        fail_count=0
        return candles[-30:]
    else:
        fail_count+=1
        return []

def is_perfect(candles):
    if len(candles)<10: return None
    last=candles[-2]
    try:
        o=float(last.get('open',0)) if isinstance(last,dict) else float(last[1])
        c=float(last.get('close',0)) if isinstance(last,dict) else float(last[2])
        h=float(last.get('high',0)) if isinstance(last,dict) else float(last[3])
        l=float(last.get('low',0)) if isinstance(last,dict) else float(last[4])
        tot=h-l
        if tot==0: return None
        body=abs(c-o); up=h-max(o,c); low=min(o,c)-l
        closes=[float(x.get('close',0)) if isinstance(x,dict) else float(x[2]) for x in candles[-20:]]
        r=rsi(closes)
        if low/tot>=0.15 and body/tot<=0.70: return "BUY",f"TURBO {low/tot*100:.0f}% RSI {r:.0f}"
        if up/tot>=0.15 and body/tot<=0.70: return "SELL",f"TURBO {up/tot*100:.0f}% RSI {r:.0f}"
    except: pass
    return None

def process(pair,period,label):
    try:
        k=f"{pair}_{label}"
        if k in sent and time.time()-sent[k]<60: return
        candles=get_candles(pair,period)
        if not candles: return
        res=is_perfect(candles)
        if res:
            d,det=res; e="🔵" if d=="BUY" else "🔴"
            send_tg(f"💎 *{label} {e} {pair.upper()} {d}*\n{det}\n⏰ {label}"); sent[k]=time.time()
    except: pass

def bot_loop():
    global fail_count
    send_tg("✅ *V17 FINAL ONLINE*\n💥 SSID OK - Test 15% attivo")
    while True:
        try:
            if fail_count>=20:
                time.sleep(15); fail_count=0
            for period,label in [(300,"M5"),(900,"M15")]:
                for p in PAIRS:
                    process(p,period,label)
                    time.sleep(1)
        except: time.sleep(10)
        time.sleep(2)

def run_flask():
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))

if __name__=="__main__":
    threading.Thread(target=run_flask,daemon=True).start()
    bot_loop()
