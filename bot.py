import os, time, requests, yfinance as yf, pandas as pd
from threading import Thread
from flask import Flask
from datetime import datetime, timedelta

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
VERSION = "V60 7 LAVORI TRACKER"
SYMBOLS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURGBP=X","EURJPY=X","GBPJPY=X","NZDUSD=X"]

app = Flask(__name__)
@app.route("/")
def home(): return f"{VERSION} LIVE - {datetime.now()}"

def send_tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": m, "parse_mode": "Markdown"}, timeout=15)
    except: pass

def rsi(c,p=14):
    d=c.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

last_block={}
stats={"L1":[0,0],"L2":[0,0],"L3":[0,0],"L4":[0,0],"L5":[0,0],"L6":[0,0],"L7":[0,0]}
pending=[]

def check_results():
    global pending
    now=datetime.now()
    new_pending=[]
    for p in pending:
        if (now-p['time']).total_seconds() >= 900:
            try:
                df=yf.download(p['sym'], period="1d", interval="1m", progress=False, auto_adjust=True)
                if len(df)<2:
                    new_pending.append(p); continue
                if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
                curr=float(df['Close'].iloc[-1])
                entry=p['price']
                is_buy="BUY" in p['msg']
                win=(curr>entry) if is_buy else (curr<entry)
                job=p['job']
                stats[job][1]+=1
                if win: stats[job][0]+=1
                res="✅ WIN" if win else "❌ LOSS"
                winrate=stats[job][0]/stats[job][1]*100 if stats[job][1]>0 else 0
                send_tg(f"{res} {p['msg']}\nEntry {entry:.5f} -> {curr:.5f}\n{job} TOT: {stats[job][0]}/{stats[job][1]} = {winrate:.0f}%")
                time.sleep(2)
            except Exception as e:
                print(e); new_pending.append(p)
        else:
            new_pending.append(p)
    pending=new_pending

def get_signals(sym):
    try:
        df=yf.download(sym, period="5d", interval="15m", progress=False, auto_adjust=True)
        if len(df)<100: return
        if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        c=df['Close']; o=df['Open']; h=df['High']; l=df['Low']
        e9=c.ewm(9).mean(); e20=c.ewm(20).mean(); e50=c.ewm(50).mean(); sma50=c.rolling(50).mean()
        r=rsi(c); macd=c.ewm(12).mean()-c.ewm(26).mean(); sig=macd.ewm(9).mean(); hist=macd-sig
        bb_mid=c.rolling(20).mean(); bb_std=c.rolling(20).std(); bb_low=bb_mid-2*bb_std; bb_up=bb_mid+2*bb_std
        atr=(h-l).rolling(14).mean()

        price=float(c.iloc[-1]); pr=float(c.iloc[-2]); pr2=float(c.iloc[-3])
        e9v=float(e9.iloc[-1]); e20v=float(e20.iloc[-1]); e50v=float(e50.iloc[-1]); sma50v=float(sma50.iloc[-1]) if not pd.isna(sma50.iloc[-1]) else e50v
        rv=float(r.iloc[-1]); hv=float(hist.iloc[-1]); hv2=float(hist.iloc[-2])
        bbl=float(bb_low.iloc[-1]); bbu=float(bb_up.iloc[-1]); atrv=float(atr.iloc[-1])
        high20=float(h.rolling(20).max().iloc[-2]); low20=float(l.rolling(20).min().iloc[-2])

        if sym in last_block and datetime.now()-last_block[sym] < timedelta(minutes=40): return
        pair=sym.replace("=X","")
        found=False

        # L1 TREND 4 regole
        if e20v>e50v and price>e20v and 55<=rv<=68 and hv>hv2 and hv>0:
            msg=f"🟢 L1 TREND BUY {pair} 15m RSI {rv:.0f}"
            send_tg(msg); pending.append({"sym":sym,"price":price,"time":datetime.now(),"msg":msg,"job":"L1"}); last_block[sym]=datetime.now(); found=True; time.sleep(1)
        if not found and e20v<e50v and price<e20v and 32<=rv<=45 and hv<hv2 and hv<0:
            msg=f"🔻 L1 TREND SELL {pair} 15m RSI {rv:.0f}"
            send_tg(msg); pending.append({"sym":sym,"price":price,"time":datetime.now(),"msg":msg,"job":"L1"}); last_block[sym]=datetime.now(); found=True; time.sleep(1)

        # L2 RIMBALZO 3 regole
        if not found and price<=bbl*1.001 and rv<38 and hv>hv2:
            msg=f"🟢 L2 RIMBALZO BUY {pair} RSI {rv:.0f}"
            send_tg(msg); pending.append({"sym":sym,"price":price,"time":datetime.now(),"msg":msg,"job":"L2"}); last_block[sym]=datetime.now(); found=True; time.sleep(1)
        if not found and price>=bbu*0.999 and rv>62 and hv<hv2:
            msg=f"🔻 L2 RIMBALZO SELL {pair} RSI {rv:.0f}"
            send_tg(msg); pending.append({"sym":sym,"price":price,"time":datetime.now(),"msg":msg
