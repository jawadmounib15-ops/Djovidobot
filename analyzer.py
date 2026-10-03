# Analyzer.py - V124 TUTTI OTC 34 + SUONO FIX - FILE UNICO - AUTO START
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
    "EURTRY OTC": "EURTRY=X", "GBPUSD OTC-2": "GBPUSD=X", "USDTRY OTC": "TRY=X",
    "AED/CNY OTC": "CNY=X", "BHD/CNY OTC": "CNY=X", "USD/BDT OTC": "BDT=X",
    "USD/EGP OTC": "EGP=X", "USD/PKR OTC": "PKR=X", "BTC/USD OTC": "BTC-USD",
}

CACHE = {"signals": [], "time": 0, "batch": 0, "scanned": "Mai", "queue": [], "started": False}
BATCH_SIZE = 4
pairs_list = list(ALL_PAIRS.items())

def calc_rsi(df):
    try:
        closes = df['Close'].tail(15); g=l=0
        for i in range(1,len(closes)):
            d=float(closes.iloc[i])-float(closes.iloc[i-1])
            if d>0: g+=d
            else: l+=abs(d)
        if l==0: return 70
        return 100-(100/(1+(g/14)/(l/14)))
    except: return 50.0

def scan_batch():
    try:
        import yfinance as yf
        idx=CACHE["batch"]%len(pairs_list)
        batch_pairs=[pairs_list[(idx+i)%len(pairs_list)] for i in range(BATCH_SIZE)]
        CACHE["queue"]=[p[0] for p in batch_pairs]
        out=CACHE["signals"][:]
        for otc,real in batch_pairs:
            try:
                df=yf.download(real,period="2d",interval="1m",progress=False,auto_adjust=True,threads=False,timeout=6)
                if df is None or len(df)<20: continue
                try: df.columns=df.columns.get_level_values(0)
                except: pass
                c=float(df.iloc[-1]['Close']); o=float(df.iloc[-1]['Open']); h=float(df.iloc[-1]['High']); lv=float(df.iloc[-1]['Low'])
                rt=h-lv
                if rt<=0: continue
                body=abs(c-o); up=h-max(c,o); down=min(c,o)-lv; rsi=calc_rsi(df)
                orig=score=0; reason=""
                if down>rt*0.65 and body<rt*0.30 and (5<=rsi<=65): orig="BUY"; score=90; reason=f"Pin 65% {int(rsi)}"
                elif up>rt*0.65 and body<rt*0.30 and (35<=rsi<=95): orig="SELL"; score=90; reason=f"Pin 65% {int(rsi)}"
                elif down>rt*0.55 and body<rt*0.35 and (10<=rsi<=60): orig="BUY"; score=80; reason=f"Pin 55% {int(rsi)}"
                elif up>rt*0.55 and body<rt*0.35 and (40<=rsi<=90): orig="SELL"; score=80; reason=f"Pin 55% {int(rsi)}"
                elif down>rt*0.50 and body<rt*0.40 and (10<=rsi<=65): orig="BUY"; score=70; reason=f"Pin 50% {int(rsi)}"
                elif up>rt*0.50 and body<rt*0.40 and (35<=rsi<=90): orig="SELL"; score=70; reason=f"Pin 50% {int(rsi)}"
                else: continue
                final="SELL" if orig=="BUY" else "BUY"
                out=[s for s in out if s["pair"]!=otc]
                out.append({"pair":otc,"dir":final,"orig":orig,"price":f"{c:.5f}","score":score,"reason":reason,"time":time.time()})
                del df; gc.collect()
            except: gc.collect(); continue
        now=time.time()
        out=[s for s in out if now-s.get("time",now)<180]
        CACHE["signals"]=sorted(out,key=lambda x:x['score'],reverse=True)[:10]
        CACHE["time"]=now; CACHE["batch"]=(CACHE["batch"]+BATCH_SIZE)%len(pairs_list); CACHE["scanned"]=time.strftime("%H:%M:%S")
        CACHE["started"]=True
        gc.collect()
    except Exception as e:
        CACHE["scanned"]=f"Err {str(e)[:20]}"
        gc.collect()

# AUTO START anche con gunicorn
def start_thread():
    if not CACHE["started"]:
        threading.Thread(target=scan_batch, daemon=True).start()

@app.route('/')
def home():
    start_thread()
    return '''
<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V124 SUONO FIX</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:8px}
.btn{padding:18px;border-radius:14px;font-weight:bold;font-size:16px;width:96%;max-width:420px;display:block;margin:8px auto;cursor:pointer;border:none}
.g{background:#00ff88;color:#000}.y{background:#ffff00;color:#000}
.card{background:#1e1e1e;border-radius:14px;padding:12px;margin:8px auto;max-width:420px;text-align:left;border-left:10px solid #ff00ff}
.on{background:#00ff88;color:#000;padding:10px;border-radius:10px;margin:8px auto;max-width:420px;font-weight:bold}
.batch{background:#222;border:1px solid #555;border-radius:8px;padding:6px;margin:6px auto;max-width:440px;font-size:11px}
</style></head><body>
<h2>🔊 V124 TUTTI OTC + SUONO FIX</h2>
<div class="on" id="status">🔇 Clicca ATTIVA SUONO</div>
<div class="batch" id="queue">Carico batch...</div>
<div class="btn y" id="soundBtn" onclick="enableSound()">🔊 ATTIVA SUONO + VIBRA</div>
<div class="btn g" onclick="fastScan()">⚡ SCAN TUTTI OTC (0 sec)</div>
<div id="live">Avvio scan...</div>
<div id="debug" style="color:#888;font-size:11px"></div>
<script>
let soundOn=false; let lastCount=0; let audioCtx=null;
function enableSound(){
 try{
  audioCtx=new (window.AudioContext||window.webkitAudioContext)();
  soundOn=true;
  document.getElementById("soundBtn").innerText="✅ SUONO ATTIVO";
  document.getElementById("soundBtn").className="btn g";
  beep(800,300); beep(1000,300);
  if(navigator.vibrate) navigator.vibrate(200);
  document.getElementById("status").innerText="🔊 SUONO ATTIVO - Beep ad ogni segnale";
 }catch(e){soundOn=true;}
}
function beep(freq,dur){
 if(!soundOn||!audioCtx) return;
 try{
  let o=audioCtx.createOscillator(); let g=audioCtx.createGain();
  o.connect(g); g.connect(audioCtx.destination);
  o.frequency.value=freq; o.type="sine";
  g.gain.setValueAtTime(0.8,audioCtx.currentTime);
  g.gain.exponentialRampToValueAtTime(0.01,audioCtx.currentTime+dur/1000);
  o.start(); o.stop(audioCtx.currentTime+dur/1000);
 }catch(e){}
}
function playSignal(dir){
 if(!soundOn) return;
 if(dir=="BUY"){beep(800,200); setTimeout(()=>beep(1000,300),250);}
 else{beep(500,200); setTimeout(()=>beep(400,400),250);}
 if(navigator.vibrate) navigator.vibrate([200,100,300]);
 document.body.style.background="#ff00ff"; setTimeout(()=>document.body.style.background="#0a0a0a",400);
}
function fastScan(){
 fetch("/api/scan").then(r=>r.json()).then(d=>{
  let h="";
  if(d.signals.length==0){h="<p style=color:#888>Nessun pin 50/40<br>Batch: "+(d.queue.length?d.queue.join(", "):"avvio...")+"</p>";}
  if(d.signals.length>lastCount && lastCount!=0){
   let newest=d.signals[0]; playSignal(newest.dir);
   document.getElementById("status").innerText="🔊 NUOVO! "+newest.pair+" "+newest.dir+" "+newest.score;
  }
  lastCount=d.signals.length;
  d.signals.forEach(s=>{
   let col=s.dir=="BUY"?"#00ff88":"#ff3b3b";
   let age=Math.round(Date.now()/1000 - s.time);
   h+="<div class=card><b style=color:"+col+">"+s.pair+"</b> <span style=font-size:10px;color:#888>"+age+"s</span><br><span style=font-size:32px;font-weight:900;color:"+col+">"+s.score+"</span> 🔄 "+s.dir+" <span style=color:#ff00ff;font-size:11px>ERA "+s.orig+"</span><br>"+s.reason+" - 2 MIN</div>";
  });
  document.getElementById("live").innerHTML=h;
  document.getElementById("queue").innerText="BATCH "+d.batch_idx+"/"+d.total+" | Ora: "+(d.queue.length?d.queue.join(" | "):"carico...");
  document.getElementById("debug").innerText="Tot:"+d.total+" | Scannate:"+d.batch_idx+" | Scan:"+d.scanned+" | Segnali:"+d.signals.length+" | Suono:"+(soundOn?"ON":"OFF");
 }).catch(e=>{});
 fetch("/api/trigger");
}
fastScan(); setInterval(fastScan,8000);
</script></body></html>
'''

@app.route('/api/scan')
def api_scan():
    start_thread()
    return jsonify({"signals":CACHE["signals"],"total":len(ALL_PAIRS),"queue":CACHE["queue"],"batch_idx":CACHE["batch"],"scanned":CACHE["scanned"],"cache_time":CACHE["time"]})

@app.route('/api/trigger')
def trigger():
    if time.time() - CACHE["time"] > 10:
        threading.Thread(target=scan_batch, daemon=True).start()
    return jsonify({"ok":True})

@app.route('/ping')
def ping():
    start_thread()
    return "pong sound fix"

# Avvio per python diretto
if __name__ == "__main__":
    threading.Thread(target=scan_batch, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
