import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
from datetime import datetime

# =========================
# 텔레그램 설정
# =========================
TELEGRAM_TOKEN = "8117624184:AAFa8oVpO1Xx-ep8RdA14hRgNbUMKG_28Js"
CHAT_ID = "6626061234"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data)
    except:
        pass


# =========================
# 중복 방지 + 날짜 초기화
# =========================
today = datetime.now().date()

if "sent" not in st.session_state:
    st.session_state.sent = set()

if "last_reset" not in st.session_state:
    st.session_state.last_reset = today

# 🔥 하루 1회 초기화
if st.session_state.last_reset != today:
    st.session_state.sent = set()
    st.session_state.last_reset = today


# =========================
# 종목 리스트
# =========================
stocks = {
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "NAVER": "035420.KS",
    "현대차": "005380.KS",
    "LG에너지솔루션": "373220.KS"
}


# =========================
# 데이터 수집
# =========================
def get_data(name, ticker):
    try:
        df = yf.Ticker(ticker).history(period="3mo")

        if df is None or len(df) < 20:
            return None

        df["MA5"] = df["Close"].rolling(5).mean()
        df["MA20"] = df["Close"].rolling(20).mean()
        df["VOL_MA20"] = df["Volume"].rolling(20).mean()

        df = df.dropna()

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        price = latest["Close"]
        ma5 = latest["MA5"]
        ma20 = latest["MA20"]

        change = ((price - prev["Close"]) / prev["Close"]) * 100

        volume_ratio = latest["Volume"] / latest["VOL_MA20"]
        golden = ma5 > ma20

        score = 0

        if change > 0:
            score += 20
        if change > 2:
            score += 10
        if price > ma5:
            score += 20
        if price > ma20:
            score += 25
        if golden:
            score += 20
        if volume_ratio > 1.5:
            score += 15

        return {
            "종목명": name,
            "현재가": round(price, 0),
            "등락률(%)": round(change, 2),
            "거래량비율": round(volume_ratio, 2),
            "골든크로스": "YES" if golden else "NO",
            "매수점수": score
        }

    except Exception:
        return None


# =========================
# 자동 실행 (핵심)
# =========================
st.title("📊 모바일 주식 자동검색기 (6단계) - 무인 감시")

placeholder = st.empty()

while True:

    data = []

    for name, ticker in stocks.items():
        result = get_data(name, ticker)
        if result:
            data.append(result)

    df = pd.DataFrame(data)

    if not df.empty:
        df = df.sort_values("매수점수", ascending=False)

        with placeholder.container():

            st.subheader("🔥 전체 TOP")
            st.dataframe(df, use_container_width=True)

            st.subheader("🚀 TOP 3")
            st.dataframe(df.head(3), use_container_width=True)

            st.subheader("📊 점수 비교")
            st.bar_chart(df.set_index("종목명")["매수점수"])

        # =========================
        # 🔔 자동 알림
        # =========================
        for _, row in df.iterrows():
            key = row["종목명"]

            if (
                row["매수점수"] >= 80
                and (row["골든크로스"] == "YES" or row["거래량비율"] > 1.5)
                and key not in st.session_state.sent
            ):
                msg = f"""
📊 매수 신호 발생

종목: {row['종목명']}
현재가: {row['현재가']}
점수: {row['매수점수']}
골든크로스: {row['골든크로스']}
거래량: {row['거래량비율']}
"""

                send_telegram(msg)
                st.session_state.sent.add(key)

    time.sleep(300)  # 🔥 5분마다 실행