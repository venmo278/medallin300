import yfinance as yf, pandas as pd, time, requests, os

TELEGRAM_TOKEN = os.getenv("8876434733:AAG2HGDf7_aYTvMMtYIPkyti_NuSwDG4U_A")
TELEGRAM_CHAT_ID = os.getenv("7817556351")

ALL_TICKERS = ["NVDA","AMD","CRWV","AVGO","TSM","ASML","AMAT","LRCX","KLAC","MRVL","ARM","SMCI","PLTR","SOUN","AAPL","MSFT","GOOGL","AMZN","META","TSLA","ORCL","ADBE","CRM","NOW","INTU","UBER","ABNB","APP","MSTR","COIN","HOOD","RBLX","DKNG","AFRM","UPST","SOFI","LCID","RIVN","IONQ","QBTS","RGTI","ASTS","JPM","V","MA","BAC","WFC","GS","MS","BLK","C","AXP","HD","LOW","COST","WMT","TGT","NKE","SBUX","MCD","DIS","PEP","KO","PG","JNJ","UNH","PFE","LLY","MRK","ABBV","TMO","XOM","CVX","COP","SLB","CAT","DE","HON","GE","BA","LMT","UNP","FDX","UPS","DAL","UAL","MAR","HLT","BKNG","LIN","SHW","APD","NUE","FCX","NEM","EMR","ETN","PH","ITW","TXN","QCOM","ADI","NXPI","ON","CDNS","SNPS","FTNT","PANW","CRWD","ZS","DDOG","NET","SNOW","MDB","AI","PATH","SHOP","SQ","PYPL","DASH","PINS","SNAP","RDDT","NFLX","IBM","INTC","CSCO","VZ","T","CVS","WBA","KHC","GIS","CL","KMB","MO","PM","RIO","BHP","VALE","GOLD","EWJ","EWZ","EEM","FXI","SPY","QQQ","IWM","DIA","VOO","ARKK","SMH","SOXX","XLF","XLE","XLV","XLK","GLD","SLV","USO","TLT","BABA","JD","PDD","BIDU","NIO","LI","XPEV","SE","GRAB","MELI","NU","NVO","OXY","EOG","MPC","PSX","VLO","HAL","BKR","APA","DVN","FANG","EQT","CTRA","MRO","CHTR","CMCSA","WBD","PARA","FOX","NWSA","LUMN","BBY","GME","AMC","BB","NOK","ERIC","SIRI","CROX","UAA","LULU","DECK","SKX","EL","ULTA","DG","DLTR","KR","ACI","SFM","TSCO","RH","WSM","TPX","LEG","WHR","NVR","LEN","DHI","PHM","KBH","BZH","TOL","MTCH","BMBL","GRND","WYNN","LVS","MGM","DANGCEM.LG","MTNN.LG","GTCO.LG","ZENITHBANK.LG","UBA.LG","ACCESSCORP.LG","BUACEMENT.LG","BUAFOODS.LG","SEPLAT.LG","ARADEL.LG","FBNH.LG","STANBIC.LG","DANGSUGAR.LG","NASCON.LG","NESTLE.LG","UNILEVER.LG","CADBURY.LG","NB.LG","GUINNESS.LG","INTBREW.LG","PRESCO.LG","OKOMUOIL.LG","FIDELITYBK.LG","STERLINGNG.LG","WEMABANK.LG","JAIZBANK.LG","TRANSCORP.LG","TRANSPOWER.LG","AIRTELAFRI.LG","FLOURMILL.LG","HONYFLOUR.LG","VITAFOAM.LG","BERGER.LG","JULIUS.LG","CUTIX.LG","ETERNA.LG","TOTAL.LG","CONOIL.LG","MRS.LG","ARDOVA.LG","OANDO.LG","LIVESTOCK.LG","AIICO.LG","CUSTODIAN.LG","MANSARD.LG","CHAMS.LG","CWG.LG","AFRIPRUD.LG","UCAP.LG","FCMB.LG","UNITYBNK.LG"]

def send_telegram(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
    except: pass

def calc_rsi(data, period=14):
    delta=data.diff(); gain=(delta.where(delta>0,0)).rolling(window=period).mean(); loss=(-delta.where(delta<0,0)).rolling(window=period).mean(); rs=gain/loss; return 100-(100/(1+rs))

def scan_once():
    print(f"Scanning 300...")
    buys=[]; sells=[]
    for i in range(0, len(ALL_TICKERS), 50):
        chunk=ALL_TICKERS[i:i+50]
        try:
            df=yf.download(chunk, period="1mo", interval="1d", progress=False, group_by='ticker', threads=True)
            for ticker in chunk:
                try:
                    hist=df if len(chunk)==1 else df[ticker]
                    hist=hist.dropna(); close=hist['Close']
                    if len(close)<20: continue
                    last=float(close.iloc[-1]); prev=float(close.iloc[-2]); pct=((last-prev)/prev)*100
                    sma20=float(close.rolling(20).mean().iloc[-1]); vs_sma=((last-sma20)/sma20)*100
                    rsi=float(calc_rsi(close).iloc[-1])
                    vol=float(hist['Volume'].iloc[-1]); avg_vol=float(hist['Volume'].rolling(20).mean().iloc[-1]); vr=vol/avg_vol if avg_vol>0 else 1
                    if (rsi<32 and vs_sma<-8) or (pct<-4 and rsi<35) or (rsi<30 and vr>1.5):
                        buys.append({"t":ticker,"p":last,"pct":pct,"rsi":rsi,"vs":vs_sma,"vr":vr})
                    if (rsi>72 and vs_sma>10) or (pct>6 and vr>2.5) or (rsi>75):
                        sells.append({"t":ticker,"p":last,"pct":pct,"rsi":rsi,"vs":vs_sma,"vr":vr})
                except: continue
        except: continue
    buys=sorted(buys, key=lambda x: x['rsi'])[:5]
    sells=sorted(sells, key=lambda x: x['rsi'], reverse=True)[:5]
    msg="📊 MEDALLION 300 - 5 MINS\n\n"
    if buys:
        msg+="🟢 BUY / BOUNCE:\n"
        for b in buys:
            flag="🇳🇬" if ".LG" in b['t'] else "🇺🇸"
            msg+=f"{flag} {b['t']} ${b['p']:.2f} {b['pct']:+.2f}% RSI {b['rsi']:.0f} vs SMA {b['vs']:.1f}% Vol {b['vr']:.1f}x\n"
    else:
        msg+="🟢 BUY: No oversold now\n"
    msg+="\n"
    if sells:
        msg+="🔴 SELL / AVOID:\n"
        for s in sells:
            flag="🇳🇬" if ".LG" in s['t'] else "🇺🇸"
            msg+=f"{flag} {s['t']} ${s['p']:.2f} {s['pct']:+.2f}% RSI {s['rsi']:.0f} vs SMA {s['vs']:.1f}% Vol {s['vr']:.1f}x\n"
    else:
        msg+="🔴 SELL: No overbought\n"
    print(msg); send_telegram(msg)

send_telegram("✅ Medallion 300 BUY/SELL don start! Every 5 mins.")
while True:
    try: scan_once()
    except Exception as e: print(e)
    time.sleep(300)
