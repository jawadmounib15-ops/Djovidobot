import yfinance as yf, pandas as pd
from flask import Flask, jsonify, render_template_string, request
from datetime import datetime
app = Flask(__name__)

PAIRS = {
    "EUR/USD-OTC":"EURUSD=X","GBP/USD-OTC":"GBPUSD=X","USD/JPY-OTC":"USDJPY=X",
    "AUD/USD-OTC":"AUDUSD=X","USD/CAD-OTC":"USDCAD=X","USD/CHF-OTC":"USDCHF=X",
    "EUR/JPY-OTC":"EURJPY=X","EUR/GBP-OTC":"EURGBP=X","GBP/JPY-OTC":"GBPJPY=X",
    "AUD/JPY-OTC":"AUDJPY=X","EUR/AUD-OTC":"EURAUD=X","NZD/USD-OTC":"NZDUSD=X",
    "BTC/USD-OTC":"BTC-USD","ETH/USD-OTC":"ETH-USD","SOL/USD-OTC":"SOL-USD",
    "BNB/USD-OTC":"BNB-USD","EUR/CAD-OTC":"EURCAD=X","GBP/CAD-OTC":"GBPCAD=X"
}

def analyze_pair(y, tf_label):
    try:
        interval = {"1m":"1m","3m":"2m","5m":"5m","15m":"15m","30m":"30m","1h":"1h"}[tf_label]
        period = "1d" if interval in ["1m","2m"] else "3d" if interval=="5m" else "7d"
        df=yf.download(y, period=period, interval=interval, progress=False, auto_adjust=False)
        if len(df)<60: return None
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        c=df['Close']; l=df['Low']; h=df['High']; o=df['Open']
        df['EMA9']=c.ewm(9).mean(); df['EMA21']=c.ewm(21).mean(); df['EMA50']=c.ewm(50).mean()
        delta=c.diff(); g=delta.where(delta>0,0).ewm(14).mean(); ls=-delta.where(delta<0,0).ewm(14).mean()
        df['RSI']=100-(100/(1+g/ls))
        df['SMA20']=c.rolling(20).mean(); std=c.rolling(20).std()
        df['BB_UP']=df['SMA20']+2*std; df['BB_LOW']=df['SMA20']-2*std
        low14=l.rolling(14).min(); high14=h.rolling(14).max()
        df['STO_K']=100*(c-low14)/((high14-low14).replace(0,1)); df['STO_D']=df['STO_K'].rolling(3).mean()
        last=df.iloc[-1]; prev=df.iloc[-2]
        price=float(last['Close']); ema9=float(last['EMA9']); ema21=float(last['EMA21']); ema50=float(last['EMA50'])
        rsi=float(last['RSI']); bb_up=float(last['BB_UP']); bb_low=float(last['BB_LOW'])
        k=float(last['STO_K']); d=float(last['STO_D']); close_c=float(last['Close']); open_c=float(last['Open'])
        prev_close=float(prev['Close'])
        now = datetime.now()

        # FILTRI 91% - via di mezzo
        f1_buy = ema9 > ema21 and price > ema21
        f1_sell = ema9 < ema21 and price < ema21
        f1_extra_buy = ema21 > ema50
        f1_extra_sell = ema21 < ema50
        f2_buy = 40 <= rsi <= 61
        f2_sell = 39 <= rsi <= 60
        f3_buy = price < bb_up * 0.988
        f3_sell = price > bb_low * 1.012
        f4_buy = 23 <= k <= 68 and k > d
        f4_sell = 23 <= k <= 68 and k < d
        f5_buy = close_c > open_c
        f5_sell = close_c < open_c

        buy_pass = sum([f1_buy,f2_buy,f3_buy,f4_buy,f5_buy])
        sell_pass = sum([f1_sell,f2_sell,f3_sell,f4_sell,f5_sell])

        # SCALA 91% - 95%
        if buy_pass==5 and f1_extra_buy:
            score=95; action="BUY 95% SICURA"; reason=f"5/5 + TREND {tf_label} RSI {rsi:.0f}"
        elif sell_pass==5 and f1_extra_sell:
            score=95; action="SELL 95% SICURA"; reason=f"5/5 + TREND {tf_label} RSI {rsi:.0f}"
        elif buy_pass==5 or sell_pass==5:
            score=92; action="BUY 92%" if buy_pass==5 else "SELL 92%"; reason=f"5/5 PERFETTI {tf_label}"
        elif buy_pass==4 and f1_extra_buy:
            score=91; action="BUY 91%"; reason=f"4/5 + TREND {tf_label} RSI {rsi:.0f}"
        elif sell_pass==4 and f1_extra_sell:
            score=91; action="SELL 91%"; reason=f"4/5 + TREND {tf_label} RSI {rsi:.0f}"
        else:
            score=0; action="WAIT"; reason=f"{buy_pass}/5 o {sell_pass}/5 - sotto 91% {tf_label}"

        return {"price":round(price,5),"rsi":round(rsi,1),"k":round(k,0),"score":score,"action":action,"reason":reason,"tf":tf_label,"time":now.strftime("%H:%M:%S")}
    except: return None

HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>91% MINIMO</title>
<style>body{background:#0e0e10;color:#fff;font-family:system-ui;padding:12px}
select{width:100%;padding:12px;border-radius:10px;background:#1a1a1f;color:#fff;font-size:16px;border:1px solid #333;margin:6px 0}
.row{display:flex;gap:8px}.row select{flex:1}
.card{background:#1a1a1f;padding:14px;border-radius:14px;margin:10px 0;border-left:5px solid #444}
.sbuy{border-left-color:gold;border:3px solid gold}.ssell{border-left-color:gold;border:3px solid gold}
.buy{border-left-color:#00c853}.sell{border-left-color:#ff1744}
.badge{padding:7px 14px;border-radius:20px;font-weight:bold}.sB{background:gold;color:#000;animation:blink 1s infinite}.gB{background:#00c853;color:#000}.yB{background:#ffab00;color:#000}.waitB{background:#333}
.fresh{background:#00e676;color:#000;padding:3px 8px;border-radius:10px;font-size:11px;font-weight:bold;margin-left:6px}
.old{background:#ff5252;color:#fff;padding:3px 8px;border-radius:10px;font-size:11px;font-weight:bold;margin-left:6px}
@keyframes blink{50%{opacity:0.5}}
button{width:100%;padding:13px;background:gold;color:#000;border:none;border-radius:10px;font-weight:bold;font-size:17px;margin-top:6px}
.time{font-size:12px;color:#aaa;margin-top:4px}
</style></head><body>
<h2>📈 SOLO 91%+ - Piano piano</h2>
<div class="row">
<select id="pair"><option>BTC/USD-OTC</option><option>SOL/USD-OTC</option><option>ETH/USD-OTC</option><option>EUR/USD-OTC</option><option>USD/JPY-OTC</option><option>USD/CHF-OTC</option><option>GBP/USD-OTC</option></select>
<select id="tf"><option value="1m">1m</option><option value="3m">3m</option><option value="5m">5m</option><option value="15m" selected>15m</option><option value="30m">30m</option><option value="1h">1h</option></select>
</div>
<button onclick="analyze()">ANALIZZA 🔍</button>
<label style="display:flex;align-items:center;gap:8px;margin:10px 0"><input type="checkbox" id="sound" checked> 🔊 Suona da 91% in su</label>
<div id="result"></div><hr><h3>Auto Scan - Solo 91%+ con orario</h3><div id="auto">...</div>
<audio id="beep" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" preload="auto"></audio>
<script>
function freshnessHtml(scanTime){
  let now=new Date(); let parts=scanTime.split(':'); let sigDate=new Date(); sigDate.setHours(parts[0],parts[1],parts[2]);
  let diffSec=(now - sigDate)/1000; if(diffSec<0) diffSec+=86400;
  let diffMin=Math.floor(diffSec/60);
  if(diffSec<90) return `<span class="fresh">🟢 FRESCO ${Math.floor(diffSec)}s fa - ENTRA ORA</span>`;
  if(diffMin<3) return `<span class="fresh">🟢 FRESCO ${diffMin} min fa</span>`;
  if(diffMin<6) return `<span class="old">🟡 VECCHIO ${diffMin} min fa</span>`;
  return `<span class="old">🔴 VECCHIO ${diffMin} min fa - NON ENTRARE</span>`;
}
async function analyze(){
 let p=document.getElementById('pair').value; let tf=document.getElementById('tf').value;
 document.getElementById('result').innerHTML='Analizzo '+p+' '+tf+'...';
 let r=await fetch('/api/analyze?pair='+p+'&tf='+tf); let d=await r.json();
 if(!d){document.getElementById('result').innerHTML='Dati non disponibili'; return;}
 let cls='card '+(d.score>=91?(d.action.includes('BUY')?'sbuy':'ssell'):''); let badge=d.score>=95?'sB':d.score>=92?'gB':d.score>=91?'yB':'waitB';
 let freshTag=d.score>=91?freshnessHtml(d.time):'';
 document.getElementById('result').innerHTML=`<div class="${cls}"><b>${p} [${d.tf}]</b> <span class="badge ${badge}">${d.action} ${d.score}%</span> ${freshTag}<br><div class="time">⏰ ${d.time} | ${d.reason}</div><small>Prezzo ${d.price} | RSI ${d.rsi}</small></div>`;
 if(d.score>=91 && document.getElementById('sound').checked){document.getElementById('beep').play(); if(navigator.vibrate) navigator.vibrate(d.score>=95?[400,100,400]:[300]);}
}
async function scanAuto(){
 let tf=document.getElementById('tf').value;
 try{let r=await fetch('/api/scan?tf='+tf); let data=await r.json(); let html=''; data.forEach(c=>{
  let cls='card '+(c.action.includes('BUY')?'sbuy':'ssell'); let b=c.score>=95?'sB':c.score>=92?'gB':'yB'; let freshTag=freshnessHtml(c.time);
  html+=`<div class="${cls}"><b>${c.pair} [${c.tf}]</b> <span class="badge ${b}">${c.action} ${c.score}%</span><br>${freshTag}<div class="time">⏰ ${c.time} | ${c.reason}</div></div>`;
 }); if(html=='') html='<div class=card>⏳ Nessuna 91% su '+tf+' - aspetta BEEP</div>'; document.getElementById('auto').innerHTML=html;}catch(e){}
}
analyze(); scanAuto(); setInterval(scanAuto,12000);
</script></body></html>
"""
@app.route('/')
def home(): return render_template_string(HTML)
@app.route('/api/analyze')
def api_analyze():
    label=request.args.get('pair','BTC/USD-OTC'); tf=request.args.get('tf','15m'); y=PAIRS.get(label)
    return jsonify(analyze_pair(y,tf))
@app.route('/api/scan')
def api_scan():
    tf=request.args.get('tf','15m'); res=[]
    for lab,y in PAIRS.items():
        d=analyze_pair(y,tf)
        if d and d['score']>=91: res.append({"pair":lab,**d})
    return jsonify(sorted(res,key=lambda x:x['score'],reverse=True)[:6])
if __name__=='__main__': app.run(host="0.0.0.0",port=10000)
