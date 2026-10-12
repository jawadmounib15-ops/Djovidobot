# Analyzer.py - V20.3 DUAL ITALIA - 5m vs 30m - CON STORICO, SUONO, NUOVO/VECCHIO
import os, time, threading
from flask import Flask, render_template_string, jsonify
import yfinance as yf
import pandas as pd
from curl_cffi import requests as cffi_requests
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","GBPJPY=X","EURJPY=X","AUDJPY=X","EURGBP=X","USDCHF=X","AUDUSD=X","USDCAD=X","NZDJPY=X","CADJPY=X","GBPAUD=X","EURAUD=X","CHFJPY=X","GBPCHF=X"]

app = Flask(__name__)
_YF = cffi_requests.Session(impersonate="chrome", timeout=10)
logs_5 = []
logs_30 = []
last_scan = "V20.3 ITALIA pronto..."
lock = threading.Lock()
ITALY = ZoneInfo("Europe/Rome")

def ora_italia(): return datetime.now(ITALY).strftime("%H:%M:%S")
def data_italia(): return datetime.now(ITALY).strftime("%d/%m %H:%M:%S")

HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>V20.3 ITALIA</title>
<style>
body{background:#0a0a0f;color:#fff;font-family:Arial;padding:10px;margin:0}
.card{background:#1e1e2a;padding:12px;border-radius:14px;margin:7px 0;border-left:6px solid #00ff88}
.card5{border-left-color:#00d9ff}.card30{border-left-color:#ffaa00}
.bu{background:#00ff88;color:#000;padding:5px 10px;border-radius:7px;font-weight:bold;font-size:12px}
.se{background:#ff3838;color:#fff;padding:5px 10px;border-radius:7px;font-weight:bold;font-size:12px}
.new{background:#ffff00;color:#000;padding:3px 8px;border-radius:12px;font-weight:bold;font-size:11px;animation:blink 1s infinite}
.old{background:#444;color:#aaa;padding:3px 8px;border-radius:12px;font-size:10px}
.t{color:#ffff00;font-weight:bold;font-size:18px}
button{padding:16px;width:100%;border-radius:14px;border:none;font-weight:bold;font-size:16px;margin:5px 0}
.btn-scan{background:#00ff88;color:#000}.btn-clear{background:#2a2a3a;color:#fff;padding:10px;font-size:12px}
.small{color:#8b8ba7;font-size:10px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
@keyframes blink{0%,50%{opacity:1} 51%,100%{opacity:0.3}}
@media(max-width:600px){.grid{grid-template-columns:1fr}}
</style></head><body>
<h2>🇮🇹 V20.3 DUAL ITALIA</h2>
<div class="card">🕐 Ora Italia: <b id="clock">{{now}}</b> | 5m: {{logs5|length}} | 30m: {{logs30|length}}<br><span class="small">{{last}} - NUOVO = <2 min</span></div>
<button class="btn-scan" onclick="doScan()">⚡ SCANNA ORA</button>
<button class="btn-clear" onclick="fetch('/clear').then(()=>location.reload())">🗑️ PULISCI STORICO</button>

<div class="grid">
<div class="card card5"><h3>⚡ SCALP 5 MIN<br><small class="small">Scadenza 5 min</small><br>LIVE: <span id="c5">0</span></h3><div id="live5">Cerco...</div></div>
<div class="card card30"><h3>✅ SICURA 30 MIN<br><small class="small">Scadenza 30 min</small><br>LIVE: <span id="c30">0</span></h3><div id="live30">Cerco...</div></div>
</div>

<div class="card"><h3>📜 STORICO 5 MIN - Ora Italia</h3><table style="width:100%;font-size:10px"><tr><th>Ora IT</th><th>Stato</th><th>Segnale</th><th>Prezzo</th></tr>
{% for s in logs5[::-1][:80] %}<tr><td>{{s.time_it}}</td><td>{% if s.age < 120 %}<span class="new">🔔 NUOVO</span>{% else %}<span class="old">VECCHIO</span>{% endif %}</td><td><span class="{{'bu' if s.side=='BUY' else 'se'}}">{{s.side}} {{s.pair}}</span></td><td>{{s.price}}<br><span class="small">{{s.why}}</span></td></tr>{% endfor %}</table></div>

<div class="card"><h3>📜 STORICO 30 MIN - Ora Italia</h3><table style="width:100%;font-size:10px"><tr><th>Ora IT</th><th>Stato</th><th>Segnale</th><th>Prezzo</th></tr>
{% for s in logs30[::-1][:80] %}<tr><td>{{s.time_it}}</td><td>{% if s.age < 120 %}<span class="new">🔔 NUOVO</span>{% else %}<span class="old">VECCHIO</span>{% endif %}</td><td><span class="{{'bu' if s.side=='BUY' else 'se'}}">{{s.side}} {{s.pair}}</span></td><td>{{s.price}}<br><span class="small">{{s.why}}</span></td></tr>{% endfor %}</table></div>

<audio id="beep" preload="auto" loop><source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg"></audio>
<audio id="beep2" preload="auto"><source src="https://actions.google.com/sounds/v1/cartoon/clang_and_wobble.ogg" type="audio/ogg"></audio>
<script>
let d5={{logs5|tojson}}, d30={{logs30|tojson}};
let lastIds5=new Set(d5.map(x=>x.id)), lastIds30=new Set(d30.map(x=>x.id));
function playSound(){try{let a=document.getElementById('beep'); a.currentTime=0; a.play(); setTimeout(()=>{a.pause();},2000); document.getElementById('beep2').play(); if(navigator.vibrate)navigator.vibrate([300,100,300,100,500]);}catch(e){}}
function doScan(){let b=document.querySelector('.btn-scan'); b.innerText='⏳ SCANNO...'; fetch('/scan').then(r=>r.json()).then(j=>{ let isNew=j.s5.length>0||j.s30.length>0; if(isNew)playSound(); setTimeout(()=>location.reload(),1000); });}
function render(){
 let now=Date.now(), h5='', h30='', c5=0,c30=0, seen={};
 d5.slice().reverse().forEach(s=>{let diff=Math.floor((s.exp*1000-now)/1000); if(diff>0&&!seen[s.pair]){seen[s.pair]=1; c5++; let m=Math.floor(diff/60); let sc=diff%60; let isNew=(now/1000 - s.created)<120; h5+=`<div class="card card5">${isNew?'<span class="new">🔔 NUOVO</span>':'<span class="old">VECCHIO</span>'} <span class="${s.side=='BUY'?'bu':'se'}">${s.side} ${s.pair}</span> ${s.price} <span class="t">${String(m).padStart(2,'0')}:${String(sc).padStart(2,'0')}</span><br><small>${s.time_it} - ${s.why}</small></div>`;}});
 seen={}; d30.slice().reverse().forEach(s=>{let diff=Math.floor((s.exp*1000-now)/1000); if(diff>0&&!seen[s.pair]){seen[s.pair]=1; c30++; let m=Math.floor(diff/60); let sc=diff%60; let isNew=(now/1000 - s.created)<120; h30+=`<div class="card card30">${isNew?'<span class="new">🔔 NUOVO</span>':'<span class="old">VECCHIO</span>'} <span class="${s.side=='BUY'?'bu':'se'}">${s.side} ${s.pair}</span> ${s.price} <span class="t">${String(m).padStart(2,'0')}:${String(sc).padStart(2,'0')}</span><br><small>${s.time_it} - ${s.why}</small></div>`;}});
 document.getElementById('c5').innerText=c5; document.getElementById('c30').innerText=c30;
 document.getElementById('live5').innerHTML=h5||'<small style=color:#8b8ba7>Nessun 5m live</small>';
 document.getElementById('live30').innerHTML=h30||'<small style=color:#8b8ba7>Nessuna 30m live</small>';
 // aggiorna age per storico
 document.querySelectorAll('table').forEach(t=>{});
}
function updateClock(){let now=new Date().toLocaleTimeString('it-IT',{timeZone:'Europe/Rome'}); let el=document.getElementById('clock'); if(el)el.innerText=now;}
setInterval(()=>{fetch('/api').then(r=>r.json()).then(j=>{let n5=j.s5.filter(x=>!lastIds5.has(x.id)), n30=j.s30.filter(x=>!lastIds30.has(x.id)); if(n5.length>0||n30.length>0){playSound(); n5.forEach(x=>lastIds5.add(x.id)); n30.forEach(x=>lastIds30.add(x.id));} d5=j.s5; d30=j.s30; render();})},3000);
setInterval(render,1000); setInterval(updateClock,1000); render(); updateClock();
</script></body></html>
"""

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

def is_pinbar(o,h,l,c, min_wick=0.50, max_body=0.50):
    rng=h-l
    if rng==0: return None,0
    body=abs(c-o)
    if body/rng>max_body: return None,0
    upper=h-max(o,c); lower=min(o,c)-l
    if lower>=rng*min_wick and lower>body*1.5 and upper<=rng*0.35: return "BUY", lower/rng
    if upper>=rng*min_wick and upper>body*1.5 and lower<=rng*0.35: return "SELL", upper/rng
    return None,0

def signal_5m(sym):
    try:
        name=sym.replace("=X","")
        df=fix_df(yf.Ticker(sym, session=_YF).history(period="5d", interval="5m"))
        if len(df)<60: return None
        df['ema20']=df['Close'].ewm(span=20).mean(); df['ema50']=df['Close'].ewm(span=50).mean(); df['rsi']=rsi(df['Close'])
        for idx in [-1,-2]:
            c=df.iloc[idx]
            side, forza = is_pinbar(float(c['Open']),float(c['High']),float(c['Low']),float(c['Close']),0.50,0.50)
            if not side: continue
            dist=min(abs(float(c['Close'])-float(c['ema20'])),abs(float(c['Close'])-float(c['ema50'])))/float(c['Close'])
            if dist>0.015: continue
            rsi_v=float(c['rsi'])
            if side=="BUY" and not (20<=rsi_v<=65): continue
            if side=="SELL" and not (35<=rsi_v<=80): continue
            now_ts=time.time()
            return {"id":f"{name}{now_ts}","pair":name+" OTC","side":side,"price":round(float(df.iloc[-1]['Close']),5 if "JPY" not in name else 3),"why":f"PULITA 5m {forza*100:.0f}% RSI{rsi_v:.0f}","time_it":ora_italia(),"created":now_ts,"age":0,"exp":now_ts+300,"sym":sym,"dist":forza}
        return None
    except: return None

def signal_30m(sym):
    try:
        name=sym.replace("=X","")
        df5=fix_df(yf.Ticker(sym, session=_YF).history(period="5d", interval="5m"))
        df15=fix_df(yf.Ticker(sym, session=_YF).history(period="5d", interval="15m"))
        if len(df5)<60 or len(df15)<60: return None
        df5['ema20']=df5['Close'].ewm(span=20).mean(); df5['ema50']=df5['Close'].ewm(span=50).mean(); df5['rsi']=rsi(df5['Close']); df15['rsi']=rsi(df15['Close'])
        s5=None
        for idx in [-1,-2]:
            c=df5.iloc[idx]
            side, f = is_pinbar(float(c['Open']),float(c['High']),float(c['Low']),float(c['Close']),0.50,0.50)
            if side:
                dist=min(abs(float(c['Close'])-float(c['ema20'])),abs(float(c['Close'])-float(c['ema50'])))/float(c['Close'])
                if dist>0.015: continue
                s5=(side,f,float(c['rsi'])); break
        if not s5: return None
        side5,f5,rsi5=s5
        ok15=False
        for idx in [-1,-2]:
            c=df15.iloc[idx]
            side15,_ = is_pinbar(float(c['Open']),float(c['High']),float(c['Low']),float(c['Close']),0.55,0.45)
            if side15==side5: ok15=True; break
            if side15 is None:
                rsi15=float(c['rsi'])
                if side5=="BUY" and rsi15<60: ok15=True; break
                if side5=="SELL" and rsi15>40: ok15=True; break
        if not ok15: return None
        now_ts=time.time()
        return {"id":f"{name}{now_ts}30","pair":name+" OTC","side":side5,"price":round(float(df5.iloc[-1]['Close']),5 if "JPY" not in name else 3),"why":f"DOPPIA 5m+15m {f5*100:.0f}%","time_it":ora_italia(),"created":now_ts,"age":0,"exp":now_ts+1800,"sym":sym,"dist":f5}
    except: return None

def get_both():
    f5=[]; f30=[]
    with ThreadPoolExecutor(max_workers=6) as ex:
        fut5={ex.submit(signal_5m,s):s for s in PAIRS}
        fut30={ex.submit(signal_30m,s):s for s in PAIRS}
        for fut in as_completed(list(fut5.keys())+list(fut30.keys()), timeout=30):
            try:
                sig=fut.result(timeout=8)
                if not sig: continue
                if fut in fut5: f5.append(sig)
                else: f30.append(sig)
            except: pass
    return sorted(f5,key=lambda x:x['dist'],reverse=True)[:5], sorted(f30,key=lambda x:x['dist'],reverse=True)[:3]

def loop():
    global last_scan
    time.sleep(5)
    while True:
        try:
            with lock:
                live5=len([x for x in logs_5 if x['exp']>time.time()])
                live30=len([x for x in logs_30 if x['exp']>time.time()])
            if live5>=5 and live30>=3:
                last_scan=f"{data_italia()} - pausa {live5}/5 e {live30}/3"
                time.sleep(20); continue
            s5,s30=get_both()
            with lock:
                for sig in s5:
                    if not any(x.get('sym')==sig['sym'] and x['exp']>time.time() for x in logs_5):
                        logs_5.append(sig)
                for sig in s30:
                    if not any(x.get('sym')==sig['sym'] and x['exp']>time.time() for x in logs_30):
                        logs_30.append(sig)
                # aggiorna age per badge NUOVO/VECCHIO
                now=time.time()
                for l in logs_5+logs_30: l['age']=now-l['created']
                if len(logs_5)>200: logs_5.pop(0)
                if len(logs_30)>200: logs_30.pop(0)
            last_scan=f"{data_italia()} - 5m:{len(s5)} | 30m:{len(s30)}"
        except Exception as e:
            last_scan=f"Err {e}"
        time.sleep(25)

@app.route('/')
def home():
    with lock:
        now_ts=time.time()
        for l in logs_5+logs_30: l['age']=now_ts-l['created']
        return render_template_string(HTML, logs5=logs_5, logs30=logs_30, last=last_scan, now=ora_italia())
@app.route('/scan')
def scan():
    s5,s30=get_both()
    with lock:
        for sig in s5:
            if not any(x.get('sym')==sig['sym'] and x['exp']>time.time() for x in logs_5): logs_5.append(sig)
        for sig in s30:
            if not any(x.get('sym')==sig['sym'] and x['exp']>time.time() for x in logs_30): logs_30.append(sig)
    return jsonify({"s5":s5,"s30":s30})
@app.route('/api')
def api():
    with lock:
        now_ts=time.time()
        for l in logs_5+logs_30: l['age']=now_ts-l['created']
        return jsonify({"s5":logs_5,"s30":logs_30})
@app.route('/clear')
def clear():
    with lock: logs_5.clear(); logs_30.clear()
    return jsonify({"ok":1})

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
