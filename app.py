import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="모바일 주식 자동검색기", layout="wide")

# =========================

# 종목 불러오기

# =========================

try:
stocks_df = pd.read_excel("stocks.xlsx")
except:
st.error("stocks.xlsx 파일이 없습니다.")
st.stop()

# =========================

# 점수 계산

# =========================

@st.cache_data(ttl=300)
def analyze_stock(name, ticker):
try:
df = yf.Ticker(ticker).history(period="3mo")

```
    if len(df) < 30:
        return None

    df["MA5"] = df["Close"].rolling(5).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["VOL20"] = df["Volume"].rolling(20).mean()

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    score = 0

    price = float(latest["Close"])
    ma5 = float(latest["MA5"])
    ma20 = float(latest["MA20"])

    change = ((price - float(prev["Close"])) / float(prev["Close"])) * 100

    volume_ratio = (
        float(latest["Volume"]) / float(latest["VOL20"])
        if float(latest["VOL20"]) > 0
        else 0
    )

    golden = ma5 > ma20

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
        "매수점수": score,
    }

except:
    return None
```

# =========================

# 전체 분석

# =========================

results = []

progress = st.progress(0)

total = len(stocks_df)

for idx, row in stocks_df.iterrows():

```
result = analyze_stock(
    row["종목명"],
    row["종목코드"]
)

if result:
    results.append(result)

progress.progress((idx + 1) / total)
```

df = pd.DataFrame(results)

if df.empty:
st.warning("분석 가능한 종목이 없습니다.")
st.stop()

df = df.sort_values(
by="매수점수",
ascending=False
)

# =========================

# 화면

# =========================

st.title("📊 모바일 주식 자동검색기")

tab1, tab2, tab3, tab4 = st.tabs(
[
"전체 TOP",
"자동추천 TOP3",
"결과 검색",
"점수 비교"
]
)

with tab1:
st.dataframe(df, width="stretch")

with tab2:
st.dataframe(df.head(3), width="stretch")

with tab3:
keyword = st.text_input("종목명 검색")

```
if keyword:
    result_df = df[
        df["종목명"].str.contains(
            keyword,
            case=False,
            na=False
        )
    ]

    st.dataframe(result_df, width="stretch")
```

with tab4:
st.bar_chart(
df.set_index("종목명")["매수점수"]
)
