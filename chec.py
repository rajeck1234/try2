import yfinance as yf
import time

# Example stock list
stocks = ["HDFCBANK.NS", "INFY.NS", "RELIANCE.NS","MAZDOCK.NS","360ONE.NS","63MOONS.NS","TCS.NS","A2ZINFRA.NS","CONCORDBIO.NS","BSE.NS"]  # You can change this
prices_cache = {}

# -----------------------------
# Fetch Price
# -----------------------------
def fetch_price(symbol):
    try:
        ticker = yf.Ticker(symbol)

        # 1️⃣ Primary
        price = ticker.info.get("currentPrice")
        
        # 2️⃣ Fallback
        if price is None:
            print("fail")
            price = ticker.fast_info.get("last_price")

        # 3️⃣ Last fallback
        if price is None:
            print("fail")
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = hist["Close"].iloc[-1]

        print(f"{symbol} Price: {price}")
        return price

    except Exception as e:
        print("Fetch error:", symbol, e)
        return None


# -----------------------------
# Update Prices
# -----------------------------
def update_prices():
    global prices_cache
    while True:
        print("Updating prices...\n")
        
        for symbol in stocks:
            price = fetch_price(symbol)

            if price is not None:
                prices_cache[symbol] = float(price)
            else:
                print("fail")
                break
        print("\nUpdated Cache:", prices_cache)
        print(len(prices_cache))
        time.sleep(1)


# -----------------------------
# Run Test
# -----------------------------
if __name__ == "__main__":
    update_prices()
