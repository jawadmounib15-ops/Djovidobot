import os, time, requests, threading, yfinance as yf, pandas as pd
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "BOT PINBAR TUTTI OTC+REALI LIVE"

TOKEN=os.environ.get("TELEGRAM_TOKEN")
CHAT=os.environ.get("TELEGRAM_CHAT_ID")

# Dati reali presi da Yahoo, ma segnalati come OTC
BASE_PAIRS={
"EURUSD":"EURUSD=X","GBPUSD":"GBPUSD=X","USDJPY":"USDJPY=X","EURJPY":"EURJPY=X",
"GBPJPY":"GBPJPY=X","AUDJPY":"AUDJPY=X","USDCHF":"USDCHF=X","AUDUSD":"AUDUSD=X",
"NZDUSD":"NZDUSD=X","EURGBP":"EURGBP=X","USDCAD":"USDCAD=X","GBPCHF":"GBPCHF=X",
"AUDCAD":"AUDCAD=X","AUDCHF":"AUDCHF=X","AUDNZD":"AUDNZD=X","CADCHF":"CADCHF=X",
"CADJPY":"CADJPY=X","CHFJPY":"CHFJPY=X","EURAUD":"EURAUD=X","EURCAD":"EURCAD=X",
"EURCHF":"EURCHF=X","EURNZD":"EURNZD=X","GBPAUD":"GBPAUD=X","GBPCAD":"GBPCAD=X",
"NZDJPY":"NZDJPY=X","NZDCAD":"NZDCAD=X"
}

# Lista finale: 12 REALI + 26 OTC Pocket Option
NAMES=["EURUSD","GBPUSD","USDJPY","EURJPY","GBPJPY","AUDJPY","USDCHF","AUDUSD","NZDUSD","EURGBP","USDCAD","GBPCHF",
"EURUSD-OTC","GBPUSD-OTC","USDJPY-OTC","EURJPY-OTC","GBPJPY-OTC","AUDJPY-OTC","USDCHF-OTC","AUDUSD-OTC","NZDUSD-OTC","EURGBP-OTC","USDCAD-OTC","GBPCHF-OTC",
"AUDCAD-OTC","AUDCHF-OTC","AUDNZD-OTC","CADJPY-OTC","CHFJPY-OTC","EURAUD-OTC","EURCAD-OTC","EURNZD-OTC","GBPAUD-OTC","NZDJPY-OTC","EURCHF-OTC","GBPCAD-OTC"]

PAIRS=["EURUSD=X","GBPUSD=X","USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X","USDCHF=X","AUDUSD=X","NZDUSD=X","EURGBP=X","USDCAD=X","GBPCHF=X",
"EURUSD=X","GBPUSD=X","USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X","USDCHF=X","AUDUSD=X","NZDUSD=X","EURGBP=X","USDCAD=X","GBPCHF=X",
"AUDCAD=X","AUDCHF=X","AUDNZD=X","CADJPY=X","CHFJPY=X","EURAUD=X","EURCAD=X","EURNZD=X","GBPAUD=X","NZDJPY=X","EURCHF=X","GBPCAD=X"]

last_signal={}

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0); l=-d.where(d<0,0)
    return 100-(100/(1+g.ewm(alpha=1/p).mean()/l.ewm(alpha=1/p).mean()))

def bot():
    send("📌💪 *BOT PINBAR TUTTI OTC POCKET LIVE*\n36 coppie - 12 REALI + 24 OTC - Regole forti")
    while True:
        try:
            for i,pair in enumerate(PAIRS):
                try:
                    df=yf.download(pair,period="2d",interval="1m",progress=False)
                    if len(df)<210: continue
                    if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)

                    df["EMA200"]=df["Close"].ewm(span=200).mean()
                    df["RSI"]=rsi(df["Close"])
                    df["MA20"]=df["Close"].rolling(20).mean()
                    df["STD"]=df["Close"].rolling(20).std()
                    df["LOW"]=df["MA20"]-2.0*df["STD"]
                    df["UP"]=df["MA20"]+2.0*df["STD"]

                    c=df["Close"].iloc[-1]; o=df["Open"].iloc[-1]; h=df["High"].iloc[-1]; l=df["Low"].iloc[-1]
                    ema200=df["EMA200"].iloc[-1]; r=df["RSI"].iloc[-1]; r_prev=df["RSI"].iloc[-2]
                    low=df["LOW"].iloc[-1]; up=df["UP"].iloc[-1]; nome=NAMES[i]

                    if nome in last_signal and time.time()-last_signal[nome] < 900: continue

                    body=abs(c-o); upper_wick=h-max(c,o); lower_wick=min(c,o)-l; total_range=h-l
                    if total_range==0 or body==0: continue
                    ratio_low=lower_wick/body; ratio_up=upper_wick/body

                    bull_forma=ratio_low>=2.2 and ratio_low<=6.0 and body<=total_range*0.35 and c>o
                    bear_forma=ratio_up>=2.2 and ratio_up<=6.0 and body<=total_range*0.35 and c<o

                    bull_loc=lower_wick>=total_range*0.60 and (l<=low*1.01 or l<=ema200*1.001) and r<38 and r>22 and c>ema200*0.999
                    bear_loc=upper_wick>=total_range*0.60 and (h>=up*0.99 or h>=ema200*0.999) and r>68 and r<85 and c<ema200*1.001

                    bull_close=r>r_prev and (r-r_prev)>=0.5
                    bear_close=r<r_prev and (r_prev-r)>=0.5

                    if bull_forma and bull_loc and bull_close:
                        last_signal[nome]=time.time()
                        send(f"📌🔵 *{nome} PINBAR FORTE BUY*\nForma {ratio_low:.1f}x ✅ Coda 60% ✅\nEMA200 + RSI {r:.0f}->{r_prev:.0f} ✅\n5m BUY!")

                    if bear_forma and bear_loc and bear_close:
                        last_signal[nome]=time.time()
                        send(f"📌🔴 *{nome} PINBAR FORTE SELL*\nForma {ratio_up:.1f}x ✅ Coda 60% ✅\nEMA200 + RSI {r:.0f}->{r_prev:.0f} ✅\n5m SELL!")

                except: continue
            time.sleep(60)
        except: time.sleep(30)

threading.Thread(target=bot,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
