from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import yfinance as yf
import os
import json
import threading
import time
import requests
app = Flask(__name__, static_folder="public")
CORS(app)
import time
PORT = int(os.environ.get("PORT", 3000))

print("CURRENT WORKING DIR:", os.getcwd())
import asyncio
import aiohttp
BASE_URL = "https://groww.in/v1/api/stocks_data/v1/accord_points/exchange/NSE/segment/CASH/latest_prices_ohlc/{}"

# BASE_URL = "https://groww.in/v1/api/stocks_data/v1/tr_live_book/exchange/NSE/segment/CASH/{}/latest"

MAX_CONCURRENT_REQUESTS = 100
SEM = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
# -----------------------------
# JSON Helpers
# -----------------------------
def load_json(file, default):
    try:
        with open(file) as f:
            return json.load(f)
    except:
        return default



def save_json(file, data):
    # print(file)
    # print(data)
    with open(file, "w") as f:
        # print("check")
        # print(file)
        json.dump(data, f, indent=2)
    # print("Full file path:", os.path.abspath(file))
    # with open(file, "r") as f:
    #     content = json.load(f)   # load json data
    #     print("JSON file content:")
    #     print(content)
# -----------------------------
# Load Files
# -----------------------------
stocks = load_json("stocks.json", [])
portfolio = load_json("portfolio.json", [])
prices_cache = load_json("prices.json", {})
# -----------------------------
# Load CSV Momentum Stocks
# -----------------------------
import pandas as pd
import logging

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

df = pd.read_csv("ind_copy.csv")

if "Symbol" not in df.columns:
    raise Exception("CSV must contain 'Symbol' column")

def clean_symbol(symbol):
    symbol = str(symbol).strip()
    symbol = symbol.replace("$", "")
    symbol = symbol.replace("-", "")
    return symbol + ".NS"

stocks1 = [clean_symbol(s) for s in df["Symbol"].tolist()]

print("Momentum stock list loaded:", len(stocks1))


# -----------------------------
# ⭐ BEST PRICE FETCH FUNCTION
# -----------------------------
def fetch_price(symbol):

    try:
        ticker = yf.Ticker(symbol)

        # 1️⃣ Primary
        price = ticker.info.get("currentPrice")

        # 2️⃣ Fallback
        
        if price is None:
            # print("fail")
            price = ticker.fast_info.get("last_price")

        # 3️⃣ Last fallback
        if price is None:
            # print("fail")
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = hist["Close"].iloc[-1]
        # print(price)
        return price

    except Exception as e:
        print("Fetch error:", symbol, e)
        return None


# -----------------------------
# Update Prices From Yahoo
# -----------------------------
def update_prices():
    global prices_cache

    print("Updating prices...")

    for symbol in stocks:

        price = fetch_price(symbol)

        if price:
            prices_cache[symbol] = float(price)
            
    save_json("prices.json", prices_cache)


# -----------------------------
# Background Scheduler
# -----------------------------
def scheduler():
    while True:
        update_prices()
        time.sleep(1)

momentum_30_cache = []
momentum_3min_cache = []
momentum_30_price_cache = []
momentum_3min_price_cache = []

last_10_cycles = load_json("last_10_cycles.json", [])


async def fetch_price_async(session, symbol):

    grow_symbol = symbol.replace(".NS", "")

    url = BASE_URL.format(grow_symbol)

    try:
        async with SEM:
            async with session.get(url) as response:
                data = await response.json()
                # print(data)
                # best_sell = data.get("sellBook", {}).get("1", {}).get("price")
                ltp_price = data.get("ltp")
                # print(symbol)
                # print(ltp_price)
                if ltp_price:
                    return symbol, float(ltp_price)

                return symbol, 0

                # if best_sell is not None:
                #     return symbol, float(best_sell)

                # return symbol, 0

    except:
        return symbol, 0


async def fetch_all_prices_async():

    prices = {}

    connector = aiohttp.TCPConnector(
        limit=MAX_CONCURRENT_REQUESTS,
        ttl_dns_cache=300,
        ssl=False
    )

    timeout = aiohttp.ClientTimeout(total=5)

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout
    ) as session:

        tasks = [fetch_price_async(session, symbol) for symbol in stocks1]

        results = await asyncio.gather(
            *tasks,
            return_exceptions=False
        )

        for symbol, price in results:
            prices[symbol] = price

    return prices



# def fetch_all_prices():
#     return asyncio.run(fetch_all_prices_async())


def calculate_momentum(start, end):

    results = []
    # print("0")
    for stock in start:
        if stock in end and start[stock] != 0:
            change = ((end[stock] - start[stock]) / start[stock]) * 100
            results.append({
                "name": stock,
                "price": end[stock],
                "change": round(change,3)
            })

    results.sort(key=lambda x: x["change"], reverse=True)
    return results

def calculate_continuous_price_raise(cycles):
    
    results = []

    if len(cycles) < 5:
        return []

    stocks = cycles[0].keys()

    for stock in stocks:

        increases = []
        valid = True

        for i in range(len(cycles) - 1):

            start_price = cycles[i].get(stock)
            end_price = cycles[i + 1].get(stock)

            if not start_price or not end_price:
                valid = False
                break

            diff = end_price - start_price

            if diff < 0:   # ❌ if price falls, remove stock
                valid = False
                break

            increases.append(diff)

        if valid and len(increases) > 0:
            avg_increase = sum(increases) / len(increases)

            results.append({
                "name": stock,
                "price": cycles[-1][stock],
                "diff": round(avg_increase, 3)
            })

    results.sort(key=lambda x: x["diff"], reverse=True)

    return results[:5]


def calculate_static_momentum(cycles):
    
    results = []
   
    if len(cycles) < 2:
        return []

    start_cycle = cycles[0]
    end_cycle = cycles[-1]

    for stock in start_cycle:

        if stock in end_cycle and start_cycle[stock] != 0:

            start_price = start_cycle[stock]
            end_price = end_cycle[stock]

            change = ((end_price - start_price) / start_price) * 100

            results.append({
                "name": stock,
                "price": end_price,
                "change": round(change, 3)
            })

    results.sort(key=lambda x: x["change"], reverse=True)

    return results[:5]

def calculate_static_price_raise(cycles):
    
    results = []

    if len(cycles) < 5:
        return []

    stocks = cycles[0].keys()

    for stock in stocks:

        valid = True
        increases = []

        for i in range(len(cycles) - 1):

            start_price = cycles[i].get(stock)
            end_price = cycles[i + 1].get(stock)
            # print("yess")
            # print(start_price)
            # print(end_price)
            if not start_price or not end_price or start_price == 0:
                valid = False
                break

            # % growth per cycle
            percent_change = ((end_price - start_price) / start_price) * 100
            # print(percent_change)
            if percent_change < 0.07:   # ❌ minimum growth condition
                valid = False
                break
            # valid = True
            # store absolute price increase
            increases.append(end_price - start_price)
            # print("hii")
        if valid and len(increases) >= 0:
            # print("hii")
            avg_increase = sum(increases) / len(increases)

            results.append({
                "name": stock,
                "price": cycles[-1][stock],
                "diff": round(avg_increase, 3)
            })

    results.sort(key=lambda x: x["diff"], reverse=True)
    # print(results)
    return results[:5]

def momentum_scheduler():
    
    global momentum_30_cache
    global momentum_3min_cache
    global momentum_30_price_cache
    global momentum_3min_price_cache
    global last_10_cycles

    # ✅ Create ONE event loop only once
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    previous_prices = loop.run_until_complete(fetch_all_prices_async())

    if not previous_prices:
        previous_prices = {}
    coun = 0
    while True:
        
        coun += 1
        # print(coun)

        current_prices = loop.run_until_complete(fetch_all_prices_async())

        if not current_prices:
            time.sleep(5)
            continue

        # ⭐ STORE LAST 5 CYCLES FIRST
        last_10_cycles.append(current_prices)

        if len(last_10_cycles) > 5:
            last_10_cycles.pop(0)

        save_json("last_10_cycles.json", last_10_cycles)

        # ⭐ 30 SEC MOMENTUM
        if previous_prices:

            temp_percent = calculate_momentum(previous_prices, current_prices)
            momentum_30_cache = temp_percent[:5]

            # ✅ NOW calculate continuous increase
            momentum_30_price_cache = calculate_continuous_price_raise(last_10_cycles)

        previous_prices = current_prices

        # ⭐ 3 MIN MOMENTUM
        if len(last_10_cycles) == 5:

            momentum_3min_cache = calculate_static_momentum(last_10_cycles)
            momentum_3min_price_cache = calculate_static_price_raise(last_10_cycles)
            # end_time = time.time()   # ⬅️ ADD HERE (end timer)

            # print("Loop execution time:", round(end_time - start_time, 2), "seconds")
        # time.sleep(10)



@app.route("/momentum30")
def momentum30():
    # print(momentum_30_cache)
    return jsonify(momentum_30_cache)

@app.route("/momentum3min")
def momentum3min():
    return jsonify(momentum_3min_cache)

@app.route("/momentum30price")
def momentum30price():
    return jsonify(momentum_30_price_cache)

@app.route("/momentum3minprice")
def momentum3minprice():
    return jsonify(momentum_3min_price_cache)

# -----------------------------
# Serve Frontend
# -----------------------------
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(app.static_folder, path)


# -----------------------------
# Get Stocks
# -----------------------------
@app.route("/stocks")
def get_stocks():

    result = []
    # print("jss")
    for symbol in stocks:
        result.append({
            "name": symbol,
            "price": prices_cache.get(symbol)
        })
        # print(result)
        # print(symbol)
    return jsonify(result)


# -----------------------------
# Add Stock
# -----------------------------
@app.route("/add-stock", methods=["POST"])
def add_stock():
    
    data = request.get_json()
    symbol = data["symbol"].upper() 
    if not symbol.endswith(".NS"):
        symbol += ".NS"

    if symbol not in stocks:
        stocks.append(symbol)
        save_json("stocks.json", stocks)

    return jsonify(stocks)


@app.route("/removeStock/<name>", methods=["DELETE"])
def remove_stock(name):

    if name in stocks:
        stocks.remove(name)
        save_json("stocks.json", stocks)
        return jsonify({"status":"removed"})

    return jsonify({"status":"not found"})

# -----------------------------
# Portfolio
# -----------------------------
@app.route("/portfolio")
def get_portfolio():
    return jsonify(portfolio)


# -----------------------------
# Buy Stock
# -----------------------------
@app.route("/buy", methods=["POST"])
def buy_stock():

    data = request.get_json()
    buy_price = float(data["price"])

    stock = {
        "name": data["name"],
        "buy_price": buy_price,
        "target_price": buy_price,
        "highest_price": buy_price,
        "alert_triggered": False
    }
    portfolio.append(stock)
    save_json("portfolio.json", portfolio)

    return jsonify(portfolio)


# -----------------------------
# Sell Stock
# -----------------------------
@app.route("/sell", methods=["POST"])
def sell_stock():

    name = request.get_json()["name"]

    global portfolio
    portfolio = [s for s in portfolio if s["name"] != name]

    save_json("portfolio.json", portfolio)

    return jsonify(portfolio)


# -----------------------------
# ALERT LOGIC
# -----------------------------

@app.route("/check-alerts")
def check_alerts():

    alerts = []
    # print("hii")
    # print("check-alerts called")
    # print(portfolio)
    for stock in portfolio:
        
        symbol = stock["name"]
        current_price = prices_cache.get(symbol)
        # print(current_price)
        if current_price is None:
            continue

        buy_price = stock["buy_price"]
        # print("buy price")
        # print(buy_price)
        # Initialize highest price
        if "highest_price" not in stock:
            stock["highest_price"] = buy_price

        # Update highest price
        
        if current_price > stock["highest_price"]:
            
            stock["highest_price"] = current_price

        highest_price = stock["highest_price"]

        # -----------------------------
        # 🔴 CONDITION 1: STOP LOSS
        # -----------------------------
        # buy_price = stock["buy_price"]
        stop_loss_price = buy_price - 3

        # -----------------------------
        # 🔴 CONDITION 2: TRAILING STOP
        # -----------------------------
        trailing_price = highest_price - 5

        # -----------------------------
        # 🚨 ALARM CONDITIONS
        # -----------------------------
        # print("utkarsh")
        # print(stop_loss_price)
        # print(current_price)
        # print("condition")
        # print(current_price)
        # print("2nd")
        # print(stop_loss_price)
        if current_price <= stop_loss_price:
            # print(current_price)
            # print(stop_loss_price)
            # print(f"🚨 STOP LOSS HIT: {symbol}")
            alerts.append(symbol)

        elif current_price <= trailing_price:
            # print(f"🚨 TRAILING STOP HIT: {symbol}")
            alerts.append(symbol)

    save_json("portfolio.json", portfolio)
    return jsonify(alerts)

if __name__ == "__main__":

    threading.Thread(target=scheduler, daemon=True).start()
    threading.Thread(target=momentum_scheduler, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT)

