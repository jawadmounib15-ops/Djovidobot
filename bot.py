import os
import requests
import time
from flask import Flask
from threading import Thread

app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")

def send(m):
    try:
        if TOKEN and CHAT:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT, "text": m}, timeout=10)
    except Exception as e:
        print(e)

def loop():
    send("BOT PARTITO - TEST OK")
    print("Loop partito")
    while True:
        time.sleep(60)
        print("vivo")

@app.route("/")
def home():
    return "OK"

Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
