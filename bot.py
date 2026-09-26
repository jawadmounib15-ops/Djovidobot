import os, time, threading, requests
from flask import Flask
from datetime import datetime

app = Flask(__name__)
@app.route('/')
def home(): return "V23 FINAL M1+M5 EXPIRY"
@app.route('/ping')
def ping(): return "OK"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POCKET_SSID = os.getenv("POCKET_SSID")

PAIRS = ["EURUSD_otc","GBPUSD_otc","AUDCAD_otc","EURJPY_otc","GBPJPY_otc","EURGBP_otc"]
TIMEFRAMES = {"M1":60, "M5":300} # controlla sia M1 che M5 come la tua foto
sent = {}

def send_tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id":TELEGRAM_CHAT_ID,"text":m,"parse_mode":"Markdown"}, timeout=10)
    except: pass
    print(m)

def get_candles(pair, period):
    # Prova Pocket API web
    try:
        asset = pair.replace("_otc","").upper()
        headers = {"User-Agent":"Mozilla/5.0","Origin":"https://pocketoption.com","Referer":"https://pocketoption.com/","Cookie":f"session={POCKET_SSID}"}
        r = requests.get(f"https://pocketoption.com/api/candles?asset={asset}&period={period}&count=50", headers=headers, timeout=10)
        if r.status_code==200 and isinstance(r.json(), list) and len(r.json())>10:
            out=[]
            for c in r.json():
                if isinstance(c,dict): out.append(c)
                elif isinstance(c,list): out.append({"open":float(c[1]),"close":float(c[2]),"high":float(c[3]),"low":float(c[4])})
            if len(out)>10: return out
    except: pass
    # Fallback Binance
    try:
        mmap={"EURUSD_otc":"EURUSDT","GBPUSD_otc":"GBPUSDT","AUDCAD_otc":"AUDUSDT","EURJPY_otc":"EURJPY","GBPJPY_otc":"GBPJPY","EURGBP_otc":"EURGBP"}
        sym=mmap.get(pair,"EURUSDT")
        interval="1m" if period==60 else "5m"
        r=requests.get(f"https://api.binance.com/api/v3/klines?symbol={sym}&interval={interval}&limit=50",timeout=10).json()
        return [{"open":float(x[1]),"high":float(x[2]),"low":float(x[3]),"close":float(x[4])} for x in r]
    except: return []

def check_pair_tf(pair, tf_name, period):
    candles = get_candles(pair, period)
    if len(candles)<20: return
    last = candles[-2]
    o=float(last.get('open',0)); c=float(last.get('close',0)); h=float(last.get('high',0)); l=float(last.get('low',0))
    total=h-l
    if total==0: return
    body=abs(c-o); upper=h-max(o,c); lower=min(o,c)-l

    signal=None
    perc=0
    if lower/total>=0.10 and body/total<=0.80:
        signal="BUY"; perc=lower/total*100
        expiry="5 MIN" if tf_name=="M1" else "5-10 MIN"
    elif upper/total>=0.10 and body/total<=0.80:
        signal="SELL"; perc=upper/total*100
        expiry="5 MIN" if tf_name=="M1" else "5-10 MIN"
    else: return

    key=f"{pair}_{tf_name}_{signal}"
    if key in sent and time.time()-sent[key]<90: return # 90 sec anti-spam

    emoji="🟢" if signal=="BUY" else "🔴"
    action="ACQUISTA" if signal=="BUY" else "VENDI"

    msg=f"💎 *{tf_name} {emoji} {pair} {signal}*\n⚡ TURBO {perc:.0f}% | Body {body/total*100:.0f}%\n🎯 *{action} -> {expiry}*\n⏰ {datetime.now().strftime('%H:%M:%S')} [10% LARGO]"
    send_tg(msg)
    sent[key]=time.time()

def bot_loop():
    send_tg("✅ *V23 FINAL ONLINE*\n🔥 M1+M5 ATTIVO\n🎯 Ti dice scadenza 5 / 10 MIN\n💥 Come la tua foto AUDCAD")
    while True:
        for pair in PAIRS:
            for tf_name, period in TIMEFRAMES.items():
                try: check_pair_tf(pair, tf_name, period)
                except Exception as e: print(e)
                time.sleep(1)
        time.sleep(10)

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))

if __name__=="__main__":
    threading.Thread(target=run_flask,daemon=True).start()
    bot_loop()
