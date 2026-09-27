import yfinance as yf, pandas as pd
from flask import Flask, jsonify, render_template_string, request
app = Flask(__name__)

PAIRS = {
    "EUR/USD-OTC":"EURUSD=X","GBP/USD-OTC":"GBPUSD=X","USD/JPY-OTC":"USDJPY=X",
    "AUD/USD-OTC":"AUDUSD=X","USD/CAD-OTC":"USDCAD=X","USD/CHF-OTC":"USDCHF=X",
    "EUR/JPY-OTC":"EURJPY=X","EUR/GBP-OTC":"EURGBP=X","GBP/JPY-OTC":"GBPJPY=X",
    "AUD/JPY-OTC":"AUDJPY=X","EUR/AUD-OTC":"EURAUD=X","NZD/USD-OTC":"NZDUSD=X",
    "BTC/USD-OTC":"BTC-USD","ETH/USD-OTC":"ETH-USD","SOL/USD-OTC":"SOL-USD",
    "BNB/USD-OTC":"BNB-USD","EUR/CAD-OTC":"EURCAD=X","GBP/CAD-OTC":"GBPCAD=X"
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

        # BILANCIATO: più largo del 5 stretto, più sicuro del vecchio
        f1_buy = ema9 > ema21 and price > ema21
        f1_sell = ema9 < ema21 and price < ema21
        f1_extra_buy = ema21 > ema50 # bonus per SICURA
        f1_extra_sell = ema21 < ema50

        f2_buy = 38 <= rsi <= 62 # allargato da 40-58
        f2_sell = 38 <= rsi <= 62
        f3_buy = price < bb_up * 0.992 # allargato da 0.988
        f3_sell = price > bb_low * 1.008
        f4_buy = 20 <= k <= 75 and k > d # allargato
        f4_sell = 20 <= k <= 78 and k < d
        f5_buy = close_c >= open_c * 0.9998 # basta non sia rossa forte
        f5_sell = close_c <= open_c * 1.0002

        buy_pass = sum([f1_buy,f2_buy,f3_buy,f4_buy,f5_buy])
        sell_pass = sum([f1_sell,f2_sell,f3_sell,f4_sell,f5_sell])
        is_strong_buy = f1_extra_buy and buy_pass==5
        is_strong_sell = f1_extra_sell and sell_pass==5

        if is_strong_buy: score=95; action="BUY SICURA"; reason=f"5/5 + TREND FORTE {tf}"
        elif is_strong_sell: score=95; action="SELL SICURA"; reason=f"5/5 + TREND FORTE {tf}"
        elif buy_pass==5 or sell_pass==5: score=90; action="BUY" if buy_pass==5 else "SELL"; reason=f"5/5 PERFETTI {tf}"
        elif buy_pass==4: score=88; action="BUY"; reason=f"4/5 BUONA {tf} - RSI {rsi:.0f}"
        elif sell_pass==4: score=88; action="SELL"; reason=f"4/5 BUONA {tf} - RSI {rsi:.0f}"
        else: score=0; action="WAIT"; reason=f"Mercato sporco TF {tf}"

        return {"price":round(price,5),"rsi":round(rsi,1),"k":round(k,0),"score":score,"action":action,"reason":reason,"tf":tf}
    except: return None

HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>BILANCIATO 88% + 95%</title>
<style>body{background:#0e0e10;color:#fff;font-family:system-ui;padding:12px}
select{width:100%;padding:12px;border-radius:10px;background:#1a1a1f;color:#fff;font-size:16px;border:1px solid #333;margin:6px 0}
.row{display:flex;gap:8px}.row select{flex:1}
.card{background:#1a1a1f;padding:14px;border-radius:14px;margin:10px 0;border-left:5px solid #444}
.sbuy{border-left-color:gold;border:3px solid gold}.ssell{border-left-color:gold;border:3px solid gold}
.buy{border-left-color:#00c853}.sell{border-left-color:#ff1744}
.badge{padding:7px 14px;border-radius:20px;font-weight:bold}.sB{background:gold;color:#000;animation:blink 1s infinite}.gB{background:#00c853;color:#000}.yB{background:#ffab00;color:#000}.waitB{background:#333}
@keyframes blink{50%{opacity:0.5}}
button{width:100%;padding:13px;background:gold;color:#000;border:none;border-radius:10px;font-weight:bold;font-size:17px;margin-top:6px}
</style></head><body>
<h2>⚖️ BILANCIATO - 88% BUONA + 95% SICURA</h2>
<div class="row">
<select id="pair"><option>EUR/USD-OTC</option><option>BTC/USD-OTC</option><option>ETH/USD-OTC</option><option>USD/JPY-OTC</option><option>GBP/USD-OTC</option><option>AUD/JPY-OTC</option><option>EUR/JPY-OTC</option><option>GBP/JPY-OTC</option><option>EUR/GBP-OTC</option><option>SOL/USD-OTC</option></select>
<select id="tf"><option value="1m">1m</option><option value="3m">3m</option><option value="5m" selected>5m</option><option value="15m">15m</option><option value="30m">30m</option><option value="1h">1h</option></select>
</div>
<button onclick="analyze()">ANALIZZA 🔍</button>
<label style="display:flex;align-items:center;gap:8px;margin:10px 0"><input type="checkbox" id="sound" checked> 🔊 Suona da 88% in su</label>
<div id="result"></div><hr><h3>Auto Scan - Solo 88%+</h3><div id="auto">...</div>
<audio id="beep" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" preload="auto"></audio>
<script>
async function analyze(){
 let p=document.getElementById('pair').value; let tf=document.getElementById('tf').value;
 document.getElementById('result').innerHTML='Analizzo '+p+' '+tf+'...';
 let r=await fetch('/api/analyze?pair='+p+'&tf='+tf); let d=await r.json();
 if(!d){document.getElementById('result').innerHTML='Dati non disponibili'; return;}
 let cls='card '+(d.score>=95?(d.action.includes('BUY')?'sbuy':'ssell'):d.action.includes('BUY')?'buy':'sell');
 let badge=d.score>=95?'sB':d.score>=90?'gB':d.score>=88?'yB':'waitB';
 document.getElementById('result').innerHTML=`<div class="${cls}"><b>${p} [${d.tf}]</b> <span class="badge ${badge}">${d.action} ${d.score}%</span><br><small>${d.reason}</small><br><small>Prezzo ${d.price} | RSI ${d.rsi} STO ${d.k}</small></div>`;
 if(d.score>=88 && document.getElementById('sound').checked){document.getElementById('beep').play(); if(navigator.vibrate) navigator.vibrate(d.score>=95?[400,100,400,100,400]:[300]);}
}
async function scanAuto(){
 let tf=document.getElementById('tf').value;
 try{let r=await fetch('/api/scan?tf='+tf); let data=await r.json(); let html=''; data.forEach(c=>{
  let cls='card '+(c.score>=95?(c.action.includes('BUY')?'sbuy':'ssell'):c.action.includes('BUY')?'buy':'sell'); let b=c.score>=95?'sB':c.score>=90?'gB':'yB';
  html+=`<div class="${cls}"><b>${c.pair} [${c.tf}]</b> <span class="badge ${b}">${c.action} ${c.score}%</span><br><small>${c.reason}</small></div>`;
  if(c.score>=88 && document.getElementById('sound').checked && c.score>=95){document.getElementById('beep').play();}
 }); if(html=='') html='<div class=card>⏳ Nessuna 88% ora su '+tf+' - aspetta BEEP</div>'; document.getElementById('auto').innerHTML=html;}catch(e){}
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
        if d and d['score']>=88: res.append({"pair":lab,**d})
    return jsonify(sorted(res,key=lambda x:x['score'],reverse=True)[:6])
if __name__=='__main__': app.run(host="0.0.0.0",port=10000)
