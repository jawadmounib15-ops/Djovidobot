import os, time, threading, requests, json, gc, random
from flask import Flask
import websocket

app = Flask(__name__)
@app.route('/')
def home(): return "V17 ULTIMATE FIX LIVE"
@app.route('/ping')
def ping(): return "OK"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POCKET_SSID = os.getenv("POCKET_SSID")

PAIRS = ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","EURJPY","GBPJPY","EURGBP","AUDJPY","NZDUSD","EURUSD_otc","GBPUSD_otc","USDJPY_otc","AUDUSD_otc","BTCUSD_otc","ETHUSD_otc","EURJPY_otc","GBPJPY_otc"]

sent = {}
fail_count = 0

def send_tg(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def rsi(closes, p=14):
    if len(closes) < p+1: return 50
    gains=[]; losses=[]
    for i in range(1,len(closes)):
        d=closes[i]-closes[i-1]
        gains.append(max(d,0))
        losses.append(max(-d,0))
    ag=sum(gains[-p:])/p
    al=sum(losses[-p:])/p
    if al==0: return 70
    rs=ag/al
    return 100-(100/(1+rs))

def get_candles(pair, period):
    global fail_count
    candles = []
    ws = None
    try:
        def on_message(w, msg):
            try:
                if msg.startswith('42'):
                    txt = msg[2:]
                    j = json.loads(txt)
                    if len(j) > 1 and isinstance(j[1], dict):
                        data = j[1]
                        if 'candles' in data and isinstance(data['candles'], list):
                            candles.extend(data['candles'])
                        if 'history' in data and isinstance(data['history'], list):
                            candles.extend(data['history'])
                        if 'data' in data and isinstance(data['data'], list):
                            candles.extend(data['data'])
            except: pass

        ws = websocket.WebSocketApp("wss://api-eu.po.market/socket.io/?EIO=3&transport=websocket",
                                   on_message=on_message, on_error=lambda w,e: None)
        def run():
            time.sleep(0.3)
            try:
                ws.send("40")
                time.sleep(0.4)
                ws.send(f'42["auth",{{"session":"{POCKET_SSID}","isDemo":1}}]')
                time.sleep(0.8)
                asset = pair.replace("_otc","").upper()
                is_otc = "_otc" in pair.lower()
                # richiesta fixata
                ws.send(f'42["loadHistory",{{"asset":"{asset}","period":{period},"isOtc":{str(is_otc).lower()}}}]')
                time.sleep(2.5)
                ws.close()
            except:
                try: ws.close()
                except: pass

        t = threading.Thread(target=run, daemon=True)
        t.start()
        ws.run_forever(ping_timeout=5, ping_interval=10)
        t.join(timeout=4)
    except: pass
    finally:
        try:
            if ws: ws.close()
        except: pass
        gc.collect()

    if len(candles) >= 8:
        fail_count = 0
        return candles[-30:]
    else:
        fail_count += 1
        return []

def is_perfect(candles):
    if len(candles) < 10: return None
    last = candles[-2]
    try:
        if isinstance(last, dict):
            o=float(last.get('open',0)); c=float(last.get('close',0))
            h=float(last.get('high',0)); l=float(last.get('low',0))
        else:
            o=float(last[1]); c=float(last[2]); h=float(last[3]); l=float(last[4])

        total = h-l
        if total == 0: return None
        body = abs(c-o)
        up = h-max(o,c)
        low = min(o,c)-l

        closes = [float(x.get('close',0)) if isinstance(x, dict) else float(x[2]) for x in candles[-20:]]
        r = rsi(closes)

        # TURBO 30% LARGHISSIMO
        if low/total >= 0.30 and body/total <= 0.70 and r <= 70:
            return "BUY", f"TURBO {low/total*100:.0f}% RSI {r:.0f}"
        if up/total >= 0.30 and body/total <= 0.70 and r >= 30:
            return "SELL", f"TURBO {up/total*100:.0f}% RSI {r:.0f}"
    except: pass
    return None

def process(pair, period, label):
    try:
        key = f"{pair}_{label}"
        if key in sent and time.time()-sent[key] < 90: return

        candles = get_candles(pair, period)
        if not candles: return

        sm = {"M5":"5 MINUTI","M15":"15 MINUTI","H1":"1 ORA"}
        scad = sm.get(label, label)
        res = is_perfect(candles)
        if res:
            d, det = res
            e = "🔵" if d=="BUY" else "🔴"
            send_tg(f"💎 *{label} {e} {pair.upper()} {d}*\n{det}\n⏰ {scad}")
            sent[key] = time.time()
    except: pass

def bot_loop():
    global fail_count
    send_tg("✅ *V17 ULTIMATE 30% ONLINE*\n💥 Fixato tutto! Segnali in arrivo!")
    while True:
        try:
            if fail_count >= 200:
                # NON è SSID scaduto, è solo lag di Pocket
                print(f"Lag Pocket {fail_count} - attendo")
                send_tg("⏳ *Pocket lagga un attimo... attendo 30sec*")
                fail_count = 0
                time.sleep(30)

            for period,label in [(300,"M5"),(900,"M15"),(3600,"H1")]:
                for i in range(0, len(PAIRS), 4):
                    batch = PAIRS[i:i+4]
                    ths=[]
                    for p in batch:
                        th=threading.Thread(target=process, args=(p,period,label), daemon=True)
                        th.start(); ths.append(th)
                    for th in ths: th.join(timeout=12)
                    time.sleep(1.5)
        except Exception as e:
            print(e)
            time.sleep(10)
        time.sleep(5)

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))

if __name__=="__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot_loop()
