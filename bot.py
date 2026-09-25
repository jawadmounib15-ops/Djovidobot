import os, time, threading, requests, json, gc
from flask import Flask
import websocket
app = Flask(__name__)
@app.route('/')
def home(): return "V15.7 ULTRA LARGATO LIVE"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POCKET_SSID = os.getenv("POCKET_SSID")
PAIRS = ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","EURJPY","GBPJPY","EURGBP","AUDJPY","NZDUSD","USDCHF","EURCHF","CADJPY","AUDCAD","NZDJPY","EURNZD","EURUSD_otc","GBPUSD_otc","USDJPY_otc","AUDUSD_otc","EURJPY_otc","GBPJPY_otc","AUDJPY_otc","BTCUSD_otc","ETHUSD_otc","EURGBP_otc","USDCHF_otc","EURCHF_otc","GBPCHF_otc","AUDCHF_otc","CADCHF_otc"]
sent = {}
def send_tg(msg):
    try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=8)
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
        ws = websocket.WebSocketApp("wss://api-eu.po.market/socket.io/?EIO=3&transport=websocket", on_message=on_message)
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
        # ULTRA LARGATO 45% invece di 50%
        if low/total>=0.45 and body/total<=0.40 and r<=55:
            return "BUY", f"L1 PINBAR Coda {low/total*100:.0f}% RSI {r:.0f}"
        if up/total>=0.45 and body/total<=0.40 and r>=45:
            return "SELL", f"L1 PINBAR Coda {up/total*100:.0f}% RSI {r:.0f}"
    except: pass
    return None

def is_double_top(candles):
    try:
        if len(candles)<15: return None
        highs=[]
        for i in range(len(candles)-15, len(candles)-2):
            c=candles[i]
            h=float(c.get('high',0)) if isinstance(c,dict) else float(c[3])
            highs.append((i,h))
        top1=max(highs, key=lambda x: x[1])
        rest=[x for x in highs if abs(x[0]-top1[0])>=2]
        if not rest: return None
        top2=max(rest, key=lambda x: x[1])
        h1=top1[1]; h2=top2[1]
        if abs(h1-h2)/h1 > 0.003: return None
        last=candles[-2]
        close=float(last.get('close',0)) if isinstance(last,dict) else float(last[2])
        if close < h1*0.999:
            return f"L2 M {h1:.5f} + {h2:.5f}"
    except: pass
    return None

def is_double_bottom(candles):
    try:
        if len(candles)<15: return None
        lows=[]
        for i in range(len(candles)-15, len(candles)-2):
            c=candles[i]
            l=float(c.get('low',0)) if isinstance(c,dict) else float(c[4])
            lows.append((i,l))
        bot1=min(lows, key=lambda x: x[1])
        rest=[x for x in lows if abs(x[0]-bot1[0])>=2]
        if not rest: return None
        bot2=min(rest, key=lambda x: x[1])
        l1=bot1[1]; l2=bot2[1]
        if abs(l1-l2)/l1 > 0.003: return None
        last=candles[-2]
        close=float(last.get('close',0)) if isinstance(last,dict) else float(last[2])
        if close > l1*1.001:
            return f"L3 W {l1:.5f} + {l2:.5f}"
    except: pass
    return None

def is_engulfing(candles):
    try:
        if len(candles)<5: return None
        prev=candles[-3]; last=candles[-2]
        if isinstance(prev, dict): po=float(prev.get('open',0)); pc=float(prev.get('close',0))
        else: po=float(prev[1]); pc=float(prev[2])
        if isinstance(last, dict): o=float(last.get('open',0)); c=float(last.get('close',0))
        else: o=float(last[1]); c=float(last[2])
        if pc<po and c>o and c>po and o<pc:
            return "BUY", f"L4 ENGULF BULL"
        if pc>po and c<o and c<po and o>pc:
            return "SELL", f"L4 ENGULF BEAR"
    except: pass
    return None

def process(pair, period, label):
    try:
        key=f"{pair}_{label}"
        if key in sent and time.time()-sent[key]<300: return # 5 MIN COOLDOWN
        candles=get_candles(pair, period)
        if not candles: return
        sm={"M5":"5 MINUTI","M15":"15 MINUTI","H1":"1 ORA","H4":"4 ORE"}
        scad=sm.get(label,label)
        res=is_perfect(candles)
        if res:
            d,det=res; e="🔵" if d=="BUY" else "🔴"
            send_tg(f"💎 *{label} {e} {pair.upper()} {d}*\n{det}\n⏰ {scad}")
            sent[key]=time.time(); return
        dt=is_double_top(candles)
        if dt:
            send_tg(f"🔥 *{label} 🔴 {pair.upper()} SELL*\n{dt}\n⏰ {scad}")
            sent[key]=time.time(); return
        db=is_double_bottom(candles)
        if db:
            send_tg(f"🔥 *{label} 🔵 {pair.upper()} BUY*\n{db}\n⏰ {scad}")
            sent[key]=time.time(); return
        eng=is_engulfing(candles)
        if eng:
            d,det=eng; e="🔵" if d=="BUY" else "🔴"
            send_tg(f"⚡ *{label} {e} {pair.upper()} {d}*\n{det}\n⏰ {scad}")
            sent[key]=time.time(); return
    except: pass

def bot_loop():
    send_tg("✅ *V15.7 ULTRA LARGATO ONLINE*\n💎 45% Pinbar | M | W | Engulfing\n⏰ Cooldown 5min - TEST SEGNALI!")
    while True:
        try:
            for period,label in [(300,"M5"),(900,"M15"),(3600,"H1"),(14400,"H4")]:
                for i in range(0, len(PAIRS), 5):
                    batch=PAIRS[i:i+5]
                    ths=[]
                    for p in batch:
                        th=threading.Thread(target=process, args=(p,period,label), daemon=True)
                        th.start(); ths.append(th)
                    for th in ths: th.join(timeout=8)
                    time.sleep(1)
        except: time.sleep(10)
        time.sleep(10)

def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
if __name__=="__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot_loop()
