import os, time, threading, requests, json
from flask import Flask
import websocket

app = Flask(__name__)
@app.route('/')
def home(): return "V18 DEBUG"
@app.route('/ping')
def ping(): return "OK"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POCKET_SSID = os.getenv("POCKET_SSID")
PAIRS = ["EURUSD_otc","BTCUSD_otc"]
sent = {}

def send_tg(m):
    try:
        print(m)
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id":TELEGRAM_CHAT_ID,"text":m,"parse_mode":"Markdown"}, timeout=10)
    except Exception as e:
        print(e)

def get_candles(pair, period):
    candles = []
    logs = []
    try:
        def on_msg(ws, msg):
            logs.append(msg[:150])
            try:
                if msg.startswith('42'):
                    j = json.loads(msg[2:])
                    if isinstance(j, list) and len(j) > 1:
                        data = j[1]
                        if isinstance(data, dict):
                            if 'candles' in data: candles.extend(data['candles'])
                            if 'history' in data: candles.extend(data['history'])
            except: pass
            if msg == "2": ws.send("3")

        ws = websocket.WebSocketApp("wss://api-eu.po.market/socket.io/?EIO=3&transport=websocket", on_message=on_msg, on_error=lambda w,e: logs.append(str(e)))

        def run():
            try:
                time.sleep(0.5)
                ws.send("40")
                time.sleep(0.5)
                ws.send(f'42["auth",{{"session":"{POCKET_SSID}","isDemo":1}}]')
                time.sleep(2)
                asset = pair.replace("_otc","").upper()
                otc = "_otc" in pair.lower()
                ws.send(f'42["loadHistory",{{"asset":"{asset}","period":{period},"isOtc":{str(otc).lower()}}}]')
                time.sleep(5)
                ws.close()
            except Exception as e:
                logs.append(f"RUN ERR {e}")
                try: ws.close()
                except: pass

        t = threading.Thread(target=run, daemon=True)
        t.start()
        ws.run_forever(ping_timeout=10)
        t.join(timeout=7)
    except Exception as e:
        logs.append(f"OUTER {e}")

    # Manda debug su Telegram solo la prima volta
    if len(candles) < 3 and "debug_sent" not in sent:
        send_tg(f"🛠 DEBUG {pair} candele:{len(candles)}\nLogs:\n" + "\n".join(logs[-5:])[:800])
        sent["debug_sent"] = True
    if len(candles) >= 3:
        if "ok_sent" not in sent:
            send_tg(f"✅ CONNESSO! Prese {len(candles)} candele su {pair}\nSSID OK!")
            sent["ok_sent"] = True
        return candles
    return []

def bot_loop():
    send_tg(f"🔄 V18 DEBUG AVVIATO\nSSID:{POCKET_SSID[:8]}... len:{len(POCKET_SSID) if POCKET_SSID else 0}")
    while True:
        for p in PAIRS:
            c = get_candles(p, 300)
            if c:
                send_tg(f"💎 SEGNALE TEST {p} - {len(c)} candele OK")
            time.sleep(3)
        time.sleep(10)

def run_flask():
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))

if __name__=="__main__":
    threading.Thread(target=run_flask,daemon=True).start()
    bot_loop()
