# Analyzer.py - FIX DATI + TEST SUONO
import yfinance as yf
import pandas as pd
from flask import Flask, jsonify
from datetime import datetime
from zoneinfo import ZoneInfo
from curl_cffi import requests as cffi_requests
import threading, time, os, random

PAIRS = ["EURUSD=X","GBPUSD=X","EURGBP=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","AUDJPY=X","EURCAD=X","GBPCAD=X","USDCAD=X","USDCHF=X"]
_YF = cffi_requests.Session(impersonate="chrome", timeout=20)
ITALY = ZoneInfo("Europe/Rome")
pins_live = []

# PINBAR FINTA PER TESTARE SUONO SUBITO
pins_live.append({"asset":"TEST","dir":"CALL SU","tipo":"HAMMER TEST","entry":1.12345,"forza":99,"ora":datetime.now(ITALY).strftime("%H:%M:%S"),"scad":"5 MIN - SUONO OK?"})

def ora_it(): return datetime.now(ITALY).strftime("%H:%M:%S")
def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df

def check_pin(df, symbol):
    if len(df)<20: return None
    c=df.iloc[-1]
    O,H,L,C=float(c['Open']),float(c['High']),float(c['Low']),float(c['Close'])
    total=H-L
    if total<=0 or total<0.00005: return None
    corpo=abs(O-C) or total*0.1
    inf=min(O,C)-L; sup=H-max(O,C)
    # SUPER ALLARGATO PER VEDERE QUALCOSA
    is_hammer=inf>=corpo*1.2 and inf>=total*0.35
    is_star=sup>=corpo*1.2 and sup>=total*0.35
    if not (is_hammer or is_star): return None
    return {"asset":symbol.replace("=X",""),"dir":"CALL SU" if is_hammer else "PUT GIÙ","tipo":"HAMMER" if is_hammer else "STAR","entry":round((H+L)/2,5),"forza":round((inf if is_hammer else sup)/total*100),"ora":ora_it(),"scad":"5 MIN"}

def loop():
    global pins_live
    while True:
        try:
            for sym in PAIRS:
                try:
                    # Provo 5d invece di 1d - più dati
                    df=fix_df(yf.Ticker(sym, session=_YF).history(period="5d", interval="1m"))
                    if len(df)<20: continue
                    pin=check_pin(df,sym)
                    if pin and not any(p['asset']==pin['asset'] and abs((datetime.strptime(p['ora'],"%H:%M:%S") - datetime.strptime(pin['ora'],"%H:%M:%S")).total_seconds())<60 for p in pins_live if p['asset']!="TEST"):
                        pins_live.insert(0,pin)
                        pins_live=[p for p in pins_live if p['asset']!="TEST"][:1] + pins_live
                        pins_live=pins_live[:25]
                        print(f"TROVATA {pin}")
                except Exception as e:
                    print(f"Err {sym}: {e}")
                    continue
            time.sleep(15)
        except Exception as e:
            print(f"Loop err {e}"); time.sleep(10)

app=Flask(__name__)

@app.route('/')
def home():
    return """<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'>
<style>body{font-family:Arial;background:#0f0f0f;color:#fff;padding:15px}.card{background:#1e1e1e;border-radius:12px;padding:12px;margin:8px 0;display:flex;justify-content:space-between}.call{border-left:4px solid #00ff88}.put{border-left:4px solid #ff4444}.test{border-left:4px solid #ffff00}small{color:#aaa}h2{color:#00ff88}button{background:#00ff88;border:0;padding:14px 20px;border-radius:10px;font-weight:bold;width:100%;margin:10px 0;font-size:18px}</style></head><body>
<h2>📡 SCANNER PINBAR LIVE</h2>
<button id=btn onclick="attiva()">🔔 ATTIVA SUONO FORTE</button>
<small>Ora: <span id=ora></span> | <a href='/debug' style='color:#aaa'>debug dati</a></small>
<div id=list>Carico...</div>
<script>
let suonoAttivo=false, lastCount=0, audioCtx=null;
function attiva(){
  suonoAttivo=true; audioCtx=new (window.AudioContext||window.webkitAudioContext)();
  document.getElementById('btn').innerText='🔊 SUONO ATTIVO - FORTE'; document.getElementById('btn').style.background='#ffaa00';
  beepForte(); if(navigator.vibrate) navigator.vibrate(300);
}
function beepForte(){
  if(!audioCtx) return;
  for(let i=0;i<3;i++){ setTimeout(()=>{ let o=audioCtx.createOscillator(); let g=audioCtx.createGain(); o.type='square'; o.frequency.value=880; g.gain.value=0.9; o.connect(g); g.connect(audioCtx.destination); o.start(); g.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime+0.4); o.stop(audioCtx.currentTime+0.4); }, i*500); }
}
async function load(){
  let r=await fetch('/api/pins'); let data=await r.json();
  document.getElementById('ora').innerText=new Date().toLocaleTimeString();
  if(data.length>lastCount && lastCount!==0 && suonoAttivo){ beepForte(); if(navigator.vibrate) navigator.vibrate([300,100,300,100,600]); }
  lastCount=data.length;
  let h=''; data.forEach(p=>{
    let cls=p.asset=='TEST'?'test':(p.dir.includes('CALL')?'call':'put');
    h+=`<div class='card ${cls}'><div><b>${p.asset}</b> <small>${p.tipo}</small><br><small>Entry: ${p.entry} | ${p.scad}</small></div><div style='text-align:right'><b style='color:${p.asset=='TEST'?'#ffff00':(p.dir.includes('CALL')?'#00ff88':'#ff4444')}'>${p.dir}</b><br><small>${p.ora} - ${p.forza}%</small></div></div>`;
  });
  if(data.length==0) h="<p style='color:#888;text-align:center;margin-top:30px'>Nessuna pinbar...</p>";
  document.getElementById('list').innerHTML=h;
}
if(Notification) Notification.requestPermission();
load(); setInterval(load,8000);
</script></body></html>"""

@app.route('/api/pins')
def api(): return jsonify(pins_live)

@app.route('/debug')
def debug():
    out=[]
    for sym in PAIRS:
        try:
            df=fix_df(yf.Ticker(sym, session=_YF).history(period="5d", interval="1m"))
            out.append(f"{sym}: {len(df)} candele OK - ultima {df.iloc[-1]['Close'] if len(df)>0 else 'vuota'}")
        except Exception as e:
            out.append(f"{sym}: ERRORE {e}")
    return "<br>".join(out)

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
