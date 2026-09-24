import os, time, requests, threading, pandas as pd
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "BOT V9 REAL+OTC PINBAR 100% ONLINE"

TOKEN=os.environ.get("TELEGRAM_TOKEN")
CHAT=os.environ.get("TELEGRAM_CHAT_ID")
EMAIL=os.environ.get("POCKET_EMAIL")
PASSWORD=os.environ.get("POCKET_PASSWORD")

# COPPIE REALI + OTC - TUTTE QUELLE DI POCKET
NAMES=[
"EURUSD","GBPUSD","USDJPY","EURJPY","GBPJPY","AUDJPY","USDCHF","AUDUSD","NZDUSD","EURGBP","USDCAD",
"EURUSD_otc","GBPUSD_otc","USDJPY_otc","EURJPY_otc","GBPJPY_otc","AUDJPY_otc","USDCHF_otc","AUDUSD_otc","NZDUSD_otc","EURGBP_otc","USDCAD_otc","GBPCHF_otc","AUDCAD_otc","AUDCHF_otc","AUDNZD_otc","CADJPY_otc","CHFJPY_otc","EURAUD_otc","EURCAD_otc","EURNZD_otc","GBPAUD_otc","NZDJPY_otc","EURCHF_otc","GBPCAD_otc"
]

last={}
def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=15)
    except: pass

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0); l=-d.where(d<0,0)
    return 100-(100/(1+g.ewm(alpha=1/p).mean()/l.ewm(alpha=1/p).mean()))

def check(df):
    if len(df)<210: return None
    df["EMA200"]=df["Close"].ewm(span=200).mean()
    df["RSI"]=rsi(df["Close"])
    df["MA20"]=df["Close"].rolling(20).mean()
    df["STD"]=df["Close"].rolling(20).std()
    df["LOW"]=df["MA20"]-2*df["STD"]
    df["UP"]=df["MA20"]+2*df["STD"]
    c=float(df["Close"].iloc[-1]); o=float(df["Open"].iloc[-1]); h=float(df["High"].iloc[-1]); l=float(df["Low"].iloc[-1])
    ema=float(df["EMA200"].iloc[-1]); r=float(df["RSI"].iloc[-1]); rp=float(df["RSI"].iloc[-2]); low=float(df["LOW"].iloc[-1]); up=float(df["UP"].iloc[-1])
    body=abs(c-o); total=h-l
    if body==0 or total==0: return None
    up_w=h-max(c,o); lw=min(c,o)-l
    bull = lw/body>=2.2 and lw/body<=6.0 and body<=total*0.35 and c>o and lw>=total*0.60 and (l<=low*1.01 or l<=ema*1.001) and 22<r<38 and c>ema*0.999 and r>rp and r-rp>=0.5
    bear = up_w/body>=2.2 and up_w/body<=6.0 and body<=total*0.35 and c<o and up_w>=total*0.60 and (h>=up*0.99 or h>=ema*0.999) and 58<r<85 and c<ema*1.001 and r<rp and rp-r>=0.5
    if bull: return "BUY",lw/body,rp,r
    if bear: return "SELL",up_w/body,rp,r
    return None

def bot():
    send("🔄 Provo login Pocket REAL+OTC...")
    try:
        from pocketoptionapi.stable_api import PocketOption
        api=PocketOption(EMAIL,PASSWORD)
        if not api.connect():
            send("❌ Login fallito")
            return
        send(f"✅ *LOGIN OK!*\nLeggo {len(NAMES)} coppie REALI + OTC vere!")
        while True:
            for sym in NAMES:
                try:
                    if sym in last and time.time()-last[sym]<900: continue
                    candles=api.get_candles(sym, 60, 250)
                    if not candles or len(candles)<210: continue
                    df=pd.DataFrame(candles, columns=["Time","Open","Close","High","Low"])
                    res=check(df)
                    if res:
                        side,ratio,rp,r=res
                        last[sym]=time.time()
                        icon="🔵" if side=="BUY" else "🔴"
                        tipo="OTC" if "otc" in sym else "REALE"
                        send(f"📌{icon} *{sym.upper()} {tipo} PINBAR {side}*\nCandele vere Pocket ✅\nForma {ratio:.1f}x RSI {rp:.0f}->{r:.0f}\n5m {side}!")
                except: continue
            time.sleep(5)
    except Exception as e:
        send(f"❌ Errore: {e}")

threading.Thread(target=bot,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
