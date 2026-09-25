import os, time, threading, requests, json, gc
from flask import Flask
import websocket
app = Flask(__name__)
@app.route('/')
def home():
    return "V16 TEST 15% REAL FIX"
@app.route('/ping')
def ping():
    return "OK"
TELEGRAM_TOKEN=os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID")
POCKET_SSID=os.getenv("POCKET_SSID")
PAIRS=["EURUSD","GBPUSD","USDJPY","AUDUSD","EURUSD_otc","GBPUSD_otc","BTCUSD_otc","ETHUSD_otc","EURJPY_otc","GBPJPY_otc"]
sent={}; fail_count=0
def send_tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",data={"chat_id":TELEGRAM_CHAT_ID,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass
def rsi(closes,p=14):
    if len(closes)<p+1: return 50
    g=[]; l=[]
    for i in range(1,len(closes)): d=closes[i]-closes[i-1]; g.append(max(d,0)); l.append(max(-d,0))
    ag=sum(g[-p:])/p; al=sum(l[-p:])/p
    if al==0: return 70
    return 100-(100/(1+ag/al))
def get_candles(pair,period):
    global fail_count; candles=[]; ws=None
    try:
        def on_msg(w,msg):
            try:
                if '42' in msg: j=json.loads(msg[2:]); d=j[1] if len(j)>1 else {}
                if isinstance(d,dict):
                    if 'candles' in d: candles.extend(d['candles'])
                    if 'history' in d: candles.extend(d['history'])
            except: pass
        ws=websocket.WebSocketApp("wss://api-eu.po.market/socket.io/?EIO=3&transport=websocket",on_message=on_msg,on_error=lambda w,e:None)
        def run():
            time.sleep(0.3)
            try:
                ws.send("40"); time.sleep(0.3)
                ws.send(f'42["auth",{{"session":"{POCKET_SSID}","isDemo":1}}]'); time.sleep(0.8)
                asset=pair.replace("_otc","").upper(); otc="_otc" in pair.lower()
                ws.send(f'42["loadHistory",{{"asset":"{asset}","period":{period},"isOtc":{str(otc).lower()}}}]'); time.sleep(2.5); ws.close()
            except:
                try: ws.close() except: pass
        t=threading.Thread(target=run,daemon=True); t.start(); ws.run_forever(ping_timeout=5); t.join(timeout=4)
    except: pass
    finally:
        try:
            if ws: ws.close()
        except: pass
        gc.collect()
    if len(candles)>=8: fail_count=0; return candles[-30:]
    else: fail_count+=1; return []
def is_perfect(candles):
    if len(candles)<10: return None
    last=candles[-2]
    try:
        o=float(last.get('open',0)) if isinstance(last,dict) else float(last[1]); c=float(last.get('close',0)) if isinstance(last,dict) else float(last[2]); h=float(last.get('high',0)) if isinstance(last,dict) else float(last[3]); l=float(last.get('low',0)) if isinstance(last,dict) else float(last[4])
        tot=h-l
        if tot==0: return None
        body=abs(c-o); up=h-max(o,c); low=min(o,c)-l
        closes=[float(x.get('close',0)) if isinstance(x,dict) else float(x[2]) for x in candles[-20:]]; r=rsi(closes)
        if low/tot>=0.15 and body/tot<=0.70 and r<=70:
            return "BUY",f"TURBO {low/tot*100:.0f}% RSI {r:.0f}"
        if up/tot>=0.15 and body/tot<=0.70 and r>=30:
            return "SELL",f"TURBO {up/tot*100:.0f}% RSI {r:.0f}"
    except: pass
    return None
def process(pair,period,label):
    try:
        k=f"{pair}_{label}"
        if k in sent and time.time()-sent[k]<90: return
        candles=get_candles(pair,period)
        if not candles: return
        sm={"M5":"5 MINUTI","M15":"15 MINUTI","H1":"1 ORA"}; scad=sm.get(label,label); res=is_perfect(candles)
        if res:
            d,det=res; e="🔵" if d=="BUY" else "🔴"; send_tg(f"💎 *{label} {e} {pair.upper()} {d}*\n{det}\n⏰ {scad}"); sent[k]=time.time()
    except: pass
def bot_loop():
    global fail_count; send_tg("✅ *V16 TEST 15% ONLINE*\n💥 Test segnali attivi!")
    while True:
        try:
            if fail_count>=40: send_tg("⏳ *Pocket lagga un attimo... attendo*"); fail_count=0; time.sleep(20)
            for period,label in [(300,"M5"),(900,"M15"),(3600,"H1")]:
                for i in range(0,len(PAIRS),4):
                    batch=PAIRS[i:i+4]; ths=[]
                    for p in batch: th=threading.Thread(target=process,args=(p,period,label),daemon=True); th.start(); ths.append(th)
                    for th in ths: th.join(timeout=12)
                    time.sleep(1)
        except: time.sleep(10)
        time.sleep(3)
def run_flask():
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))
if __name__=="__main__":
    threading.Thread(target=run_flask,daemon=True).start(); bot_loop()as
