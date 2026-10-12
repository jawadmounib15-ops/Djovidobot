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
logs_5 = []; logs_30 = []
last_scan = "V20.6 POCKET 75% pronto..."
lock = threading.Lock()
ITALY = ZoneInfo("Europe/Rome")
cooldown_5 = {}; cooldown_30 = {}

def ora_italia(): return datetime.now(ITALY).strftime("%H:%M:%S")
def data_italia(): return datetime.now(ITALY).strftime("%d/%m %H:%M:%S")
def is_weekend(): return datetime.now(ITALY).weekday() >= 5

def is_news_time():
    now = datetime.now(ITALY)
    hm = now.hour*60 + now.minute
    # 14:25-14:45 e 15:55-16:15 blocco news
    if 865 <= hm <= 885: return True
    if 955 <= hm <= 975: return True
    # evita 22:00-00:30 spread alto Pocket
    if hm >= 1320 or hm <= 30: return True
    return False

HTML = """... usa lo stesso HTML di prima, cambia solo titolo in V20.6 POCKET 75%..."""
HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>V20.6 POCKET 75%</title>
<style>
body{background:#0a0a0f;color:#fff;font-family:Arial;padding:10px;margin:0}
.card{background:#1e1e2a;padding:12px;border-radius:14px;margin:7px 0;border-left:6px solid #00ff88}
.card5{border-left-color:#00d9ff}.card30{border-left-color:#ffaa00}
.bu{background:#00ff88;color:#000;padding:5px 10px;border-radius:7px;font-weight:bold;font-size:12px}
.se{background:#ff3838;color:#fff;padding:5px 10px;border-radius:7px;font-weight:bold;font-size:12px}
.new{background:#ffff00;color:#000;padding:3px 8px;border-radius:12px;font-weight:bold;font-size:11px;animation:blink 1s infinite}
.t{color:#ffff00;font-weight:bold;font-size:18px}
button{padding:16px;width:100%;border-radius:14px;border:none;font-weight:bold;font-size:16px;margin:5px 0}
.btn-scan{background:#00ff88;color:#000}.btn-clear{background:#2a2a3a;color:#fff;padding:10px;font-size:12px}
.small{color:#8b8ba7;font-size:10px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
@keyframes blink{0%,50%{opacity:1} 51%,100%{opacity:0.3}}
</style></head><body>
<h2>🎯 V20.6 POCKET 75% - ADX + NEWS FILTER</h2>
<div class="card">🕐 {{now}} | 5m: {{logs5|length}} | 30m: {{logs30|length}}<br><span class="small">{{last}} {% if weekend %} - WEEKEND OTC NO TRADE {% endif %} {% if news %} - 🔴 NEWS TIME BLOCCATO {% endif %}</span></div>
<button class="btn-scan" onclick="doScan()">🎯 SCANNA 75%</button>
<button class="btn-clear" onclick="fetch('/clear').then(()=>location.reload())">🗑️ PULISCI</button>
<div class="grid">
<div class="card card5"><h3>⚡ 5 MIN - ADX>22<br>LIVE: <span id="c5">0</span></h3><div id="live5"></div></div>
<div class="card card30"><h3>✅ 30 MIN DOPPIA<br>LIVE: <span id="c30">0</span></h3><div id="live30"></div></div>
</div>
<div class="card"><h3>STORICO 5 MIN</h3><table style="width:100%;font-size:10px">{% for s in logs5[::-1][:50] %}<tr><td>{{s.time_it}}</td><td><span class="{{'bu' if s.side=='BUY' else 'se'}}">{{s.side}} {{s.pair}}</span></td><td>{{s.price}}<br><span class="small">{{s.why}}</span></td></tr>{% endfor %}</table></div>
<div class="card"><h3>STORICO 30 MIN</h3><table style="width:100%;font-size:10px">{% for s in logs30[::-1][:50] %}<tr><td>{{s.time_it}}</td><td><span class="{{'bu' if s.side=='BUY' else 'se'}}">{{s.side}} {{s.pair}}</span></td><td>{{s.price}}<br><span class="small">{{s.why}}</span></td></tr>{% endfor %}</table></div>
<audio id="beep" preload="auto"><source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg"></audio>
<script>
let d5={{logs5|tojson}}, d30={{logs30|tojson}}; function beep(){try{document.getElementById('beep').play();}catch(e){}}
function doScan(){fetch('/scan').then(r=>r.json()).then(j=>{if(j.s5.length>0||j.s30.length>0)beep(); setTimeout(()=>location.reload(),1000);});}
function render(){let now=Date.now(),h5='',h30='',c5=0,c30=0,seen={}; d5.slice().reverse().forEach(s=>{let diff=Math.floor((s.exp*1000-now)/1000); if(diff>0&&!seen[s.pair]){seen[s.pair]=1; c5++; let m=Math.floor(diff/60); let sc=diff%60; h5+=`<div class="card card5"><span class="${s.side=='BUY'?'bu':'se'}">${s.side} ${s.pair}</span> ${s.price} <span class="t">${String(m).padStart(2,'0')}:${String(sc).padStart(2,'0')}</span><br><small>${s.why}</small></div>`;}}); seen={}; d30.slice().reverse().forEach(s=>{let diff=Math.floor((s.exp*1000-now)/1000); if(diff>0&&!seen[s.pair]){seen[s.pair]=1; c30++; let m=Math.floor(diff/60); let sc=diff%60; h30+=`<div class="card card30"><span class="${s.side=='BUY'?'bu':'se'}">${s.side} ${s.pair}</span> ${s.price} <span class="t">${String(m).padStart(2,'0')}:${String(sc).padStart(2,'0')}</span><br><small>${s.why}</small></div>`;}}); document.getElementById('c5').innerText=c5; document.getElementById('c30').innerText=c30; document.getElementById('live5').innerHTML=h5||'Nessun segnale - filtro stretto = buono'; document.getElementById('live30').innerHTML=h30||'Nessun segnale';}
setInterval(()=>{fetch('/api').then(r=>r.json()).then(j=>{d5=j.s5; d30=j.s30; render();})},3000); setInterval(render,1000); render();
</script></body></html>
"""

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).ewm(alpha=1/p, adjust=False).mean(); l=-d.where(d<0,0).ewm(alpha=1/p, adjust=False).mean()
    return 100-(100/(1+g/l))

def adx(df, p=14):
    try:
        h=df['High']; l=df['Low']; c=df['Close']
        tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
        plus_dm = h.diff(); minus_dm = -l.diff()
        plus_dm = plus_dm.where((plus_dm>minus_dm)&(plus_dm>0),0.0)
        minus_dm = minus_dm.where((minus_dm>plus_dm)&(minus_dm>0),0.0)
        tr14 = tr.ewm(alpha=1/p, adjust=False).mean()
        plus14 = plus_dm.ewm(alpha=1/p, adjust=False).mean()
        minus14 = minus_dm.ewm(alpha=1/p, adjust=False).mean()
        plus_di = 100*plus14/tr14; minus_di = 100*minus14/tr14
        dx = 100*((plus_di-minus_di).abs()/(plus_di+minus_di))
        return float(dx.ewm(alpha=1/p, adjust=False).mean().iloc[-1])
    except: return 0

def is_pinbar_strict(o,h,l,c):
    rng=h-l;
    if rng==0: return None,0
    body=abs(c-o)
    if body/rng>0.40: return None,0
    upper=h-max(o,c); lower=min(o,c)-l
    if lower>=rng*0.60 and lower>body*2.0 and upper<=rng*0.20: return "BUY", lower/rng
    if upper>=rng*0.60 and upper>body*2.0 and lower<=rng*0.20: return "SELL", upper/rng
    return None,0

def signal_5m_strict(sym):
    try:
        if is_weekend() or is_news_time(): return None
        with lock:
            if sym in cooldown_5 and time.time()-cooldown_5[sym]<900: return None
        name=sym.replace("=X",""); pair_real=name[:3]+"/"+name[3:]
        df=fix_df(yf.Ticker(sym, session=_YF).history(period="5d", interval="5m"))
        if len(df)<90: return None
        df['ema20']=df['Close'].ewm(span=20).mean(); df['ema50']=df['Close'].ewm(span=50).mean(); df['rsi']=rsi(df['Close'])
        # FILTRO ADX
        adx_v = adx(df)
        if adx_v < 22: return None
        for idx in [-1,-2]:
            c=df.iloc[idx]
            side, forza = is_pinbar_strict(float(c['Open']),float(c['High']),float(c['Low']),float(c['Close']))
            if not side: continue
            cc=float(c['Close']); ema20=float(c['ema20']); ema50=float(c['ema50'])
            dist=min(abs(cc-ema20),abs(cc-ema50))/cc
            if dist>0.010: continue
            rsi_v=float(c['rsi'])
            if side=="BUY" and not (25<=rsi_v<=55): continue
            if side=="SELL" and not (45<=rsi_v<=75): continue
            now_ts=time.time()
            with lock: cooldown_5[sym]=now_ts
            return {"id":f"{name}{now_ts}","pair":pair_real,"side":side,"price":round(float(df.iloc[-1]['Close']),5 if "JPY" not in name else 3),"why":f"REAL ADX{adx_v:.0f} {forza*100:.0f}% RSI{rsi_v:.0f}","time_it":ora_italia(),"created":now_ts,"age":0,"exp":now_ts+300,"sym":sym,"dist":forza+adx_v/100}
        return None
    except Exception as e:
        print(f"ERR 5m {sym}: {e}"); return None

def signal_30m_strict(sym):
    try:
        if is_weekend() or is_news_time(): return None
        with lock:
            if sym in cooldown_30 and time.time()-cooldown_30[sym]<1800: return None
        name=sym.replace("=X",""); pair_real=name[:3]+"/"+name[3:]
        df5=fix_df(yf.Ticker(sym, session=_YF).history(period="5d", interval="5m"))
        df15=fix_df(yf.Ticker(sym, session=_YF).history(period="5d", interval="15m"))
        if len(df5)<90 or len(df15)<90: return None
        if adx(df15) < 22: return None
        if adx(df5) < 22: return None
        df5['ema20']=df5['Close'].ewm(span=20).mean(); df5['ema50']=df5['Close'].ewm(span=50).mean(); df5['rsi']=rsi(df5['Close'])
        s5=None
        for idx in [-1,-2]:
            c=df5.iloc[idx]
            side,f=is_pinbar_strict(float(c['Open']),float(c['High']),float(c['Low']),float(c['Close']))
            if side:
                dist=min(abs(float(c['Close'])-float(c['ema20'])),abs(float(c['Close'])-float(c['ema50'])))/float(c['Close'])
                if dist>0.010: continue
                if side=="BUY" and not (25<=float(c['rsi'])<=55): continue
                if side=="SELL" and not (45<=float(c['rsi'])<=75): continue
                s5=(side,f,float(c['rsi'])); break
        if not s5: return None
        side5,f5,rsi5=s5
        ok15=False; f15=0
        for idx in [-1,-2]:
            c=df15.iloc[idx]
            side15,ff=is_pinbar_strict(float(c['Open']),float(c['High']),float(c['Low']),float(c['Close']))
            if side15==side5: ok15=True; f15=ff; break
        if not ok15: return None
        now_ts=time.time()
        with lock: cooldown_30[sym]=now_ts
        return {"id":f"{name}{now_ts}30","pair":pair_real,"side":side5,"price":round(float(df5.iloc[-1]['Close']),5 if "JPY" not in name else 3),"why":f"DOPPIA ADX{adx(df15):.0f} 5m{f5*100:.0f}%+15m{f15*100:.0f}%","time_it":ora_italia(),"created":now_ts,"age":0,"exp":now_ts+1800,"sym":sym,"dist":(f5+f15)/2}
    except Exception as e:
        print(f"ERR 30m {sym}: {e}"); return None

def get_both():
    f5=[]; f30=[]
    with ThreadPoolExecutor(max_workers=6) as ex:
        fut5={ex.submit(signal_5m_strict,s):s for s in PAIRS}
        fut30={ex.submit(signal_30m_strict,s):s for s in PAIRS}
        for fut in as_completed(list(fut5.keys())+list(fut30.keys()), timeout=35):
            try:
                sig=fut.result(timeout=10)
                if not sig: continue
                if fut in fut5: f5.append(sig)
                else: f30.append(sig)
            except: pass
    return sorted(f5,key=lambda x:x['dist'],reverse=True)[:2], sorted(f30,key=lambda x:x['dist'],reverse=True)[:1]

def loop():
    global last_scan
    time.sleep(5)
    while True:
        try:
            if is_news_time():
                last_scan=f"{data_italia()} - NEWS/SPREAD ALTO BLOCCATO"
                time.sleep(60); continue
            with lock:
                live5=len([x for x in logs_5 if x['exp']>time.time()])
                live30=len([x for x in logs_30 if x['exp']>time.time()])
            if live5>=2 and live30>=1:
                last_scan=f"{data_italia()} - pausa {live5}/2 e {live30}/1 live"
                time.sleep(25); continue
            s5,s30=get_both()
            with lock:
                for sig in s5:
                    if not any(x.get('sym')==sig['sym'] and x['exp']>time.time() for x in logs_5): logs_5.append(sig)
                for sig in s30:
                    if not any(x.get('sym')==sig['sym'] and x['exp']>time.time() for x in logs_30): logs_30.append(sig)
                now=time.time()
                for l in logs_5+logs_30: l['age']=now-l['created']
                if len(logs_5)>200: del logs_5[:-200]
                if len(logs_30)>200: del logs_30[:-200]
            last_scan=f"{data_italia()} - trovati 5m:{len(s5)} 30m:{len(s30)} ADX>22"
        except Exception as e:
            last_scan=f"Err {e}"
        time.sleep(35)

@app.route('/')
def home():
    with lock:
        now_ts=time.time()
        for l in logs_5+logs_30: l['age']=now_ts-l['created']
        return render_template_string(HTML, logs5=logs_5, logs30=logs_30, last=last_scan, now=ora_italia(), weekend=is_weekend(), news=is_news_time())
@app.route('/scan')
def scan():
    s5,s30=get_both()
    with lock:
        for sig in s5:
            if not any(x.get('sym')==sig['sym'] and x['exp']>time.time() for x in logs_5): logs_5.append(sig)
        for sig in s30:
            if not any(x.get('sym')==sig['sym'] and x['exp']>time.time() for x in logs_30): logs_30.append(sig)
        if len(logs_5)>200: del logs_5[:-200]
        if len(logs_30)>200: del logs_30[:-200]
    return jsonify({"s5":s5,"s30":s30})
@app.route('/api')
def api():
    with lock:
        now_ts=time.time()
        for l in logs_5+logs_30: l['age']=now_ts-l['created']
        return jsonify({"s5":logs_5,"s30":logs_30})
@app.route('/clear')
def clear():
    with lock: logs_5.clear(); logs_30.clear(); cooldown_5.clear(); cooldown_30.clear()
    return jsonify({"ok":1})

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
