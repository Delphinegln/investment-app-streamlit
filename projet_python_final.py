! pip install streamlit
! pip install yfinance
! pip install --upgrade yfinance
! pip install fuzzywuzzy[speedup]
import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import numpy as np
import warnings
from fuzzywuzzy import fuzz

# Define the period
start_date = datetime.date.today() - datetime.timedelta(days=5*365)
start_date = start_date.strftime("%Y-%m-%d")
end_date = datetime.date.today().strftime("%Y-%m-%d")

# Define the tickers
ticker_symbols = ["AAPL","TSLA","JNJ","NVDA","AIR.PA","SIE.DE","OR.PA","NESN.SW","TCS.NS","VALE","BABA","NIO","VOO","VEA","VWO","ARKK","FBALX","VBIAX","TLT","BND","IEI","SHV","GLD","BTC-USD","AMZN","GOOGL","META","PYPL","DIS","PEP","V","NFLX","INTC","WMT","VOW3.DE","BAYN.DE","ASML.AS","LHA.DE","BMW.DE","QQQ","SPY","EFA","IEMG","XLF","XLE"]

# Create a dictionary to store tickers and full company names
ticker_names = {}

# Define asset classes
safe_assets = ["VOO","VEA","VWO","ARKK","FBALX","VBIAX","TLT","BND","IEI","SHV","QQQ","SPY","EFA","IEMG","XLF","XLE"]
high_growth_assets = ["AAPL", "TSLA", "JNJ", "NVDA", "AMZN", "GOOGL", "META","PYPL", "DIS", "PEP", "V", "NFLX", "INTC", "WMT","TCS.NS", "VALE", "BABA", "NIO","VOW3.DE", "BAYN.DE", "ASML.AS", "LHA.DE", "BMW.DE","AIR.PA", "SIE.DE", "OR.PA", "NESN.SW","GLD","BTC-USD"]

all_data = pd.DataFrame()
volatility_data = []

# Loop through the tickers
for ticker_symbol in ticker_symbols:
    try:
        data = yf.download(ticker_symbol, start=start_date, end=end_date, progress=False)

        # Obtain the company's full name
        ticker_info = yf.Ticker(ticker_symbol)
        company_name = ticker_info.info.get('longName', 'Unknown')
        ticker_names[ticker_symbol] = company_name

        if not data.empty:
            data['Daily_Return'] = data['Close'].pct_change()

            # Calculate annual volatility and return
            annual_volatility = data['Daily_Return'].std() * np.sqrt(252)
            annual_return = data['Daily_Return'].mean() * 252

            #print(f"{ticker_symbol} - Volatility: {annual_volatility:.4f}, Return: {annual_return:.4f}")

            # Store info for later filtering
            volatility_data.append({
                "Ticker": ticker_symbol,
                "Annual_Volatility": annual_volatility,
                "Annual_Return": annual_return
            })

            # Merge closing prices into all_data
            # Check if column already exists
            if all_data.empty:
                all_data = data[['Close']]
            else:
                all_data = pd.merge(all_data, data[['Close']], left_index=True, right_index=True, how='outer', suffixes=('', f'_{ticker_symbol}'))
             # Rename column
            all_data = all_data.rename(columns={'Close': f'{ticker_symbol}_Close'})
        else:
            print(f"No data found for ticker: {ticker_symbol}")

    except Exception as e:
        print(f"Error fetching data for {ticker_symbol}: {e}")

# Remove rows with missing values
all_data = all_data.dropna()
all_data.to_csv('daily_prices_combined.csv')
#print("Combined daily prices saved to daily_prices_combined.csv")


# Function to map user profile to a volatility filter
def map_user_risk_to_vol_filter(risk_profile):
    risk_profile = risk_profile.lower()
    if risk_profile == "conservative":
        return lambda vol: vol < 0.2
    elif risk_profile == "balanced":
        return lambda vol: 0.2 <= vol < 0.4
    elif risk_profile == "aggressive":
        return lambda vol: vol >= 0.4
    else:
        return lambda vol: False


# Function to request user info
def get_user_input():
      # Print the welcome message before asking for input
    print("🎯 Welcome in your personal investment allocation assistant!\n")
    print("This tool has been designed to help you select an investment portfolio suited to your profile. By answering a few simple questions about your amount to invest, your risk tolerance, your investment horizon and your desired return, you'll get:\n")
    print("✅ A selection of financial products (equities, ETFs, funds, bonds, crypto, etc.) corresponding to your profile.")
    print("✅ An estimate of your portfolio's average volatility and potential return.")
    print("✅ A proposal adapted to the amount invested, with an adjusted number of products for greater diversification.\n")
    print("This simulator uses historical financial data from the last 5 years to assess asset performance and volatility.\n")
    print("🔐 No personal data is stored: everything remains confidential and local to your session.\n")
    print("\n--- Investment Profile ---")

    # Loop to validate the amount
    while True:
        try:
            amount = float(input("Amount to invest (€): "))
            if amount > 0:
                break
            else:
                print("Please enter a positive amount.")
        except ValueError:
            print("Please enter a valid number.")

    # Loop to validate the risk profile
    while True:
        risk_profile = input("Risk profil (Conservative, Balanced, Aggressive): ").lower()
        options = ["conservative", "balanced", "aggressive"]
        best_match = max(options, key=lambda x: fuzz.ratio(risk_profile, x))
        if fuzz.ratio(risk_profile, best_match) > 80:  # Similarity threshold
            risk_profile = best_match
            break
        else:
            print("Invalid risk profile. Please choose from Conservative, Balanced or Aggressive.")

    # Loop to validate the horizon with spelling correction
    while True:
        horizon = input("Horizon (Short, Medium, Long): ").lower()
        options = ["short", "medium", "long"]
        best_match = max(options, key=lambda x: fuzz.ratio(horizon, x))
        if fuzz.ratio(horizon, best_match) > 80:  # Similarity threshold
            horizon = best_match
            break
        else:
            print("Invalid horizon. Please choose from Short, Medium or Long.")


    # Loop to validate the desired return
    while True:
        try:
            desired_return = float(input("Desired return (% per year): "))
            if desired_return > 0:
                break
            else:
                print("Please enter a positive return.")
        except ValueError:
            print("Please enter a valid number.")

    return amount, risk_profile, horizon, desired_return


# Determine how many products to offer based on the amount
def determine_num_products(amount):
    l = [[10_000, 5], [100_000, 7], [500_000, 10]]
    num_products = 3  # default value
    for i in range(len(l)-1, -1, -1):
        if l[i][0] <= amount:
            num_products = l[i][1]
            break
    return num_products


# Suggest products based on profile and amount
def suggest_products(volatility_data, risk_profile, amount,desired_return, horizon):
    vol_filter = map_user_risk_to_vol_filter(risk_profile)
    filtered = [item for item in volatility_data if vol_filter(item["Annual_Volatility"]) and item["Annual_Return"] >= desired_return/100]

    # Filter based on horizon
    if horizon == "short":
        # 80% safe assets
        num_safe_assets = int(0.8 * determine_num_products(amount))
        safe_assets_filtered = [item for item in filtered if item["Ticker"] in safe_assets]
        other_assets_filtered = [item for item in filtered if item["Ticker"] not in safe_assets]

        # Proritize safe assets
        suggest_products = safe_assets_filtered[:num_safe_assets] + other_assets_filtered[:determine_num_products(amount) - num_safe_assets]
    elif horizon == "medium":
        # No specific filtering, use the originial logic
        suggest_products = filtered[:determine_num_products(amount)]
    elif horizon == "long":
      # 70% high growth asset
      num_high_growth_assets = int(0.7 * determine_num_products(amount))
      high_growth_assets_filtered = [item for item in filtered if item["Ticker"] in high_growth_assets]
      other_assets_filtered = [item for item in filtered if item["Ticker"] not in high_growth_assets]

      # Proritize high growth assets
      suggest_products = high_growth_assets_filtered[:num_high_growth_assets] + other_assets_filtered[:determine_num_products(amount) - num_high_growth_assets]
    else:
      suggest_products = []


    # Sort by decreasing return
    filtered.sort(key=lambda x: x["Annual_Return"], reverse=True)

    # Number of products to offer
    num_products = determine_num_products(amount)

    # Calculate average volatility and average return
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        avg_volatility = np.mean([p["Annual_Volatility"] for p in suggest_products[:num_products]])
        avg_return = np.mean([p["Annual_Return"] for p in suggest_products[:num_products]])

    print(f"\n Recommendations for a {risk_profile.capitalize()} with an investment of {amount:.0f} € :")
    if suggest_products:
        for p in suggest_products[:num_products]:
            company_name = ticker_names.get(p['Ticker'], 'Unknown')
            print(f"- {p['Ticker']} ({company_name}) | Volatility: {p['Annual_Volatility']:.2%} | Annual Return: {p['Annual_Return']:.2%}")
        # Display average volatility and average return
        print(f"Average portfolio volatility : {avg_volatility:.2%}")
        print(f"Average portfolio return : {avg_return:.2%}")


    else:
        print("None of the results will fit you perfectly, but here are the most relevant recommendations!")
        volatility_data.sort(key=lambda x: abs(x["Annual_Return"] - (desired_return / 100)), reverse=False)
        num_products = determine_num_products(amount)
        for p in volatility_data[:num_products]:
            print(f"- {p['Ticker']} | Volatility: {p['Annual_Volatility']:.2%} | Annual Return: {p['Annual_Return']:.2%}")
        with warnings.catch_warnings():
          warnings.simplefilter("ignore", category=RuntimeWarning)
          avg_volatility = np.mean([p["Annual_Volatility"] for p in volatility_data[:num_products]])
          avg_return = np.mean([p["Annual_Return"] for p in volatility_data[:num_products]])
        print(f"Average portfolio volatility : {avg_volatility:.2%}")
        print(f"Average portfolio return : {avg_return:.2%}")

    # Get suggested tickers
    num_products = determine_num_products(amount)
    suggested_tickers = [p['Ticker'] for p in suggest_products[:num_products]] # tickers selected

    # Filter all_data to include only suggested tickers
    filtered_data = all_data[[f'{ticker}_Close' for ticker in suggested_tickers]]


# Execution
if __name__ == "__main__":
    while True:  # Beginning of the while loop
        amount, risk_profile, horizon, desired_return = get_user_input()
        suggest_products(volatility_data, risk_profile, amount, desired_return, horizon)

        another_simulation = input("Do you want to perform another simulation? (Yes/No): ").lower()
        if another_simulation != "yes":
            break  # Exit the while loop if the user does not want to restart

