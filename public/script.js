// const API = "http://localhost:3000";
// const API = "https://try2-c0yp.onrender.com/"
let coun = 0;
const alarm = new Audio("alarm.mp3");
let alertStocks = [];

let coun1 = 0;
let coun2 = 0;
let totalOrders = 0;
let totalProfit = 0;

/* ================= COPY FUNCTION ================= */
function copyName(fullName) {
    const cleanName = fullName.replace(".NS", "");
    navigator.clipboard.writeText(cleanName)
        .then(() => alert("Copied: " + cleanName))
        .catch(err => console.error("Copy failed", err));
}

/* ================= LOAD STOCKS ================= */
async function loadStocks() {

    coun++;

    const res = await fetch("/stocks");
    const data = await res.json();

    const div = document.getElementById("stocks");
    div.innerHTML = "";

    data.forEach(stock => {

        div.innerHTML += `
        <div class="stock">
            <h3>${stock.name}</h3>
            <p>Price: ₹${stock.price ?? 0}</p>
            <button onclick="copyName('${stock.name}')">Copy</button>
            <button class="buy" onclick="buyStock('${stock.name}', ${stock.price})">Buy</button>
            <button onclick="removeStock('${stock.name}')">Remove</button>
        </div>
        `;
    });
}

/* ================= ALERT SECTION ================= */
async function checkAlerts() {

    const res = await fetch("/check-alerts");
    const data = await res.json();

    alertStocks = data;
    loadPortfolio();

    if (data.length > 0) {
        alarm.play();
        document.getElementById("stopAlarm").style.display = "block";
    }
}

async function addStock() {

    let symbol = prompt("Enter Stock Symbol (Example: HCLTECH)");
    if (!symbol) return;

    await fetch("/add-stock", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol })
    });

    loadStocks();
}

async function removeStock(name){
    await fetch("/removeStock/" + name,{ method:"DELETE" });
    loadStocks();
}

/* ================= PORTFOLIO ================= */
async function loadPortfolio() {

    const res = await fetch("/portfolio");
    const data = await res.json();

    const div = document.getElementById("portfolio");
    div.innerHTML = "";

    data.forEach(stock => {

        const isAlert = alertStocks.includes(stock.name);

        div.innerHTML += `
        <div class="stock ${isAlert ? "alert-stock" : ""}">
            <h3>${stock.name}</h3>
            <p>Bought At: ₹${stock.buy_price ?? 0}</p>
            <button onclick="sellStock('${stock.name}')"
                class="${isAlert ? "sell-alert" : ""}">
                Sell
            </button>
        </div>
        `;
    });
}

/* ================= BUY (AUTO PRICE) ================= */
async function buyStock(name, price) {

    if (!price) {
        alert("Price not available");
        return;
    }

    await fetch("/add-stock", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: name.replace(".NS","") })
    });

    await fetch("/buy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, price })
    });

    loadStocks();
    loadPortfolio();
}

/* ================= SELL ================= */
function stopAlarm() {
    alarm.pause();
    alarm.currentTime = 0;
    document.getElementById("stopAlarm").style.display = "none";
}

async function sellStock(name) {

    // Get portfolio first to calculate profit
    const res = await fetch("/portfolio");
    const data = await res.json();

    const stock = data.find(s => s.name === name);

    if (stock) {

        const currentPriceRes = await fetch("/stocks");
        const stocksData = await currentPriceRes.json();
        const currentStock = stocksData.find(s => s.name === name);

        if (currentStock) {
            const profit = (currentStock.price ?? 0) - (stock.buy_price ?? 0);
            totalProfit += profit;
            totalOrders += 1;
            updateTradeSummary();
        }
    }

    await fetch("/sell", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name })
    });

    loadPortfolio();
}

function updateTradeSummary() {
    document.getElementById("tradeSummary").innerText =
        `Orders: ${totalOrders} | Profit: ₹${totalProfit.toFixed(2)}`;
}


/* ================= MOMENTUM 5 SEC % ================= */
async function loadMomentum30() {

    const res = await fetch("/momentum30");
    const data = await res.json();

    const container = document.getElementById("momentum30");
    container.innerHTML = "";

    data.forEach(stock => {
        container.innerHTML += `
        <div class="stock">
            <div style="flex:1;">
                ${stock.name}
                ₹${(stock.price ?? 0).toFixed(2)}
                (${Number(stock.change ?? 0).toFixed(2)}%)
            </div>
            <button onclick="copyName('${stock.name}')">Copy</button>
            <button class="buy" onclick="buyStock('${stock.name}', ${stock.price})">Buy</button>
        </div>
        `;
    });
}

/* ================= MOMENTUM 10 SEC % ================= */
async function loadMomentum3() {

    const res = await fetch("/momentum3min");
    const data = await res.json();

    const container = document.getElementById("momentum3");
    container.innerHTML = "";

    data.forEach(stock => {
        container.innerHTML += `
        <div class="stock">
            <div style="flex:1;">
                ${stock.name}
                ₹${(stock.price ?? 0).toFixed(2)}
                (${Number(stock.change ?? 0).toFixed(2)}%)
            </div>
            <button onclick="copyName('${stock.name}')">Copy</button>
            <button class="buy" onclick="buyStock('${stock.name}', ${stock.price})">Buy</button>
        </div>
        `;
    });
}

/* ================= MOMENTUM 5 SEC PRICE ================= */
async function loadMomentum30Price(){

    const res = await fetch("/momentum30price");
    const data = await res.json();

    const div = document.getElementById("momentum30price");
    div.innerHTML = "";

    data.forEach(stock=>{
        div.innerHTML += `
        <div class="stock">
            <div style="flex:1;">
                <b>${stock.name}</b>
                ₹${stock.price ?? 0}
                +₹${stock.diff ?? 0}
            </div>
            <button onclick="copyName('${stock.name}')">Copy</button>
            <button class="buy" onclick="buyStock('${stock.name}', ${stock.price})">Buy</button>
        </div>
        `;
    });
}

/* ================= MOMENTUM 10 SEC PRICE ================= */
async function loadMomentum3Price(){

    const res = await fetch("/momentum3minprice");
    const data = await res.json();
    console.log("hii")
    const div = document.getElementById("momentum3price");
    div.innerHTML = "";

    data.forEach(stock=>{
        console.log(stock)
        div.innerHTML += `
        <div class="stock">
            <div style="flex:1;">
                <b>${stock.name}</b>
                ₹${stock.price ?? 0}
                +₹${stock.diff ?? 0}
            </div>
            <button onclick="copyName('${stock.name}')">Copy</button>
            <button class="buy" onclick="buyStock('${stock.name}', ${stock.price})">Buy</button>
        </div>
        `;
    });
}

/* ================= INTERVALS ================= */
setInterval(loadMomentum30Price,10000);
setInterval(loadMomentum3Price,10000);
setInterval(loadMomentum30,10000);
setInterval(loadMomentum3,10000);
setInterval(loadStocks, 1000);
setInterval(checkAlerts, 5000);

loadMomentum30();
loadMomentum3();
loadStocks();
loadPortfolio();
loadMomentum30Price();
loadMomentum3Price();
