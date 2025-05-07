import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import numpy as np
import matplotlib.pyplot as plt
from fuzzywuzzy import fuzz
import warnings

# Dates
start_date = datetime.date.today() - datetime.timedelta(days=5*365)
start_date = start_date.strftime("%Y-%m-%d")
end_date = datetime.date.today().strftime("%Y-%m-%d")

# Tickers
ticker_symbols = ["AAPL","TSLA","JNJ","NVDA","AIR.PA","SIE.DE","OR.PA","NESN.SW","TCS.NS","VALE","BABA","NIO","VOO","VEA","VWO","ARKK","FBALX","VBIAX","TLT","BND","IEI","SHV","GLD","BTC-USD","AMZN","GOOGL","META","PYPL","DIS","PEP","V","NFLX","INTC","WMT","VOW3.DE","BAYN.DE","ASML.AS","LHA.DE","BMW.DE","QQQ","SPY","EFA","IEMG","XLF","XLE"]
safe_assets = ["VOO","VEA","VWO","ARKK","FBALX","VBIAX","TLT","BND","IEI","SHV","QQQ","SPY","EFA","IEMG","XLF","XLE"]
high_growth_assets = ["AAPL", "TSLA", "JNJ", "NVDA", "AMZN", "GOOGL", "META","PYPL", "DIS", "PEP", "V", "NFLX", "INTC", "WMT","TCS.NS", "VALE", "BABA", "NIO","VOW3.DE", "BAYN.DE", "ASML.AS", "LHA.DE", "BMW.DE","AIR.PA", "SIE.DE", "OR.PA", "NESN.SW","GLD","BTC-USD"]

# Préchargement des données
@st.cache_data(show_spinner=True)
def load_data():
    all_data = pd.DataFrame()
    volatility_data = []
    ticker_names = {}

    for ticker in ticker_symbols:
        try:
            data = yf.download(ticker, start=start_date, end=end_date, progress=False)
            info = yf.Ticker(ticker).info
            company_name = info.get('longName', 'Unknown')
            ticker_names[ticker] = company_name

            if not data.empty:
                data['Daily_Return'] = data['Close'].pct_change()
                ann_vol = data['Daily_Return'].std() * np.sqrt(252)
                ann_ret = data['Daily_Return'].mean() * 252

                volatility_data.append({
                    "Ticker": ticker,
                    "Annual_Volatility": ann_vol,
                    "Annual_Return": ann_ret
                })

                if all_data.empty:
                    all_data = data[['Close']]
                else:
                    all_data = pd.merge(all_data, data[['Close']], left_index=True, right_index=True, how='outer', suffixes=('', f'_{ticker}'))

                all_data = all_data.rename(columns={'Close': f'{ticker}_Close'})
        except Exception as e:
            st.warning(f"Erreur chargement {ticker} : {e}")
    return all_data.dropna(), volatility_data, ticker_names

all_data, volatility_data, ticker_names = load_data()

# Fonctions
def map_user_risk_to_vol_filter(risk):
    risk = risk.lower()
    if risk == "conservative": return lambda vol: vol < 0.2
    elif risk == "balanced": return lambda vol: 0.2 <= vol < 0.4
    elif risk == "aggressive": return lambda vol: vol >= 0.4
    else: return lambda vol: False

def determine_num_products(amount):
    l = [[10_000, 5], [100_000, 7], [500_000, 10]]
    num_products = 3
    for threshold, n in reversed(l):
        if amount >= threshold:
            return n
    return num_products

def suggest_products(volatility_data, risk_profile, amount, desired_return, horizon):
    vol_filter = map_user_risk_to_vol_filter(risk_profile)
    filtered = [p for p in volatility_data if vol_filter(p["Annual_Volatility"]) and p["Annual_Return"] >= desired_return/100]

    if horizon == "short":
        num_safe = int(0.8 * determine_num_products(amount))
        safe_filtered = [p for p in filtered if p["Ticker"] in safe_assets]
        other_filtered = [p for p in filtered if p["Ticker"] not in safe_assets]
        suggested = safe_filtered[:num_safe] + other_filtered[:determine_num_products(amount) - num_safe]
    elif horizon == "long":
        num_growth = int(0.7 * determine_num_products(amount))
        growth_filtered = [p for p in filtered if p["Ticker"] in high_growth_assets]
        other_filtered = [p for p in filtered if p["Ticker"] not in high_growth_assets]
        suggested = growth_filtered[:num_growth] + other_filtered[:determine_num_products(amount) - num_growth]
    else:
        suggested = filtered[:determine_num_products(amount)]

    num_products = determine_num_products(amount)
    avg_vol = np.mean([p["Annual_Volatility"] for p in suggested[:num_products]])
    avg_ret = np.mean([p["Annual_Return"] for p in suggested[:num_products]])

    return suggested[:num_products], avg_vol, avg_ret

# Interface Streamlit
st.title("🎯 Personal Investment Allocation Assistant")
st.markdown("This tool suggests a portfolio tailored to your profile based on historical data (last 5 years).")

st.sidebar.header("Your Investment Profile")
amount = st.sidebar.number_input("💰 Amount to invest (€)", min_value=100.0, step=100.0)
risk_profile = st.sidebar.selectbox("📈 Risk Profile", ["Conservative", "Balanced", "Aggressive"])
horizon = st.sidebar.selectbox("⏳ Investment Horizon", ["Short", "Medium", "Long"])
desired_return = st.sidebar.number_input("🎯 Desired Annual Return (%)", min_value=0.1, step=0.1)

if st.sidebar.button("Generate Portfolio"):
    suggestions, avg_volatility, avg_return = suggest_products(volatility_data, risk_profile, amount, desired_return, horizon)

    st.subheader(f"📊 Portfolio Suggestions for a {risk_profile} investor with {amount:.0f} €")
    for p in suggestions:
        company = ticker_names.get(p["Ticker"], "Unknown")
        st.markdown(f"- **{p['Ticker']}** ({company}) | Volatility: `{p['Annual_Volatility']:.2%}` | Return: `{p['Annual_Return']:.2%}`")

    st.markdown(f"**Average Portfolio Volatility:** `{avg_volatility:.2%}`")
    st.markdown(f"**Average Portfolio Return:** `{avg_return:.2%}`")

    # Graph
    tickers = [p["Ticker"] for p in suggestions]
    filtered = all_data[[f"{ticker}_Close" for ticker in tickers]]
    normed = filtered / filtered.iloc[0] * 100

    fig, ax = plt.subplots(figsize=(10, 6))
    normed.plot(ax=ax)
    ax.set_title("📈 Price Evolution of Suggested Products (Base 100)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Normalized Price")
    ax.legend(tickers, loc="best", fontsize='small', ncol=3)
    ax.grid(True)
    st.pyplot(fig)
