import os, time, threading, requests, json, gc
from flask import Flask
import websocket

app = Flask(__name__)
@app.route('/')
def home(): return "FIX LIVE"
@app.route('/ping')
def ping(): return "OK"

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")
SSID = os.getenv("POCKET_SSID")
PAIRS = ["EURUSD","GBPUSD","USDJPY","AUDUSD","EURJPY","GBPJPY"]
sent = {}

def send_tg(m):
    try:
        requests.post("https://api.telegram.org/bot"+TOKEN+"/sendMessage", data={"chat_id": CHAT, "text": m, "parse_mode": "Markdown"}, timeout=8)
    except:
        pass

def get_candles(pair, period):
    candles = []
    try:
        def on_msg(w, msg):
            if "candles" in msg:
                try:
                    d = json.loads(msg[2:])
                    if len(d) > 1 and isinstance(d[1], dict):
                        for c in d[1].get("candles", []):
                            candles.append(c)
                except:
                    pass
        ws = websocket.WebSocketApp("wss://api-eu.po.market/socket.io/?EIO=3&transport=websocket", on_message=on_msg)
        def run():
            time.sleep(0.3)
            try:
                ws.send("40")
                time.sleep(0.2)
                ws.send('42["auth",{"session":"'+SSID+'"}]')
                time.sleep(0.3)
                ws.send('42["changeSymbol",{"asset":"'+pair+'","period":'+str(period)+'}]')
                time.sleep(1.5)
                ws.close()
            except:
                try:
                    ws.close()
                except:
                    pass
        t = threading.Thread(target=run, daemon=True)
        t.start()
        ws.run_forever(ping_timeout=3)
        t.join(timeout=2)
    except:
        pass
    gc.collect()
    if len(candles) >= 5:
        return candles[-30:]
    return []

def process(pair, period, label):
    try:
        candles = get_candles(pair, period)
        if len(candles) == 0:
            k = "empty_"+pair+label
            if k not in sent:
                send_tg("⚠️ "+pair+" "+label+" 0 candele - Pocket non manda dati")
                sent[k] = time.time()
            return
        last = candles[-2]
        if isinstance(last, dict):
            o = float(last.get("open",0))
            c = float(last.get("close",0))
            h = float(last.get("high",0))
            l = float(last.get("low",0))
        else:
            o = float(last[1]); c = float(last[2]); h = float(last[3]); l = float(last[4])
        total = h-l
        if total == 0:
            return
        body = abs(c-o)
        low = min(o,c)-l
        up = h-max(o,c)
        k = pair+label
        if k in sent and time.time()-sent[k] < 60:
            return
        if low/total >= 0.25:
            send_tg("💎 *"+label+" "+pair+" BUY* PINBAR "+str(int(low/total*100))+"% Candele:"+str(len(candles)))
            sent[k] = time.time()
            return
        if up/total >= 0.25:
            send_tg("💎 *"+label+" "+pair+" SELL* PINBAR "+str(int(up/total*100))+"% Candele:"+str(len(candles)))
            sent[k] = time.time()
            return
    except Exception as e:
        send_tg("Errore "+str(e)[:50])

def bot_loop():
    send_tg("✅ FIX LIVE - 25% Pinbar - Debug 0 candele")
    while True:
        try:
            for period,label in [(300,"M5"),(900,"M15")]:
                for p in PAIRS:
                    process(p, period, label)
                    time.sleep(1)
        except:
            time.sleep(5)
        time.sleep(5)

def run_flask():
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot_loop()
