import streamlit as st
import pandas as pd
import yfinance as yf

# =========================
# 페이지 설정 (항상 맨 위!)
# =========================
st.set_page_config(page_title="초단 자동 주식 검색기", layout="wide")

st.title("📊 초단 자동 주식 검색기 (Streamlit 엔진)")

# =========================
# Excel 로드 (입력용)
# =========================
try:
    stocks = pd.read_excel("stocks.xlsx")
    stocks.columns = stocks.columns.str.strip()
except Exception as e:
    st.error(f"stocks.xlsx 로드 실패: {e}")
    st.stop()

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
# 점수 (예전 구조 유지)
# =========================
def calc_score(rsi_val, gap, drawdown, macd_cross, vol_ratio, alignment, gc):

    score = 0

    # 하락률
    if drawdown <= -30:
        score += 30
    elif drawdown <= -20:
        score += 20
    elif drawdown <= -10:
        score += 10

    # RSI
    if rsi_val <= 30:
        score += 30
    elif rsi_val <= 35:
        score += 20
    elif rsi_val <= 45:
        score += 10

    # 볼린저 괴리율
    if gap <= -12:
        score += 30
    elif gap <= -8:
        score += 20
    elif gap <= -5:
        score += 10

    # MACD
    if macd_cross:
        score += 15

    # 거래량
    if vol_ratio >= 1.5:
        score += 10

    # 정배열
    if alignment:
        score += 10

    # 골든크로스
    if gc:
        score += 15

    return score


# =========================
# 분석 실행
# =========================
results = []
progress = st.progress(0)

total = len(stocks)

for i, row in stocks.iterrows():

    ticker = row["종목코드"]
    name = row["종목명"]
    sector = row["섹터"]

    try:
        data = yf.Ticker(ticker).history(period="1y")

        if data.empty:
            continue

        close = data["Close"]
        volume = data["Volume"]

        price = close.iloc[-1]

        # RSI
        rsi_val = rsi(close).iloc[-1]

        # 이동평균
        ma5 = close.rolling(5).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()

        gc = ma5.iloc[-2] <= ma20.iloc[-2] and ma5.iloc[-1] > ma20.iloc[-1]
        alignment = ma5.iloc[-1] > ma20.iloc[-1] > ma60.iloc[-1]

        # 거래량
        avg_vol = volume.rolling(5).mean().iloc[-1]
        vol_ratio = volume.iloc[-1] / avg_vol if avg_vol > 0 else 0

        # 볼린저 괴리율 (MA20 기준)
        gap = ((price - ma20.iloc[-1]) / ma20.iloc[-1]) * 100

        # 하락률
        drawdown = ((price - close.max()) / close.max()) * 100

        # MACD
        macd = close.ewm(span=12).mean() - close.ewm(span=26).mean()
        signal = macd.ewm(span=9).mean()
        macd_cross = macd.iloc[-2] <= signal.iloc[-2] and macd.iloc[-1] > signal.iloc[-1]

        # 점수
        score = calc_score(
            rsi_val, gap, drawdown,
            macd_cross, vol_ratio,
            alignment, gc
        )

        # 판정
        if score >= 90:
            signal_txt = "강력매수"
        elif score >= 80:
            signal_txt = "매수"
        elif score >= 60:
            signal_txt = "관심"
        else:
            signal_txt = "관망"

        results.append([
            name,
            ticker,
            sector,
            round(price, 2),
            round(rsi_val, 2),
            round(gap, 2),
            score,
            signal_txt
        ])

    except:
        pass

    progress.progress((i + 1) / total)


# =========================
# DataFrame
# =========================
df = pd.DataFrame(results, columns=[
    "종목명", "종목코드", "섹터",
    "현재가", "RSI", "볼린저괴리율",
    "점수", "최종판정"
])

df.columns = df.columns.str.strip()

# 숫자 안정화
df["점수"] = pd.to_numeric(df["점수"], errors="coerce")

# =========================
# TOP 10
# =========================
st.subheader("🔥 TOP 10")

st.dataframe(
    df.sort_values("점수", ascending=False).head(10),
    use_container_width=True
)

# =========================
# 전체
# =========================
st.subheader("📊 전체")

st.dataframe(
    df.sort_values("점수", ascending=False),
    use_container_width=True
)

# =========================
# 섹터 TOP 3
# =========================
st.subheader("📊 섹터 TOP 3")

if "섹터" in df.columns:

    for sector in df["섹터"].dropna().unique():

        st.markdown(f"### 📌 {sector} TOP 3")

        top3 = (
            df[df["섹터"] == sector]
            .sort_values("점수", ascending=False)
            .head(3)
        )

        st.dataframe(
            top3[[
                "종목명",
                "종목코드",
                "현재가",
                "RSI",
                "볼린저괴리율",
                "점수",
                "최종판정"
            ]],
            use_container_width=True
        )

else:
    st.error("❌ 섹터 컬럼 없음 (stocks.xlsx 확인)")
