import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="주식 자동검색기", layout="wide")

# =========================
# RSI
# =========================
def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# =========================
# 점수 계산 (예전 구조 유지)
# =========================
def score_calc(rsi_val, gap, drawdown, macd_cross, vol_ratio, alignment, gc):

    score = 0

    if drawdown <= -30:
        score += 30
    elif drawdown <= -20:
        score += 20
    elif drawdown <= -10:
        score += 10

    if rsi_val <= 30:
        score += 30
    elif rsi_val <= 35:
        score += 20
    elif rsi_val <= 45:
        score += 10

    if gap <= -12:
        score += 30
    elif gap <= -8:
        score += 20
    elif gap <= -5:
        score += 10

    if macd_cross:
        score += 15

    if vol_ratio >= 1.5:
        score += 10

    if alignment:
        score += 10

    if gc:
        score += 15

    return score


# =========================
# 종목 리스트 (원하는 만큼 추가)
# =========================
stocks = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "TSLA": "Tesla",
    "AMZN": "Amazon"
}

results = []

st.title("📊 초간단 주식 자동검색기")

progress = st.progress(0)
total = len(stocks)

for i, (ticker, name) in enumerate(stocks.items()):

    df = yf.Ticker(ticker).history(period="1y")

    if df.empty:
        continue

    close = df["Close"]
    volume = df["Volume"]

    price = close.iloc[-1]

    rsi_val = rsi(close).iloc[-1]

    ma5 = close.rolling(5).mean()
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()

    gc = ma5.iloc[-2] <= ma20.iloc[-2] and ma5.iloc[-1] > ma20.iloc[-1]
    alignment = ma5.iloc[-1] > ma20.iloc[-1] > ma60.iloc[-1]

    avg_vol = volume.rolling(5).mean().iloc[-1]
    vol_ratio = volume.iloc[-1] / avg_vol if avg_vol > 0 else 0

    gap = ((price - ma20.iloc[-1]) / ma20.iloc[-1]) * 100
    drawdown = ((price - close.max()) / close.max()) * 100

    macd = close.ewm(span=12).mean() - close.ewm(span=26).mean()
    signal = macd.ewm(span=9).mean()
    macd_cross = macd.iloc[-2] <= signal.iloc[-2] and macd.iloc[-1] > signal.iloc[-1]

    score = score_calc(
        rsi_val, gap, drawdown,
        macd_cross, vol_ratio,
        alignment, gc
    )

    if score >= 90:
        signal_txt = "강력매수"
    elif score >= 80:
        signal_txt = "매수"
    elif score >= 60:
        signal_txt = "관심"
    else:
        signal_txt = "관망"

    results.append([
        name, ticker, price, rsi_val, score, signal_txt
    ])

    progress.progress((i + 1) / total)


df = pd.DataFrame(results, columns=[
    "종목명", "종목코드", "현재가", "RSI", "점수", "신호"
])

st.subheader("🔥 TOP 10")
st.dataframe(df.sort_values("점수", ascending=False).head(10))

st.subheader("📊 전체")
st.dataframe(df)
