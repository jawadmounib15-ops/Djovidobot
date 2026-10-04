# Analyzer.py - V128 LARGO 40/50 - ORA FUNZIONA - SUONO
from flask import Flask, jsonify
import os, gc, time, threading
app = Flask(__name__)

ALL_PAIRS = {
    "EURUSD OTC": "EURUSD=X", "GBPUSD OTC": "GBPUSD=X", "USDJPY OTC": "USDJPY=X",
    "AUDUSD OTC": "AUDUSD=X", "USDCAD OTC": "USDCAD=X", "USDCHF OTC": "USDCHF=X",
    "NZDUSD OTC": "NZDUSD=X", "EURJPY OTC": "EURJPY=X", "EURGBP OTC": "EURGBP=X",
    "EURAUD OTC": "EURAUD=X", "EURCAD OTC": "EURCAD=X", "EURCHF OTC": "EURCHF=X",
    "EURNZD OTC": "EURNZD=X", "GBPJPY OTC": "GBPJPY=X", "GBPAUD OTC": "GBPAUD=X",
    "GBPCAD OTC": "GBPCAD=X", "GBPCHF OTC": "GBPCHF=X", "GBPNZD OTC": "GBPNZD=X",
    "AUDJPY OTC": "AUDJPY=X", "AUDCAD OTC": "AUDCAD=X", "AUDCHF OTC": "AUDCHF=X",
    "AUDNZD OTC": "AUDNZD=X", "CADJPY OTC": "CADJPY=X", "CHFJPY OTC": "CHFJPY=X",
    "NZDJPY OTC": "NZDJPY=X", "NZDCAD OTC": "NZDCAD=X", "CADCHF OTC": "CADCHF=X",
    "EURTRY OTC": "EURTRY=X", "USDTRY OTC": "TRY=X", "AED/CNY OTC": "CNY=X",
    "BHD/CNY OTC": "CNY=X", "USD/BDT OTC": "BDT=X", "USD/EGP OTC": "EGP=X",
    "USD/PKR OTC": "PKR=X", "BTC/USD OTC": "BTC-USD", "ETH/USD OTC": "ETH-USD", "USD/INR OTC": "INR=X"
}

CACHE = {"signals": [], "time": 0, "batch": 0, "scanned": "Mai", "queue": [], "error": "Largo 40/50...", "tries": 0}
BATCH_SIZE = 4
pairs_list = list(ALL_PAIRS.items())

def calc_rsi(df):
    try:
        closes=df['Close'].tail(14); g=l=0
        for i in range(1,len(closes)):
            d=float(closes.iloc[i])-float(closes.iloc[i-1])
            if d>0: g+=d
            else: l+=abs(d)
        if l==0: return 70
        return 100-(100/(1+(g/14)/(l/14)))
    except: return 50

def scan_batch_sync():
    CACHE["tries"]+=1
    try:
        import yfinance as yf
        idx=CACHE["batch"]%len(pairs_list)
        batch_pairs=[pairs_list[(idx+i)%len(pairs_list)] for i in range(BATCH_SIZE)]
        CACHE["queue"]=[p[0] for p in batch_pairs]
        out=CACHE["signals"][:]
        for otc,real in batch_pairs:
            try:
                df=yf.download(real, period="2d", interval="1m", progress=False, auto_adjust=True, threads=False, timeout=8)
                if df is None or len(df)<10: continue
                try:
                    if hasattr(df.columns,'get_level_values'): df.columns=df.columns.get_level_values(0)
                except: pass
                c=float(df['Close'].iloc[-1]); o=float(df['Open'].iloc[-1]); h=float(df['High'].iloc[-1]); lv=float(df['Low'].iloc[-1])
                rt=h-lv
                if rt<=0: continue
                body=abs(c-o); up=h-max(c,o); down=min(c,o)-lv; rsi=calc_rsi(df)
                orig=score=0; reason=""
                # LARGO 40/50 - 3 livelli
                if down>rt*0.60 and body<rt*0.35: orig="BUY"; score=90; reason=f"Pin 60% RSI{int(rsi)}"
                elif up>rt*0.60 and body<rt*0.35: orig="SELL"; score=90; reason=f"Pin 60% RSI{int(rsi)}"
                elif down>rt*0.50 and body<rt*0.45: orig="BUY"; score=75; reason=f"Pin 50% RSI{int(rsi)}"
                elif up>rt*0.50 and body<rt*0.45: orig="SELL"; score=75; reason=f"Pin 50% RSI{int(rsi)}"
                elif down>rt*0.40 and body<rt*0.50: orig="BUY"; score=60; reason=f"Pin 40% LARGO RSI{int(rsi)}"
                elif up>rt*0.40 and body<rt*0.50: orig="SELL"; score=60; reason=f"Pin 40% LARGO RSI{int(rsi)}"
                else: continue
                final="SELL" if orig=="BUY" else "BUY"
                out=[s for s in out if s["pair"]!=otc]
                out.append({"pair":otc,"dir":final,"orig":orig,"price":f"{c:.5f}","score":score,"reason":reason,"time":time.time()})
                del df; gc.collect()
            except: gc.collect(); continue
        now=time.time()
        out=[s for s in out if now-s.get("time",now)<300]
        CACHE["signals"]=sorted(out,key=lambda x:x['score'],reverse=True)[:15]
        CACHE["time"]=now; CACHE["batch"]=(CACHE["batch"]+BATCH_SIZE)%len(pairs_list)
        CACHE["scanned"]=time.strftime("%H:%M:%S")
        CACHE["error"]=f"LARGO OK | Scan {CACHE['tries']} | Trovati {len(CACHE['signals'])}"
        gc.collect()
    except Exception as e:
        CACHE["error"]=f"ERR {str(e)[:40]}"; CACHE["scanned"]=time.strftime("%H:%M:%S")+" ERR"; gc.collect()

scan_batch_sync()

@app.route('/')
def home():
    return '''
<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V128 LARGO 40/50</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:8px}
.btn{padding:18px;border-radius:14px;font-weight:bold;font-size:16px;width:96%;max-width:420px;display:block;margin:8px auto;cursor:pointer;border:none}
.g{background:#00ff88;color:#000}.y{background:#ffff00;color:#000}
.card{background:#1e1e1e;border-radius:14px;padding:12px;margin:8px auto;max-width:420px;text-align:left;border-left:10px solid #ff00ff}
.on{background:#00ff88;color:#000;padding:10px;border-radius:10px;margin:8px auto;max-width:440px;font-weight:bold}
.batch{background:#222;border:1px solid #555;border-radius:8px;padding:6px;margin:6px auto;max-width:440px;font-size:11px}
</style></head><body>
<h2>📢 V128 LARGO 40/50 - ORA FUNZIONA</h2>
<div class="on" id="status">LARGO 40/50</div>
<div class="batch" id="queue">...</div>
<div style="background:#111;border:1px solid #ffff00;border-radius:8px;padding:6px;margin:6px auto;max-width:440px;font-size:10px;color:#ffff00" id="error">...</div>
<div class="btn y" id="soundBtn" onclick="enableSound()">🔊 ATTIVA SUONO</div>
<div class="btn g" onclick="forceScan()">🔧 FORZA SCAN LARGO</div>
<div id="live">...</div>
<div id="debug" style="color:#888;font-size:11px"></div>
<script>
let soundOn=false; let lastCount=0; let audioCtx=null;
function enableSound(){try{audioCtx=new(window.AudioContext||window.webkitAudioContext)(); soundOn=true; document.getElementById("soundBtn").innerText="✅ SUONO ON"; let o=audioCtx.createOscillator(); let g=audioCtx.createGain(); o.connect(g); g.connect(audioCtx.destination); o.frequency.value=900; g.gain.setValueAtTime(0.5,audioCtx.currentTime); o.start(); o.stop(audioCtx.currentTime+0.3);}catch(e){soundOn=true;}}
function beep(f,d){if(!soundOn||!audioCtx)return;try{let o=audioCtx.createOscillator(); let g=audioCtx.createGain(); o.connect(g); g.connect(audioCtx.destination); o.frequency.value=f; g.gain.setValueAtTime(0.8,audioCtx.currentTime); g.gain.exponentialRampToValueAtTime(0.01,audioCtx.currentTime+d/1000); o.start(); o.stop(audioCtx.currentTime+d/1000);}catch(e){}}
function playSignal(dir){if(!soundOn)return; if(dir=="BUY"){beep(800,150); setTimeout(()=>beep(1100,250),200);}else{beep(500,150); setTimeout(()=>beep(350,300),200);} if(navigator.vibrate)navigator.vibrate([200,100,300]); document.body.style.background="#ffff00"; setTimeout(()=>document.body.style.background="#0a0a0a",500);}
function forceScan(){fetch("/api/force").then(r=>r.json()).then(d=>{fastScan();});}
function fastScan(){fetch("/api/scan").then(r=>r.json()).then(d=>{
 let h=""; if(d.signals.length==0){h="<p style=color:#888>Nessun pin 40/50 in questo batch<br>"+d.queue.join(", ")+"</p>";}
 if(d.signals.length>lastCount && lastCount!=0){playSignal(d.signals[0].dir);} lastCount=d.signals.length;
 d.signals.forEach(s=>{let col=s.dir=="BUY"?"#00ff88":"#ff3b3b"; let badge=s.score>=90?"#00ff88":s.score>=75?"#ffff00":"#ffaa00"; let age=Math.round(Date.now()/1000-s.time); h+="<div class=card><b style=color:"+col+">"+s.pair+"</b> "+age+"s <span style=background:"+badge+";color:#000;padding:2px 6px;border-radius:4px>"+s.score+"</span><br><span style=font-size:30px;font-weight:900;color:"+col+">"+s.dir+"</span> ERA "+s.orig+"<br>"+s.reason+"</div>";});
 document.getElementById("live").innerHTML=h; document.getElementById("queue").innerText="BATCH "+d.batch_idx+"/"+d.total+" | "+d.queue.join(" | "); document.getElementById("error").innerText=d.error+" | 90=60% | 75=50% | 60=40% LARGO"; document.getElementById("debug").innerText="Tot:"+d.total+" Batch:"+d.batch_idx+" Scan:"+d.scanned+" Segnali:"+d.signals.length; document.getElementById("status").innerText=(d.signals.length? "🔊 "+d.signals.length+" SEGNALI LARGO | ":"⏳ ")+d.scanned;
}).catch(e=>{}); fetch("/api/trigger");}
fastScan(); setInterval(fastScan,7000);
</script></body></html>
'''

@app.route('/api/scan')
def api_scan(): return jsonify({"signals":CACHE["signals"],"total":len(ALL_PAIRS),"queue":CACHE["queue"],"batch_idx":CACHE["batch"],"scanned":CACHE["scanned"],"error":CACHE["error"],"tries":CACHE["tries"]})
@app.route('/api/force')
def api_force(): scan_batch_sync(); return jsonify({"ok":True,"scanned":CACHE["scanned"],"error":CACHE["error"],"signals":CACHE["signals"]})
@app.route('/api/trigger')
def trigger():
    if time.time() - CACHE["time"] > 10:
        threading.Thread(target=scan_batch_sync, daemon=True).start()
    return jsonify({"ok":True})
@app.route('/ping')
def ping(): return "pong v128 largo"
if __name__ == "__main__":
    scan_batch_sync()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
