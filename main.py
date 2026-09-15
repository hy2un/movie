import datetime
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# 페이지 기본 설정
st.set_page_config(page_title="박스오피스 스마트 탐색기", layout="wide")

st.title("🎬 박스오피스 스마트 탐색기")

# 1. secrets에서 API 키 불러오기
try:
    api_key = st.secrets["KOBIS_KEY"]
except KeyError:
    st.error("API 키를 찾을 수 없습니다. Streamlit Cloud의 Secrets 설정에서 'KOBIS_KEY'를 등록해 주세요.")
    st.stop()

# 2. 한국 시간(UTC+9) 기준 조회 날짜 선택 (최대 어제)
kst_timezone = datetime.timezone(datetime.timedelta(hours=9))
today_kst = datetime.datetime.now(kst_timezone).date()
max_selectable_date = today_kst - datetime.timedelta(days=1)

col_date, col_search = st.columns([1, 2])

with col_date:
    selected_date = st.date_input(
        "📅 조회 날짜 선택",
        value=max_selectable_date,
        max_value=max_selectable_date,
        min_value=datetime.date(2004, 1, 1),
    )

with col_search:
    # 영화 이름/키워드 검색 입력 창
    search_keyword = st.text_input(
        "🔍 영화 제목/키워드 검색 (선택사항)",
        placeholder="예: 파묘, 범죄도시, 바이러스 등",
    ).strip()

target_date = selected_date.strftime("%Y%m%d")

# 3. KOBIS API 데이터 호출
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
        st.info("💡 Secrets의 'KOBIS_KEY' 값을 다시 확인해 주세요.")
        st.stop()

    movie_list = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])

    if not movie_list:
        st.warning("그날은 아직 집계 전입니다.")
        st.info("💡 선택하신 날짜의 데이터가 존재하지 않거나 집계 중일 수 있습니다.")
        st.stop()

except requests.exceptions.RequestException:
    st.error("네트워크 통신 중 오류가 발생했습니다.")
    st.stop()

# 4. 데이터 가공 및 숫자형 변환
df = pd.DataFrame(movie_list)

df["rank"] = pd.to_numeric(df["rank"])
df["rankInten"] = pd.to_numeric(df["rankInten"])
df["audiCnt"] = pd.to_numeric(df["audiCnt"])
df["audiAcc"] = pd.to_numeric(df["audiAcc"])
df["scrnCnt"] = pd.to_numeric(df["scrnCnt"])

# 순위 변환 기호 가공
def format_rank_change(row):
    inten = row["rankInten"]
    if row.get("rankOldAndNew") == "NEW":
        return "🆕 신규"
    elif inten > 0:
        return f"🔺 {inten}"
    elif inten < 0:
        return f"🔻 {abs(inten)}"
    else:
        return "-"

# 100만 관객 트로피 가공
def format_movie_name(row):
    name = row["movieNm"]
    if row["audiAcc"] >= 1000000:
        return f"{name} 🏆"
    return name

df["순위변동"] = df.apply(format_rank_change, axis=1)
df["표시_영화명"] = df.apply(format_movie_name, axis=1)

st.markdown("---")

# 5. 검색어 유무에 따른 분기 처리
if search_keyword:
    # 검색어가 포함된 영화 필터링 (대소문자 구분 없음)
    filtered_df = df[df["movieNm"].str.contains(search_keyword, case=False, na=False)].copy()

    st.subheader(f"🔎 '{search_keyword}' 검색 결과 ({len(filtered_df)}건)")

    if filtered_df.empty:
        st.warning(f"선택한 날짜 TOP 10 안에 '{search_keyword}'이(가) 포함된 영화가 없습니다.")
    else:
        # 검색된 영화들 내에서 자체 상대 순위 계산
        filtered_df = filtered_df.sort_values(by="rank").reset_index(drop=True)
        filtered_df["검색내순위"] = filtered_df.index + 1

        # 검색된 영화 간 비교 지표 카드
        top_search_movie = filtered_df.iloc[0]
        st.success(f"🎯 검색 영화 중 최고 순위: **{top_search_movie['movieNm']}** (전체 {top_search_movie['rank']}위)")

        # 검색된 영화간 순위 및 관객수 비교 차트
        fig_search = px.bar(
            filtered_df,
            x="audiCnt",
            y="movieNm",
            orientation="h",
            text_auto=",d",
            color="audiCnt",
            color_continuous_scale="Reds",
            labels={"audiCnt": "일일 관객수(명)", "movieNm": "영화명"},
            title=f"'{search_keyword}' 검색 영화 간 관객수 비교",
        )
        fig_search.update_layout(showlegend=False, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_search, use_container_width=True)

        # 검색 결과 상세 표
        search_display_df = filtered_df[
            ["검색내순위", "rank", "순위변동", "표시_영화명", "openDt", "audiCnt", "audiAcc"]
        ].copy()
        
        search_display_df.columns = [
            "검색 내 순위",
            "전체 순위",
            "순위 변동",
            "영화명",
            "개봉일",
            "관객수(명)",
            "누적관객(명)",
        ]

        st.dataframe(
            search_display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "관객수(명)": st.column_config.NumberColumn(format="%d"),
                "누적관객(명)": st.column_config.NumberColumn(format="%d"),
            },
        )

else:
    # 검색어가 없을 때는 기존 전체 박스오피스 화면 출력
    top1 = df.iloc[0]

    st.subheader(f"🥇 1위: {top1['표시_영화명']}")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="일일 관객수", value=f"{top1['audiCnt']:,}명")
    with col2:
        st.metric(label="누적 관객수", value=f"{top1['audiAcc']:,}명")
    with col3:
        st.metric(label="상영 스크린수", value=f"{top1['scrnCnt']:,}개")

    st.markdown("---")

    # 전체 TOP 5 차트
    st.subheader("📊 관객수 TOP 5")
    top5_df = df.head(5).sort_values(by="rank", ascending=False)

    fig = px.bar(
        top5_df,
        x="audiCnt",
        y="표시_영화명",
        orientation="h",
        text_auto=",d",
        labels={"audiCnt": "일일 관객수(명)", "표시_영화명": "영화명"},
        color="audiCnt",
        color_continuous_scale="Blues",
    )
    fig.update_layout(showlegend=False, height=350, yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # 전체 순위 표
    st.subheader("📋 전체 순위 목록")

    display_df = df[
        ["rank", "순위변동", "표시_영화명", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
    ].copy()

    display_df.columns = [
        "순위",
        "순위 변동",
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
