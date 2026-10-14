# Analyzer.py - SCANNER WEB PINBAR
import yfinance as yf
import pandas as pd
from flask import Flask, jsonify
from datetime import datetime
from zoneinfo import ZoneInfo
from curl_cffi import requests as cffi_requests
import threading, time, os

PAIRS = ["EURUSD=X","GBPUSD=X","EURGBP=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","AUDJPY=X"]
_YF = cffi_requests.Session(impersonate="chrome", timeout=20)
ITALY = ZoneInfo("Europe/Rome")
pins_live = []

def ora_it(): return datetime.now(ITALY).strftime("%H:%M:%S")
def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df
def ema(s,p): return s.ewm(span=p).mean()

def check_pin(df, symbol):
    if len(df)<60: return None
    c=df.iloc[-2]; conf=df.iloc[-1]
    O,H,L,C=float(c['Open']),float(c['High']),float(c['Low']),float(c['Close'])
    total=H-L
    if total<=0: return None
    corpo=abs(O-C) or total*0.05
    inf=min(O,C)-L; sup=H-max(O,C)
    is_hammer=inf>=corpo*2 and inf>=total*0.50 and sup<=total*0.30 and corpo<=total*0.40
    is_star=sup>=corpo*2 and sup>=total*0.50 and inf<=total*0.30 and corpo<=total*0.40
    if not (is_hammer or is_star): return None
    if is_hammer and float(conf['Close'])<=float(conf['Open']): return None
    if is_star and float(conf['Close'])>=float(conf['Open']): return None
    return {"asset":symbol.replace("=X",""),"dir":"CALL SU" if is_hammer else "PUT GIÙ","tipo":"HAMMER" if is_hammer else "STAR","entry":round((H+L)/2,5),"forza":round((inf if is_hammer else sup)/total*100),"ora":ora_it(),"scad":"5 MIN"}

def loop():
    global pins_live
    while True:
        try:
            for sym in PAIRS:
                try:
                    df=fix_df(yf.Ticker(sym, session=_YF).history(period="1d", interval="1m"))
                    if len(df)<60: continue
                    pin=check_pin(df,sym)
                    if pin and not any(p['asset']==pin['asset'] and p['ora']==pin['ora'] for p in pins_live):
                        pins_live.insert(0,pin); pins_live=pins_live[:20]
                except: continue
            time.sleep(30)
        except: time.sleep(10)

app=Flask(__name__)
@app.route('/')
def home():
    return """<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'>
<style>body{font-family:Arial;background:#0f0f0f;color:#fff;padding:15px}.card{background:#1e1e1e;border-radius:12px;padding:12px;margin:8px 0;display:flex;justify-content:space-between}.call{border-left:4px solid #00ff88}.put{border-left:4px solid #ff4444}small{color:#aaa}h2{color:#00ff88}</style></head><body>
<h2>📡 SCANNER PINBAR LIVE 1m -> 5m</h2><small>Aggiorna ogni 10 sec | <span id=ora></span></small><div id=list>Carico...</div>
<script>async function load(){let r=await fetch('/api/pins');let data=await r.json();document.getElementById('ora').innerText=new Date().toLocaleTimeString();let h='';data.forEach(p=>{h+=`<div class='card ${p.dir.includes('CALL')?'call':'put'}'><div><b>${p.asset}</b> <small>${p.tipo}</small><br><small>Entry: ${p.entry} | ${p.scad}</small></div><div style='text-align:right'><b style='color:${p.dir.includes('CALL')?'#00ff88':'#ff4444'}'>${p.dir}</b><br><small>${p.ora} - ${p.forza}%</small></div></div>`});if(data.length==0)h="<p>Nessuna pinbar - aspetta...</p>";document.getElementById('list').innerHTML=h;}load();setInterval(load,10000);</script></body></html>"""
@app.route('/api/pins')
def api(): return jsonify(pins_live)

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
