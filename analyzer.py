# app.py - NUOVO 5 MIN ULTRA - SOSTITUISCE V69
import os, time, threading
from flask import Flask, jsonify
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
from curl_cffi import requests as cffi_requests

PAIRS = ["EURUSD=X","GBPUSD=X","EURGBP=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCAD=X"]
ITALY = ZoneInfo("Europe/Rome")

app = Flask(__name__)
pins_live, pins_storico, cooldown = [], [], {}

def ema(s,p): return s.ewm(span=p).mean()
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def atr(df,p=14):
    hl=df['High']-df['Low']; hc=abs(df['High']-df['Close'].shift()); lc=abs(df['Low']-df['Close'].shift())
    tr=pd.concat([hl,hc,lc],axis=1).max(axis=1)
    return tr.rolling(p).mean()

def get_df(sym):
    try:
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=5m&range=5d"
        r=cffi_requests.get(url, impersonate="chrome120", timeout=8)
        q=r.json()['chart']['result'][0]['indicators']['quote'][0]
        df=pd.DataFrame({'Open':q['open'],'High':q['high'],'Low':q['low'],'Close':q['close']}).dropna()
        return df.tail(400)
    except: return pd.DataFrame()

def scan_5m():
    global pins_live, pins_storico
    for sym in PAIRS:
        clean=sym.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean]<900: continue # 15 min no duplicati
        df=get_df(sym)
        if len(df)<120: continue
        try:
            df['ema20']=ema(df['Close'],20); df['ema50']=ema(df['Close'],50); df['ema200']=ema(df['Close'],200)
            df['rsi']=rsi(df['Close']); df['atr']=atr(df,14); df['atr_ma']=df['atr'].rolling(50).mean()
            c=df.iloc[-2]; conf=df.iloc[-1]
            O,H,L,C=float(c['Open']),float(c['High']),float(c['Low']),float(c['Close'])
            total=H-L
            if total<0.00007: continue
            # ULTRA FILTRO ATR
            if float(c['atr']) < float(c['atr_ma'])*0.75: continue
            if float(c['atr']) > float(c['atr_ma'])*2.5: continue
            
            corpo=abs(O-C); inf=min(O,C)-L; sup=H-max(O,C)
            forza=max(inf,sup)/total*100
            # PINBAR VERO 5M
            hammer=inf>=corpo*2.0 and inf>=total*0.55 and sup<=total*0.20 and corpo<=total*0.30
            star=sup>=corpo*2.0 and sup>=total*0.55 and inf<=total*0.20 and corpo<=total*0.30
            if not ((hammer or star) and 70<=forza<=92): continue
            
            low30=df['Low'].iloc[-31:-2].min(); high30=df['High'].iloc[-31:-2].max()
            if hammer and L > low30*1.001: continue
            if star and H < high30*0.999: continue
            
            e20=float(c['ema20']); e200=float(c['ema200']); rv=float(c['rsi']); price=C
            if hammer and not (22 <= rv <= 40): continue
            if star and not (60 <= rv <= 78): continue
            if abs(price-e20)/price > 0.004: continue
            if hammer and price < e200*0.998: continue
            if star and price > e200*1.002: continue
            
            conf_c=float(conf['Close'])
            if hammer and (conf_c < L+total*0.60 or conf_c <= float(conf['Open'])): continue
            if star and (conf_c > H-total*0.60 or conf_c >= float(conf['Open'])): continue
            
            sl=L-total*0.3 if hammer else H+total*0.3
            if abs(sl-price)/price < 0.0007: continue
            
            signal="BUY" if hammer else "SELL"
            pin={
                "asset":clean,
                "dir":"CALL SU 📈 5M" if signal=="BUY" else "PUT GIÙ 📉 5M",
                "signal":signal,
                "entry":round((H+L)/2,5),
                "price":round(price,5),
                "rsi":round(rv),
                "forza":round(forza),
                "ema20":round(e20,5),
                "atr":round(float(c['atr']),5),
                "sl":round(sl,5),
                "tp":round(price+total*1.8,5) if hammer else round(price-total*1.8,5),
                "ora":datetime.now(ITALY).strftime("%H:%M:%S"),
                "data":datetime.now(ITALY).strftime("%d/%m %H:%M:%S"),
                "scadenza":(datetime.now(ITALY)+timedelta(minutes=5)).strftime("%H:%M:%S"),
                "scad_label":"5M",
                "id":f"{clean}{time.time()}"
            }
            pins_live.insert(0,pin); pins_storico.insert(0,pin)
            pins_live=pins_live[:20]; pins_storico=pins_storico[:500]
            cooldown[clean]=time.time()
        except: continue

def loop():
    while True:
        try: scan_5m()
        except: pass
        time.sleep(30)

@app.route('/')
def home():
    return """<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>5M ULTRA NUOVO</title>
<style>body{background:#0a0a0a;color:#fff;font-family:Arial;padding:12px}h2{color:#00ff88}.card{background:#1e1e1e;padding:14px;margin:10px 0;border-radius:12px}.call{border-left:5px solid #00ff88}.put{border-left:5px solid #ff4444}button{padding:14px;width:100%;border-radius:10px;font-weight:bold;margin:6px 0;border:0}small{color:#aaa;font-size:12px}.det{color:#ffcc00;font-size:11px}</style></head><body>
<h2>⚡ NUOVO - SCANNER 5M ULTRA - SCAD 5 MIN</h2>
<button id="btn" onclick="attiva()" style="background:#ff4444;color:#fff">🔴 ATTIVA SUONO</button>
<div style="margin:12px 0"><button onclick="show('live')" style="background:#00ff88;padding:10px 16px;border-radius:8px;border:0">LIVE</button>
<button onclick="show('stor')" style="background:#222;color:#fff;padding:10px 16px;border-radius:8px;border:1px solid #333">STORICO (<span id="numStor">0</span>)</button>
<button onclick="localStorage.clear();location.reload()" style="background:#ff4444;color:#fff;padding:10px;border-radius:8px;border:0">🗑️ PULISCI</button></div>
<div id="ora" style="color:#0f8"></div><div id="listLive"></div><div id="listStor" style="display:none"></div>
<script>
let audioCtx=null,suono=false,last=0;
let storico=JSON.parse(localStorage.getItem('ultra5m_storico')||'[]');let live=JSON.parse(localStorage.getItem('ultra5m_live')||'[]');
function attiva(){audioCtx=new(window.AudioContext||window.webkitAudioContext)();suono=true;document.getElementById('btn').innerHTML='🟢 SUONO ATTIVO';document.getElementById('btn').style.background='#00ff88';document.getElementById('btn').style.color='#000';let o=audioCtx.createOscillator(),g=audioCtx.createGain();o.frequency.value=880;g.gain.value=0.8;o.connect(g);g.connect(audioCtx.destination);o.start();setTimeout(()=>o.stop(),400);}
function beep(){if(!suono||!audioCtx) return;if(audioCtx.state==='suspended') audioCtx.resume();for(let i=0;i<3;i++){setTimeout(()=>{let o=audioCtx.createOscillator(),g=audioCtx.createGain();o.type='square';o.frequency.value=900;g.gain.value=0.9;o.connect(g);g.connect(audioCtx.destination);o.start();setTimeout(()=>o.stop(),350);},i*500);}if(navigator.vibrate) navigator.vibrate([300,100,300]);}
function show(t){document.getElementById('listLive').style.display=t=='live'?'block':'none';document.getElementById('listStor').style.display=t=='stor'?'block':'none';}
function render(d,el){let h='';d.forEach(p=>{h+=`<div class='card ${p.signal=='BUY'?'call':'put'}'><div><b>${p.asset}</b> <small>RSI ${p.rsi} Forza ${p.forza}%</small><br><small>Entry ${p.entry} | ${p.data}</small><br><small class="det">EMA20 ${p.ema20} | SL ${p.sl} TP ${p.tp} | ATR ${p.atr}</small><br><small style="color:#fa0">Scad ${p.scadenza} (${p.scad_label})</small></div><div style='text-align:right'><b style='color:${p.signal=='BUY'?'#0f8':'#f44'}'>${p.dir}</b></div></div>`;});if(d.length==0) h='<p style="color:#888;text-align:center">Nessun segnale - filtro ULTRA 70%<br>Fa 2-5 segnali al giorno ma reali</p>';document.getElementById(el).innerHTML=h;}
async function load(){let r1=await fetch('/api/pins');let l=await r1.json();let r2=await fetch('/api/storico');let s=await r2.json();l.forEach(p=>{if(!live.find(x=>x.id==p.id)) live.unshift(p);});s.forEach(p=>{if(!storico.find(x=>x.id==p.id)) storico.unshift(p);});live=live.slice(0,20);storico=storico.slice(0,300);localStorage.setItem('ultra5m_live',JSON.stringify(live));localStorage.setItem('ultra5m_storico',JSON.stringify(storico));document.getElementById('ora').innerText=new Date().toLocaleString('it-IT',{timeZone:'Europe/Rome'})+' | Storico:'+storico.length;document.getElementById('numStor').innerText=storico.length;if(live.length>last&&last!=0&&suono) beep();last=live.length;render(live,'listLive');render(storico,'listStor');}load();setInterval(load,7000);
</script></body></html>"""
@app.route('/api/pins')
def api_pins(): return jsonify(pins_live)
@app.route('/api/storico')
def api_storico(): return jsonify(pins_storico)

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
