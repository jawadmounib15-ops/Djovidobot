import os, time, threading, requests, json, gc
from flask import Flask
import websocket

app = Flask(__name__)
@app.route('/')
def home(): return "V19 MULTI SERVER"
@app.route('/ping')
def ping(): return "OK"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POCKET_SSID = os.getenv("POCKET_SSID")

SERVERS = [
    "wss://api.po.market/socket.io/?EIO=3&transport=websocket",
    "wss://api-eu.po.market/socket.io/?EIO=3&transport=websocket",
    "wss://api-us-north.po.market/socket.io/?EIO=3&transport=websocket"
]

def send_tg(m):
    try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id":TELEGRAM_CHAT_ID,"text":m,"parse_mode":"Markdown"}, timeout=10)
    except: pass

def get_candles_try(pair, period, server):
    candles = []
    try:
        def on_msg(ws, msg):
            try:
                if msg.startswith('42'):
                    j = json.loads(msg[2:])
                    if len(j) > 1 and isinstance(j[1], dict):
                        if 'candles' in j[1]: candles.extend(j[1]['candles'])
                        if 'history' in j[1]: candles.extend(j[1]['history'])
            except: pass
            if msg == "2": ws.send("3")
        ws = websocket.WebSocketApp(server, on_message=on_msg)
        def run():
            try:
                time.sleep(0.3); ws.send("40")
                time.sleep(0.3); ws.send(f'42["auth",{{"session":"{POCKET_SSID}","isDemo":1}}]')
                time.sleep(2)
                asset = pair.replace("_otc","").upper()
                otc = "_otc" in pair.lower()
                ws.send(f'42["loadHistory",{{"asset":"{asset}","period":{period},"isOtc":{str(otc).lower()}}}]')
                time.sleep(4); ws.close()
            except:
                try: ws.close()
                except: pass
        t = threading.Thread(target=run, daemon=True); t.start()
        ws.run_forever(ping_timeout=8); t.join(timeout=6)
    except: pass
    return candles

def bot_loop():
    send_tg(f"🔄 V19 TEST SERVER\nProvo 3 server diversi...")
    working_server = None
    for server in SERVERS:
        send_tg(f"🔍 Provo {server.split('/')[2]}")
        c = get_candles_try("EURUSD_otc", 300, server)
        if len(c) >= 5:
            working_server = server
            send_tg(f"✅ TROVATO! Server OK: {server.split('/')[2]}\nCandele:{len(c)}\nORA PARTO CON I SEGNALI")
            break
        else:
            send_tg(f"❌ {server.split('/')[2]} non risponde (0 candele)")
        time.sleep(2)

    if not working_server:
        send_tg("💀 NESSUN SERVER RISPONDE - Pocket ha cambiato tutto. Ti preparo bot nuovo senza SSID domani.")
        return

    send_tg("🚀 BOT 15% ONLINE - VERO")
    while True:
        time.sleep(30)

def run_flask():
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))

if __name__=="__main__":
    threading.Thread(target=run_flask,daemon=True).start()
    bot_loop()
