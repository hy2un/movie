import datetime
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# 페이지 테마 및 레이아웃 설정
st.set_page_config(
    page_title="GRAND BOX OFFICE | 웅장한 영화 탐색기",
    page_icon="🎬",
    layout="wide",
)

# 웅장하고 거대한 분위기의 커스텀 헤더 스타일 적용
st.markdown(
    """
    <style>
    .grand-header {
        font-size: 2.8rem;
        font-weight: 900;
        letter-spacing: -1px;
        background: linear-gradient(90deg, #ff4b4b, #ff8c00, #ff0055);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-transform: uppercase;
        margin-bottom: 0px;
    }
    .sub-title {
        color: #888;
        font-size: 1.1rem;
        margin-bottom: 25px;
    }
    .recommend-box {
        background-color: #1a1c23;
        border-left: 5px solid #ff4b4b;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<p class="grand-header">💥 CINEMATIC EMPIRE</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-title">압도적 스케일의 일별 박스오피스 & 스마트 키워드 맞춤 영화 탐색 시스템</p>',
    unsafe_allow_html=True,
)

# 1. Secrets에서 API 키 불러오기
try:
    api_key = st.secrets["KOBIS_KEY"]
except KeyError:
    st.error(
        "🚨 [CRITICAL ERROR] API 키를 찾을 수 없습니다. Secrets에 'KOBIS_KEY'를 등록해 주세요."
    )
    st.stop()

# 2. 한국 시간(UTC+9) 기준 조회 날짜 선택 (최대 어제)
kst_timezone = datetime.timezone(datetime.timedelta(hours=9))
today_kst = datetime.datetime.now(kst_timezone).date()
max_selectable_date = today_kst - datetime.timedelta(days=1)

# 사이드바 제어판
with st.sidebar:
    st.header("⚙️ 검색 및 제어판")
    selected_date = st.date_input(
        "📅 박스오피스 날짜 선택",
        value=max_selectable_date,
        max_value=max_selectable_date,
        min_value=datetime.date(2004, 1, 1),
    )

    st.markdown("---")
    st.subheader("💡 테마별 영화 추천 탐색")
    preset_mood = st.selectbox(
        "원하는 분위기를 골라보세요:",
        ["선택 안 함", "🔥 개 웅장하고 거대한 대작", "🌌 압도적인 SF/스페이스", "🗡️ 스펙터클 액션/화려함"],
    )

    # 테마 선택 시 검색어 자동 입력 처리
    preset_keywords = {
        "🔥 개 웅장하고 거대한 대작": "아바타",
        "🌌 압도적인 SF/스페이스": "인터스텔라",
        "🗡️ 스펙터클 액션/화려함": "범죄도시",
    }

    default_search = preset_keywords.get(preset_mood, "")

    search_keyword = st.text_input(
        "🔍 키워드/영화명 검색",
        value=default_search,
        placeholder="예: 파묘, 아바타, 명량 등",
    ).strip()

target_date = selected_date.strftime("%Y%m%d")

# 3. KOBIS 일별 박스오피스 API 호출
boxoffice_url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
params = {"key": api_key, "targetDt": target_date}

try:
    response = requests.get(boxoffice_url, params=params, timeout=10)
    if response.status_code != 200:
        st.error(f"서버 응답 오류 (상태 코드: {response.status_code})")
        st.stop()

    data = response.json()
    if "faultInfo" in data:
        st.error(f"API 오류: {data['faultInfo'].get('message', '알 수 없는 오류')}")
        st.info("💡 Secrets의 'KOBIS_KEY' 값을 다시 확인해 주세요.")
        st.stop()

    movie_list = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
    if not movie_list:
        st.warning("⚡ 그날은 아직 집계 전이거나 데이터가 없습니다.")
        st.stop()

except requests.exceptions.RequestException:
    st.error("네트워크 통신 오류가 발생했습니다.")
    st.stop()

# 4. 박스오피스 데이터 전처리
df = pd.DataFrame(movie_list)
df["rank"] = pd.to_numeric(df["rank"])
df["rankInten"] = pd.to_numeric(df["rankInten"])
df["audiCnt"] = pd.to_numeric(df["audiCnt"])
df["audiAcc"] = pd.to_numeric(df["audiAcc"])
df["scrnCnt"] = pd.to_numeric(df["scrnCnt"])


def format_rank_change(row):
    inten = row["rankInten"]
    if row.get("rankOldAndNew") == "NEW":
        return "🔥 NEW"
    elif inten > 0:
        return f"🔺 {inten}"
    elif inten < 0:
        return f"🔻 {abs(inten)}"
    else:
        return "➖"


def format_movie_name(row):
    name = row["movieNm"]
    if row["audiAcc"] >= 10000000:
        return f"{name} 👑 [천만영화]"
    elif row["audiAcc"] >= 1000000:
        return f"{name} 🏆"
    return name


df["순위변동"] = df.apply(format_rank_change, axis=1)
df["표시_영화명"] = df.apply(format_movie_name, axis=1)


# 5. KOBIS 영화목록 검색 API 연동 함수 (추천/검색 확장용)
@st.cache_data(ttl=3600)
def search_kobis_movies(keyword):
    search_url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/movie/searchMovieList.json"
    s_params = {"key": api_key, "movieNm": keyword}
    try:
        res = requests.get(search_url, params=s_params, timeout=10)
        res_data = res.json()
        return res_data.get("movieListResult", {}).get("movieList", [])
    except Exception:
        return []


# ==========================================
# 메인 화면 레이아웃 구성
# ==========================================

# 💡 A. 키워드 검색 또는 테마 추천 모드
if search_keyword:
    st.markdown(
        f'<div class="recommend-box">🔍 <b>"{search_keyword}"</b> 키워드 분석 및 영화 추천 데이터베이스 조회 결과입니다.</div>',
        unsafe_allow_html=True,
    )

    # 1) 당일 박스오피스 상위 10개 중 검색어 일치 확인
    daily_match = df[df["movieNm"].str.contains(search_keyword, case=False, na=False)].copy()

    # 2) KOBIS 전체 영화 DB 검색
    db_movies = search_kobis_movies(search_keyword)
    db_df = pd.DataFrame(db_movies) if db_movies else pd.DataFrame()

    tab1, tab2 = st.tabs(["🔥 선택 일자 박스오피스 내 비교", "🌐 KOBIS 통합 영화 DB 연관검색"])

    with tab1:
        if daily_match.empty:
            st.warning(f"선택하신 날짜({selected_date}) TOP 10 내에는 '{search_keyword}' 관련 영화가 없습니다.")
        else:
            daily_match = daily_match.sort_values(by="rank").reset_index(drop=True)
            daily_match["검색내순위"] = daily_match.index + 1

            st.subheader(f"📊 당일 박스오피스 내 '{search_keyword}' 관련 영화 순위 비교")

            # 압도적인 시각화 차트 (Plotly Red/Gold 그래디언트)
            fig_search = px.bar(
                daily_match,
                x="audiCnt",
                y="movieNm",
                orientation="h",
                text_auto=",d",
                color="audiCnt",
                color_continuous_scale="Reds",
                labels={"audiCnt": "일일 관객수(명)", "movieNm": "영화 제목"},
                title=f"'{search_keyword}' 관련 영화 일일 관객수 압도적 비교",
            )
            fig_search.update_layout(
                showlegend=False,
                height=300,
                yaxis={"categoryorder": "total ascending"},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_search, use_container_width=True)

            # 상세 정보 데이터프레임
            display_match = daily_match[
                ["검색내순위", "rank", "순위변동", "표시_영화명", "openDt", "audiCnt", "audiAcc"]
            ]
            display_match.columns = ["그룹 내 순위", "전체 순위", "변동", "영화 제목", "개봉일", "일일 관객수", "누적 관객수"]
            st.dataframe(display_match, use_container_width=True, hide_index=True)

    with tab2:
        if db_df.empty:
            st.info("KOBIS 데이터베이스에 일치하는 관련 영화가 없습니다.")
        else:
            st.subheader(f"🎬 KOBIS 등록 연관 영화 목록 (총 {len(db_df)}건)")
            show_cols = ["movieNm", "movieNmEn", "prdtYear", "nationAlt", "genreAlt", "directors"]
            
            # 감독 정보 가공
            if "directors" in db_df.columns:
                db_df["directors"] = db_df["directors"].apply(
                    lambda x: ", ".join([d.get("peopleNm", "") for d in x]) if isinstance(x, list) else ""
                )

            renamed_db = db_df[show_cols].copy()
            renamed_db.columns = ["영화 제목(한글)", "영화 제목(영문)", "제작년도", "제작국가", "장르", "감독"]
            st.dataframe(renamed_db, use_container_width=True, hide_index=True)

# 💡 B. 일반 모드 (전체 웅장한 박스오피스 보드)
else:
    # 1위 영화 하이라이트 (HERO SECTION)
    top1 = df.iloc[0]

    st.markdown("### 🏛️ DAILY KINGDOM : 1위 챔피언")
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #1f1c2c, #928dab); padding: 25px; border-radius: 12px; color: white; box-shadow: 0 10px 20px rgba(0,0,0,0.5);">
            <h1 style="margin:0; font-size: 2.5rem; color: #ffd700;">🥇 {top1['표시_영화명']}</h1>
            <p style="margin-top:5px; font-size:1.1rem; opacity:0.8;">개봉일자: {top1['openDt']} | 전일대비: {top1['순위변동']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="💥 일일 관객수", value=f"{top1['audiCnt']:,} 명")
    with col2:
        st.metric(label="👑 누적 관객수", value=f"{top1['audiAcc']:,} 명")
    with col3:
        st.metric(label="🛡️ 상영 스크린수", value=f"{top1['scrnCnt']:,} 개")

    st.markdown("---")

    # TOP 5 스펙터클 막대그래프
    st.subheader("📊 관객수 TOP 5 압도적 스케일 비교")
    top5_df = df.head(5).sort_values(by="rank", ascending=False)

    fig = px.bar(
        top5_df,
        x="audiCnt",
        y="표시_영화명",
        orientation="h",
        text_auto=",d",
        color="audiCnt",
        color_continuous_scale="Viridis",
        labels={"audiCnt": "일일 관객수(명)", "표시_영화명": "영화 제목"},
    )
    fig.update_layout(
        showlegend=False,
        height=380,
        yaxis={"categoryorder": "total ascending"},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # 전체 순위표
    st.subheader("📋 일별 박스오피스 전체 순위 (1~10위)")

    display_df = df[
        ["rank", "순위변동", "표시_영화명", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
    ].copy()

    display_df.columns = [
        "순위",
        "순위 변동",
        "영화 제목",
        "개봉일",
        "일일 관객수(명)",
        "누적 관객수(명)",
        "스크린수(개)",
    ]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "일일 관객수(명)": st.column_config.NumberColumn(format="%d"),
            "누적 관객수(명)": st.column_config.NumberColumn(format="%d"),
            "스크린수(개)": st.column_config.NumberColumn(format="%d"),
        },
    )
