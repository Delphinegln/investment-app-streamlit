import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import warnings

# -------------------- CONFIGURATION --------------------

# Define the analysis period (5 years)
start_date = datetime.date.today() - datetime.timedelta(days=5*365)
start_date = start_date.strftime("%Y-%m-%d")
end_date = datetime.date.today().strftime("%Y-%m-%d")

# Tickers and asset classes
ticker_symbols = ["AAPL","TSLA","JNJ","NVDA","AIR.PA","SIE.DE","OR.PA","NESN.SW","TCS.NS","VALE","BABA","NIO","VOO",
                  "VEA","VWO","ARKK","FBALX","VBIAX","TLT","BND","IEI","SHV","GLD","BTC-USD","AMZN","GOOGL","META",
                  "PYPL","DIS","PEP","V","NFLX","INTC","WMT","VOW3.DE","BAYN.DE","ASML.AS","LHA.DE","BMW.DE",
                  "QQQ","SPY","EFA","IEMG","XLF","XLE"]

safe_assets = ["VOO","VEA","VWO","ARKK","FBALX","VBIAX","TLT","BND","IEI","SHV","QQQ","SPY","EFA","IEMG","XLF","XLE"]
high_growth_assets = ["AAPL", "TSLA", "JNJ", "NVDA", "AMZN", "GOOGL", "META","PYPL", "DIS", "PEP", "V", "NFLX", "INTC", "WMT",
                      "TCS.NS", "VALE", "BABA", "NIO","VOW3.DE", "BAYN.DE", "ASML.AS", "LHA.DE", "BMW.DE","AIR.PA", "SIE.DE", 
                      "OR.PA", "NESN.SW","GLD","BTC-USD"]

# -------------------- DATA LOADING --------------------

@st.cache_data(show_spinner=True)
def load_data():
    volatility_data = []
    ticker_names = {}
    all_data = pd.DataFrame()

    for ticker_symbol in ticker_symbols:
        try:
            data = yf.download(ticker_symbol, start=start_date, end=end_date, progress=False)
            ticker_info = yf.Ticker(ticker_symbol)
            company_name = ticker_info.info.get('longName', 'Unknown') 
            ticker_names[ticker_symbol] = company_name

            if not data.empty:
                data['Daily_Return'] = data['Close'].pct_change()
                annual_volatility = data['Daily_Return'].std() * np.sqrt(252)
                annual_return = data['Daily_Return'].mean() * 252

                volatility_data.append({
                    "Ticker": ticker_symbol,
                    "Annual_Volatility": annual_volatility,
                    "Annual_Return": annual_return
                })

                data = data[['Close']].rename(columns={"Close": f"{ticker_symbol}_Close"})
                all_data = pd.merge(all_data, data, left_index=True, right_index=True, how='outer') if not all_data.empty else data

        except Exception as e:
            st.warning(f"Error with {ticker_symbol}: {e}")
            continue

    all_data = all_data.dropna()
    return volatility_data, all_data, ticker_names

# -------------------- ANALYSIS FUNCTIONS --------------------

def map_user_risk_to_vol_filter(risk_profile):
    if risk_profile == "Conservative":
        return lambda vol: vol < 0.2
    elif risk_profile == "Balanced":
        return lambda vol: 0.2 <= vol < 0.4
    elif risk_profile == "Aggressive":
        return lambda vol: vol >= 0.4
    return lambda vol: False

def determine_num_products(amount):
    if amount >= 500_000:
        return 10
    elif amount >= 100_000:
        return 7
    elif amount >= 10_000:
        return 5
    return 3

def suggest_products(volatility_data, risk_profile, amount, desired_return, horizon):
    vol_filter = map_user_risk_to_vol_filter(risk_profile)
    filtered = [item for item in volatility_data if vol_filter(item["Annual_Volatility"]) and item["Annual_Return"] >= desired_return/100]
    num_products = determine_num_products(amount)

    if horizon == "Short":
        num_safe = int(0.8 * num_products)
        safe = [item for item in filtered if item["Ticker"] in safe_assets]
        rest = [item for item in filtered if item["Ticker"] not in safe_assets]
        final = safe[:num_safe] + rest[:num_products - num_safe]

    elif horizon == "Medium":
        final = filtered[:num_products]

    elif horizon == "Long":
        num_high = int(0.7 * num_products)
        high = [item for item in filtered if item["Ticker"] in high_growth_assets]
        rest = [item for item in filtered if item["Ticker"] not in high_growth_assets]
        final = high[:num_high] + rest[:num_products - num_high]

    else:
        final = filtered[:num_products]

    return final[:num_products]

# -------------------- STREAMLIT UI --------------------

st.set_page_config(page_title="Smart Investment Assistant", layout="centered")
st.title("🎩 Abracadabra! Time to Make Your Investments Grow Faster Than Your WiFi Speed!")

st.markdown("""  
🎯 Welcome in your personal investment allocation assistant!

This tool has been designed to help you select an investment portfolio suited to your profile. By answering a few simple questions about your amount to invest, your risk tolerance, your investment horizon and your desired return, you'll get:

✅ A selection of financial products (equities, ETFs, funds, bonds, crypto, etc.) corresponding to your profile.  
✅ An estimate of your portfolio's average volatility and potential return.  
✅ A proposal adapted to the amount invested, with an adjusted number of products for greater diversification.  

This simulator uses historical financial data from the last 5 years to assess asset performance and volatility.

🔐 No personal data is stored: everything remains confidential and local to your session.
""")

with st.form("investment_form"):
    amount = st.number_input("💰 Amount to invest (€)", min_value=1000.0, step=1000.0, value=1000.0, format="%.2f", 
                            help="Enter the amount you want to invest (starting at 1000€).")
    risk_profile = st.selectbox("📊 Risk Profile", ["Conservative", "Balanced", "Aggressive"])
    horizon = st.selectbox("🕒 Investment Horizon", ["Short", "Medium", "Long"])
    
    # 🎯 Curseur pour le rendement
    desired_return = st.slider("🎯 Desired Annual Return (%)", min_value=1.0, max_value=40.0, step=0.5, value=6.0, 
                               help="Select your target annual return.")
    
    submitted = st.form_submit_button("Get Magic!")

if submitted:
    with st.spinner("Fetching data and computing suggestions... Please wait. ⏳"):
        volatility_data, all_data, ticker_names = load_data()
        suggestions = suggest_products(volatility_data, risk_profile, amount, desired_return, horizon)

    if suggestions:
        st.subheader("📈 Recommended Portfolio")
        for asset in suggestions:
            st.write(f"- **{asset['Ticker']}** ({ticker_names.get(asset['Ticker'], 'Unknown')}): "
                     f"Volatility: `{asset['Annual_Volatility']:.2%}` | Return: `{asset['Annual_Return']:.2%}`")

        avg_vol = np.mean([a["Annual_Volatility"] for a in suggestions])
        avg_ret = np.mean([a["Annual_Return"] for a in suggestions])
        st.markdown(f"**Average Portfolio Volatility:** `{avg_vol:.2%}`")
        st.markdown(f"**Average Portfolio Return:** `{avg_ret:.2%}`")

        # Adding a conclusion text with variables, each item on a new line
        st.markdown(f"""
        🎉 Congratulations! Based on the details you provided, here is your customized portfolio:

        ✅ **Investment Amount**: €{amount}  
        ✅ **Risk Profile**: {risk_profile}  
        ✅ **Investment Horizon**: {horizon}  
        ✅ **Desired Return**: {desired_return}% per year  

        📊 **Average Portfolio Volatility**: `{avg_vol:.2%}`  
        📈 **Average Portfolio Return**: `{avg_ret:.2%}`  

        We hope this helps you on your investment journey! 💪
        """)
    else:
        st.markdown("**Sorry, no results found according to your criteria. Please try adjusting your filters and try again!**")
