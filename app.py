import streamlit as st
import pandas as pd
import yfinance as yf
from streamlit_autorefresh import st_autorefresh
st.set_page_config(page_title="모바일 주식 자동검색기", layout="wide")

# =========================
# 자동 새로고침 (5분)
# =========================
st_autorefresh(interval=300000, key="refresh")

# =========================
# 세션 상태 (알림 중복 방지)
# =========================
if "sent_alerts" not in st.session_state:
    st.session_state.sent_alerts = set()

# =========================
# 종목 로딩
# =========================
try:
    stocks_df = pd.read_excel("stocks.xlsx")
except:
    st.error("stocks.xlsx 파일이 없습니다.")
    st.stop()

stocks_df.columns = [c.strip() for c in stocks_df.columns]

tickers = stocks_df["종목코드"].dropna().unique().tolist()

# =========================
# 데이터 다운로드 (핵심: batch)
# =========================
@st.cache_data(ttl=300)
def load_data(tickers):
    data = yf.download(
        tickers,
        period="1y",
        interval="1d",
        group_by="ticker",
        threads=True,
        auto_adjust=True
    )
    return data

data = load_data(tickers)

# =========================
# 지표 함수
# =========================
def rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(series):
    ema12 = series.ewm(span=12).mean()
    ema26 = series.ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9).mean()
    return macd_line, signal


# =========================
# 점수 계산
# =========================
def calculate_score(rsi_val, gap20, drawdown, macd_cross, volume_ratio, alignment, gc_status):

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
# 분석 엔진 (batch 기반)
# =========================
results = []

for _, row in stocks_df.iterrows():

    ticker = row["종목코드"]
    name = row["종목명"]

    try:
        if ticker not in data.columns.get_level_values(0):
            continue

        df = data[ticker].dropna()

        if len(df) < 100:
            continue

        close = df["Close"]
        volume = df["Volume"]

        current_price = float(close.iloc[-1])

        # RSI
        rsi_val = float(rsi(close).iloc[-1])

        # MA
        ma5 = close.rolling(5).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()

        current_ma5 = ma5.iloc[-1]
        current_ma20 = ma20.iloc[-1]
        current_ma60 = ma60.iloc[-1]

        prev_ma5 = ma5.iloc[-2]
        prev_ma20 = ma20.iloc[-2]

        gc_status = (prev_ma5 <= prev_ma20 and current_ma5 > current_ma20)
        alignment = (current_ma5 > current_ma20 > current_ma60)

        # 거래량
        avg_volume = volume.rolling(5).mean().iloc[-1]
        current_volume = volume.iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0

        # MACD
        macd_line, signal = macd(close)
        macd_cross = (macd_line.iloc[-2] <= signal.iloc[-2] and macd_line.iloc[-1] > signal.iloc[-1])

        # 괴리율
        gap20 = ((current_price - current_ma20) / current_ma20) * 100

        # 하락률
        high_price = close.max()
        drawdown = ((current_price - high_price) / high_price) * 100

        # 점수
        score = calculate_score(
            rsi_val, gap20, drawdown,
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

        results.append({
            "종목명": name,
            "종목코드": ticker,
            "현재가": round(current_price, 0),
            "RSI": round(rsi_val, 2),
            "점수": score,
            "신호": signal_text
        })

    except:
        continue


df = pd.DataFrame(results)

if df.empty:
    st.warning("분석 결과 없음")
    st.stop()

df = df.sort_values("점수", ascending=False)

# =========================
# 알림 (중복 방지)
# =========================
for _, row in df.iterrows():
    if row["점수"] >= 80:
        if row["종목명"] not in st.session_state.sent_alerts:
            st.error(f"🚨 매수 신호: {row['종목명']} ({row['점수']}점)")
            st.session_state.sent_alerts.add(row["종목명"])

# =========================
# UI
# =========================
st.title("📊 모바일 주식 자동검색기 (고속버전)")

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
