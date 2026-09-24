import os, time, requests, threading, pandas as pd, yfinance as yf
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "BOT V8 AUTO-LOGIN POCKET ONLINE"

TOKEN=os.environ.get("TELEGRAM_TOKEN")
CHAT=os.environ.get("TELEGRAM_CHAT_ID")
EMAIL=os.environ.get("POCKET_EMAIL")
PASSWORD=os.environ.get("POCKET_PASSWORD")

NAMES=["EURUSD-OTC","GBPUSD-OTC","USDJPY-OTC","EURJPY-OTC","GBPJPY-OTC","AUDJPY-OTC","USDCHF-OTC","AUDUSD-OTC","NZDUSD-OTC","EURGBP-OTC","USDCAD-OTC","GBPCHF-OTC","AUDCAD-OTC","AUDCHF-OTC","AUDNZD-OTC","CADJPY-OTC","CHFJPY-OTC","EURAUD-OTC","EURCAD-OTC","EURNZD-OTC","GBPAUD-OTC","NZDJPY-OTC","EURCHF-OTC","GBPCAD-OTC"]
PAIRS=["EURUSD=X","GBPUSD=X","USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X","USDCHF=X","AUDUSD=X","NZDUSD=X","EURGBP=X","USDCAD=X","GBPCHF=X","AUDCAD=X","AUDCHF=X","AUDNZD=X","CADJPY=X","CHFJPY=X","EURAUD=X","EURCAD=X","EURNZD=X","GBPAUD=X","NZDJPY=X","EURCHF=X","GBPCAD=X"]

last={}
def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0); l=-d.where(d<0,0)
    return 100-(100/(1+g.ewm(alpha=1/p).mean()/l.ewm(alpha=1/p).mean()))

def check(c,o,h,l,r,rp,ema,low,up):
    body=abs(c-o); total=h-l
    if body==0 or total==0: return None
    up_w=h-max(c,o); lw=min(c,o)-l
    bull = lw/body>=2.2 and lw/body<=6.0 and body<=total*0.35 and c>o and lw>=total*0.60 and (l<=low*1.01 or l<=ema*1.001) and 22<r<38 and c>ema*0.999 and r>rp and r-rp>=0.5
    bear = up_w/body>=2.2 and up_w/body<=6.0 and body<=total*0.35 and c<o and up_w>=total*0.60 and (h>=up*0.99 or h>=ema*0.999) and 58<r<85 and c<ema*1.001 and r<rp and rp-r>=0.5
    if bull: return "BUY",lw/body
    if bear: return "SELL",up_w/body
    return None

def get_ssid():
    try:
        s=requests.Session()
        s.post("https://pocketoption.com/en/cabinet/", data={"email":EMAIL,"password":PASSWORD}, timeout=15)
        for ck in s.cookies:
            if "ssid" in ck.name.lower(): return ck.value
    except: pass
    return None

def bot():
    ssid=get_ssid()
    if ssid: send(f"✅ Login Pocket OK\nSSID preso automatico!")
    else: send("⚠️ Login Pocket fallito, uso Yahoo OTC per ora")

    while True:
        for i,p in enumerate(PAIRS):
            try:
                nome=NAMES[i]
                if nome in last and time.time()-last[nome]<900: continue
                df=yf.download(p,period="2d",interval="1m",progress=False)
                if len(df)<210: continue
                if hasattr(df.columns,'get_level_values'):
                    try: df.columns=df.columns.get_level_values(0)
                    except: pass
                df["EMA200"]=df["Close"].ewm(span=200).mean()
                df["RSI"]=rsi(df["Close"])
                df["MA20"]=df["Close"].rolling(20).mean()
                df["STD"]=df["Close"].rolling(20).std()
                df["LOW"]=df["MA20"]-2*df["STD"]
                df["UP"]=df["MA20"]+2*df["STD"]
                c=float(df["Close"].iloc[-1]); o=float(df["Open"].iloc[-1]); h=float(df["High"].iloc[-1]); l=float(df["Low"].iloc[-1])
                ema=float(df["EMA200"].iloc[-1]); r=float(df["RSI"].iloc[-1]); rp=float(df["RSI"].iloc[-2]); low=float(df["LOW"].iloc[-1]); up=float(df["UP"].iloc[-1])
                res=check(c,o,h,l,r,rp,ema,low,up)
                if res:
                    side,ratio=res
                    last[nome]=time.time()
                    icon="🔵" if side=="BUY" else "🔴"
                    send(f"📌{icon} *{nome} PINBAR {side}*\nForma {ratio:.1f}x ✅\nRSI {rp:.0f}->{r:.0f} ✅\n5m {side}!")
            except: continue
        time.sleep(60)

threading.Thread(target=bot,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
