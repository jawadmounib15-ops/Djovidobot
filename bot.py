import os, time, requests, yfinance as yf, threading
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V111 OTC 8% ULTRA LARGO WEEKEND ONLINE"
@app.route('/ping')
def ping(): return "OK"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")

OTC_LIST = ["EURUSD_otc","GBPUSD_otc","USDJPY_otc","AUDUSD_otc","USDCHF_otc","USDCAD_otc","EURJPY_otc","GBPJPY_otc","EURGBP_otc","AUDJPY_otc","CADJPY_otc","CHFJPY_otc","EURCHF_otc","GBPCHF_otc","AUDCHF_otc","EURAUD_otc","GBPAUD_otc","EURCAD_otc","AUDCAD_otc","NZDCAD_otc"]
MAP = {"EURUSD_otc":"EURUSD=X","GBPUSD_otc":"GBPUSD=X","USDJPY_otc":"USDJPY=X","AUDUSD_otc":"AUDUSD=X","USDCHF_otc":"USDCHF=X","USDCAD_otc":"USDCAD=X","EURJPY_otc":"EURJPY=X","GBPJPY_otc":"GBPJPY=X","EURGBP_otc":"EURGBP=X","AUDJPY_otc":"AUDJPY=X","CADJPY_otc":"CADJPY=X","CHFJPY_otc":"CHFJPY=X","EURCHF_otc":"EURCHF=X","GBPCHF_otc":"GBPCHF=X","AUDCHF_otc":"AUDCHF=X","EURAUD_otc":"EURAUD=X","GBPAUD_otc":"GBPAUD=X","EURCAD_otc":"EURCAD=X","AUDCAD_otc":"AUDCAD=X","NZDCAD_otc":"NZDCAD=X"}

COOLDOWN = {}

def send(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
        print(m, flush=True)
    except: pass

def pinbar(o,h,l,c):
    rng=h-l
    if rng==0: return 0,0
    return ((min(o,c)-l)/rng)*100, ((h-max(o,c))/rng)*100

def bot():
    send("✅ *V111 OTC 8% ULTRA LARGO WEEKEND ONLINE*\n• Solo OTC\n• Cerca nelle ultime 3 candele\n• M1 8% OR M5 8% = SEGNALE")

    while True:
        try:
            for pair_otc in OTC_LIST:
                if pair_otc in COOLDOWN and time.time() - COOLDOWN[pair_otc] < 40:
                    continue
                yahoo = MAP[pair_otc]
                display = pair_otc.replace('_otc','-OTC')
                try:
                    time.sleep(1)

                    df1 = yf.download(yahoo, period="2d", interval="1m", progress=False, auto_adjust=True)
                    if len(df1)<10: continue
                    best_b1=best_s1=0
                    for i in range(2,5): # ultime 3 candele per weekend
                        o,h,l,c = float(df1["Open"].iloc[-i]), float(df1["High"].iloc[-i]), float(df1["Low"].iloc[-i]), float(df1["Close"].iloc[-i])
                        b,s = pinbar(o,h,l,c)
                        best_b1=max(best_b1,b); best_s1=max(best_s1,s)

                    df5 = yf.download(yahoo, period="5d", interval="5m", progress=False, auto_adjust=True)
                    if len(df5)<10: continue
                    best_b5=best_s5=0
                    for i in range(2,5):
                        o,h,l,c = float(df5["Open"].iloc[-i]), float(df5["High"].iloc[-i]), float(df5["Low"].iloc[-i]), float(df5["Close"].iloc[-i])
                        b,s = pinbar(o,h,l,c)
                        best_b5=max(best_b5,b); best_s5=max(best_s5,s)

                    print(f"{display} M1 B{best_b1:.0f} S{best_s1:.0f} | M5 B{best_b5:.0f} S{best_s5:.0f}", flush=True)

                    sig=None; p1=p5=0
                    # ULTRA LARGO: basta M1 8% OR M5 8%
                    if best_b1>=8 or best_b5>=8:
                        if best_b1>=best_s1 and best_b5>=best_s5:
                            sig="BUY"; p1=best_b1; p5=best_b5
                    elif best_s1>=8 or best_s5>=8:
                        if best_s1>=best_b1 and best_s5>=best_b5:
                            sig="SELL"; p1=best_s1; p5=best_s5

                    if sig:
                        COOLDOWN[pair_otc]=time.time()
                        send(f"💎 *{sig} {display} 8% OTC*\nM1:{p1:.0f}% M5:{p5:.0f}%\n👉 *POCKET: {sig}*")

                except Exception as e:
                    print(f"ERR {pair_otc} {e}", flush=True)
                    continue
            time.sleep(5)
        except Exception as e:
            print(f"LOOP ERR {e}", flush=True)
            time.sleep(10)

threading.Thread(target=bot, daemon=True).start()
app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
