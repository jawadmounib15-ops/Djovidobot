# Analyzer.py - V17 LARGHISSIMO - 5 MIN - TROVA 10 AL COLPO
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
last_scan = "V17 LARGHISSIMO..."
lock = threading.Lock()

HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>V17 LARGHISSIMO</title>
<style>
body{background:#000;color:#fff;font-family:Arial;padding:10px;margin:0}
.card{background:#1a1a1a;padding:14px;border-radius:14px;margin:8px 0;border-left:6px solid #00ff00}
.sell{border-left-color:#ff0000}
.bu{background:#00ff00;color:#000;padding:6px 12px;border-radius:8px;font-weight:bold;display:inline-block}
.se{background:#ff0000;color:#fff;padding:6px 12px;border-radius:8px;font-weight:bold;display:inline-block}
.t{color:#ffff00;font-weight:bold;font-size:22px}
button{padding:20px;width:100%;border-radius:14px;border:none;font-weight:bold;color:#000;font-size:19px;margin:6px 0}
.btn-scan{background:#00ff00} .btn-clear{background:#333;color:#fff;padding:12px;font-size:13px}
.small{color:#aaa;font-size:11px}
</style></head><body>
<h2>💥 V17 LARGHISSIMO - 5 MIN</h2>
<div class="card">Trovati: {{logs|length}} | {{last}}<br><span class="small">LARGHISSIMO: Ogni candela = segnale | EMA9 vs 21 | Trova 10 per scan</span></div>
<button class="btn-scan" onclick="doScan()">💥 SCANNA LARGHISSIMO - TROVA 10</button>
<button class="btn-clear" onclick="fetch('/clear').then(()=>location.reload())">🗑️ PULISCI STORICO</button>
<div class="card"><h3>🔴 LIVE 5 MIN - <span id="liveCount">0</span> SEGNALI</h3><div id="live">V17 larghissimo...</div></div>
<div class="card"><h3>📜 STORICO</h3><table style="width:100%;font-size:11px"><tr><th>Ora</th><th>Segnale</th><th>Prezzo</th><th>Motivo</th></tr>
{% for s in logs[::-1][:200] %}
<tr><td>{{s.time}}</td><td><span class="{{'bu' if s.side=='BUY' else 'se'}}">{{s.side}} {{s.pair}}</span></td><td>{{s.price}}</td><td class="small">{{s.why}}</td></tr>
{% endfor %}</table></div>
<audio id="beep" preload="auto"><source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg"></audio>
<script>
let data={{logs|tojson}}; let lastIds=new Set(data.map(d=>d.time+d.pair));
function playBeep(){try{document.getElementById('beep').play(); if(navigator.vibrate)navigator.vibrate([300,100,300]);}catch(e){}}
function doScan(){document.querySelector('.btn-scan').innerText='💥 SCANNO LARGHISSIMO...'; fetch('/scan').then(r=>r.json()).then(d=>{ if(d.length>0)playBeep(); setTimeout(()=>location.reload(),1200); });}
function render(){let h=''; let now=Date.now(); let seen={}; let c=0; data.slice().reverse().forEach(s=>{let diff=Math.floor((s.exp*1000-now)/1000); if(diff>0&&!seen[s.pair]){seen[s.pair]=1;c++; let m=Math.floor(diff/60); let sec=diff%60; h+=`<div class="card ${s.side=='BUY'?'':'sell'}"><span class="${s.side=='BUY'?'bu':'se'}">${s.side} ${s.pair}}</span> ${s.price} <span class="t">${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}</span><br><span class="small">${s.why}</span></div>`;}}); document.getElementById('liveCount').innerText=c; if(!h)h='Clicca SCANNA - trova 10 subito'; document.getElementById('live').innerHTML=h;}
setInterval(()=>{fetch('/api').then(r=>r.json()).then(d=>{let n=d.filter(x=>!lastIds.has(x.time+x.pair)); if(n.length>0){playBeep(); n.forEach(x=>lastIds.add(x.time+x.pair));} data=d; render();})},3000); setInterval(render,1000); render();
</script></body></html>
"""

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df

def signal_largo(sym):
    try:
        name = sym.replace("=X","") + " OTC"
        df = fix_df(yf.Ticker(sym, session=_YF).history(period="1d", interval="5m"))
        if len(df) < 20:
            df = fix_df(yf.Ticker(sym, session=_YF).history(period="5d", interval="15m"))
            if len(df) < 20: return None
        
        df['ema9'] = df['Close'].ewm(span=9).mean()
        df['ema21'] = df['Close'].ewm(span=21).mean()
        
        c2 = df.iloc[-1]
        cc = float(c2['Close']); oo = float(c2['Open'])
        ema9 = float(c2['ema9']); ema21 = float(c2['ema21'])

        if "JPY" in name and (cc < 30 or cc > 400): return None
        if "JPY" not in name and (cc < 0.2 or cc > 10): return None

        now_str = datetime.now().strftime("%H:%M:%S")
        exp_ts = time.time() + 300
        exp_str = (datetime.now() + timedelta(minutes=5)).strftime("%H:%M:%S")
        price_str = round(cc, 5 if "JPY" not in name else 3)

        # LARGHISSIMO: Non guarda incrocio, guarda SOLO dove sta EMA9 vs EMA21
        # Se EMA9 sopra EMA21 = BUY sempre, sotto = SELL sempre. Trova per forza.
        if ema9 > ema21:
            return {"pair":name,"side":"BUY","price":price_str,"why":f"LARGO BUY EMA9 {ema9:.4f} > 21 {ema21:.4f}","time":now_str,"exp":exp_ts,"exp_str":exp_str,"sym":sym}
        else:
            return {"pair":name,"side":"SELL","price":price_str,"why":f"LARGO SELL EMA9 {ema9:.4f} < 21 {ema21:.4f}","time":now_str,"exp":exp_ts,"exp_str":exp_str,"sym":sym}

    except Exception as e:
        print(f"ERR {sym}: {e}")
        return None

def loop():
    global last_scan
    time.sleep(4)
    while True:
        try:
            to_scan=[]
            with lock:
                for s in PAIRS:
                    if not any(x.get('sym')==s and x['exp']>time.time() for x in logs):
                        to_scan.append(s)
            found=0
            with ThreadPoolExecutor(max_workers=5) as ex: # 5 thread = larghissimo veloce
                futs={ex.submit(signal_largo, sym): sym for sym in to_scan}
                for fut in as_completed(futs, timeout=20):
                    try:
                        sig=fut.result(timeout=7)
                        if sig:
                            with lock:
                                logs.append(sig)
                                if len(logs)>250: logs.pop(0)
                            found+=1
                    except: pass
            last_scan=datetime.now().strftime("%H:%M:%S")+f" - LARGHISSIMO trovati {found}/15"
        except Exception as e:
            last_scan=f"Err {e}"
        time.sleep(15) # ogni 15 sec

@app.route('/')
def home():
    with lock: return render_template_string(HTML, logs=logs, last=last_scan)
@app.route('/scan')
def scan():
    out=[]
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs={ex.submit(signal_largo, s): s for s in PAIRS if not any(x.get('sym')==s and x['exp']>time.time() for x in logs)}
        for fut in as_completed(futs, timeout=20):
            try:
                sig=fut.result(timeout=7)
                if sig:
                    with lock:
                        logs.append(sig)
                        if len(logs)>250: logs.pop(0)
                    out.append(sig)
            except: pass
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
