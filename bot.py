import requests, os, time
from flask import Flask
from threading import Thread

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
app = Flask(__name__)

@app.route('/')
def home():
    return "BOT LIVE", 200

def send(t):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": t}, timeout=10)
    except Exception as e:
        print(e)

def run():
    print("BOT AVVIATO")
    send("✅ BOT AVVIATO - test ok")
    while True:
        time.sleep(60)

Thread(target=run, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
