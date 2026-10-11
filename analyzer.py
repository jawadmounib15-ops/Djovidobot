# Analyzer.py - V18 MEDIO GIUSTO - TOP 3 FORTI - 5 MIN
import os, time, threading
from flask import Flask, render_template_string, jsonify
import yfinance as yf
import pandas as pd
from curl_cffi import requests as cffi_requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","GBPJPY=X","EURJPY=X","AUDJPY=X","EURGBP=X","USDCHF=X","AUDUSD=X","USDCAD=X","NZDJPY=X","CADJPY=X","GBPAUD=X","EURAUD=X","CHFJPY=X"]

app = Flask(__name__)
_YF = cffi_requests.Session(impersonate="chrome", timeout=8)
logs = []
last_scan = "V18 TOP3 pronto..."
lock = threading.Lock()

HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>V18 TOP3</title>
<style>
body{background:#0a0a0f;color:#fff;font-family:Arial;padding:10px;margin:0}
.card{background:#1e1e2a;padding:14px;border-radius:14px;margin:8px 0;border-left:6px solid #00ff88}
.sell{border-left-color:#ff3838}
.bu{background:#00ff88;color:#000;padding:7px 14px;border-radius:8px;font-weight:bold;display:inline-block}
.se{background:#ff3838;color:#fff;padding:7px 14px;border-radius:8px;font-weight:bold;display:inline-block}
.t{color:#ffff00;font-weight:bold;font-size:22px}
button{padding:18px;width:100%;border-radius:14px;border:none;font-weight:bold;font-size:18px;margin:6px 0;cursor:pointer}
.btn-scan{background:#00ff88;color:#000} .btn-clear{background:#2a2a3a;color:#fff;padding:10px;font-size:13px}
.small{color:#8b8ba7;font-size:11px}
</style></head><body>
<h2>⚡ V18 - TOP 3 FORTI - 5 MIN</h2>
<div class="card">Trovati: {{logs|length}} | {{last}}<br><span class="small">MEDIO: solo dist >0.05% + TOP 3 più forti - max 3 live</span></div>
<button class="btn-scan" onclick="doScan()">⚡ SCANNA TOP 3</button>
<button class="btn-clear" onclick="fetch('/clear').then(()=>location.reload())">🗑️ PULISCI STORICO</button>
<div class="card"><h3>🔴 LIVE 5 MIN - <span id="liveCount">0</span> / 3 MAX</h3><div id="live">V18 filtra i migliori...</div></div>
<div class="card"><h3>📜 STORICO</h3><table style="width:100%;font-size:11px;border-collapse:collapse"><tr><th>Ora</th><th>Segnale</th><th>Prezzo</th><th>Forza</th></tr>
{% for s in logs[::-1][:200] %}
<tr><td>{{s.time}}</td><td><span class="{{'bu' if s.side=='BUY' else 'se'}}">{{s.side}} {{s.pair}}</span></td><td>{{s.price}}</td><td class="small">{{s.why}}</td></tr>
{% endfor %}</table></div>
<audio id="beep" preload="auto"><source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg"></audio>
<script>
let data={{logs|tojson}}; let lastIds=new Set(data.map(d=>d.time+d.pair));
function playBeep(){try{document.getElementById('beep').play(); if(navigator.vibrate)navigator.vibrate([250,100,250]);}catch(e){}}
function doScan(){document.querySelector('.btn-scan').innerText='⏳ CERCO TOP 3...'; fetch('/scan').then(r=>r.json()).then(d=>{ if(d.length>0)playBeep(); setTimeout(()=>location.reload(),1000); });}
function render(){let h=''; let now=Date.now(); let seen={}; let c=0; data.slice().reverse().forEach(s=>{let diff=Math.floor((s.exp*1000-now)/1000); if(diff>0&&!seen[s.pair]){seen[s.pair]=1;c++; let m=Math.floor(diff/60); let sec=diff%60; h+=`<div class="card ${s.side=='BUY'?'':'sell'}"><span class="${s.side=='BUY'?'bu':'se'}">${s.side} ${s.pair}</span> ${s.price} <span class="t">${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}</span><br><span class="small">${s.why}</span></div>`;}}); document.getElementById('liveCount').innerText=c; if(!h)h='<small style=color:#8b8ba7>Nessun trend forte ora, clicca fra 1 min - filtra solo dist >0.05%</small>'; document.getElementById('live').innerHTML=h;}
setInterval(()=>{fetch('/api').then(r=>r.json()).then(d=>{let n=d.filter(x=>!lastIds.has(x.time+x.pair)); if(n.length>0){playBeep(); n.forEach(x=>lastIds.add(x.time+x.pair));} data=d; render();})},3000); setInterval(render,1000); render();
</script></body></html>
"""

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df

def signal_top3(sym):
    try:
        name = sym.replace("=X","") + " OTC"
        df = fix_df(yf.Ticker(sym, session=_YF).history(period="2d", interval="5m"))
        if len(df) < 30:
            df = fix_df(yf.Ticker(sym, session=_YF).history(period="5d", interval="15m"))
            if len(df) < 30: return None
        df['ema9'] = df['Close'].ewm(span=9).mean()
        df['ema21'] = df['Close'].ewm(span=21).mean()
        c2 = df.iloc[-1]
        cc = float(c2['Close'])
        ema9 = float(c2['ema9']); ema21 = float(c2['ema21'])
        if "JPY" in name and (cc < 30 or cc > 400): return None
        if "JPY" not in name and (cc < 0.2 or cc > 10): return None
        
        dist = abs(ema9 - ema21) / ema21 * 100
        if dist < 0.05: # FILTRO MEDIO - toglie mercato morto
            return None

        now_str = datetime.now().strftime("%H:%M:%S")
        exp_ts = time.time() + 300
        exp_str = (datetime.now() + timedelta(minutes=5)).strftime("%H:%M:%S")
        price_str = round(cc, 5 if "JPY" not in name else 3)

        if ema9 > ema21:
            return {"pair":name,"side":"BUY","price":price_str,"why":f"TOP BUY dist {dist:.3f}% forte","time":now_str,"exp":exp_ts,"exp_str":exp_str,"sym":sym,"dist":dist}
        else:
            return {"pair":name,"side":"SELL","price":price_str,"why":f"TOP SELL dist {dist:.3f}% forte","time":now_str,"exp":exp_ts,"exp_str":exp_str,"sym":sym,"dist":dist}
    except Exception as e:
        print(f"ERR {sym}: {e}")
        return None

def get_top3_signals():
    found=[]
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs={ex.submit(signal_top3, s): s for s in PAIRS}
        for fut in as_completed(futs, timeout=25):
            try:
                sig=fut.result(timeout=8)
                if sig: found.append(sig)
            except: pass
    # Ordina per forza e prendi solo top 3
    found = sorted(found, key=lambda x: x['dist'], reverse=True)[:3]
    return found

def loop():
    global last_scan
    time.sleep(5)
    while True:
        try:
            # Pulisci segnali scaduti e controlla quanti live ci sono
            with lock:
                live_now = len([x for x in logs if x['exp']>time.time()])
            if live_now >= 3:
                last_scan = datetime.now().strftime("%H:%M:%S") + f" - {live_now}/3 live - aspetto"
                time.sleep(20)
                continue

            top3 = get_top3_signals()
            with lock:
                for sig in top3:
                    if not any(x.get('sym')==sig['sym'] and x['exp']>time.time() for x in logs):
                        logs.append(sig)
                        if len(logs)>250: logs.pop(0)
            last_scan = datetime.now().strftime("%H:%M:%S") + f" - TOP3 trovati {len(top3)} - max 3 live"
        except Exception as e:
            last_scan=f"Err {e}"
        time.sleep(25)

@app.route('/')
def home():
    with lock: return render_template_string(HTML, logs=logs, last=last_scan)
@app.route('/scan')
def scan():
    top3 = get_top3_signals()
    out=[]
    with lock:
        for sig in top3:
            if not any(x.get('sym')==sig['sym'] and x['exp']>time.time() for x in logs):
                logs.append(sig)
                if len(logs)>250: logs.pop(0)
                out.append(sig)
    return jsonify(out)
@app.route('/api')
def api():
    with lock: return jsonify(logs)
@app.route('/clear')
def clear():
    with lock: logs.clear()
    return jsonify({"ok":1})

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
