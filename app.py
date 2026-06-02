import streamlit as st
import pandas as pd
import yfinance as yf
from streamlit_autorefresh import st_autorefresh

# =========================
# PAGE CONFIG (반드시 최상단)
# =========================
st.set_page_config(page_title="주식 자동검색기", layout="wide")

# 자동 새로고침 (5분)
st_autorefresh(interval=300000, key="refresh")

st.title("📊 통합 주식 자동검색기 (Excel + 실시간)")

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
# RSI 계산
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
# 현재가 + RSI 가져오기
# =========================
@st.cache_data(ttl=300)
def get_stock_data(ticker):
    try:
        df = yf.Ticker(ticker).history(period="6mo")
        if df.empty:
            return None, None

        close = df["Close"]
        current_price = float(close.iloc[-1])
        rsi_val = float(rsi(close).iloc[-1])

        return current_price, rsi_val

    except:
        return None, None


# =========================
# 점수 계산 (간단 버전)
# =========================
def calc_score(rsi_val):
    score = 0

    if rsi_val <= 30:
        score += 30
    elif rsi_val <= 40:
        score += 20
    elif rsi_val <= 50:
        score += 10

    return score


def get_signal(score):
    if score >= 70:
        return "강력매수"
    elif score >= 50:
        return "매수신호"
    elif score >= 30:
        return "관심"
    else:
        return "관망"


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
# 필터 적용
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
# 분석 실행
# =========================
results = []

progress = st.progress(0)
total = len(filtered)

for i, row in enumerate(filtered.iterrows()):

    _, r = row

    price, rsi_val = get_stock_data(r["종목코드"])

    if price is None:
        continue

    score = calc_score(rsi_val)
    signal = get_signal(score)

    results.append({
        "종목명": r["종목명"],
        "종목코드": r["종목코드"],
        "국가": r["국가"],
        "섹터": r["섹터"],
        "현재가": round(price, 2),
        "RSI": round(rsi_val, 2),
        "점수": score,
        "신호": signal
    })

    progress.progress((i + 1) / total)


df = pd.DataFrame(results)

if df.empty:
    st.warning("데이터 없음")
    st.stop()

df = df.sort_values("점수", ascending=False)


# =========================
# TOP 10
# =========================
st.subheader("🔥 TOP 10 종목")
st.dataframe(df.head(10), use_container_width=True)


# =========================
# 전체 테이블
# =========================
st.subheader("📊 전체 결과")

st.dataframe(
    df[[
        "종목명",
        "종목코드",
        "국가",
        "섹터",
        "현재가",
        "RSI",
        "점수",
        "신호"
    ]],
    use_container_width=True,
    hide_index=True
)


# =========================
# 차트
# =========================
st.subheader("📈 점수 차트")
st.bar_chart(df.set_index("종목명")["점수"])
