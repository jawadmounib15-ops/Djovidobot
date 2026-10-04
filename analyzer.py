# Analyzer.py - V135 SCADENZA 5 MIN + ANTI-LAG BATCH 3 + KEEP 10 MIN + DOPPIO LAVORO + STORICO + RSI ZONA
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
    "EURTRY OTC": "EURTRY=X", "USDTRY OTC": "TRY=X", "USD/BRL OTC": "BRL=X",
    "USD/MXN OTC": "MXN=X", "USD/ZAR OTC": "ZAR=X", "USD/SEK OTC": "SEK=X",
    "USD/NOK OTC": "NOK=X", "USD/DKK OTC": "DKK=X", "USD/SGD OTC": "SGD=X",
    "BTC/USD OTC": "BTC-USD", "ETH/USD OTC": "ETH-USD", "USD/INR OTC": "INR=X"
}

CACHE = {"signals": [], "history": [], "time": 0, "batch": 0, "scanned": "Mai", "queue": [], "error": "V135 scadenza 5 min...", "tries": 0}
BATCH_SIZE = 3
pairs_list = list(ALL_PAIRS.items())
EXPIRY_SEC = 300 # 5 MINUTI!

def calc_rsi(df):
    try:
        closes=df['Close'].tail(14); g=l=0
        for i in range(1,len(closes)):
            d=float(closes.iloc[i])-float(closes.iloc[i-1])
            if d>0: g+=d
            else: l+=abs(d)
        if l==0: return 70.0
        return 100-(100/(1+(g/14)/(l/14) if l!=0 else 9))
    except: return 50.0

def get_rsi_zone(rsi):
    if rsi<30: return "🟢 Ipervenduto", "#00ff88"
    elif rsi<45: return "🟡 Venduto", "#ffff00"
    elif rsi<55: return "⚪ Neutro", "#888"
    elif rsi<70: return "🟠 Comprato", "#ffaa00"
    else: return "🔴 Ipercomprato", "#ff3b3b"

def scan_batch_sync():
    CACHE["tries"]+=1
    try:
        import yfinance as yf
        idx=CACHE["batch"]%len(pairs_list)
        batch_pairs=[pairs_list[(idx+i)%len(pairs_list)] for i in range(BATCH_SIZE)]
        CACHE["queue"]=[p[0] for p in batch_pairs]
        out=CACHE["signals"][:]
        hist=CACHE["history"][:]
        for otc,real in batch_pairs:
            try:
                df=yf.download(real, period="2d", interval="1m", progress=False, auto_adjust=True, threads=False, timeout=5)
                if df is None or len(df)<10: continue
                try:
                    if hasattr(df.columns,'get_level_values'): df.columns=df.columns.get_level_values(0)
                except: pass
                c=float(df['Close'].iloc[-1]); o=float(df['Open'].iloc[-1]); h=float(df['High'].iloc[-1]); lv=float(df['Low'].iloc[-1])
                rt=h-lv
                if rt<=0: continue
                body=abs(c-o); up=h-max(c,o); down=min(c,o)-lv; rsi=calc_rsi(df)
                rsi_zone, rsi_color = get_rsi_zone(rsi)
                orig=score=0; reason=""; lavoro=""
                # L1 40/50/60
                if down>rt*0.60 and body<rt*0.35: orig="BUY"; score=90; reason=f"Pin 60% | RSI {int(rsi)} {rsi_zone}"; lavoro="L1"
                elif up>rt*0.60 and body<rt*0.35: orig="SELL"; score=90; reason=f"Pin 60% | RSI {int(rsi)} {rsi_zone}"; lavoro="L1"
                elif down>rt*0.50 and body<rt*0.45: orig="BUY"; score=75; reason=f"Pin 50% | RSI {int(rsi)} {rsi_zone}"; lavoro="L1"
                elif up>rt*0.50 and body<rt*0.45: orig="SELL"; score=75; reason=f"Pin 50% | RSI {int(rsi)} {rsi_zone}"; lavoro="L1"
                elif down>rt*0.40 and body<rt*0.50: orig="BUY"; score=60; reason=f"Pin 40% | RSI {int(rsi)} {rsi_zone}"; lavoro="L1"
                elif up>rt*0.40 and body<rt*0.50: orig="SELL"; score=60; reason=f"Pin 40% | RSI {int(rsi)} {rsi_zone}"; lavoro="L1"
                # L2
                if not orig:
                    if down > body*2.5 and body/rt < 0.35 and down > rt*0.50: orig="BUY"; score=85; reason=f"📌 HAMMER {down/body:.1f}x RSI {int(rsi)} {rsi_zone}"; lavoro="L2"
                    elif up > body*2.5 and body/rt < 0.35 and up > rt*0.50: orig="SELL"; score=85; reason=f"📌 SHOOTING {up/body:.1f}x RSI {int(rsi)} {rsi_zone}"; lavoro="L2"
                    elif down > body*2.0 and body/rt < 0.40 and down > rt*0.45: orig="BUY"; score=65; reason=f"📌 Soft {down/body:.1f}x RSI {int(rsi)} {rsi_zone}"; lavoro="L2"
                    elif up > body*2.0 and body/rt < 0.40 and up > rt*0.45: orig="SELL"; score=65; reason=f"📌 Soft {up/body:.1f}x RSI {int(rsi)} {rsi_zone}"; lavoro="L2"
                if not orig:
                    del df; gc.collect(); continue
                final="SELL" if orig=="BUY" else "BUY"
                out=[s for s in out if s["pair"]!=otc]
                new_sig={"pair":otc,"dir":final,"orig":orig,"price":f"{c:.5f}","score":score,"reason":reason,"time":time.time(),"exp":EXPIRY_SEC,"lavoro":lavoro,"rsi":int(rsi),"rsi_zone":rsi_zone,"rsi_color":rsi_color}
                out.append(new_sig)
                hist.insert(0, {**new_sig, "scanned_at": time.strftime("%H:%M:%S")})
                if len(hist)>50: hist=hist[:50]
                del df; gc.collect()
            except: gc.collect(); continue
        now=time.time()
        active=[s for s in out if now-s["time"]<600] # keep 10 min
        for s in active:
            s["age"]=int(now-s["time"])
            s["is_new"]=s["age"]<60
        CACHE["signals"]=sorted(active,key=lambda x:(x['score'], x['time']),reverse=True)[:20]
        CACHE["history"]=hist
        CACHE["time"]=now; CACHE["batch"]=(CACHE["batch"]+BATCH_SIZE)%len(pairs_list)
        CACHE["scanned"]=time.strftime("%H:%M:%S")
        l1=len([s for s in active if s["lavoro"]=="L1"]); l2=len([s for s in active if s["lavoro"]=="L2"])
        diverse=len(set([s["pair"] for s in active]))
        CACHE["error"]=f"V135 5 MIN SCAD | Batch {BATCH_SIZE} | Diverse {diverse} | L1:{l1} L2:{l2} | Tot {len(active)} | Scan {CACHE['tries']} | Keep 10m | Exp 5m"
        gc.collect()
    except Exception as e:
        CACHE["error"]=f"ERR {str(e)[:50]}"; gc.collect()

scan_batch_sync()

@app.route('/')
def home():
    return f'''
<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V135 5 MIN</title>
<style>
body{{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:8px}}
.btn{{padding:16px;border-radius:14px;font-weight:bold;font-size:15px;width:96%;max-width:440px;display:block;margin:8px auto;cursor:pointer;border:none}}
.g{{background:#00ff88;color:#000}}.y{{background:#ffff00;color:#000}}.b{{background:#00aaff;color:#fff}}
.card{{background:#1e1e1e;border-radius:14px;padding:14px;margin:10px auto;max-width:440px;text-align:left;border-left:12px solid #ff00ff}}
.card.l1{{border-left-color:#00ff88}}.card.l2{{border-left-color:#ffaa00}}
.card.new{{box-shadow:0 0 20px #00ff88;animation:pulse 1s infinite}}.card.old{{opacity:0.6}}
@keyframes pulse{{0%{{box-shadow:0 0 5px #00ff88}}50%{{box-shadow:0 0 20px #00ff88}}100%{{box-shadow:0 0 5px #00ff88}}}}
.on{{background:#00ff88;color:#000;padding:12px;border-radius:10px;margin:8px auto;max-width:440px;font-weight:bold}}
.batch{{background:#222;border:1px solid #555;border-radius:8px;padding:6px;margin:6px auto;max-width:440px;font-size:11px}}
.timer{{font-size:22px;font-weight:900;color:#ffff00;background:#000;padding:6px 12px;border-radius:8px;display:inline-block;margin-top:6px;border:2px solid #ffff00}}
.badge-l1{{background:#00ff88;color:#000;padding:3px 8px;border-radius:8px;font-size:10px;font-weight:900}}
.badge-l2{{background:#ffaa00;color:#000;padding:3px 8px;border-radius:8px;font-size:10px;font-weight:900}}
.badge-new{{background:#00ff88;color:#000;padding:3px 8px;border-radius:10px;font-size:11px;font-weight:900;animation:blink 0.8s infinite}}
@keyframes blink{{0%{{opacity:1}}50%{{opacity:0.3}}100%{{opacity:1}}}}
.rsi-badge{{padding:3px 8px;border-radius:8px;font-size:10px;font-weight:bold;color:#000}}
.hist{{background:#151515;border-radius:10px;padding:8px;margin:8px auto;max-width:440px;text-align:left;border:1px solid #333}}
</style></head><body>
<h2>⏰ V135 SCADENZA 5 MIN</h2>
<div class="on" id="status">5 min scadenza...</div>
<div class="batch" id="queue">...</div>
<div style="background:#111;border-radius:10px;padding:8px;margin:6px auto;max-width:440px;font-size:12px;text-align:center;border:2px solid #ffff00">
⏰ <b>SCADENZA ORA 5 MINUTI</b><br>
Entra entro 1 min | Timer 5:00 → 0:00 | Keep 10 min
</div>
<div style="background:#111;border:1px solid #00ff88;border-radius:8px;padding:6px;margin:6px auto;max-width:440px;font-size:11px" id="error">...</div>
<div class="btn y" id="soundBtn" onclick="enableSound()">🔊 ATTIVA SUONO</div>
<div class="btn g" onclick="forceScan()">🔧 FORZA SCAN 5 MIN</div>
<div class="btn b" onclick="toggleHist()">📚 STORICO 50</div>
<div id="live">...</div>
<div id="history" style="display:none"></div>
<script>
let soundOn=false; let lastCount=0; let audioCtx=null; let signalsData=[]; let histVisible=false;
const EXPIRY={EXPIRY_SEC};
function enableSound(){{try{{audioCtx=new(window.AudioContext||window.webkitAudioContext)(); soundOn=true; document.getElementById("soundBtn").innerText="✅ SUONO ON 5 MIN";}}catch(e){{soundOn=true;}}}}
function beep(f,d){{if(!soundOn||!audioCtx)return;try{{let o=audioCtx.createOscillator(); let g=audioCtx.createGain(); o.connect(g); g.connect(audioCtx.destination); o.frequency.value=f; g.gain.setValueAtTime(0.8,audioCtx.currentTime); g.gain.exponentialRampToValueAtTime(0.01,audioCtx.currentTime+d/1000); o.start(); o.stop(audioCtx.currentTime+d/1000);}}catch(e){{}}}}
function playSignal(d,l){{if(!soundOn)return; if(l=="L2"){{beep(1100,80); setTimeout(()=>beep(1500,250),120);}}else{{if(d=="BUY"){{beep(800,120); setTimeout(()=>beep(1100,220),150);}}else{{beep(500,120); setTimeout(()=>beep(350,280),150);}}}} if(navigator.vibrate)navigator.vibrate([200,100,300]);}}
function forceScan(){{document.getElementById("status").innerText="⏳ Scan 3 coppie..."; fetch("/api/force").then(r=>r.json()).then(d=>{{fastScan();}});}}
function toggleHist(){{histVisible=!histVisible; document.getElementById("history").style.display=histVisible?"block":"none";}}
function updateTimers(){{let now=Date.now()/1000; signalsData.forEach((s,i)=>{{let el=document.getElementById("timer-"+i); if(!el)return; let age=Math.floor(now-s.time); let left=s.exp-age; if(left<=0){{el.innerText="⛔ SCADUTO "+age+"s fa | 5 MIN FINITI"; el.style.color="#ff3b3b"; el.style.borderColor="#ff3b3b";}}else{{let m=Math.floor(left/60); let sec=left%60; el.innerText="⏰ "+m+":"+String(sec).padStart(2,'0')+" | "+(s.is_new?"🔥 NUOVO "+age+"s":"🕐 "+age+"s")+" | SCAD 5 MIN | RSI "+s.rsi; if(left<60){{el.style.color="#ffaa00";}}}}}});}}
function fastScan(){{fetch("/api/scan").then(r=>r.json()).then(d=>{{
 signalsData=d.signals; let h=""; if(d.signals.length==0){{h="<p style=color:#888>Nessun pin in batch "+d.queue.join(", ")+"<br>Keep 10 min accumula - scadenza 5 min</p>";}}
 if(d.signals.length>lastCount && lastCount!=0){{playSignal(d.signals[0].dir,d.signals[0].lavoro);}} lastCount=d.signals.length;
 let pairs={{}}; d.signals.forEach(s=>pairs[s.pair]=1);
 h="<p style=color:#00ff88;font-size:12px>Coppie diverse: "+Object.keys(pairs).length+" | Scadenza 5 MIN | Keep 10 min</p>"+h;
 d.signals.forEach((s,i)=>{{
  let col=s.dir=="BUY"?"#00ff88":"#ff3b3b"; let badge=s.score>=85?"#00ff88":s.score>=75?"#ffff00":"#ffaa00";
  let age=Math.round(Date.now()/1000-s.time); let isNew=age<60; let cardClass="card "+(s.lavoro=="L1"?"l1":"l2")+(isNew?" new":"");
  let badgeLavoro=s.lavoro=="L1"?'<span class=badge-l1>L1 '+s.score+'</span>':'<span class=badge-l2>📌 L2 '+s.score+'</span>';
  let badgeAge=isNew?'<span class=badge-new>🔥 NUOVO '+age+'s</span>':'<span style=background:#555;color:#aaa;padding:2px 6px;border-radius:8px;font-size:10px>🕐 '+age+'s</span>';
  h+="<div class='"+cardClass+"'><b style=color:"+col+">"+s.pair+"</b> "+badgeLavoro+" "+badgeAge+" <span style=background:"+badge+";color:#000;padding:2px 6px;border-radius:4px>"+s.score+"</span><br><span style=font-size:32px;font-weight:900;color:"+col+">"+s.dir+"</span> <span style=color:#ff00ff;font-size:12px>ERA "+s.orig+"</span><br><span style=font-size:12px>"+s.reason+"</span><br><span class=rsi-badge style=background:"+(s.rsi_color||"#888")+">RSI "+s.rsi+" "+s.rsi_zone+"</span><br><div class=timer id=timer-"+i+">⏰ 5:00 | SCAD 5 MIN</div><div style=font-size:10px;color:"+(isNew?"#00ff88":"#888")+";margin-top:4px>"+(isNew?"✅ ENTRA ORA! Scad 5 min":"⚠️ "+age+"s fa - ancora "+(300-age)+"s")+" | Keep 10 min</div></div>";
 }});
 document.getElementById("live").innerHTML=h;
 let histHtml="<div class=hist><b>📚 STORICO 50 - SCAD 5 MIN</b><br>"; let seen={{}}; d.history.forEach(it=>{{seen[it.pair]=(seen[it.pair]||0)+1;}}); histHtml+="<div style=font-size:11px;color:#00ff88>Diverse: "+Object.keys(seen).length+" coppie</div><br>";
 d.history.forEach(item=>{{let col=item.dir=="BUY"?"#00ff88":"#ff3b3b"; let bl=item.lavoro=="L1"?'<span class=badge-l1>L1</span>':'<span class=badge-l2>L2</span>'; histHtml+="<div style=font-size:11px;padding:4px;border-bottom:1px solid #222;display:flex;justify-content:space-between><span>"+bl+" <b style=color:"+col+">"+item.pair+"</b> "+item.dir+" "+item.score+"</span><span>RSI"+item.rsi+" "+item.scanned_at+"</span></div>";}}); histHtml+="</div>"; document.getElementById("history").innerHTML=histHtml;
 document.getElementById("queue").innerText="Batch: "+d.queue.join(" | ")+" | Prossimo 10 sec";
 document.getElementById("error").innerText=d.error;
 document.getElementById("status").innerText=(d.signals.length? "⏰ "+d.signals.length+" | "+Object.keys(pairs).length+" diverse | SCAD 5 MIN | ":"⏳ ")+d.scanned;
}}).catch(e=>{{}}); fetch("/api/trigger");}}
fastScan(); setInterval(fastScan,10000); setInterval(updateTimers,1000);
</script></body></html>
'''

@app.route('/api/scan')
def api_scan():
    diverse=len(set([s["pair"] for s in CACHE["signals"]]))
    return jsonify({"signals":CACHE["signals"],"queue":CACHE["queue"],"scanned":CACHE["scanned"],"error":CACHE["error"],"tries":CACHE["tries"],"history":CACHE["history"],"diverse":diverse})

@app.route('/api/force')
def api_force():
    threading.Thread(target=scan_batch_sync, daemon=True).start()
    return jsonify({"ok":True})

@app.route('/api/trigger')
def trigger():
    if time.time() - CACHE["time"] > 12:
        threading.Thread(target=scan_batch_sync, daemon=True).start()
    return jsonify({"ok":True})

@app.route('/ping')
def ping(): return "pong v135 5min"
if __name__ == "__main__":
    scan_batch_sync()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
