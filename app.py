from flask import Flask, render_template
import yfinance as yf
import pandas as pd
import numpy as np
import os

app = Flask(__name__)

def get_data():
    assets = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "AAPL"]
    results = []

    for asset in assets:
        try:
            data = yf.download(asset, period="7d", interval="5m")

            if data is None or data.empty:
                continue

            close = data["Close"]

            if len(close.shape) > 1:
                close = close.iloc[:, 0]

            close = close.dropna()

            if len(close) < 20:
                continue

            # ----------------
            # BASIC METRICS
            # ----------------
            change = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5]
            vol = close.pct_change().std()

            # ----------------
            # EMA
            # ----------------
            ema_short = close.ewm(span=5).mean().iloc[-1]
            ema_long = close.ewm(span=15).mean().iloc[-1]

            # ----------------
            # RSI SAFE
            # ----------------
            delta = close.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = -delta.clip(upper=0).rolling(14).mean()

            if loss.iloc[-1] == 0 or np.isnan(loss.iloc[-1]):
                rsi_value = 50
            else:
                rs = gain.iloc[-1] / loss.iloc[-1]
                rsi_value = 100 - (100 / (1 + rs))

            if np.isnan(rsi_value):
                rsi_value = 50

            # ----------------
            # TREND
            # ----------------
            trend = "Bullish" if change > 0 else "Bearish"

            # ----------------
            # RISK
            # ----------------
            risk = "High" if vol > 0.02 else "Low"

            # ----------------
            # NOISE FILTER (avoid fake signals)
            # ----------------
            if abs(change) < 0.001:
                signal = "HOLD"

            else:
                # ----------------
                # IMPROVED SIGNAL LOGIC
                # ----------------
                if ema_short > ema_long and rsi_value < 65 and change > 0:
                    signal = "STRONG BUY"

                elif ema_short > ema_long and change > 0:
                    signal = "BUY"

                elif ema_short < ema_long and rsi_value > 35 and change < 0:
                    signal = "STRONG SELL"

                elif ema_short < ema_long and change < 0:
                    signal = "SELL"

                else:
                    signal = "HOLD"    

            # ----------------
            # CONFIDENCE
            # ----------------
            confidence = 50
            if "BUY" in signal:
                confidence += 20
            if ema_short > ema_long:
                confidence += 15
            if rsi_value < 60:
                confidence += 15

            confidence = min(confidence, 100)

            # ----------------
            # CHART SAFE
            # ----------------
            chart_data = close.tail(30).fillna(0).tolist()

            results.append({
                "asset": asset,
                "price": round(float(close.iloc[-1]), 2),
                "change": round(float(change * 100), 2),
                "trend": trend,
                "risk": risk,
                "signal": signal,
                "confidence": confidence,
                "rsi": round(float(rsi_value), 2),
                "chart": chart_data
            })

        except Exception as e:
            print("ERROR:", asset, e)
            continue

    # ----------------
    # MARKET SUMMARY
    # ----------------
    if len(results) == 0:
        summary = "No Data"
    else:
        bullish = sum(1 for x in results if x["trend"] == "Bullish")
        bearish = len(results) - bullish
        summary = "Bullish Market 🚀" if bullish > bearish else "Bearish Market 🔻"

        # ----------------
        # BEST TRADE PICK
        # ----------------
        best_trade = None
        if len(results) > 0:
            best_trade = max(results, key=lambda x: x["confidence"])

        return results, summary, best_trade


@app.route("/")
def home():
    data, summary, best = get_data()
    return render_template(
    "index.html",
    data=data,
    summary=summary,
    best=best
)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
