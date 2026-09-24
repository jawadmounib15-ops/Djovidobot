import os, time, json, requests, threading, pandas as pd, websocket
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "BOT V13 FINALE 26 REALI+OTC SSID ONLINE"

TOKEN=os.environ.get("TELEGRAM_TOKEN")
CHAT=os.environ.get("TELEGRAM_CHAT_ID")
SSID=os.environ.get("POCKET_SSID")

SYMBOLS=["EURUSD","GBPUSD","USDJPY","EURJPY","GBPJPY","AUDJPY","USDCHF","AUDUSD","NZDUSD","EURGBP","USDCAD","EURCHF","AUDCAD","NZDJPY","EURUSD_otc","GBPUSD_otc","USDJPY_otc","EURJPY_otc","GBPJPY_otc","AUDJPY_otc","AUDUSD_otc","EURGBP_otc","USDCHF_otc","EURCHF_otc","AUDCAD_otc","GBPCHF_otc"]

last={}; ssid_alert_sent=False

def send(m):
 try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=15)
 except: pass

def rsi(s,p=14):
 d=s.diff(); g=d.where(d>0,0); l=-d.where(d<0,0)
 rs=g.ewm(alpha=1/p).mean()/l.ewm(alpha=1/p).mean()
 return 100-(100/(1+rs))

def check_pinbar(df):
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
 # FIX BUY/SELL GIUSTO
 bull=lw/body>=2.2 and lw/body<=6.0 and body<=total*0.35 and c>o and lw>=total*0.60 and (l<=low*1.01 or l<=ema*1.001) and 22<r<38 and r>rp
 bear=up_w/body>=2.2 and up_w/body<=6.0 and body<=total*0.35 and c<o and up_w>=total*0.60 and (h>=up*0.99 or h>=ema*0.999) and 58<r<85 and r<rp
 if bull: return "BUY",lw/body,rp,r
 if bear: return "SELL",up_w/body,rp,r
 return None

def get_candles(symbol):
 global ssid_alert_sent
 try:
  ws=websocket.create_connection("wss://api-eu.po.market/socket.io/?EIO=3&transport=websocket",timeout=12)
  ws.send(SSID)
  time.sleep(1.2)
  ws.send(f'42["changeSymbol",{{"asset":"{symbol}","period":60}}]')
  start=time.time(); cnd=[]
  while time.time()-start<4.5:
   try:
    msg=ws.recv()
    if msg=='2': ws.send('3'); continue
    if 'auth' in msg and 'session' not in msg and 'isDemo' not in msg:
        if not ssid_alert_sent:
            send("🚨 *SSID SCADUTO PA!*\nCopia nuovo SSID su Render!")
            ssid_alert_sent=True
        ws.close(); return None
    if '"history"' in msg or '"candles"' in msg or '"open"' in msg:
        try:
            j=json.loads(msg[2:]); d=j[1] if len(j)>1 else j
            lst=d if isinstance(d,list) else d.get('history',[]) if isinstance(d,dict) else []
            for x in lst:
                if isinstance(x,dict) and 'open' in x: cnd.append(x)
        except: pass
   except: break
  ws.close()
  ssid_alert_sent=False
  if len(cnd)>=210:
   df=pd.DataFrame(cnd[-250:])
   df=df.rename(columns={"open":"Open","close":"Close","high":"High","low":"Low"})
   return df[["Open","Close","High","Low"]].astype(float)
 except Exception as e:
  print(f"err {symbol} {e}")
  return None

def bot_loop():
 if not SSID:
  send("❌ Metti POCKET_SSID su Render!")
  return
 send("✅ *BOT V13 FINALE ONLINE*\n26 coppie REALI+OTC\nCandele VERE Pocket ✅\nBUY/SELL FIX OK\nAvviso scadenza ON")
 while True:
  for sym in SYMBOLS:
   try:
    if sym in last and time.time()-last[sym]<900: continue
    df=get_candles(sym)
    if df is None or len(df)<210: continue
    res=check_pinbar(df)
    if res:
     side,ratio,rp,r=res
     last[sym]=time.time()
     tipo="OTC" if "otc" in sym else "REALE"
     icon="🔵" if side=="BUY" else "🔴"
     send(f"📌{icon} *{sym.upper()} {tipo} {side}*\nCandele VERE Pocket ✅\nPinbar {ratio:.1f}x RSI {rp:.0f}->{r:.0f}\nEntra 5m {side}!")
   except Exception as e:
    print(e); continue
  time.sleep(4)

threading.Thread(target=bot_loop,daemon=True).start()

if __name__=="__main__":
 app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
