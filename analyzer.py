# V109 MEGA LARGO 40/50 - PRENDE TUTTO - 60 COPPIE + FIX BLANK
from flask import Flask, jsonify
import os, gc
app = Flask(__name__)

OTC_MAP = {
    "EURUSD OTC":"EURUSD=X", "EURUSD-OTC":"EURUSD=X", "GBPUSD OTC":"GBPUSD=X", "GBPUSD-OTC":"GBPUSD=X",
    "USDJPY OTC":"USDJPY=X", "USDJPY-OTC":"USDJPY=X", "AUDUSD OTC":"AUDUSD=X", "AUDUSD-OTC":"AUDUSD=X",
    "USDCAD OTC":"USDCAD=X", "USDCHF OTC":"USDCHF=X", "NZDUSD OTC":"NZDUSD=X",
    "EURGBP OTC":"EURGBP=X", "EURJPY OTC":"EURJPY=X", "EURCHF OTC":"EURCHF=X",
    "EURAUD OTC":"EURAUD=X", "EURCAD OTC":"EURCAD=X", "GBPJPY OTC":"GBPJPY=X",
    "GBPCHF OTC":"GBPCHF=X", "GBPAUD OTC":"GBPAUD=X", "AUDJPY OTC":"AUDJPY=X",
    "AUDCHF OTC":"AUDCHF=X", "AUDCAD OTC":"AUDCAD=X", "CADJPY OTC":"CADJPY=X",
    "CHFJPY OTC":"CHFJPY=X", "NZDJPY OTC":"NZDJPY=X",
    "AED/CNY OTC":"CNY=X", "AEDCNY OTC":"CNY=X", "BHD/CNY OTC":"CNY=X", "BHDCNY OTC":"CNY=X",
    "SAR/CNY OTC":"CNY=X", "QAR/CNY OTC":"CNY=X",
    "USD/BDT OTC":"BDT=X", "USD/EGP OTC":"EGP=X", "USD/PKR OTC":"PKR=X",
    "USD/INR OTC":"INR=X", "USD/BRL OTC":"BRL=X", "USD/MXN OTC":"MXN=X",
    "USD/TRY OTC":"TRY=X", "EUR/TRY OTC":"TRY=X",
    "BTC/USD OTC":"BTC-USD", "BTC-OTC":"BTC-USD", "ETH/USD OTC":"ETH-USD", "ETH-OTC":"ETH-USD",
    "SOL/USD OTC":"SOL-USD", "Gold OTC":"GC=F"
}

def calc_rsi(series, period=14):
    try:
        delta=series.diff(); gain=(delta.where(delta>0,0)).rolling(window=period).mean()
        loss=(-delta.where(delta<0,0)).rolling(window=period).mean()
        if float(loss.iloc[-1])==0: return 50.0
        rs=gain/loss; rsi=100-(100/(1+rs)); v=float(rsi.iloc[-1])
        return v if str(v)!='nan' else 50.0
    except: return 50.0

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V109 MEGA LARGO</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:8px}
.btn{padding:20px;border-radius:16px;font-weight:bold;font-size:18px;width:98%;max-width:440px;display:block;margin:8px auto;cursor:pointer}
.g{background:#00ff88;color:#000;border:3px solid #00ff88}.d{background:#222;color:#fff;border:2px solid #555}
.card{background:#1e1e1e;border-radius:20px;padding:16px;margin:10px auto;max-width:460px;text-align:left;border-left:10px solid #00ff88;position:relative}
.sell{border-left-color:#ff3b3b}.perf{border:2px solid gold;box-shadow:0 0 12px gold}
.score{font-size:48px;font-weight:900}.badge{position:absolute;top:12px;right:12px;text-align:right}
.prepara{background:#00ff88;color:#000;font-weight:bold;padding:12px;border-radius:10px;margin-top:10px;text-align:center}
.sellbg{background:#ff3b3b;color:#fff}
.warn40{background:#ffcc00;color:#000;font-weight:900;padding:14px;border-radius:12px;margin:10px auto;max-width:460px;animation:blink 0.5s infinite}
@keyframes blink{0%,50%{opacity:1}51%,100%{opacity:0.6}}
.storico{background:#111;border:1px solid #333;border-radius:12px;padding:12px;margin:14px auto;max-width:460px;text-align:left;font-size:12px}
.tag{font-size:10px;padding:3px 6px;border-radius:6px;font-weight:bold;margin-top:4px;display:inline-block}
.tag-rsi{background:#00ff88;color:#000}.tag-perf{background:gold;color:#000}.tag-easy{background:#00ccff;color:#000}.tag-mega{background:#ff00ff;color:#fff}
#s{padding:12px;border-radius:8px;margin:8px auto;max-width:440px;font-weight:bold}
.on{background:#00ff88;color:#000}.off{background:#ff3b3b;color:#fff}
</style></head><body>
<h2>✅ V109 MEGA LARGO 40/50</h2>
<div id="s" class="off">🔇 ATTIVA SUONO</div>
<div class="btn g" onclick="att()">🔔 ATTIVA SUONO + 40 SEC</div>
<div class="btn d" onclick="scan()">🔍 SCAN MEGA LARGO</div>
<p id="info">V109: 40/50 + 45/50 + 50/45 + 60/35 + 70/25 - PRENDE TUTTO</p>
<div id="warn40box"></div><div id="live"></div><div id="debug" style="color:#888;font-size:11px"></div>
<div class="storico"><b>📜 STORICO:</b><div id="storico">Vuoto</div><div style="margin-top:6px"><span onclick="clearStor()" style="color:#ff3b3b;cursor:pointer">🗑️ Pulisci</span> | <span onclick="testSuono()" style="color:#00ff88;cursor:pointer">🔊 Test suono</span> | <span onclick="test40()" style="color:#ffcc00;cursor:pointer">⏰ Test 40sec</span></div></div>
<script>
let ctx=null,ok=false,expMin=2,warned40=false;
let stor=JSON.parse(localStorage.getItem('v109_stor')||'[]');
function updStor(){let h=''; stor.slice(0,30).forEach(s=>{h+=`<div>${s}</div>`}); document.getElementById('storico').innerHTML=h||'Vuoto';}
updStor();
function clearStor(){stor=[]; localStorage.setItem('v109_stor',JSON.stringify(stor)); updStor();}
function att(){try{ctx=new (window.AudioContext||window.webkitAudioContext)(); ctx.resume().then(()=>{ok=true; document.getElementById('s').className='on'; document.getElementById('s').innerText='🔊 ON MEGA LARGO'; beep(900,0.4); setTimeout(()=>beep(1300,0.5),300); if(navigator.vibrate) navigator.vibrate([300,100,300]); if(Notification && Notification.permission!=='granted') Notification.requestPermission(); scan();});}catch(e){}}
function beep(f,d){if(!ctx) return; try{let o=ctx.createOscillator(),g=ctx.createGain(); o.type='square'; o.frequency.value=f; o.connect(g); g.connect(ctx.destination); g.gain.setValueAtTime(1,ctx.currentTime); g.gain.exponentialRampToValueAtTime(0.01,ctx.currentTime+d); o.start(); o.stop(ctx.currentTime+d);}catch(e){}}
function suonaSegnale(){if(!ok) return; beep(1100,0.6); setTimeout(()=>beep(1500,0.6),400); if(navigator.vibrate) navigator.vibrate([400,100,600]);}
function avviso40(){if(!ok) return; if(ctx && ctx.state=='suspended') ctx.resume(); beep(1000,0.5); setTimeout(()=>beep(1000,0.5),400); setTimeout(()=>beep(1500,0.6),800); setTimeout(()=>beep(2000,0.8),1300); if(navigator.vibrate) navigator.vibrate([800,200,1000]); if(Notification && Notification.permission==='granted') new Notification('⏰ 40 SEC MEGA', {body: cur.length+' segnali'}); document.getElementById('warn40box').innerHTML='<div class="warn40">⏰ 40 SEC - PREPARA 2 MIN!! ⏰</div>'; setTimeout(()=>{document.getElementById('warn40box').innerHTML='';},12000);}
function testSuono(){if(!ok){alert('Attiva prima'); return;} suonaSegnale();}
function test40(){if(!ok){alert('Attiva prima'); return;} avviso40();}
let cur=[],ent=0; function getN(){let n=new Date(); let nx=new Date(n); nx.setSeconds(0,0); nx.setMilliseconds(0); nx.setMinutes(n.getMinutes()+1); return nx;}
function scan(){document.getElementById('info').innerText='⏳ Scan MEGA LARGO...'; fetch('/api/scan').then(r=>r.json()).then(d=>{cur=d.signals; ent=getN().getTime(); warned40=false; document.getElementById('debug').innerText=`${d.total} coppie | ${d.signals.length} segnali | ${d.debug}`; if(d.signals.length>0){suonaSegnale(); let now=new Date().toLocaleTimeString('it-IT'); d.signals.forEach(s=>{stor.unshift(`${now} - ${s.score}/100 ${s.dir} ${s.pair} RSI${s.rsi} ${s.tag}`);}); localStorage.setItem('v109_stor',JSON.stringify(stor.slice(0,50))); updStor();} render();}).catch(e=>{document.getElementById('info').innerText='Errore';});}
function render(){let now=Date.now(); let diff=Math.ceil((ent-now)/1000); let tot=expMin*60; let h=''; if(cur.length>0){if(diff>40) document.getElementById('info').innerText=`✅ ${cur.length} segnali MEGA LARGO`; else if(diff<=40 && diff>0 && !warned40){ avviso40(); warned40=true; } } cur.forEach(s=>{let col=s.dir=='BUY'?'#00ff88':'#ff3b3b'; let left=Math.max(0,tot+diff); let txt=diff>40?`AVVISO TRA ${diff-40}s` : diff>0?`⏰ ENTRA TRA ${diff}s` : `SCAD ${left}s`; let perfClass=s.tag.includes('PERFETTA')?'perf':''; h+=`<div class="card ${s.dir=='SELL'?'sell':''} ${perfClass}"><div class="badge"><div class="score" style="color:${col}">${s.score}/100</div><div style="color:${col};font-weight:900">${s.dir}</div><div style="font-size:11px">RSI ${s.rsi}</div><div style="font-size:10px">${s.pct}%</div><div class="tag ${s.tag.includes('PERFETTA')?'tag-perf': s.tag.includes('MEGA')?'tag-mega': s.tag.includes('FACILE')?'tag-easy':'tag-rsi'}">${s.tag}</div></div><div style="width:58%"><b style="color:${col}">${s.pair}</b><br><span style="color:#aaa;font-size:11px">${s.reason}</span><br><span style="font-size:12px">${s.price}</span></div><div class="prepara ${s.dir=='SELL'?'sellbg':''}">${txt}</div></div>`;}); document.getElementById('live').innerHTML=h||`Nessun segnale - ma con 40/50 dovrebbe dare sempre`;}
setInterval(render,1000); setInterval(scan,15000);
</script></body></html>"""

@app.route('/api/scan')
def api():
    try:
        import yfinance as yf, pandas as pd
    except:
        return jsonify({"signals":[],"debug":"no yf","total":0})
    out=[]; total=0
    for otc, real in OTC_MAP.items():
        total+=1
        try:
            df=yf.download(real, period="5d", interval="1m", progress=False, auto_adjust=True, threads=False)
            if df is None or len(df)<20: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
            c=float(df.iloc[-1]['Close']); o=float(df.iloc[-1]['Open']); h=float(df.iloc[-1]['High']); l=float(df.iloc[-1]['Low'])
            rt=h-l
            if rt<=0: continue
            body=abs(c-o); up=h-max(c,o); down=min(c,o)-l
            rsi=calc_rsi(df['Close'])
            pct_up=int((up/rt)*100); pct_down=int((down/rt)*100); body_pct=int((body/rt)*100)
            dire=None; score=0; tag=""; reason=""; pct=0
            
            # MEGA LARGO - PRENDE QUASI TUTTO
            cond_mega_bull = (down > rt*0.40) and (body < rt*0.50)
            cond_mega_bear = (up > rt*0.40) and (body < rt*0.50)
            cond_mega2_bull = (down > rt*0.45) and (body < rt*0.50)
            cond_mega2_bear = (up > rt*0.45) and (body < rt*0.50)
            cond_easy_bull = (down > rt*0.50) and (body < rt*0.45)
            cond_easy_bear = (up > rt*0.50) and (body < rt*0.45)
            cond_base_bull = (down > rt*0.60) and (body < rt*0.35)
            cond_base_bear = (up > rt*0.60) and (body < rt*0.35)
            cond_perf_bull = (down > rt*0.70) and (body < rt*0.25)
            cond_perf_bear = (up > rt*0.70) and (body < rt*0.25)

            if cond_perf_bull and (5 <= rsi <= 65):
                dire="BUY"; pct=pct_down; score=88; tag="PERFETTA LARGO"; reason=f"PERFETTA {pct}% >70% corpo {body_pct}% <25% RSI {int(rsi)}"
            elif cond_perf_bear and (35 <= rsi <= 95):
                dire="SELL"; pct=pct_up; score=88; tag="PERFETTA LARGO"; reason=f"PERFETTA {pct}% >70% corpo {body_pct}% <25% RSI {int(rsi)}"
            elif cond_base_bull and (10 <= rsi <= 60):
                dire="BUY"; pct=pct_down; score=78; tag="ZONA RSI BUY"; reason=f"RSI {int(rsi)} 10-60 Pin {pct}% >60% corpo {body_pct}%"
            elif cond_base_bear and (40 <= rsi <= 90):
                dire="SELL"; pct=pct_up; score=78; tag="ZONA RSI SELL"; reason=f"RSI {int(rsi)} 40-90 Pin {pct}% >60% corpo {body_pct}%"
            elif cond_easy_bull and (10 <= rsi <= 65):
                dire="BUY"; pct=pct_down; score=68; tag="FACILE 50/45"; reason=f"FACILE {pct}% >50% corpo {body_pct}% <45% RSI {int(rsi)}"
            elif cond_easy_bear and (35 <= rsi <= 90):
                dire="SELL"; pct=pct_up; score=68; tag="FACILE 50/45"; reason=f"FACILE {pct}% >50% corpo {body_pct}% <45% RSI {int(rsi)}"
            elif cond_mega2_bull and (10 <= rsi <= 70):
                dire="BUY"; pct=pct_down; score=65; tag="MEGA 45/50"; reason=f"MEGA {pct}% >45% corpo {body_pct}% <50% RSI {int(rsi)}"
            elif cond_mega2_bear and (30 <= rsi <= 90):
                dire="SELL"; pct=pct_up; score=65; tag="MEGA 45/50"; reason=f"MEGA {pct}% >45% corpo {body_pct}% <50% RSI {int(rsi)}"
            elif cond_mega_bull and (10 <= rsi <= 70):
                dire="BUY"; pct=pct_down; score=60; tag="MEGA 40/50"; reason=f"MEGA {pct}% >40% corpo {body_pct}% <50% RSI {int(rsi)}"
            elif cond_mega_bear and (30 <= rsi <= 90):
                dire="SELL"; pct=pct_up; score=60; tag="MEGA 40/50"; reason=f"MEGA {pct}% >40% corpo {body_pct}% <50% RSI {int(rsi)}"
            else: continue
            
            fmt=f"{c:.5f}" if "JPY" not in otc else f"{c:.3f}"
            if "BTC" in otc: fmt=f"{c:.2f}"
            out.append({"pair":otc,"dir":dire,"price":fmt,"score":score,"pct":pct,"rsi":int(rsi),"tag":tag,"reason":reason})
            del df; gc.collect()
        except: gc.collect(); continue
    out=sorted(out, key=lambda x: x['score'], reverse=True)[:15]
    return jsonify({"signals":out,"debug":"MEGA LARGO 40/50 attivo","total":total})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
