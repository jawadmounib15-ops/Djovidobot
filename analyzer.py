import yfinance as yf, pandas as pd
from flask import Flask, jsonify, render_template_string, request
app = Flask(__name__)

PAIRS = {
    "EUR/USD-OTC":"EURUSD=X","GBP/USD-OTC":"GBPUSD=X","USD/JPY-OTC":"USDJPY=X",
    "AUD/USD-OTC":"AUDUSD=X","USD/CAD-OTC":"USDCAD=X","USD/CHF-OTC":"USDCHF=X",
    "EUR/JPY-OTC":"EURJPY=X","EUR/GBP-OTC":"EURGBP=X","GBP/JPY-OTC":"GBPJPY=X",
    "AUD/JPY-OTC":"AUDJPY=X","EUR/AUD-OTC":"EURAUD=X","NZD/USD-OTC":"NZDUSD=X",
    "BTC/USD-OTC":"BTC-USD","ETH/USD-OTC":"ETH-USD","SOL/USD-OTC":"SOL-USD",
    "BNB/USD-OTC":"BNB-USD","EUR/CAD-OTC":"EURCAD=X","GBP/CAD-OTC":"GBPCAD=X",
    "CAD/JPY-OTC":"CADJPY=X","CHF/JPY-OTC":"CHFJPY=X"
}

TF_MAP = {"1m":"1m","3m":"2m","5m":"5m","15m":"15m","30m":"30m","1h":"1h"}

def analyze_pair(y, tf):
    try:
        interval = TF_MAP.get(tf, "5m")
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
        last=df.iloc[-1]
        price=float(last['Close']); ema9=float(last['EMA9']); ema21=float(last['EMA21']); ema50=float(last['EMA50'])
        rsi=float(last['RSI']); bb_up=float(last['BB_UP']); bb_low=float(last['BB_LOW'])
        k=float(last['STO_K']); d=float(last['STO_D']); close_c=float(last['Close']); open_c=float(last['Open'])

        f1_buy = ema9 > ema21 and ema21 > ema50 and price > ema21
        f1_sell = ema9 < ema21 and ema21 < ema50 and price < ema21
        f2_buy = 40 <= rsi <= 58; f2_sell = 42 <= rsi <= 65
        f3_buy = price < bb_up * 0.988; f3_sell = price > bb_low * 1.012
        f4_buy = 28 <= k <= 68 and k > d; f4_sell = 32 <= k <= 75 and k < d
        f5_buy = close_c > open_c; f5_sell = close_c < open_c

        if f1_buy and f2_buy and f3_buy and f4_buy and f5_buy:
            score=95; action="BUY SICURA"; reason=f"5/5 TF {tf} | RSI {rsi:.1f} STO {k:.0f}"
        elif f1_sell and f2_sell and f3_sell and f4_sell and f5_sell:
            score=95; action="SELL SICURA"; reason=f"5/5 TF {tf} | RSI {rsi:.1f} STO {k:.0f}"
        else:
            bp=sum([f1_buy,f2_buy,f3_buy,f4_buy,f5_buy]); sp=sum([f1_sell,f2_sell,f3_sell,f4_sell,f5_sell])
            if bp==4: score=80; action="BUY"; reason=f"4/5 TF {tf} | RSI {rsi:.1f}"
            elif sp==4: score=80; action="SELL"; reason=f"4/5 TF {tf} | RSI {rsi:.1f}"
            else: score=0; action="WAIT"; reason=f"Mercato sporco TF {tf} - aspetta 95%"

        return {"price":round(price,5),"rsi":round(rsi,1),"k":round(k,0),"score":score,"action":action,"reason":reason,"tf":tf}
    except: return None

HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>5 FILTRI + TIMEFRAME</title>
<style>body{background:#0e0e10;color:#fff;font-family:system-ui;padding:12px}
select{width:100%;padding:12px;border-radius:10px;background:#1a1a1f;color:#fff;font-size:16px;border:1px solid #333;margin:6px 0}
.row{display:flex;gap:8px}.row select{flex:1}
.card{background:#1a1a1f;padding:14px;border-radius:14px;margin:10px 0;border-left:5px solid #444}
.sbuy{border-left-color:gold;border:3px solid gold}.ssell{border-left-color:gold;border:3px solid gold}
.badge{padding:7px 14px;border-radius:20px;font-weight:bold}.sB{background:gold;color:#000;animation:blink 1s infinite}
@keyframes blink{50%{opacity:0.5}} .buyB{background:#00c853;color:#000}.sellB{background:#ff1744}.waitB{background:#333}
button{width:100%;padding:13px;background:gold;color:#000;border:none;border-radius:10px;font-weight:bold;font-size:17px;margin-top:6px}
</style></head><body>
<h2>💎 5 FILTRI + TIMEFRAME + BEEP</h2>
<div class="row">
<select id="pair"><option>EUR/USD-OTC</option><option>USD/JPY-OTC</option><option>GBP/USD-OTC</option><option>BTC/USD-OTC</option><option>ETH/USD-OTC</option><option>AUD/JPY-OTC</option><option>EUR/JPY-OTC</option><option>GBP/JPY-OTC</option><option>EUR/GBP-OTC</option><option>SOL/USD-OTC</option></select>
<select id="tf"><option value="1m">1 min</option><option value="3m">3 min</option><option value="5m" selected>5 min</option><option value="15m">15 min</option><option value="30m">30 min</option><option value="1h">1 ora</option></select>
</div>
<button onclick="analyze()">ANALIZZA 🔍</button>
<label style="display:flex;align-items:center;gap:8px;margin:10px 0"><input type="checkbox" id="sound" checked> 🔊 Suono per 95% SICURA</label>
<div id="result"></div><hr><h3>Auto Scan - Solo 80%+ (TF scelto)</h3><div id="auto">...</div>
<audio id="beep" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" preload="auto"></audio>
<script>
async function analyze(){
 let p=document.getElementById('pair').value; let tf=document.getElementById('tf').value;
 document.getElementById('result').innerHTML='Analizzo '+p+' '+tf+'...';
 let r=await fetch('/api/analyze?pair='+p+'&tf='+tf); let d=await r.json();
 if(!d){document.getElementById('result').innerHTML='Dati non disponibili per '+tf; return;}
 let cls='card '+(d.score>=95?(d.action.includes('BUY')?'sbuy':'ssell'):''); 
 let badge=d.action.includes('SICURA')?'sB':d.action=='BUY'?'buyB':d.action=='SELL'?'sellB':'waitB';
 let html=`<div class="${cls}"><b>${p} [${d.tf}]</b> - <span class="badge ${badge}">${d.action} ${d.score}%</span><br><small>${d.reason}</small><br><small>Prezzo ${d.price} | RSI ${d.rsi} STO ${d.k}</small></div>`;
 document.getElementById('result').innerHTML=html;
 if(d.score>=95 && document.getElementById('sound').checked){document.getElementById('beep').play(); if(navigator.vibrate) navigator.vibrate([400,100,400]);}
}
async function scanAuto(){
 let tf=document.getElementById('tf').value;
 try{let r=await fetch('/api/scan?tf='+tf); let data=await r.json(); let html=''; data.forEach(c=>{
  let cls='card '+(c.score>=95?(c.action.includes('BUY')?'sbuy':'ssell'):''); let b=c.action.includes('SICURA')?'sB':c.action=='BUY'?'buyB':'sellB';
  html+=`<div class="${cls}"><b>${c.pair} [${c.tf}]</b> <span class="badge ${b}">${c.action} ${c.score}%</span><br><small>${c.reason}</small></div>`;
  if(c.score>=95 && document.getElementById('sound').checked){document.getElementById('beep').play();}
 }); if(html=='') html='<div class=card>⏳ Nessuna SICURA su TF '+tf+' - aspetta BEEP</div>'; document.getElementById('auto').innerHTML=html;}catch(e){}
}
analyze(); scanAuto(); setInterval(scanAuto,15000);
</script></body></html>
"""
@app.route('/')
def home(): return render_template_string(HTML)
@app.route('/api/analyze')
def api_analyze():
    label=request.args.get('pair','EUR/USD-OTC'); tf=request.args.get('tf','5m'); y=PAIRS.get(label)
    return jsonify(analyze_pair(y,tf))
@app.route('/api/scan')
def api_scan():
    tf=request.args.get('tf','5m'); res=[]
    for lab,y in PAIRS.items():
        d=analyze_pair(y,tf)
        if d and d['score']>=80: res.append({"pair":lab,**d})
    return jsonify(sorted(res,key=lambda x:x['score'],reverse=True)[:6])
if __name__=='__main__': app.run(host="0.0.0.0",port=10000)
