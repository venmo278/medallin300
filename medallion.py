import yfinance as yf, pandas as pd, numpy as np, time, requests, os
from datetime import datetime, timezone, timedelta
from threading import Thread
from flask import Flask

# ---------- Flask keep-alive ----------
app = Flask(__name__)
@app.route('/')
def home():
    return "Medallion 300 Final AI Quant is Live!"
def run_web():
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))
Thread(target=run_web, daemon=True).start()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    try:
        r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
        if r.status_code != 200:
            print("Telegram error:", r.text[:200])
    except Exception as e:
        print("Telegram fail:", e)

# ---------- Universe ----------
ALL_TICKERS = ["NVDA","AMD","CRWV","AVGO","TSM","ASML","AMAT","LRCX","KLAC","MRVL","ARM","SMCI","PLTR","SOUN","AAPL","MSFT","GOOGL","AMZN","META","TSLA","ORCL","ADBE","CRM","NOW","INTU","UBER","ABNB","APP","MSTR","COIN","HOOD","RBLX","DKNG","AFRM","UPST","SOFI","LCID","RIVN","IONQ","QBTS","RGTI","ASTS","JPM","V","MA","BAC","WFC","GS","MS","BLK","C","AXP","HD","LOW","COST","WMT","TGT","NKE","SBUX","MCD","DIS","PEP","KO","PG","JNJ","UNH","PFE","LLY","MRK","ABBV","TMO","XOM","CVX","COP","SLB","CAT","DE","HON","GE","BA","LMT","UNP","FDX","UPS","DAL","UAL","MAR","HLT","BKNG","LIN","SHW","APD","NUE","FCX","NEM","EMR","ETN","PH","ITW","TXN","QCOM","ADI","NXPI","ON","CDNS","SNPS","FTNT","PANW","CRWD","ZS","DDOG","NET","SNOW","MDB","AI","PATH","SHOP","SQ","PYPL","DASH","PINS","SNAP","RDDT","NFLX","IBM","INTC","CSCO","VZ","T","CVS","WBA","KHC","GIS","CL","KMB","MO","PM","RIO","BHP","VALE","GOLD","EWJ","EWZ","EEM","FXI","SPY","QQQ","IWM","DIA","VOO","ARKK","SMH","SOXX","XLF","XLE","XLV","XLK","GLD","SLV","USO","TLT","BABA","JD","PDD","BIDU","NIO","LI","XPEV","SE","GRAB","MELI","NU","NVO","OXY","EOG","MPC","PSX","VLO","HAL","BKR","APA","DVN","FANG","EQT","CTRA","MRO","CHTR","CMCSA","WBD","PARA","FOX","NWSA","LUMN","BBY","GME","AMC","BB","NOK","ERIC","SIRI","CROX","UAA","LULU","DECK","SKX","EL","ULTA","DG","DLTR","KR","ACI","SFM","TSCO","RH","WSM","TPX","LEG","WHR","NVR","LEN","DHI","PHM","KBH","BZH","TOL","MTCH","BMBL","GRND","WYNN","LVS","MGM","DANGCEM.LG","MTNN.LG","GTCO.LG","ZENITHBANK.LG","UBA.LG","ACCESSCORP.LG","BUACEMENT.LG","BUAFOODS.LG","SEPLAT.LG","ARADEL.LG","FBNH.LG","STANBIC.LG","DANGSUGAR.LG","NASCON.LG","NESTLE.LG","UNILEVER.LG","CADBURY.LG","NB.LG","GUINNESS.LG","INTBREW.LG","PRESCO.LG","OKOMUOIL.LG","FIDELITYBK.LG","STERLINGNG.LG","WEMABANK.LG","JAIZBANK.LG","TRANSCORP.LG","TRANSPOWER.LG","AIRTELAFRI.LG","FLOURMILL.LG","HONYFLOUR.LG","VITAFOAM.LG","BERGER.LG","JULIUS.LG","CUTIX.LG","ETERNA.LG","TOTAL.LG","CONOIL.LG","MRS.LG","ARDOVA.LG","OANDO.LG","LIVESTOCK.LG","AIICO.LG","CUSTODIAN.LG","MANSARD.LG","CHAMS.LG","CWG.LG","AFRIPRUD.LG","UCAP.LG","FCMB.LG","UNITYBNK.LG"]
US_TICKERS = [t for t in ALL_TICKERS if ".LG" not in t]

LEDGER = "signals.csv"
HORIZON_MIN = 240
COOLDOWN_MIN = 60
TOP_N = 5
BATCH = 50

# ---------- Indicators ----------
def calc_rsi(close, period=14):
    d = close.diff()
    gain = d.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-d.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    return 100 - 100/(1 + gain/loss)

def load_ledger():
    cols = ["t", "signal_time", "entry", "exit", "ret_pct", "closed"]
    if os.path.exists(LEDGER):
        try:
            df = pd.read_csv(LEDGER)
            for c in cols:
                if c not in df.columns:
                    df[c] = None
            return df
        except:
            pass
    return pd.DataFrame(columns=cols)

def save_ledger(df):
    try:
        df.to_csv(LEDGER, index=False)
    except Exception as e:
        print("Ledger write fail:", e)

def get_market_regime():
    try:
        spy = yf.download("SPY", period="5d", interval="1d", progress=False)['Close']
        qqq = yf.download("QQQ", period="5d", interval="1d", progress=False)['Close']
        spy_pct = float((spy.iloc[-1]-spy.iloc[-2])/spy.iloc[-2]*100)
        qqq_pct = float((qqq.iloc[-1]-qqq.iloc[-2])/qqq.iloc[-2]*100)
        avg = (spy_pct+qqq_pct)/2
        if avg > 0.5: return "BULLISH 🟢", avg
        elif avg < -0.5: return "BEARISH 🔴", avg
        else: return "NEUTRAL 🟡", avg
    except:
        return "NEUTRAL 🟡", 0

def ai_score(rsi, vs_sma, residual, vr, regime):
    score = 50
    reasons = []
    if residual < -4: score += 25; reasons.append("Huge dislocation")
    elif residual < -2.5: score += 18; reasons.append("Strong dislocation")
    elif residual < -1.5: score += 10; reasons.append("Dislocation")
    if rsi < 20: score += 15; reasons.append("Extremely oversold")
    elif rsi < 30: score += 10; reasons.append("Oversold")
    elif rsi < 35: score += 5
    if vs_sma < -12: score += 10; reasons.append("Deep discount")
    elif vs_sma < -8: score += 6
    if vr > 2: score += 8; reasons.append("Panic vol 2x")
    elif vr > 1.5: score += 5
    elif vr < 0.7: score -= 8; reasons.append("Low vol")
    if "BEARISH" in regime: score -= 12; reasons.append("Market bearish")
    elif "BULLISH" in regime: score += 5
    return max(0, min(100, score)), ", ".join(reasons)

# ---------- Backtest ----------
def backtest():
    rows = []
    for i in range(0, len(US_TICKERS), BATCH):
        chunk = US_TICKERS[i:i+BATCH]
        try:
            df = yf.download(chunk, period="1y", interval="1d", progress=False, group_by='ticker', threads=True)
        except:
            continue
        for t in chunk:
            try:
                h = df[t] if len(chunk) > 1 else df
                close = h['Close'].dropna()
                if len(close) < 60: continue
                r = calc_rsi(close)
                sma20 = close.rolling(20).mean()
                vs = (close - sma20) / sma20 * 100
                fwd = close.shift(-5) / close * 100 - 100
                mask = (r < 32) & (vs < -8)
                for dt in close.index[mask]:
                    ret = fwd.loc[dt]
                    if pd.notna(ret):
                        rows.append(float(ret))
            except:
                continue
    if not rows:
        return "🔬 Backtest: no signals."
    s = pd.Series(rows)
    wr = (s > 0).mean()*100
    return f"🔬 BACKTEST 1y (RSI<32 & -8% vs SMA, 5d hold): {len(s)} signals | Win {wr:.1f}% | Avg {s.mean():+.2f}%"

last_alerted = {}
open_signals = []

def get_history(chunk):
    df = yf.download(chunk, period="5d", interval="15m", progress=False, group_by='ticker', threads=True)
    out = {}
    for t in chunk:
        try:
            h = df[t] if len(chunk) > 1 else df
            h = h.dropna()
            if 'Close' in h and len(h) >= 40:
                out[t] = h
        except:
            continue
    return out

def scan_once():
    global open_signals
    now = datetime.now(timezone.utc)
    ledger = load_ledger()
    regime, regime_pct = get_market_regime()

    prices, candidates = {}, []
    for i in range(0, len(ALL_TICKERS), BATCH):
        chunk = ALL_TICKERS[i:i+BATCH]
        try:
            hist = get_history(chunk)
        except:
            continue
        for t, h in hist.items():
            try:
                close = h['Close']
                last = float(close.iloc[-1]); prev = float(close.iloc[-2])
                prices[t] = last
                bar_ret = (last/prev-1)*100
                r = float(calc_rsi(close).iloc[-1])
                sma20_15 = float(close.rolling(20).mean().iloc[-1])
                vs_sma = (last - sma20_15)/sma20_15*100
                vol = float(h['Volume'].iloc[-1]); avg_vol = float(h['Volume'].rolling(20).mean().iloc[-1])
                vr = vol/avg_vol if avg_vol>0 else 1
                candidates.append({"t":t,"p":last,"rsi":r,"bar":bar_ret,"vs":vs_sma,"vr":vr})
            except:
                continue

    if not candidates:
        send_telegram("⚠️ Medallion Final: no data this cycle, retry 5m")
        return

    still_open, closed_rows = [], []
    for s in open_signals:
        p_now = prices.get(s["t"])
        if p_now is None:
            still_open.append(s); continue
        if (now - s["ts"]) < timedelta(minutes=HORIZON_MIN):
            still_open.append(s); continue
        ret = (float(p_now)/s["p"]-1)*100
        closed_rows.append({"t":s["t"],"signal_time":s["ts"].strftime("%Y-%m-%d %H:%M"),"entry":round(s["p"],2),"exit":round(float(p_now),2),"ret_pct":round(ret,2),"closed":True})
    open_signals = still_open
    if closed_rows:
        ledger = pd.concat([ledger, pd.DataFrame(closed_rows)], ignore_index=True)
        save_ledger(ledger)

    rets = np.array([c["bar"] for c in candidates])
    market = float(np.median(rets))
    spread = float(np.std(rets)) or 1.0

    buys = []
    for c in candidates:
        residual = c["bar"] - market
        c["res"] = residual
        cool = last_alerted.get(c["t"])
        if cool and (now - cool).total_seconds() < COOLDOWN_MIN*60:
            continue
        if residual < -1.5*spread and c["rsi"] < 35:
            sc, rsn = ai_score(c["rsi"], c["vs"], residual, c["vr"], regime)
            if sc >= 55:
                c["score"] = sc; c["reason"] = rsn; c["ts"] = now
                buys.append(c)
    buys = sorted(buys, key=lambda x: x["score"], reverse=True)[:TOP_N]
    for b in buys:
        last_alerted[b["t"]] = now
    open_signals += [{"t":b["t"],"p":b["p"],"ts":b["ts"]} for b in buys]

    # Message with Bamboo + Chaka links
    msg = f"🤖 MEDALLION 300 FINAL - AI QUANT\nMarket: {regime} ({regime_pct:+.2f}%) | Median 15m: {market:+.2f}% | Spread: {spread:.2f}%\n\n"
    if "BEARISH" in regime:
        msg += "⚠️ AI: Market bearish — only STRONG 💎, small size, tight stop.\n\n"
    elif "BULLISH" in regime:
        msg += "✅ AI: Market bullish — good for bounce plays.\n\n"

    if buys:
        msg += "🟢 AI QUANT BUY (Dislocation + Score):\n"
        for b in buys:
            flag = "🇳🇬" if ".LG" in b["t"] else "🇺🇸"
            strength = "STRONG 💎" if b["score"]>=75 else "WATCH 👀" if b["score"]>=65 else "RISKY ⚠️"
            clean_t = b["t"].replace(".LG","")
            tp = b["p"] * 1.10
            sl = b["p"] * 0.95
            bamboo = f"https://app.investbamboo.com/stock/{clean_t}"
            chaka = f"https://chaka.com/stocks/{clean_t}"
            msg += f"{flag} {b['t']} ${b['p']:.2f} RSI {b['rsi']:.0f} Res {b['res']:+.2f}% Score {b['score']:.0f}% {strength}\n  👉 {b['reason']} | Vol {b['vr']:.1f}x vs SMA {b['vs']:.1f}%\n  🎯 TP ${tp:.2f} (+10%) | 🛑 SL ${sl:.2f} (-5%)\n  🛒 Bamboo: {bamboo}\n  📈 Chaka: {chaka}\n\n"
    else:
        msg += "🟢 No high-quality dislocation now — AI say WAIT. No fake trades.\n"

    hist = pd.to_numeric(ledger["ret_pct"], errors='coerce').dropna()
    if len(hist) >= 5:
        msg += f"\n📈 LIVE SCORE: {(hist>0).mean()*100:.0f}% win over {len(hist)} closed | avg {hist.mean():+.2f}%"
    msg += "\n💡 Only STRONG 💎 + Bullish market = consider buy. Stop -5%."
    send_telegram(msg)
    print(f"[{now:%H:%M}] scan {len(candidates)} tickers, {len(buys)} buys, market {market:.2f}%")

bt = backtest()
print(bt)
send_telegram(f"✅ Medallion 300 FINAL is live!\n{bt}\nQuant + AI Score + Market filter active.")
while True:
    try:
        scan_once()
    except Exception as e:
        print("Scan error:", e)
    time.sleep(300)
