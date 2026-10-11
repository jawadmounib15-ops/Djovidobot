# Analyzer.py - V15.0 - 5 MIN + 15 COPPIE + SUONO + ANTI-LAG
import os, time, threading
from flask import Flask, render_template_string, jsonify
import yfinance as yf
import pandas as pd
from curl_cffi import requests as cffi_requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# 15 COPPIE - TUTTE OTC FORTI
PAIRS = [
    "EURUSD=X","GBPUSD=X","USDJPY=X","GBPJPY=X","EURJPY=X",
    "AUDJPY=X","EURGBP=X","USDCHF=X","AUDUSD=X","USDCAD=X",
    "NZDJPY=X","CADJPY=X","GBPAUD=X","EURAUD=X","CHFJPY=X"
]

app = Flask(__name__)
_YF = cffi_requests.Session(impersonate="chrome", timeout=8)
logs = []
last_scan = "V15 Anti-Lag pronto..."
lock = threading.Lock()

HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>V15 5MIN PRO</title>
<style>
body{background:#08080c;color:#fff;font-family:Arial;padding:10px;margin:0}
.card{background:#1a1a24;padding:14px;border-radius:14px;margin:8px 0;border-left:5px solid #a855f7;position:relative}
.sell{border-left-color:#ff3838}
.bu{padding:6px 12px;border-radius:8px;font-weight:bold;display:inline-block;background:#a855f7;color:#fff}
.se{padding:6px 12px;border-radius:8px;font-weight:bold;display:inline-block;background:#ff3838;color:#fff}
.t{color:#facc15;font-weight:bold;font-size:20px}
button{padding:16px;width:100%;border-radius:14px;border:none;font-weight:bold;color:#fff;font-size:16px;margin:6px 0;cursor:pointer}
.btn-scan{background:#a855f7} .btn-clear{background:#2a2a3a;font-size:13px;padding:10px}
.btn-sound{background:#22c55e;color:#000}
table{width:100%;font-size:11px;border-collapse:collapse} td,th{padding:7px;border-bottom:1px solid #2a2a3a}
.small{color:#8b8ba7;font-size:11px}
.livebox{min-height:90px}
.top{position:sticky;top:0;background:#08080c;z-index:10;padding:5px 0}
</style></head><body>
<div class="top">
<h2 style="margin:5px 0">🔮 V15 PRO - 5 MIN - 15 COPPIE + SUONO</h2>
<div class="card" style="padding:10px">Trovati: {{logs|length}} | {{last}}<br><span class="small">15 coppie | 3 thread paralleli anti-lag | beep + vibrazione</span></div>
<button class="btn-scan" onclick="doScan()">⚡ SCANNA ORA (ANTI-LAG)</button>
<div style="display:flex;gap:6px">
<button class="btn-sound" style="flex:1" onclick="toggleSound()" id="soundBtn">🔊 SUONO ON</button>
<button class="btn-clear" style="flex:1" onclick="fetch('/clear').then(()=>location.reload())">🗑️ PULISCI STORICO</button>
</div>
</div>

<div class="card"><h3>🔴 LIVE 5 MINUTI - <span id="liveCount">0</span></h3><div id="live" class="livebox">Attivo... scansiono 3 coppie alla volta per non laggare</div></div>
<div class="card"><h3>📜 STORICO (ultimi 200)</h3><table><tr><th>Ora</th><th>Segnale</th><th>Prezzo</th><th>Motivo</th></tr>
{% for s in logs[::-1][:200] %}
<tr><td>{{s.time}}</td><td><span class="{{'bu' if s.side=='BUY' else 'se'}}">{{s.side}} {{s.pair}}</span></td><td>{{s.price}}</td><td class="small">{{s.why}}</td></tr>
{% endfor %}</table></div>

<audio id="beep" preload="auto">
  <source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg">
</audio>

<script>
let data={{logs|tojson}};
let soundOn = localStorage.getItem('soundOn') !== 'false';
let lastIds = new Set(data.map(d=>d.time+d.pair));
updateSoundBtn();

function updateSoundBtn(){
  document.getElementById('soundBtn').innerText = soundOn ? '🔊 SUONO ON' : '🔇 SUONO OFF';
}
function toggleSound(){
  soundOn = !soundOn;
  localStorage.setItem('soundOn', soundOn);
  updateSoundBtn();
  if(soundOn){ playBeep(); }
}
function playBeep(){
  if(!soundOn) return;
  try{
    document.getElementById('beep').play();
    if(navigator.vibrate) navigator.vibrate([200,100,200]);
    // beep di backup con WebAudio
    let ctx = new (window.AudioContext || window.webkitAudioContext)();
    let o = ctx.createOscillator(); let g = ctx.createGain();
    o.frequency.value=900; o.connect(g); g.connect(ctx.destination);
    g.gain.setValueAtTime(0.5, ctx.currentTime); o.start(); o.stop(ctx.currentTime+0.3);
  }catch(e){}
}
function doScan(){
  document.querySelector('.btn-scan').innerText='⏳ SCANNO 15 COPPIE (8 sec)...';
  fetch('/scan').then(r=>r.json()).then(d=>{
    if(d.length>0 && soundOn){ playBeep(); }
    setTimeout(()=>location.reload(),1200);
  });
}
function render(){
 let h=''; let now=Date.now(); let seen={}; let count=0;
 data.slice().reverse().forEach(s=>{
  let diff=Math.floor((s.exp*1000-now)/1000);
  if(diff>0 && !seen[s.pair]){
   seen[s.pair]=1; count++;
   let m=Math.floor(diff/60); let sec=diff%60;
   h+=`<div class="card ${s.side=='BUY'?'':'sell'}"><span class="${s.side=='BUY'?'bu':'se'}">${s.side} ${s.pair}</span> ${s.price} <span class="t">${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}</span><br><span class="small">${s.why} | scade ${s.exp_str}</span></div>`;
  }
 });
 document.getElementById('liveCount').innerText=count;
 if(!h) h='<small style=\"color:#8b8ba7\">Nessun cross adesso - mercato laterale. V15 scanna ogni 25s automatico con anti-lag.</small>';
 document.getElementById('live').innerHTML=h;
}
setInterval(()=>{
  fetch('/api').then(r=>r.json()).then(d=>{
    let newOnes = d.filter(x=>!lastIds.has(x.time+x.pair));
    if(newOnes.length>0 && soundOn){
      playBeep();
      newOnes.forEach(n=>lastIds.add(n.time+n.pair));
    }
    data=d; render();
  })
},3000);
setInterval(render,1000); render();
</script></body></html>
"""

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df

def signal_5min(sym):
    try:
        name = sym.replace("=X","") + " OTC"
        df = fix_df(yf.Ticker(sym, session=_YF).history(period="2d", interval="5m"))
        if len(df) < 50: return None
        
        df['ema9'] = df['Close'].ewm(span=9).mean()
        df['ema21'] = df['Close'].ewm(span=21).mean()
        
        c1 = df.iloc[-2]
        c2 = df.iloc[-1]
        
        cc = float(c2['Close']); oo = float(c2['Open'])
        hi = float(c2['High']); lo = float(c2['Low'])
        
        if "JPY" in name and (cc < 50 or cc > 300): return None
        if "JPY" not in name and (cc < 0.5 or cc > 5): return None
        
        body = abs(cc - oo); tr = hi - lo
        if tr == 0: return None
        body_perc = (body / tr) * 100
        if body_perc < 35: return None # filtro doji
        
        cross_up = c1['ema9'] < c1['ema21'] and c2['ema9'] > c2['ema21']
        cross_down = c1['ema9'] > c1['ema21'] and c2['ema9'] < c2['ema21']
        
        price_str = round(cc, 5 if "JPY" not in name else 3)
        now_str = datetime.now().strftime("%H:%M:%S")
        exp_ts = time.time() + 300
        exp_str = (datetime.now() + timedelta(minutes=5)).strftime("%H:%M:%S")
        
        if cross_up and cc > oo:
            return {"pair":name,"side":"BUY","price":price_str,"why":f"CROSS UP 9/21 Body {int(body_perc)}%","time":now_str,"exp":exp_ts,"exp_str":exp_str,"sym":sym}
        if cross_down and cc < oo:
            return {"pair":name,"side":"SELL","price":price_str,"why":f"CROSS DOWN 9/21 Body {int(body_perc)}%","time":now_str,"exp":exp_ts,"exp_str":exp_str,"sym":sym}
    except Exception as e:
        print(f"ERR {sym}: {e}")
        return None
    return None

def loop():
    global last_scan
    time.sleep(6)
    while True:
        try:
            start = time.time()
            to_scan = []
            with lock:
                for s in PAIRS:
                    if not any(x.get('sym')==s and x['exp']>time.time() for x in logs):
                        to_scan.append(s)
            
            found = 0
            # ANTI-LAG: 3 thread paralleli, timeout 8 sec a coppia
            with ThreadPoolExecutor(max_workers=3) as ex:
                futs = {ex.submit(signal_5min, sym): sym for sym in to_scan[:9]} # 9 alla volta max
                for fut in as_completed(futs, timeout=25):
                    try:
                        sig = fut.result(timeout=8)
                        if sig:
                            with lock:
                                logs.append(sig)
                                if len(logs) > 200: logs.pop(0)
                            found += 1
                    except: pass
            
            elapsed = int(time.time()-start)
            last_scan = datetime.now().strftime("%H:%M:%S") + f" - {found} segnali - {elapsed}s anti-lag"
        except Exception as e:
            last_scan = f"Err loop {e}"
        time.sleep(25)

@app.route('/')
def home(): 
    with lock: return render_template_string(HTML, logs=logs, last=last_scan)
@app.route('/scan')
def scan():
    out=[]
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(signal_5min, s): s for s in PAIRS if not any(x.get('sym')==s and x['exp']>time.time() for x in logs)}
        for fut in as_completed(futs, timeout=20):
            try:
                sig = fut.result(timeout=8)
                if sig:
                    with lock:
                        logs.append(sig)
                        if len(logs)>200: logs.pop(0)
                    out.append(sig)
                    if len(out)>=3: break
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
