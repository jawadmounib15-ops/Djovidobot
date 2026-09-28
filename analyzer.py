import yfinance as yf, pandas as pd
from flask import Flask, jsonify, render_template_string, request
from datetime import datetime, timezone, timedelta
app = Flask(__name__)

PAIRS = {
    "EUR/USD-OTC":"EURUSD=X","GBP/USD-OTC":"GBPUSD=X","USD/JPY-OTC":"USDJPY=X",
    "AUD/USD-OTC":"AUDUSD=X","USD/CAD-OTC":"USDCAD=X","BTC/USD-OTC":"BTC-USD",
    "ETH/USD-OTC":"ETH-USD","SOL/USD-OTC":"SOL-USD","BNB/USD-OTC":"BNB-USD",
    "EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X","USD/JPY":"USDJPY=X"
}
ITALY_TZ = timezone(timedelta(hours=2))

def analyze_pair(y, tf_label):
    try:
        tf_clean = tf_label.split(" ")[0].strip()
        interval = {"1m":"1m","3m":"2m","5m":"5m","15m":"15m","30m":"30m","1h":"1h"}.get(tf_clean, "15m")
        period = "3d" if interval in ["5m","15m"] else "7d"
        df=yf.download(y, period=period, interval=interval, progress=False, auto_adjust=False)
        if len(df)<50:
            return {"price":0,"rsi":0,"k":0,"score":0,"action":"MERCATO CHIUSO","reason":f"{tf_clean} chiuso","tf":tf_clean,"time":datetime.now(ITALY_TZ).strftime("%H:%M:%S"),"timestamp":datetime.now(ITALY_TZ).timestamp()}
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        c=df['Close']; l=df['Low']; h=df['High']; o=df['Open']
        df['EMA9']=c.ewm(9).mean(); df['EMA21']=c.ewm(21).mean(); df['EMA50']=c.ewm(50).mean()
        delta=c.diff(); g=delta.where(delta>0,0).ewm(14).mean(); ls=-delta.where(delta<0,0).ewm(14).mean()
        df['RSI']=100-(100/(1+g/ls))
        df['SMA20']=c.rolling(20).mean(); std=c.rolling(20).std()
        df['BB_UP']=df['SMA20']+2*std; df['BB_LOW']=df['SMA20']-2*std
        low14=l.rolling(14).min(); high14=h.rolling(14).max()
        df['STO_K']=100*(c-low14)/((high14-low14).replace(0,1)); df['STO_D']=df['STO_K'].rolling(3).mean()
        last=df.iloc[-1]
        price=float(last['Close']); ema9=float(last['EMA9']); ema21=float(last['EMA21']); ema50=float(last['EMA50'])
        rsi=float(last['RSI']); bb_up=float(last['BB_UP']); bb_low=float(last['BB_LOW'])
        k=float(last['STO_K']); d=float(last['STO_D']); close_c=float(last['Close']); open_c=float(last['Open'])
        now_italy = datetime.now(ITALY_TZ)
        f1_buy = ema9 > ema21 and price > ema21; f1_sell = ema9 < ema21 and price < ema21
        f1_extra_buy = ema21 > ema50; f1_extra_sell = ema21 < ema50
        f2_buy = 42 <= rsi <= 58; f2_sell = 42 <= rsi <= 58
        f3_buy = price < bb_up * 0.985; f3_sell = price > bb_low * 1.015
        f4_buy = 25 <= k <= 65 and k > d; f4_sell = 25 <= k <= 65 and k < d
        f5_buy = close_c > open_c; f5_sell = close_c < open_c
        buy_pass = sum([f1_buy,f2_buy,f3_buy,f4_buy,f5_buy])
        sell_pass = sum([f1_sell,f2_sell,f3_sell,f4_sell,f5_sell])
        if buy_pass==5 and f1_extra_buy: score=95; action="BUY 95% SICURA"; reason=f"5/5 + TREND {tf_clean}"
        elif sell_pass==5 and f1_extra_sell: score=95; action="SELL 95% SICURA"; reason=f"5/5 + TREND {tf_clean}"
        elif buy_pass==5 or sell_pass==5: score=92; action="BUY 92%" if buy_pass==5 else "SELL 92%"; reason=f"5/5 PERFETTI {tf_clean}"
        else: score=0; action="WAIT"; reason=f"{buy_pass}/5 sotto 92% {tf_clean}"
        return {"price":round(price,5),"rsi":round(rsi,1),"k":round(k,0),"score":score,"action":action,"reason":reason,"tf":tf_clean,"time":now_italy.strftime("%H:%M:%S"),"timestamp":now_italy.timestamp()}
    except Exception as e:
        return {"price":0,"score":0,"action":"ERRORE","reason":str(e)[:40],"tf":tf_label,"time":datetime.now(ITALY_TZ).strftime("%H:%M:%S"),"timestamp":datetime.now(ITALY_TZ).timestamp()}

def analyze_pinbar_only(y, tf_label):
    try:
        tf_clean = tf_label.split(" ")[0].strip()
        interval = {"1m":"1m","3m":"2m","5m":"5m","15m":"15m","30m":"30m","1h":"1h"}.get(tf_clean, "15m")
        period = "3d" if interval in ["5m","15m"] else "7d"
        df=yf.download(y, period=period, interval=interval, progress=False, auto_adjust=False)
        if len(df)<20: return None
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        last=df.iloc[-1]
        o=float(last['Open']); c=float(last['Close']); h=float(last['High']); lo=float(last['Low'])
        body=abs(c-o); rng=h-lo
        if rng==0 or body==0: return None
        up=h-max(o,c); low=min(o,c)-lo
        # PINBAR STRETTA - TOOOP
        pin_bull = low > 2.5*body and low > rng*0.65 and body < rng*0.25 and c > o
        pin_bear = up > 2.5*body and up > rng*0.65 and body < rng*0.25 and c < o
        if not (pin_bull or pin_bear): return None
        action = "BUY PINBAR 📌" if pin_bull else "SELL PINBAR 📌"
        now_italy = datetime.now(ITALY_TZ)
        return {"price":round(c,5),"score":90,"action":action,"reason":f"STRETTA wick {max(up,low)/rng*100:.0f}% corpo {body/rng*100:.0f}%","tf":tf_clean,"time":now_italy.strftime("%H:%M:%S"),"timestamp":now_italy.timestamp()}
    except: return None

HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>92% + PINBAR STRETTA</title><style>body{background:#0e0e10;color:#fff;font-family:system-ui;padding:12px} select{width:100%;padding:12px;border-radius:10px;background:#1a1a1f;color:#fff;font-size:16px;border:1px solid #333;margin:6px 0}.row{display:flex;gap:8px}.row select{flex:1}.card{background:#1a1a1f;padding:14px;border-radius:14px;margin:10px 0;border-left:5px solid #444}.sbuy{border-left-color:gold;border:3px solid gold}.ssell{border-left-color:#ff5252;border:3px solid #ff5252}.pin{border-left-color:#00e5ff;border:3px solid #00e5ff}.badge{padding:7px 14px;border-radius:20px;font-weight:bold}.sB{background:gold;color:#000;animation:blink 1s infinite}.gB{background:#00c853;color:#000}.pB{background:#00e5ff;color:#000;animation:blink 1s infinite}.fresh{background:#00e676;color:#000;padding:3px 8px;border-radius:10px;font-size:11px;font-weight:bold} @keyframes blink{50%{opacity:0.5}} button{width:100%;padding:13px;background:gold;color:#000;border:none;border-radius:10px;font-weight:bold;font-size:17px;margin-top:6px}.time{font-size:12px;color:#aaa;margin-top:4px} h3{margin-top:22px;border-top:1px solid #333;padding-top:12px} </style></head><body>
<h2>📈 2 LAVORI - TOOOP STRETTI</h2>
<div class="row"><select id="pair"><option>EUR/USD-OTC</option><option>BTC/USD-OTC</option><option>SOL/USD-OTC</option><option>EUR/USD</option><option>GBP/USD</option></select><select id="tf"><option value="5m">5m</option><option value="15m" selected>15m</option><option value="1h">1h</option></select></div>
<button onclick="analyze()">ANALIZZA LAVORO 1 (92%+) 🔍</button>
<div id="result"></div>
<hr><h3>⚡ LAVORO 1 - SOLO 92%+ STRETT0</h3><div id="auto">...</div>
<hr><h3>📌 LAVORO 2 - PINBAR STRETTA 2.5x/65%/25%</h3><div id="auto-pinbar">...</div>
<audio id="beep" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" preload="auto"></audio>
<script>
async function analyze(){ let p=document.getElementById('pair').value; let tf=document.getElementById('tf').value; document.getElementById('result').innerHTML='Analizzo '+p+' '+tf+'...'; try{ let r=await fetch('/api/analyze?pair='+p+'&tf='+tf); let d=await r.json(); if(!d || d.score<92){document.getElementById('result').innerHTML='<div class=card>⏳ '+ (d? d.reason : 'WAIT') +' - '+ (d? d.action : 'sotto 92%') +'</div>'; return;} let cls='card '+(d.action.includes('BUY')?'sbuy':'ssell'); let badge=d.score>=95?'sB':'gB'; document.getElementById('result').innerHTML=`<div class="${cls}"><b>${p} [${d.tf}]</b> <span class="badge ${badge}">${d.action} ${d.score}%</span> <span class="fresh">🟢 FRESCO ORA ${d.time}</span><br><div class="time">⏰ ${d.time} | ${d.reason}</div></div>`; document.getElementById('beep').play(); }catch(e){document.getElementById('result').innerHTML='<div class=card>⚠️ Render si sveglia, riprova 10 sec</div>';} }
async function scanAuto(){ let tf=document.getElementById('tf').value; try{ let r=await fetch('/api/scan?tf='+tf); let data=await r.json(); let html=''; let now=Date.now()/1000; let maxAge=tf==='15m'?600:180; data.forEach(c=>{ let ageSec=now-c.timestamp; if(ageSec>maxAge) return; let cls='card '+(c.action.includes('BUY')?'sbuy':'ssell'); let b=c.score>=95?'sB':'gB'; html+=`<div class="${cls}"><b>${c.pair} [${c.tf}]</b> <span class="badge ${b}">${c.action} ${c.score}%</span> <span class="fresh">🟢 ${Math.floor(ageSec)}s fa ${c.time}</span><div class="time">${c.reason}</div></div>`; }); if(html=='') html='<div class=card>⏳ Nessun 92%+ fresco su '+tf+'</div>'; document.getElementById('auto').innerHTML=html; }catch(e){} }
async function scanPinbar(){ let tf=document.getElementById('tf').value; try{ let r=await fetch('/api/scan_pinbar?tf='+tf); let data=await r.json(); let html=''; data.forEach(c=>{ html+=`<div class="card pin"><b>${c.pair} [${c.tf}]</b> <span class="badge pB">${c.action}</span> <span class="fresh">📌 ${c.time}</span><div class="time">${c.reason} | Prezzo ${c.price}</div></div>`; }); if(html=='') html='<div class=card>⏳ Nessuna pinbar stretta su '+tf+'</div>'; document.getElementById('auto-pinbar').innerHTML=html; }catch(e){} }
scanAuto(); scanPinbar(); setInterval(()=>{scanAuto(); scanPinbar();},10000);
</script></body></html>"""

@app.route('/')
def home(): return render_template_string(HTML)
@app.route('/api/analyze')
def api_analyze(): return jsonify(analyze_pair(PAIRS.get(request.args.get('pair','EUR/USD-OTC')), request.args.get('tf','15m')))
@app.route('/api/scan')
def api_scan():
    tf=request.args.get('tf','15m'); res=[]
    for lab,y in PAIRS.items():
        d=analyze_pair(y,tf)
        if d and d['score']>=92: res.append({"pair":lab,**d})
    return jsonify(sorted(res,key=lambda x:x['score'],reverse=True)[:6])
@app.route('/api/scan_pinbar')
def api_scan_pinbar():
    tf=request.args.get('tf','15m'); res=[]
    for lab,y in PAIRS.items():
        d=analyze_pinbar_only(y,tf)
        if d: res.append({"pair":lab,**d})
    return jsonify(sorted(res,key=lambda x:x['timestamp'],reverse=True)[:6])
if __name__=='__main__': app.run(host="0.0.0.0",port=10000)
