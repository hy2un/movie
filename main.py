import datetime
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# 1. 페이지 기본 설정 (Wide 모드)
st.set_page_config(
    page_title="🍿 몽글몽글 박스오피스",
    page_icon="🎬",
    layout="wide",
)

# 2. 접속하자마자 압도적으로 터지는 귀여운 축하 효과!
st.balloons()  # 화면 전체에 풍선이 둥둥 떠오릅니다.
st.toast("🎉 어제 박스오피스 순위를 가져왔어요! ✨", icon="🍿")

# 3. 귀엽고 압도적인 커스텀 CSS 스타일링
st.markdown(
    """
    <style>
    /* 전체 배경 둥글고 귀여운 느낌 주기 */
    .stApp {
        background: linear-gradient(135deg, #fff5f5 0%, #f0f7ff 100%);
    }
    /* 타이틀 카드 스타일 */
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        color: #ff4b4b;
        text-align: center;
        background: white;
        padding: 20px;
        border-radius: 20px;
        box-shadow: 0 10px 25px rgba(255, 75, 75, 0.15);
        margin-bottom: 25px;
    }
    /* 강조 메트릭 상자 */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 2px solid #ffe3e3;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 메인 타이틀
st.markdown(
    '<div class="main-title">🍿 몽글몽글 어제 박스오피스 TOP 10 🎬</div>',
    unsafe_allow_html=True,
)

# 4. secrets에서 API 키 가져오기
try:
    api_key = st.secrets["KOBIS_KEY"]
except KeyError:
    st.error(
        "🔑 API 키를 찾을 수 없습니다. Streamlit Cloud의 Secrets 설정에서 'KOBIS_KEY'를 등록해 주세요!"
    )
    st.stop()

# 5. 한국 시간(UTC+9) 기준 어제 날짜 구하기
kst_timezone = datetime.timezone(datetime.timedelta(hours=9))
today_kst = datetime.datetime.now(kst_timezone)
yesterday_kst = today_kst - datetime.timedelta(days=1)
target_date = yesterday_kst.strftime("%Y%m%d")

st.markdown(
    f"#### 📅 **기준 일자:** `{yesterday_kst.strftime('%Y년 %m월 %d일')}`"
)

# 6. KOBIS API 요청
url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
params = {"key": api_key, "targetDt": target_date}

try:
    response = requests.get(url, params=params, timeout=10)

    if response.status_code != 200:
        st.error(f"서버 응답 오류가 발생했습니다. (상태 코드: {response.status_code})")
        st.stop()

    data = response.json()

    if "faultInfo" in data:
        st.error(f"API 오류: {data['faultInfo'].get('message', '알 수 없는 오류')}")
        st.stop()

    movie_list = (
        data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
    )

    if not movie_list:
        st.warning("🎈 아쉽게도 조회된 영화 목록이 없어요.")
        st.stop()

except requests.exceptions.RequestException:
    st.error("네트워크 통신 중 오류가 발생했습니다.")
    st.stop()

# 7. 데이터 프레임 변환
df = pd.DataFrame(movie_list)

df["rank"] = pd.to_numeric(df["rank"])
df["audiCnt"] = pd.to_numeric(df["audiCnt"])
df["audiAcc"] = pd.to_numeric(df["audiAcc"])
df["scrnCnt"] = pd.to_numeric(df["scrnCnt"])

# 8. 대망의 1위 영화 하이라이트 카드로 압도적 강조!
top1 = df.iloc[0]

st.markdown(
    f"""
    <div style="background: linear-gradient(120deg, #ff9a9e 0%, #fecfef 100%); padding: 20px; border-radius: 20px; color: white; text-align: center; margin-bottom: 20px;">
        <h2 style="margin:0; font-size: 2.2rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.2);">🏆 영예의 1위: {top1['movieNm']} 🏆</h2>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="✨ 어제 다녀간 관객수", value=f"{top1['audiCnt']:,} 명")

with col2:
    st.metric(label="💖 누적 관객수", value=f"{top1['audiAcc']:,} 명")

with col3:
    st.metric(label="📺 상영 스크린수", value=f"{top1['scrnCnt']:,} 개")

st.markdown("---")

# 9. 알록달록 컬러풀한 Plotly 막대그래프
st.subheader("📊 한눈에 보는 TOP 5 차트")
top5_df = df.head(5).sort_values(by="rank", ascending=False)

fig = px.bar(
    top5_df,
    x="audiCnt",
    y="movieNm",
    orientation="h",
    text_auto=",d",
    labels={"audiCnt": "일일 관객수(명)", "movieNm": "영화 제목"},
    color="movieNm",  # 알록달록한 파스텔 색상 적용
    color_discrete_sequence=px.colors.qualitative.Pastel,
)

fig.update_layout(
    showlegend=False,
    height=380,
    yaxis={"categoryorder": "total ascending"},
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(size=14, family="Nanum Gothic, sans-serif"),
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# 10. 전체 순위표
st.subheader("📋 전체 순위 한눈에 보기")

display_df = df[
    ["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
].copy()

display_df.columns = [
    "순위",
    "영화 제목",
    "개봉일",
    "어제 관객수",
    "누적 관객수",
    "스크린수",
]

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "어제 관객수": st.column_config.NumberColumn(format="%d명"),
        "누적 관객수": st.column_config.NumberColumn(format="%d명"),
        "스크린수": st.column_config.NumberColumn(format="%d개"),
    },
)
