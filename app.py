import streamlit as st
import pandas as pd
import yfinance as yf
from streamlit_autorefresh import st_autorefresh

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="주식 자동검색기", layout="wide")
st_autorefresh(interval=300000, key="refresh")

st.title("📊 통합 주식 자동검색기 (섹터 로테이션 시스템)")

# =========================
# 데이터 로드
# =========================
@st.cache_data
def load_data():
    df = pd.read_excel("stocks.xlsx")
    df.columns = [c.strip() for c in df.columns]
    return df

stocks_df = load_data()

# =========================
# RSI
# =========================
def rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# =========================
# MACD
# =========================
def macd(series):
    ema12 = series.ewm(span=12).mean()
    ema26 = series.ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9).mean()
    return macd_line, signal


# =========================
# FULL 점수 시스템
# =========================
def calc_score(rsi_val, gap20, drawdown, macd_cross, volume_ratio, alignment, gc):

    score = 0

    # RSI
    if rsi_val <= 30:
        score += 30
    elif rsi_val <= 35:
        score += 20
    elif rsi_val <= 45:
        score += 10

    # 이격도
    if gap20 <= -12:
        score += 30
    elif gap20 <= -8:
        score += 20
    elif gap20 <= -5:
        score += 10

    # 하락률
    if drawdown <= -30:
        score += 30
    elif drawdown <= -20:
        score += 20
    elif drawdown <= -10:
        score += 10

    # MACD
    if macd_cross:
        score += 15

    # 거래량
    if volume_ratio >= 1.5:
        score += 10

    # 정배열
    if alignment:
        score += 10

    # 골든크로스
    if gc:
        score += 15

    return score


def get_signal(score):
    if score >= 90:
        return "강력매수"
    elif score >= 80:
        return "매수신호"
    elif score >= 60:
        return "관심"
    else:
        return "관망"


# =========================
# 분석 함수
# =========================
@st.cache_data(ttl=300)
def analyze_stock(ticker):
    try:
        df = yf.Ticker(ticker).history(period="6mo")
        if df.empty:
            return None

        close = df["Close"]
        volume = df["Volume"]

        current_price = float(close.iloc[-1])

        rsi_val = float(rsi(close).iloc[-1])

        ma5 = close.rolling(5).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()

        current_ma5 = ma5.iloc[-1]
        current_ma20 = ma20.iloc[-1]
        current_ma60 = ma60.iloc[-1]

        prev_ma5 = ma5.iloc[-2]
        prev_ma20 = ma20.iloc[-2]

        gc = (prev_ma5 <= prev_ma20 and current_ma5 > current_ma20)

        alignment = (current_ma5 > current_ma20 > current_ma60)

        avg_volume = volume.rolling(5).mean().iloc[-1]
        current_volume = volume.iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0

        macd_line, signal = macd(close)
        macd_cross = (macd_line.iloc[-2] <= signal.iloc[-2] and macd_line.iloc[-1] > signal.iloc[-1])

        gap20 = ((current_price - current_ma20) / current_ma20) * 100

        high_price = close.max()
        drawdown = ((current_price - high_price) / high_price) * 100

        score = calc_score(
            rsi_val, gap20, drawdown,
            macd_cross, volume_ratio,
            alignment, gc
        )

        return {
            "현재가": round(current_price, 2),
            "RSI": round(rsi_val, 2),
            "점수": score,
            "신호": get_signal(score)
        }

    except:
        return None


# =========================
# 필터 UI
# =========================
col1, col2, col3 = st.columns(3)

with col1:
    country = st.selectbox("국가", ["전체"] + sorted(stocks_df["국가"].unique()))

with col2:
    sector = st.selectbox("섹터", ["전체"] + sorted(stocks_df["섹터"].unique()))

with col3:
    keyword = st.text_input("종목 검색")


# =========================
# 필터
# =========================
filtered = stocks_df.copy()

if country != "전체":
    filtered = filtered[filtered["국가"] == country]

if sector != "전체":
    filtered = filtered[filtered["섹터"] == sector]

if keyword:
    filtered = filtered[
        filtered["종목명"].str.contains(keyword, case=False, na=False)
    ]


# =========================
# 분석
# =========================
results = []

progress = st.progress(0)
total = len(filtered)

for i, row in enumerate(filtered.iterrows()):
    _, r = row

    data = analyze_stock(r["종목코드"])

    if data:
        results.append({
            "종목명": r["종목명"],
            "종목코드": r["종목코드"],
            "국가": r["국가"],
            "섹터": r["섹터"],
            "현재가": data["현재가"],
            "RSI": data["RSI"],
            "점수": data["점수"],
            "신호": data["신호"]
        })

    progress.progress((i + 1) / total)


df = pd.DataFrame(results)

if df.empty:
    st.warning("데이터 없음")
    st.stop()

df = df.sort_values("점수", ascending=False)


# =========================
# 🔥 전체 TOP 10
# =========================
st.subheader("🔥 TOP 10")
st.dataframe(df.head(10), use_container_width=True)


# =========================
# 📊 전체 데이터
# =========================
st.subheader("📊 전체 결과")
st.dataframe(df, use_container_width=True)


# =========================
# 🔥 섹터별 TOP 3
# =========================
st.subheader("📌 섹터별 TOP 3")

for s in df["섹터"].unique():
    sector_df = df[df["섹터"] == s].sort_values("점수", ascending=False).head(3)

    st.markdown(f"### {s} TOP 3")

    st.dataframe(
        sector_df[
            ["종목명", "종목코드", "국가", "현재가", "RSI", "점수", "신호"]
        ],
        use_container_width=True,
        hide_index=True
    )


# =========================
# 🚀 강세 섹터 분석 (핵심 추가)
# =========================
st.subheader("🚀 강세 섹터 분석")

sector_score = df.groupby("섹터")["점수"].mean().sort_values(ascending=False)

best_sector = sector_score.index[0]

st.success(f"🔥 현재 가장 강한 섹터: {best_sector}")

st.dataframe(sector_score.reset_index().rename(columns={"점수": "평균점수"}))
