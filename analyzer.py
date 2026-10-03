# Analyzer.py - V123 TUTTI OTC 32 COPPIE - BATCH 4 - ALLARGATO 50/40 - FILE UNICO
from flask import Flask, jsonify
import os, gc, time, threading

app = Flask(__name__)

# TUTTI OTC DI POCKET - 32 COPPIE
ALL_PAIRS = {
    # MAJOR OTC
    "EURUSD OTC": "EURUSD=X",
    "GBPUSD OTC": "GBPUSD=X",
    "USDJPY OTC": "USDJPY=X",
    "AUDUSD OTC": "AUDUSD=X",
    "USDCAD OTC": "USDCAD=X",
    "USDCHF OTC": "USDCHF=X",
    "NZDUSD OTC": "NZDUSD=X",
    # CROSS EUR OTC
    "EURJPY OTC": "EURJPY=X",
    "EURGBP OTC": "EURGBP=X",
    "EURAUD OTC": "EURAUD=X",
    "EURCAD OTC": "EURCAD=X",
    "EURCHF OTC": "EURCHF=X",
    "EURNZD OTC": "EURNZD=X",
    # CROSS GBP OTC
    "GBPJPY OTC": "GBPJPY=X",
    "GBPAUD OTC": "GBPAUD=X",
    "GBPCAD OTC": "GBPCAD=X",
    "GBPCHF OTC": "GBPCHF=X",
    "GBPNZD OTC": "GBPNZD=X",
    # CROSS AUD/NZD/CAD/CHF
    "AUDJPY OTC": "AUDJPY=X",
    "AUDCAD OTC": "AUDCAD=X",
    "AUDCHF OTC": "AUDCHF=X",
    "AUDNZD OTC": "AUDNZD=X",
    "CADJPY OTC": "CADJPY=X",
    "CHFJPY OTC": "CHFJPY=X",
    "NZDJPY OTC": "NZDJPY=X",
    "NZDCAD OTC": "NZDCAD=X",
    # EXOTIC OTC - quelli che pagano bene sabato
    "AED/CNY OTC": "CNY=X",
    "BHD/CNY OTC": "CNY=X",
    "USD/BDT OTC": "BDT=X",
    "USD/EGP OTC": "EGP=X",
    "USD/PKR OTC": "PKR=X",
    "USD/INR OTC": "INR=X",
    # CRYPTO OTC
    "BTC/USD OTC": "BTC-USD",
    "ETH/USD OTC": "ETH-USD",
}

CACHE = {"signals": [], "time": 0, "batch": 0, "scanned": "Mai", "queue": []}
BATCH_SIZE = 4
pairs_list = list(ALL_PAIRS.items())

def calc_rsi(df):
    try:
        closes = df['Close'].tail(15)
        g = l = 0
        for i in range(1, len(closes)):
            diff = float(closes.iloc[i]) - float(closes.iloc[i-1])
            if diff > 0: g += diff
            else: l += abs(diff)
        if l == 0: return 70
        rs = (g/14) / (l/14)
        return 100 - (100/(1+rs))
    except: return 50.0

def scan_batch():
    try:
        import yfinance as yf
        idx = CACHE["batch"] % len(pairs_list)
        batch_pairs = []
        for i in range(BATCH_SIZE):
            pos = (idx + i) % len(pairs_list)
            batch_pairs.append(pairs_list[pos])

        CACHE["queue"] = [p[0] for p in batch_pairs]
        out = CACHE["signals"][:]

        for otc, real in batch_pairs:
            try:
                df = yf.download(real, period="2d", interval="1m", progress=False, auto_adjust=True, threads=False, timeout=6)
                if df is None or len(df) < 20: continue
                try: df.columns = df.columns.get_level_values(0)
                except: pass

                c = float(df.iloc[-1]['Close'])
                o = float(df.iloc[-1]['Open'])
                h = float(df.iloc[-1]['High'])
                lv = float(df.iloc[-1]['Low'])
                rt = h - lv
                if rt <= 0: continue
                body = abs(c - o)
                up = h - max(c, o)
                down = min(c, o) - lv
                rsi = calc_rsi(df)

                orig = None; score = 0; reason = ""
                # ALLARGATO 50/40
                if down > rt*0.65 and body < rt*0.30 and (5 <= rsi <= 65):
                    orig="BUY"; score=90; reason=f"Pin 65% super {int(rsi)}"
                elif up > rt*0.65 and body < rt*0.30 and (35 <= rsi <= 95):
                    orig="SELL"; score=90; reason=f"Pin 65% super {int(rsi)}"
                elif down > rt*0.55 and body < rt*0.35 and (10 <= rsi <= 60):
                    orig="BUY"; score=80; reason=f"Pin 55% {int(rsi)}"
                elif up > rt*0.55 and body < rt*0.35 and (40 <= rsi <= 90):
                    orig="SELL"; score=80; reason=f"Pin 55% {int(rsi)}"
                elif down > rt*0.50 and body < rt*0.40 and (10 <= rsi <= 65):
                    orig="BUY"; score=70; reason=f"Pin 50% largo {int(rsi)}"
                elif up > rt*0.50 and body < rt*0.40 and (35 <= rsi <= 90):
                    orig="SELL"; score=70; reason=f"Pin 50% largo {int(rsi)}"
                else: continue

                final = "SELL" if orig=="BUY" else "BUY"
                out = [s for s in out if s["pair"]!=otc]
                out.append({"pair":otc,"dir":final,"orig":orig,"price":f"{c:.5f}","score":score,"reason":reason,"time":time.time()})
                del df; gc.collect()
            except: gc.collect(); continue

        now = time.time()
        out = [s for s in out if now - s.get("time",now) < 180]
        CACHE["signals"] = sorted(out, key=lambda x: x['score'], reverse=True)[:10]
        CACHE["time"] = now
        CACHE["batch"] = (CACHE["batch"] + BATCH_SIZE) % len(pairs_list)
        CACHE["scanned"] = time.strftime("%H:%M:%S")
        gc.collect()
    except Exception as e:
        CACHE["scanned"] = f"Err {str(e)[:15]}"
        gc.collect()

@app.route('/')
def home():
    return '''
<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V123 TUTTI OTC 32</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:8px}
.btn{padding:18px;border-radius:14px;font-weight:bold;font-size:16px;width:96%;max-width:420px;display:block;margin:8px auto;cursor:pointer;border:none}
.g{background:#00ff88;color:#000}.card{background:#1e1e1e;border-radius:14px;padding:12px;margin:8px auto;max-width:420px;text-align:left;border-left:10px solid #ff00ff}
.on{background:#00ff88;color:#000;padding:10px;border-radius:10px;margin:8px auto;max-width:420px;font-weight:bold}
.batch{background:#222;border:1px solid #555;border-radius:8px;padding:6px;margin:6px auto;max-width:440px;font-size:11px}
</style></head><body>
<h2>🌍 V123 TUTTI OTC - 32 COPPIE</h2>
<div class="on" id="status">32 coppie | 4 alla volta | 0 lag</div>
<div class="batch" id="queue">Carico...</div>
<div style="background:#111;border:1px solid #00ff88;border-radius:8px;padding:6px;margin:6px auto;max-width:440px;font-size:10px">
✅ Major + Cross + Exotic + Crypto OTC<br>✅ 90=65% super | 80=55% | 70=50% largo<br>✅ CONTRARIO GIUSTO 2 MIN | Rotazione 10s
</div>
<div class="btn g" onclick="fastScan()">⚡ SCAN TUTTI OTC (0 sec)</div>
<div id="live">Carico 32 coppie...</div>
<div id="debug" style="color:#888;font-size:11px"></div>
<script>
function fastScan(){
 fetch("/api/scan").then(r=>r.json()).then(d=>{
  let h="";
  if(d.signals.length==0){h="<p style=color:#888>Nessun pin 50/40<br>Ora: "+d.queue.join(", ")+"</p>";}
  d.signals.forEach(s=>{
   let col=s.dir=="BUY"?"#00ff88":"#ff3b3b";
   let age=Math.round(Date.now()/1000 - s.time);
   h+="<div class=card><b style=color:"+col+">"+s.pair+"</b> <span style=font-size:10px;color:#888>"+age+"s</span><br><span style=font-size:32px;font-weight:900;color:"+col+">"+s.score+"</span> 🔄 "+s.dir+" <span style=color:#ff00ff;font-size:11px>ERA "+s.orig+"</span><br>"+s.reason+" - 2 MIN</div>";
  });
  document.getElementById("live").innerHTML=h;
  document.getElementById("queue").innerText="BATCH "+d.batch_idx+"/"+d.total+" | Ora: "+d.queue.join(" | ");
  document.getElementById("debug").innerText="Tot: "+d.total+" | Scannate: "+d.batch_idx*4+" | Scan: "+d.scanned+" | Segnali: "+d.signals.length;
  document.getElementById("status").innerText="🌍 "+d.total+" COPPIE | BATCH "+d.batch_idx+" | "+d.scanned;
 }).catch(e=>{});
 fetch("/api/trigger");
}
fastScan();
setInterval(fastScan, 8000);
</script></body></html>
'''

@app.route('/api/scan')
def api_scan():
    return jsonify({"signals":CACHE["signals"],"total":len(ALL_PAIRS),"queue":CACHE["queue"],"batch_idx":CACHE["batch"],"scanned":CACHE["scanned"],"cache_time":CACHE["time"]})

@app.route('/api/trigger')
def trigger():
    if time.time() - CACHE["time"] > 10:
        threading.Thread(target=scan_batch, daemon=True).start()
    return jsonify({"ok":True})

@app.route('/ping')
def ping(): return "pong 32 otc"

if __name__ == "__main__":
    threading.Thread(target=scan_batch, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
