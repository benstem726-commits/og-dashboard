from flask import Flask, render_template
import yfinance as yf

app = Flask(__name__)

# ---------------------------
# GET MARKET DATA
# ---------------------------
def get_data():
    assets = ["BTC-USD", "ETH-USD", "AAPL"]
    results = []

    for asset in assets:
        data = yf.download(asset, period="7d", interval="5m")

        if data is None or data.empty:
            continue

        close = data["Close"]

        # Fix multi-column issue
        if len(close.shape) > 1:
            close = close.iloc[:, 0]

        # Not enough data safety
        if len(close) < 6:
            continue

        # ---------------------------
        # CALCULATIONS
        # ---------------------------
        change = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5]
        vol = close.pct_change().std()

        # TREND
        if change > 0:
            trend = "📈 Bullish"
        else:
            trend = "📉 Bearish"

        # RISK
        if vol > 0.02:
            risk = "HIGH"
        elif vol > 0.01:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        # SIGNAL (FIXED INDENTATION)
        if change > 0.002 and vol < 0.01:
            signal = "BUY"
        elif change < -0.002 and vol < 0.01:
            signal = "SELL"
        else:
            signal = "HOLD"

        # PRICES FOR CHART
        prices = close.tail(20).tolist()

        # FINAL DATA (IMPORTANT FIX HERE)
        results.append({
            "symbol": asset.replace("-USD", ""),
            "price_change": round(change, 4),
            "volatility": round(vol, 4),
            "risk": risk,
            "trend": trend,
            "prices": prices,
            "signal": signal
        })

    return results


# ---------------------------
# HOME ROUTE
# ---------------------------
@app.route("/")
def home():
    data = get_data()

    if not data:
        return "No data available"

    # ---------------------------
    # MARKET SUMMARY
    # ---------------------------
    avg_vol = sum(d["volatility"] for d in data) / len(data)

    if avg_vol > 0.02:
        overall = "HIGH RISK"
    elif avg_vol > 0.01:
        overall = "MEDIUM RISK"
    else:
        overall = "LOW RISK"

    strongest = max(data, key=lambda x: x["price_change"])
    weakest = min(data, key=lambda x: x["price_change"])
    volatile = max(data, key=lambda x: x["volatility"])

    # ---------------------------
    # RENDER PAGE
    # ---------------------------
    return render_template(
        "index.html",
        data=data,
        overall=overall,
        strongest=strongest["symbol"],
        weakest=weakest["symbol"],
        volatile=volatile["symbol"]
    )


# ---------------------------
# RUN APP
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)