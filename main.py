import datetime
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# 페이지 기본 설정
st.set_page_config(page_title="어제 박스오피스", layout="wide")

st.title("🎬 어제 일별 박스오피스 순위")

# 1. secrets에서 API 키 가져오기
# Streamlit Cloud의 Secrets 관리 기능(KOBIS_KEY)을 이용합니다.
try:
    api_key = st.secrets["KOBIS_KEY"]
except KeyError:
    st.error(
        "API 키를 찾을 수 없습니다. Streamlit Cloud의 Secrets 설정에서 'KOBIS_KEY'를 등록해 주세요."
    )
    st.stop()

# 2. 한국 시간(UTC+9) 기준 어제 날짜 구하기
# 배포 서버의 시계(UTC)에 영향을 받지 않도록 한국 표준시(KST)를 직접 계산합니다.
kst_timezone = datetime.timezone(datetime.timedelta(hours=9))
today_kst = datetime.datetime.now(kst_timezone)
yesterday_kst = today_kst - datetime.timedelta(days=1)
target_date = yesterday_kst.strftime("%Y%m%d")  # YYYYMMDD 형식 문자열 변환

st.caption(f"기준 일자: {yesterday_kst.strftime('%Y년 %m월 %d일')}")

# 3. KOBIS API 요청 주소 및 파라미터 설정
url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
params = {"key": api_key, "targetDt": target_date}

# 4. API 데이터 요청 및 예외 처리
try:
    response = requests.get(url, params=params, timeout=10)

    # HTTP 상태 코드가 200(성공)이 아닌 경우
    if response.status_code != 200:
        st.error(f"서버 응답 오류가 발생했습니다. (상태 코드: {response.status_code})")
        st.info("💡 **확인해 보세요:** KOBIS 서버가 점검 중이거나 일시적 오류일 수 있습니다.")
        st.stop()

    data = response.json()

    # KOBIS 특유의 오류 구조(faultInfo) 확인
    if "faultInfo" in data:
        st.error(f"API 오류: {data['faultInfo'].get('message', '알 수 없는 오류')}")
        st.info(
            "💡 **확인해 보세요:** Secrets에 입력한 'KOBIS_KEY' 값이 올바른지 확인해 주세요."
        )
        st.stop()

    # 영화 목록 추출
    movie_list = (
        data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
    )

    # 데이터가 비어 있는 경우
    if not movie_list:
        st.warning("조회된 영화 목록이 없습니다.")
        st.info(
            "💡 **확인해 보세요:** API 데이터 집계 중이거나 조회 날짜에 데이터가 없을 수 있습니다."
        )
        st.stop()

except requests.exceptions.RequestException as e:
    st.error("네트워크 통신 중 오류가 발생했습니다.")
    st.info("💡 **확인해 보세요:** 인터넷 연결 상태를 확인해 주세요.")
    st.stop()

# 5. 데이터프레임 변환 및 타입 정리 (문자열 -> 숫자)
df = pd.DataFrame(movie_list)

# 필요한 컬럼만 선택하고 숫자 타입으로 변환
df["rank"] = pd.to_numeric(df["rank"])
df["audiCnt"] = pd.to_numeric(df["audiCnt"])
df["audiAcc"] = pd.to_numeric(df["audiAcc"])
df["scrnCnt"] = pd.to_numeric(df["scrnCnt"])

# 6. 1위 영화 주요 지표 카드 표시 (st.metric)
top1 = df.iloc[0]

st.subheader(f"🥇 1위: {top1['movieNm']}")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="일일 관객수", value=f"{top1['audiCnt']:,}명")

with col2:
    st.metric(label="누적 관객수", value=f"{top1['audiAcc']:,}명")

with col3:
    st.metric(label="상영 스크린수", value=f"{top1['scrnCnt']:,}개")

st.markdown("---")

# 7. 관객수 상위 5편 막대그래프 (Plotly)
st.subheader("📊 관객수 TOP 5")
top5_df = df.head(5).sort_values(by="rank", ascending=False)  # 차트 순서 정렬

fig = px.bar(
    top5_df,
    x="audiCnt",
    y="movieNm",
    orientation="h",
    text_auto=",d",
    labels={"audiCnt": "일일 관객수(명)", "movieNm": "영화명"},
    color="audiCnt",
    color_continuous_scale="Blues",
)
fig.update_layout(showlegend=False, height=350, yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# 8. 전체 순위표 출력
st.subheader("📋 전체 순위 목록")

# 표에 보여줄 컬럼 선택 및 이름 변경
display_df = df[
    ["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
].copy()
display_df.columns = [
    "순위",
    "영화명",
    "개봉일",
    "관객수(명)",
    "누적관객(명)",
    "스크린수(개)",
]

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "관객수(명)": st.column_config.NumberColumn(format="%d"),
        "누적관객(명)": st.column_config.NumberColumn(format="%d"),
        "스크린수(개)": st.column_config.NumberColumn(format="%d"),
    },
)
