import time
import requests
from datetime import datetime, timedelta

# === INCOLLA QUI I TUOI DATI ===
TELEGRAM_TOKEN = "TELEGRAM_TOKEN"
TELEGRAM_CHAT_ID = "TELEGRAM_CHAT_ID"
# ===============================

WIN = 0
LOSS = 0
trades = []
ultimo_id = 0

def send(text, buttons=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    if buttons:
        data["reply_markup"] = {"inline_keyboard": buttons}
    requests.post(url, json=data)

def nuovo_segnale(pair, direz):
    scadenza = datetime.now() + timedelta(minutes=16)
    trades.append({"pair": pair, "dir": direz, "scad": scadenza})
    send(f"🔔 *V64 {direz} {pair}*\nAperto {datetime.now().strftime('%H:%M')} -> check {scadenza.strftime('%H:%M')}")
    print(f"SEGNALE {direz} {pair}")

def start():
    global WIN, LOSS, ultimo_id
    print("🚀 V64 TELEGRAM ATTIVO")
    send("🚀 *V64 MOLTO LARGO ATTIVO*")

    while True:
        for t in trades[:]:
            if datetime.now() >= t["scad"]:
                btns = [[{"text": "✅ WIN", "callback_data": f"WIN|{t['pair']}|{t['dir']}"}, {"text": "❌ LOSS", "callback_data": f"LOSS|{t['pair']}|{t['dir']}"}]]
                send(f"⏰ *Scaduto {t['dir']} {t['pair']}* - Com'è andato?", btns)
                trades.remove(t)
        
        try:
            r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={ultimo_id+1}").json()
            for u in r.get("result", []):
                ultimo_id = u["update_id"]
                if "callback_query" in u:
                    d = u["callback_query"]["data"]
                    esito, pair, direz = d.split("|")
                    if esito == "WIN":
                        WIN += 1
                    else:
                        LOSS += 1
                    wr = WIN/(WIN+LOSS)*100 if (WIN+LOSS)>0 else 0
                    send(f"{'✅' if esito=='WIN' else '❌'} *{esito} {direz} {pair}*\n\n📊 WIN: {WIN} | LOSS: {LOSS}\nWinrate: {wr:.1f}%")
        except:
            pass
        time.sleep(3)

start()
