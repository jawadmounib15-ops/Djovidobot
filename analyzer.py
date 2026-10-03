# V116 FIX DEFINITIVO - ABOUT BLANK FIXATO - CONTRARIO GIUSTO
from flask import Flask, jsonify
import os, gc
app = Flask(__name__)

OTC_MAP = {
    "EURUSD OTC":"EURUSD=X", "GBPUSD OTC":"GBPUSD=X", "USDJPY OTC":"USDJPY=X",
    "AUDUSD OTC":"AUDUSD=X", "USDCAD OTC":"USDCAD=X", "USDCHF OTC":"USDCHF=X",
    "EURGBP OTC":"EURGBP=X", "EURJPY OTC":"EURJPY=X", "GBPJPY OTC":"GBPJPY=X",
    "AUDJPY OTC":"AUDJPY=X", "AED/CNY OTC":"CNY=X", "BHD/CNY OTC":"CNY=X",
    "USD/BDT OTC":"BDT=X", "USD/EGP OTC":"EGP=X", "BTC-OTC":"BTC-USD", "ETH-OTC":"ETH-USD"
}

def calc_rsi(s, p=14):
    try:
        d=s.diff()
        g=d.where(d>0,0).rolling(window=p).mean()
        l=-d.where(d<0,0).rolling(window=p).mean()
        if float(l.iloc[-1])==0:
            return 50.0
        rs=g/l
        r=100-(100/(1+rs))
        return float(r.iloc[-1])
    except:
        return 50.0

@app.route('/')
def home():
    return '<html><head><meta name=viewport content="width=device-width,initial-scale=1"><title>V116 CONTRARIO GIUSTO</title><style>body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:8px}.btn{padding:18px;border-radius:14px;font-weight:bold;font-size:16px;width:96%;max-width:420px;display:block;margin:8px auto;cursor:pointer}.g{background:#ff00ff;color:#fff;border:3px solid #ff00ff}.d{background:#222;color:#fff;border:2px solid #555}.card{background:#1e1e1e;border-radius:16px;padding:14px;margin:10px auto;max-width:440px;text-align:left;border-left:10px solid #ff00ff;position:relative;box-shadow:0 0 15px #ff00ff}.sell{border-left-color:#ff3b3b}.score{font-size:42px;font-weight:900}.badge{position:absolute;top:8px;right:8px;text-align:right}.prepara{background:#ff00ff;color:#fff;font-weight:bold;padding:12px;border-radius:10px;margin-top:8px;text-align:center}.sellbg{background:#ff3b3b;color:#fff}.warn40{background:#ffcc00;color:#000;font-weight:900;padding:12px;border-radius:10px;margin:8px auto;max-width:440px}.storico{background:#111;border:1px solid #333;border-radius:10px;padding:10px;margin:12px auto;max-width:440px;text-align:left;font-size:11px}#s{padding:10px;border-radius:8px;margin:8px auto;max-width:420px;font-weight:bold}.on{background:#ff00ff;color:#fff}.off{background:#ff3b3b;color:#fff}</style></head><body><h2>V116 CONTRARIO GIUSTO FIX</h2><div style=background:#1a1a1a;border:1px solid #ff00ff;border-radius:10px;padding:8px;margin:8px auto;max-width:440px;font-size:11px;text-align:left><b>CONTRARIO GIUSTO:</b><br>Solo 60/35 e 70/25 - NO 20/30/40<br>Vede BUY -> manda SELL - 2 MIN fisso</div><div id=s class=off>ATTIVA SUONO</div><div class="btn g" onclick=att()>ATTIVA SUONO CONTRARIO</div><div class="btn d" onclick=scan()>SCAN CONTRARIO GIUSTO</div><p id=info>V116 Fix Blank</p><div id=warn40box></div><div id=live></div><div id=debug style=color:#888;font-size:11px></div><div class=storico><b>STORICO:</b><div id=storico>Vuoto</div><div style=margin-top:6px><span onclick=clearStor() style=color:#ff3b3b;cursor:pointer>Pulisci</span></div></div><script>let ctx=null,ok=false,warned40=false;let stor=JSON.parse(localStorage.getItem("v116_fix")||"[]");function updStor(){let h="";stor.slice(0,30).forEach(s=>{h+="<div>"+s+"</div>"});document.getElementById("storico").innerHTML=h||"Vuoto"}updStor();function clearStor(){stor=[];localStorage.setItem("v116_fix",JSON.stringify(stor));updStor()}function att(){try{ctx=new (window.AudioContext||window.webkitAudioContext)();ctx.resume().then(()=>{ok=true;document.getElementById("s").className="on";document.getElementById("s").innerText="ON CONTRARIO GIUSTO";beep(900,0.3);setTimeout(()=>beep(1300,0.4),250);scan()})}catch(e){}}function beep(f,d){if(!ctx)return;try{let o=ctx.createOscillator(),g=ctx.createGain();o.type="square";o.frequency.value=f;o.connect(g);g.connect(ctx.destination);g.gain.setValueAtTime(0.8,ctx.currentTime);g.gain.exponentialRampToValueAtTime(0.01,ctx.currentTime+d);o.start();o.stop(ctx.currentTime+d)}catch(e){}}function suona(){if(!ok)return;beep(1000,0.4);setTimeout(()=>beep(1400,0.4),300)}function avviso40(){if(!ok)return;beep(1000,0.3);setTimeout(()=>beep(1000,0.3),300);setTimeout(()=>beep(1500,0.5),600);document.getElementById("warn40box").innerHTML="<div class=warn40>40 SEC CONTRARIO!</div>";setTimeout(()=>{document.getElementById("warn40box").innerHTML=""},8000)}let cur=[],ent=0;function getN(){let n=new Date();let nx=new Date(n);nx.setSeconds(0,0);nx.setMilliseconds(0);nx.setMinutes(n.getMinutes()+1);return nx}function scan(){document.getElementById("info").innerText="Scan contrario giusto...";fetch("/api/scan").then(r=>r.json()).then(d=>{cur=d.signals;ent=getN().getTime();warned40=false;document.getElementById("debug").innerText=d.total+" coppie | "+d.signals.length+" segnali BUONI invertiti";if(d.signals.length>0){suona();let now=new Date().toLocaleTimeString("it-IT");d.signals.forEach(s=>{stor.unshift(now+" - "+s.score+"/100 CONTRARIO "+s.dir+" "+s.pair+" ERA "+s.orig)});localStorage.setItem("v116_fix",JSON.stringify(stor.slice(0,50)));updStor()}render()}).catch(e=>{document.getElementById("info").innerText="Errore api"}) }function render(){let now=Date.now();let diff=Math.ceil((ent-now)/1000);let h="";if(cur.length>0 && diff<=40 && diff>0 && !warned40){avviso40();warned40=true}cur.forEach(s=>{let col=s.dir=="BUY"?"#00ff88":"#ff3b3b";let left=Math.max(0,120+diff);let txt=diff>40?"AVVISO TRA "+(diff-40)+"s - 2 MIN":diff>0?"ENTRA "+s.dir+" TRA "+diff+"s - 2 MIN":"SCAD "+left+"s";h+="<div class=card "+(s.dir=="SELL"?"sell":"")+"><div class=badge><div class=score style=color:"+col+">"+s.score+"</div><div style=color:"+col+";font-weight:900>CONTR "+s.dir+"</div><div style=font-size:9px;color:#ff00ff>ERA "+s.orig+"</div><div style=font-size:10px>2 MIN</div><div style=font-size:9px;background:#ff00ff;color:#fff;padding:2px 4px;border-radius:4px>"+s.tag+"</div></div><div style=width:58%><b style=color:"+col+">"+s.pair+"</b><br><span style=color:#ff00ff;font-size:11px;font-weight:bold>CONTRARIO: ERA "+s.orig+" ORA "+s.dir+"</span><br><span style=color:#aaa;font-size:11px>"+s.reason+"</span><br><span style=font-size:11px>"+s.price+"</span></div><div class=prepara "+(s.dir=="SELL"?"sellbg":"")+">"+txt+"</div></div>"});document.getElementById("live").innerHTML=h||"Nessun segnale buono ora - solo 60/35 e 70/25"}setInterval(render,1000);setInterval(scan,15000);</script></body></html>'

@app.route('/api/scan')
def api():
    try:
        import yfinance as yf, pandas as pd
    except:
        return jsonify({"signals":[],"debug":"no yf","total":0})
    out=[]
    total=0
    for otc, real in OTC_MAP.items():
        total+=1
        try:
            df=yf.download(real, period="5d", interval="1m", progress=False, auto_adjust=True, threads=False)
            if df is None or len(df)<20:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns=df.columns.get_level_values(0)
            c=float(df.iloc[-1]['Close'])
            o=float(df.iloc[-1]['Open'])
            h=float(df.iloc[-1]['High'])
            l=float(df.iloc[-1]['Low'])
            rt=h-l
            if rt<=0:
                continue
            body=abs(c-o)
            up=h-max(c,o)
            down=min(c,o)-l
            rsi=calc_rsi(df['Close'])
            pct_up=int((up/rt)*100)
            pct_down=int((down/rt)*100)
            body_pct=int((body/rt)*100)
            orig=None
            score=0
            reason=""
            pct=0
            tag=""
            perf_bull = (down > rt*0.70) and (body < rt*0.25)
            perf_bear = (up > rt*0.70) and (body < rt*0.25)
            base_bull = (down > rt*0.60) and (body < rt*0.35)
            base_bear = (up > rt*0.60) and (body < rt*0.35)
            if perf_bull and (5 <= rsi <= 65):
                orig="BUY"; pct=pct_down; score=90; tag="PERFETTA 70/25"; reason="Pin "+str(pct)+"% >70% corpo "+str(body_pct)+"%"
            elif perf_bear and (35 <= rsi <= 95):
                orig="SELL"; pct=pct_up; score=90; tag="PERFETTA 70/25"; reason="Pin "+str(pct)+"% >70% corpo "+str(body_pct)+"%"
            elif base_bull and (10 <= rsi <= 60):
                orig="BUY"; pct=pct_down; score=80; tag="BUONA 60/35"; reason="Pin "+str(pct)+"% >60% corpo "+str(body_pct)+"%"
            elif base_bear and (40 <= rsi <= 90):
                orig="SELL"; pct=pct_up; score=80; tag="BUONA 60/35"; reason="Pin "+str(pct)+"% >60% corpo "+str(body_pct)+"%"
            else:
                continue
            final = "SELL" if orig=="BUY" else "BUY"
            fmt="{:.5f}".format(c)
            if "JPY" in otc:
                fmt="{:.3f}".format(c)
            if "BTC" in otc:
                fmt="{:.2f}".format(c)
            out.append({"pair":otc,"dir":final,"orig":orig,"price":fmt,"score":score,"pct":pct,"rsi":int(rsi),"tag":tag,"reason":reason})
            del df
            gc.collect()
        except:
            gc.collect()
            continue
    out=sorted(out, key=lambda x: x['score'], reverse=True)[:10]
    return jsonify({"signals":out,"debug":"V116 CONTRARIO GIUSTO OK","total":total})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
