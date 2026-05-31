import streamlit as st
import pandas as pd
import yfinance as yf
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=300000, key="refresh")

st.set_page_config(page_title="모바일 주식 자동검색기", layout="wide")

# =========================
# 세션 상태 (알림 중복 방지)
# =========================
if "sent_alerts" not in st.session_state:
    st.session_state.sent_alerts = set()

# =========================
# 종목 불러오기
# =========================
try:
    stocks_df = pd.read_excel("stocks.xlsx")
except:
    st.error("stocks.xlsx 파일이 없습니다.")
    st.stop()

# =========================
# RSI
# =========================
def calculate_rsi(series, period=14):
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
def calculate_macd(series):
    ema12 = series.ewm(span=12).mean()
    ema26 = series.ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    return macd, signal

# =========================
# 점수 계산 (엑셀 로직 그대로)
# =========================
def calculate_score(rsi, gap20, drawdown, macd_cross, volume_ratio, alignment, gc_status):

    score = 0

    if drawdown <= -30:
        score += 30
    elif drawdown <= -20:
        score += 20
    elif drawdown <= -10:
        score += 10

    if rsi <= 30:
        score += 30
    elif rsi <= 35:
        score += 20
    elif rsi <= 45:
        score += 10

    if gap20 <= -12:
        score += 30
    elif gap20 <= -8:
        score += 20
    elif gap20 <= -5:
        score += 10

    if macd_cross:
        score += 15

    if volume_ratio >= 1.5:
        score += 10

    if alignment:
        score += 10

    if gc_status:
        score += 15

    return score

# =========================
# 종목 분석
# =========================
@st.cache_data(ttl=300)
def analyze_stock(name, ticker):

    try:
        df = yf.Ticker(ticker).history(period="1y", auto_adjust=True)

        if len(df) < 70:
            return None

        close = df["Close"].dropna()
        volume = df["Volume"].dropna()

        current_price = float(close.iloc[-1])

        # RSI
        rsi = float(calculate_rsi(close).iloc[-1])

        # MA
        ma5 = close.rolling(5).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()

        current_ma5 = float(ma5.iloc[-1])
        current_ma20 = float(ma20.iloc[-1])
        current_ma60 = float(ma60.iloc[-1])

        prev_ma5 = ma5.iloc[-2]
        prev_ma20 = ma20.iloc[-2]

        gc_status = (prev_ma5 <= prev_ma20 and current_ma5 > current_ma20)
        alignment = (current_ma5 > current_ma20 > current_ma60)

        # 거래량
        avg_volume = volume.rolling(5).mean().iloc[-1]
        current_volume = volume.iloc[-1]
        volume_ratio = float(current_volume / avg_volume) if avg_volume > 0 else 0

        # MACD
        macd, signal = calculate_macd(close)
        macd_cross = (macd.iloc[-2] <= signal.iloc[-2] and macd.iloc[-1] > signal.iloc[-1])

        # 괴리율
        gap20 = ((current_price - current_ma20) / current_ma20) * 100

        # 하락률
        high_price = close.max()
        drawdown = ((current_price - high_price) / high_price) * 100

        # 점수
        score = calculate_score(
            rsi, gap20, drawdown,
            macd_cross, volume_ratio,
            alignment, gc_status
        )

        # 신호
        if score >= 90:
            signal_text = "강력매수"
        elif score >= 80:
            signal_text = "매수신호"
        elif score >= 60:
            signal_text = "관심"
        else:
            signal_text = "관망"

        return {
            "종목명": name,
            "현재가": round(current_price, 0),
            "RSI": round(rsi, 2),
            "점수": score,
            "신호": signal_text
        }

    except:
        return None

# =========================
# 전체 분석
# =========================
results = []

progress = st.progress(0)
total = len(stocks_df)

for idx, row in stocks_df.iterrows():

    result = analyze_stock(row["종목명"], row["종목코드"])

    if result:
        results.append(result)

    progress.progress((idx + 1) / total)

df = pd.DataFrame(results)

if df.empty:
    st.warning("분석 결과 없음")
    st.stop()

df = df.sort_values("점수", ascending=False)

# =========================
# 🔔 80점 이상 자동 알림 (중복 방지)
# =========================
for _, row in df.iterrows():

    if row["점수"] >= 80:

        key = row["종목명"]

        if key not in st.session_state.sent_alerts:

            st.error(f"🚨 매수 신호: {row['종목명']} ({row['점수']}점)")

            st.session_state.sent_alerts.add(key)

# =========================
# UI
# =========================
st.title("📊 모바일 주식 자동검색기")

tab1, tab2, tab3 = st.tabs([
    "전체",
    "TOP 3",
    "차트"
])

with tab1:
    st.dataframe(df, use_container_width=True)

with tab2:
    st.dataframe(df.head(3), use_container_width=True)

with tab3:
    st.bar_chart(df.set_index("종목명")["점수"])
