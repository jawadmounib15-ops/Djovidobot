# Analyzer.py - V132 COMPLETO - DOPPIO LAVORO + STORICO + SCADENZA + RSI ZONA + SUONO - 37 COPPIE
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

CACHE = {"signals": [], "history": [], "time": 0, "batch": 0, "scanned": "Mai", "queue": [], "error": "V132 Completo avvio...", "tries": 0}
BATCH_SIZE = 4
pairs_list = list(ALL_PAIRS.items())

def calc_rsi(df):
    try:
        closes=df['Close'].tail(14); g=l=0
        for i in range(1,len(closes)):
            d=float(closes.iloc[i])-float(closes.iloc[i-1])
            if d>0: g+=d
            else: l+=abs(d)
        if l==0: return 70.0
        rs=(g/14)/(l/14) if l!=0 else 9
        return 100-(100/(1+rs))
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
                df=yf.download(real, period="2d", interval="1m", progress=False, auto_adjust=True, threads=False, timeout=8)
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

                # ========== LAVORO 1: LARGO 40/50/60 ==========
                if down>rt*0.60 and body<rt*0.35:
                    orig="BUY"; score=90; reason=f"Pin 60% | RSI {int(rsi)} {rsi_zone}"; lavoro="L1"
                elif up>rt*0.60 and body<rt*0.35:
                    orig="SELL"; score=90; reason=f"Pin 60% | RSI {int(rsi)} {rsi_zone}"; lavoro="L1"
                elif down>rt*0.50 and body<rt*0.45:
                    orig="BUY"; score=75; reason=f"Pin 50% | RSI {int(rsi)} {rsi_zone}"; lavoro="L1"
                elif up>rt*0.50 and body<rt*0.45:
                    orig="SELL"; score=75; reason=f"Pin 50% | RSI {int(rsi)} {rsi_zone}"; lavoro="L1"
                elif down>rt*0.40 and body<rt*0.50:
                    orig="BUY"; score=60; reason=f"Pin 40% LARGO | RSI {int(rsi)} {rsi_zone}"; lavoro="L1"
                elif up>rt*0.40 and body<rt*0.50:
                    orig="SELL"; score=60; reason=f"Pin 40% LARGO | RSI {int(rsi)} {rsi_zone}"; lavoro="L1"

                # ========== LAVORO 2: PINBAR CLASSICA COME SCREENSHOT USDCHF ==========
                if not orig:
                    body_ratio = body / rt if rt>0 else 1
                    wick_mult = (down/body) if body>0.00001 else 10
                    if down > body*2.5 and body_ratio < 0.35 and down > rt*0.50:
                        orig="BUY"; score=85; reason=f"📌 HAMMER {wick_mult:.1f}x | RSI {int(rsi)} {rsi_zone} | Come screenshot"; lavoro="L2"
                    elif up > body*2.5 and body_ratio < 0.35 and up > rt*0.50:
                        orig="SELL"; score=85; reason=f"📌 SHOOTING {up/body:.1f}x | RSI {int(rsi)} {rsi_zone}"; lavoro="L2"
                    elif down > body*2.0 and body_ratio < 0.40 and down > rt*0.45:
                        orig="BUY"; score=65; reason=f"📌 Soft Hammer {wick_mult:.1f}x | RSI {int(rsi)} {rsi_zone}"; lavoro="L2"
                    elif up > body*2.0 and body_ratio < 0.40 and up > rt*0.45:
                        orig="SELL"; score=65; reason=f"📌 Soft Shooting {up/body:.1f}x | RSI {int(rsi)} {rsi_zone}"; lavoro="L2"

                if not orig: continue

                final="SELL" if orig=="BUY" else "BUY"
                out=[s for s in out if s["pair"]!=otc]
                new_sig={"pair":otc,"dir":final,"orig":orig,"price":f"{c:.5f}","score":score,"reason":reason,"time":time.time(),"exp":120,"lavoro":lavoro,"rsi":int(rsi),"rsi_zone":rsi_zone,"rsi_color":rsi_color}
                out.append(new_sig)
                hist.insert(0, {**new_sig, "scanned_at": time.strftime("%H:%M:%S")})
                if len(hist)>40: hist=hist[:40]
                del df; gc.collect()
            except Exception as e:
                gc.collect(); continue
        now=time.time()
        active=[s for s in out if now-s["time"]<300]
        for s in active:
            age=now-s["time"]
            s["age"]=int(age)
            s["is_new"]=age<60
        CACHE["signals"]=sorted(active,key=lambda x:(x['score'], x['time']),reverse=True)[:15]
        CACHE["history"]=hist
        CACHE["time"]=now; CACHE["batch"]=(CACHE["batch"]+BATCH_SIZE)%len(pairs_list)
        CACHE["scanned"]=time.strftime("%H:%M:%S")
        l1=len([s for s in active if s["lavoro"]=="L1"]); l2=len([s for s in active if s["lavoro"]=="L2"])
        CACHE["error"]=f"V132 COMPLETO | L1:{l1} L2:{l2} | Tot {len(active)} | Scan {CACHE['tries']} | 37 coppie"
        gc.collect()
    except Exception as e:
        CACHE["error"]=f"ERR {str(e)[:60]}"; gc.collect()

scan_batch_sync()

@app.route('/')
def home():
    return '''
<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V132 COMPLETO</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:8px}
.btn{padding:16px;border-radius:14px;font-weight:bold;font-size:15px;width:96%;max-width:440px;display:block;margin:8px auto;cursor:pointer;border:none}
.g{background:#00ff88;color:#000}.y{background:#ffff00;color:#000}.b{background:#00aaff;color:#fff}
.card{background:#1e1e1e;border-radius:14px;padding:14px;margin:10px auto;max-width:440px;text-align:left;border-left:12px solid #ff00ff;position:relative}
.card.l1{border-left-color:#00ff88}.card.l2{border-left-color:#ffaa00;box-shadow:0 0 10px #ffaa0055}
.card.new{box-shadow:0 0 20px #00ff88;animation:pulse 1.2s infinite}
.card.old{opacity:0.65}
@keyframes pulse{0%{box-shadow:0 0 5px #00ff88}50%{box-shadow:0 0 25px #00ff88}100%{box-shadow:0 0 5px #00ff88}}
.on{background:#00ff88;color:#000;padding:12px;border-radius:10px;margin:8px auto;max-width:440px;font-weight:bold;font-size:17px}
.batch{background:#222;border:1px solid #555;border-radius:8px;padding:6px;margin:6px auto;max-width:440px;font-size:11px;word-break:break-word}
.timer{font-size:20px;font-weight:900;color:#ffff00;background:#000;padding:5px 10px;border-radius:8px;display:inline-block;margin-top:6px;border:2px solid #ffff00}
.badge-l1{background:#00ff88;color:#000;padding:3px 8px;border-radius:8px;font-size:10px;font-weight:900}
.badge-l2{background:#ffaa00;color:#000;padding:3px 8px;border-radius:8px;font-size:10px;font-weight:900}
.badge-new{background:#00ff88;color:#000;padding:3px 8px;border-radius:10px;font-size:11px;font-weight:900;animation:blink 0.8s infinite}
.badge-old{background:#555;color:#aaa;padding:3px 8px;border-radius:10px;font-size:10px}
.badge-recent{background:#ffff00;color:#000;padding:3px 8px;border-radius:10px;font-size:11px;font-weight:bold}
.rsi-badge{padding:3px 8px;border-radius:8px;font-size:10px;font-weight:bold;color:#000;display:inline-block}
@keyframes blink{0%{opacity:1}50%{opacity:0.3}100%{opacity:1}}
.hist{background:#151515;border-radius:10px;padding:8px;margin:8px auto;max-width:440px;text-align:left;border:1px solid #333}
</style></head><body>
<h2>📌 V132 COMPLETO - TUTTO INCLUSO</h2>
<div class="on" id="status">Carico...</div>
<div class="batch" id="queue">...</div>
<div style="background:#111;border-radius:10px;padding:8px;margin:6px auto;max-width:440px;font-size:11px;text-align:left;border:1px solid #333">
<b>DOPPIO LAVORO SEPARATO:</b><br>
<span class=badge-l1>L1</span> Largo 40/50/60 - attuale<br>
<span class=badge-l2>L2</span> 📌 Pinbar classica come screenshot USD/CHF (stoppino 2.5x body)<br>
<b>Se L1 non trova → cerca L2</b><br><br>
<b>RSI ZONA:</b><br>
<span style=background:#00ff88;color:#000;padding:2px 6px;border-radius:4px>🟢 <30 Ipervenduto</span> perfetto BUY<br>
<span style=background:#ffff00;color:#000;padding:2px 6px;border-radius:4px>🟡 30-45 Venduto</span> buono BUY<br>
<span style=background:#888;color:#fff;padding:2px 6px;border-radius:4px>⚪ 45-55 Neutro</span><br>
<span style=background:#ffaa00;color:#000;padding:2px 6px;border-radius:4px>🟠 55-70 Comprato</span> buono SELL<br>
<span style=background:#ff3b3b;color:#fff;padding:2px 6px;border-radius:4px>🔴 >70 Ipercomprato</span> perfetto SELL
</div>
<div style="background:#111;border:1px solid #00ff88;border-radius:8px;padding:6px;margin:6px auto;max-width:440px;font-size:11px" id="error">...</div>
<div class="btn y" id="soundBtn" onclick="enableSound()">🔊 ATTIVA SUONO (diverso L1/L2)</div>
<div class="btn g" onclick="forceScan()">🔧 FORZA SCAN DOPPIO</div>
<div class="btn b" onclick="toggleHist()">📚 STORICO 40 ULTIMI</div>
<div id="live">Avvio V132...</div>
<div id="history" style="display:none"></div>
<div id="debug" style="color:#666;font-size:11px;margin-top:10px"></div>
<script>
let soundOn=false; let lastCount=0; let audioCtx=null; let signalsData=[]; let histVisible=false;
function enableSound(){try{audioCtx=new(window.AudioContext||window.webkitAudioContext)(); soundOn=true; document.getElementById("soundBtn").innerText="✅ SUONO ON - L1 beep normale L2 beep acuto"; let o=audioCtx.createOscillator(); let g=audioCtx.createGain(); o.connect(g); g.connect(audioCtx.destination); o.frequency.value=900; g.gain.setValueAtTime(0.5,audioCtx.currentTime); o.start(); o.stop(audioCtx.currentTime+0.3);}catch(e){soundOn=true;}}
function beep(f,d){if(!soundOn||!audioCtx)return;try{let o=audioCtx.createOscillator(); let g=audioCtx.createGain(); o.connect(g); g.connect(audioCtx.destination); o.frequency.value=f; g.gain.setValueAtTime(0.8,audioCtx.currentTime); g.gain.exponentialRampToValueAtTime(0.01,audioCtx.currentTime+d/1000); o.start(); o.stop(audioCtx.currentTime+d/1000);}catch(e){}}
function playSignal(dir,lavoro){if(!soundOn)return; if(lavoro=="L2"){beep(1100,80); setTimeout(()=>beep(1500,250),120); setTimeout(()=>beep(1800,200),300);}else{if(dir=="BUY"){beep(800,120); setTimeout(()=>beep(1100,220),150);}else{beep(500,120); setTimeout(()=>beep(350,280),150);}} if(navigator.vibrate)navigator.vibrate(lavoro=="L2"?[100,50,100,50,300]:[200,100,300]); document.body.style.background=lavoro=="L2"?"#ffaa00":"#00ff88"; setTimeout(()=>document.body.style.background="#0a0a0a",500);}
function forceScan(){document.getElementById("status").innerText="⏳ SCAN DOPPIO 8 sec..."; fetch("/api/force").then(r=>r.json()).then(d=>{fastScan();});}
function toggleHist(){histVisible=!histVisible; document.getElementById("history").style.display=histVisible?"block":"none";}
function updateTimers(){let now=Date.now()/1000; signalsData.forEach((s,i)=>{let el=document.getElementById("timer-"+i); if(!el)return; let age=Math.floor(now-s.time); let left=s.exp-age; if(left<=0){el.innerText="⛔ SCADUTO "+age+"s fa | RSI "+s.rsi+" "+s.rsi_zone; el.style.color="#ff3b3b"; el.style.borderColor="#ff3b3b";} else{let m=Math.floor(left/60); let sec=left%60; el.innerText="⏰ "+m+":"+String(sec).padStart(2,'0')+" | "+(s.is_new?"🔥 NUOVO "+age+"s":"🕐 "+age+"s")+" | RSI "+s.rsi;}});}
function fastScan(){fetch("/api/scan").then(r=>r.json()).then(d=>{
 signalsData=d.signals; let h=""; if(d.signals.length==0){h="<p style=color:#888>Nessun L1/L2 in questo batch<br>Batch: "+d.queue.join(", ")+"<br>Clicca FORZA SCAN</p>";}
 if(d.signals.length>lastCount && lastCount!=0 && d.signals[0]){playSignal(d.signals[0].dir,d.signals[0].lavoro);} lastCount=d.signals.length;
 d.signals.forEach((s,i)=>{
  let col=s.dir=="BUY"?"#00ff88":"#ff3b3b"; let badge=s.score>=85?"#00ff88":s.score>=75?"#ffff00":"#ffaa00";
  let age=Math.round(Date.now()/1000-s.time); let isNew=age<60; let isRecent=age<120;
  let cardClass="card "+(s.lavoro=="L1"?"l1":"l2")+(isNew?" new":age>120?" old":"");
  let badgeLavoro=s.lavoro=="L1"?'<span class=badge-l1>L1 '+s.score+'</span>':'<span class=badge-l2>📌 L2 '+s.score+'</span>';
  let badgeAge=isNew?'<span class=badge-new>🔥 NUOVO '+age+'s</span>':isRecent?'<span class=badge-recent>⚡ '+age+'s</span>':'<span class=badge-old>🕐 VECCHIO '+age+'s</span>';
  let rsiBg=s.rsi_color||"#888";
  h+="<div class='"+cardClass+"'><b style=color:"+col+">"+s.pair+"</b> "+badgeLavoro+" "+badgeAge+" <span style=background:"+badge+";color:#000;padding:2px 6px;border-radius:4px>"+s.score+"</span><br><span style=font-size:32px;font-weight:900;color:"+col+">"+s.dir+"</span> <span style=color:#ff00ff;font-size:12px>ERA "+s.orig+"</span><br><span style=font-size:12px>"+s.reason+"</span><br><span class=rsi-badge style=background:"+rsiBg+">RSI "+s.rsi+" "+s.rsi_zone+"</span><br><div class=timer id=timer-"+i+">⏰ 2:00 | RSI "+s.rsi+"</div><div style=font-size:10px;color:"+(isNew?"#00ff88":"#888")+";margin-top:4px>"+(isNew?"✅ ENTRA ORA! 2 MIN":isRecent?"⚠️ Ancora buono":"⛔ VECCHIO - aspetta nuovo")+" | Scad 2 min | "+(s.lavoro=="L2"?"📌 Come screenshot USD/CHF":"L1 largo")+"</div></div>";
 });
 document.getElementById("live").innerHTML=h;
 let histHtml="<div class=hist><b>📚 STORICO 40 ULTIMI - L1/L2 + RSI ZONA</b><br>"; d.history.forEach(item=>{let col=item.dir=="BUY"?"#00ff88":"#ff3b3b"; let bl=item.lavoro=="L1"?'<span class=badge-l1>L1</span>':'<span class=badge-l2>L2</span>'; let rsiC=item.rsi_color||"#555"; histHtml+="<div style=font-size:11px;padding:5px;border-bottom:1px solid #222;display:flex;justify-content:space-between;flex-wrap:wrap><span>"+bl+" <b style=color:"+col+">"+item.pair+"</b> "+item.dir+" "+item.score+" <span style=background:"+rsiC+";color:#000;padding:1px 4px;border-radius:3px;font-size:9px>RSI"+item.rsi+"</span></span><span>"+item.scanned_at+" "+(item.rsi_zone||"")+"</span></div>";}); histHtml+="</div>"; document.getElementById("history").innerHTML=histHtml;
 document.getElementById("queue").innerText="BATCH "+d.batch_idx+"/"+d.total+" | "+d.queue.join(" | ");
 document.getElementById("error").innerText=d.error;
 document.getElementById("debug").innerText="Tot:"+d.total+" Batch:"+d.batch_idx+" Scan:"+d.scanned+" Attivi:"+d.signals.length+" Storico:"+d.history.length+" | Tries:"+d.tries;
 let newCount=d.signals.filter(s=>Date.now()/1000-s.time<60).length;
 document.getElementById("status").innerText=(d.signals.length? "📌 "+d.signals.length+" SEGNALI ("+d.signals.filter(s=>s.lavoro=="L1").length+" L1 + "+d.signals.filter(s=>s.lavoro=="L2").length+" L2) | "+newCount+" NUOVI | ":"⏳ Nessun segnale | ")+d.scanned;
}).catch(e=>{document.getElementById("live").innerText="Errore "+e;}); fetch("/api/trigger");}
fastScan(); setInterval(fastScan,7000); setInterval(updateTimers,1000);
</script></body></html>
'''

@app.route('/api/scan')
def api_scan(): return jsonify({"signals":CACHE["signals"],"total":len(ALL_PAIRS),"queue":CACHE["queue"],"batch_idx":CACHE["batch"],"scanned":CACHE["scanned"],"error":CACHE["error"],"tries":CACHE["tries"],"history":CACHE["history"]})
@app.route('/api/force')
def api_force(): scan_batch_sync(); return jsonify({"ok":True})
@app.route('/api/trigger')
def trigger():
    if time.time() - CACHE["time"] > 10:
        threading.Thread(target=scan_batch_sync, daemon=True).start()
    return jsonify({"ok":True})
@app.route('/ping')
def ping(): return "pong v132 completo"
if __name__ == "__main__":
    scan_batch_sync()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
