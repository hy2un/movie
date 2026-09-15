import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# 1. 페이지 레이아웃 및 웅장한 시네마틱 테마 설정
st.set_page_config(
    page_title="ALL-TIME POPULAR CINEMA REALM",
    page_icon="🎬",
    layout="wide",
)

# 다크 레드/골드 시네마틱 스타일 적용
st.markdown(
    """
    <style>
    .main-title {
        font-size: 3.2rem;
        font-weight: 900;
        background: linear-gradient(90deg, #E50914, #FFD700, #FF5722);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1.5px;
        margin-bottom: 5px;
    }
    .sub-title {
        font-size: 1.2rem;
        color: #B0B0B0;
        margin-bottom: 30px;
    }
    .hero-card {
        background-color: #141414;
        border: 2px solid #E50914;
        border-radius: 12px;
        padding: 22px;
        box-shadow: 0 8px 20px rgba(229, 9, 20, 0.3);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<p class="main-title">🔥 ALL-TIME POPULAR CINEMA</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-title">독립/비상업 영화 제외! 대중성이 검증된 역대 인기 상업영화만 장르별로 모아 보여드립니다.</p>',
    unsafe_allow_html=True,
)

# 2. Secrets에서 KOBIS API 키 불러오기
try:
    api_key = st.secrets["KOBIS_KEY"]
except KeyError:
    st.error("🚨 Secrets에서 'KOBIS_KEY'를 찾을 수 없습니다. Streamlit Cloud 설정을 확인해 주세요.")
    st.stop()


# 3. KOBIS API 연동 (상업영화 전용 필터 파라미터 적용)
@st.cache_data(ttl=3600)
def fetch_popular_movies(genre_name, nation_code=""):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/movie/searchMovieList.json"
    
    # movieTypeCd="장편": 단편/독립 영화를 1차적으로 배제
    params = {
        "key": api_key,
        "genreNm": "" if genre_name == "전체 장르" else genre_name,
        "repNationCd": nation_code,
        "movieTypeCd": "장편",
        "itemPerPage": 100,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return None, f"서버 오류 (코드: {response.status_code})"

        data = response.json()
        if "faultInfo" in data:
            return None, f"API 오류: {data['faultInfo'].get('message', '인증 실패')}"

        movie_list = data.get("movieListResult", {}).get("movieList", [])
        return movie_list, None

    except requests.exceptions.RequestException:
        return None, "네트워크 통신 오류가 발생했습니다."


# 4. 사이드바 제어판
with st.sidebar:
    st.header("🔮 장르 & 필터 제어판")

    genres = [
        "전체 장르",
        "액션",
        "SF",
        "드라마",
        "코미디",
        "스릴러",
        "공포(호러)",
        "미스터리",
        "범죄",
        "판타지",
        "애니메이션",
        "멜로/로맨스",
        "어드벤처",
        "전쟁",
        "사극",
    ]
    selected_genre = st.selectbox("🎭 영화 장르 선택", genres)

    nation_option = st.radio("🌏 제작 국가 선택", ["전체", "한국", "외국"])
    nation_code = "K" if nation_option == "한국" else ("F" if nation_option == "외국" else "")

    st.markdown("---")
    st.subheader("⚙️ 대중성 필터링 옵션")
    
    # 비상업/독립 영화 정제용 연도 필터
    min_year = st.slider("제작 연도 범주 (최신작 위주)", min_value=2000, max_value=2026, value=2015)

    search_keyword = st.text_input("🔍 결과 내 대중 영화 검색", placeholder="예: 파묘, 범죄도시").strip()


# 5. 데이터 요청 및 2차 필터링 (대중성 강화)
with st.spinner(f"🏛️ 역대 대중 상업영화 [{selected_genre}] 목록을 집계 중입니다..."):
    movies, error_message = fetch_popular_movies(selected_genre, nation_code)

if error_message:
    st.error(error_message)
    st.stop()

if not movies:
    st.warning("조회된 상업영화 데이터가 없습니다.")
    st.stop()

# 데이터프레임 변환
df = pd.DataFrame(movies)

# 연도 숫자 변환
df["prdtYear_num"] = pd.to_numeric(df["prdtYear"], errors="coerce").fillna(0)

# [핵심] 대중 상업영화 필터링 조건
# 1. 설정한 제작 연도 이상만 추출 (최신 상업영화 위주)
# 2. 감독 정보가 등록되어 있는 영화 (대중 상업영화 위주)
df = df[df["prdtYear_num"] >= min_year]
df = df[df["directors"].apply(lambda x: isinstance(x, list) and len(x) > 0)]

# 감독 정보 가공
df["directors_str"] = df["directors"].apply(
    lambda x: ", ".join([d.get("peopleNm", "") for d in x])
)

# 키워드 검색
if search_keyword:
    df = df[df["movieNm"].str.contains(search_keyword, case=False, na=False)]

if df.empty:
    st.warning(f"선택한 조건 내에 대중적인 '{search_keyword}' 영화 검색 결과가 없습니다.")
    st.info("💡 사이드바에서 '제작 연도 범주'를 낮추거나 다른 장르를 선택해 보세요.")
    st.stop()

# 제작연도 최신순 및 정렬
df = df.sort_values(by=["prdtYear_num", "movieNm"], ascending=[False, True]).reset_index(drop=True)
df["장르내순위"] = df.index + 1

# ==========================================
# 메인 뷰 구성
# ==========================================

# 👑 HERO SECTION
top_movie = df.iloc[0]

st.markdown(
    f"""
    <div class="hero-card">
        <h2 style="color: #FFD700; margin:0;">👑 [{selected_genre}] 최신 대중 대표작: {top_movie['movieNm']}</h2>
        <p style="color: #DDD; font-size: 1.1rem; margin-top: 8px;">
            <b>영문명:</b> {top_movie.get('movieNmEn', 'N/A')} | 
            <b>제작년도:</b> {top_movie.get('prdtYear', '미상')}년 | 
            <b>제작국가:</b> {top_movie.get('nationAlt', '미상')} | 
            <b>장르:</b> {top_movie.get('genreAlt', selected_genre)}
        </p>
        <p style="color: #AAA; margin:0;"><b>감독:</b> {top_movie['directors_str']}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

# 지표 카드
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="🎭 선택 장르", value=selected_genre)
with col2:
    st.metric(label="🎬 대중 상업영화 수", value=f"{len(df)} 편")
with col3:
    st.metric(label="📅 검색 연도 기준", value=f"{min_year}년 이후")

st.markdown("---")

# 📊 연도별 주요 상업영화 수 차트
st.subheader(f"📊 [{selected_genre}] 연도별 대중 영화 분포")

year_counts = df["prdtYear"].value_counts().sort_index().reset_index()
year_counts.columns = ["제작년도", "영화수"]

fig = px.bar(
    year_counts,
    x="제작년도",
    y="영화수",
    text_auto=True,
    color="영화수",
    color_continuous_scale="Reds",
    labels={"제작년도": "제작년도", "영화수": "등록 영화 수(편)"},
)
fig.update_layout(
    showlegend=False,
    height=320,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# 📋 영화 목록 표
st.subheader(f"🏆 [{selected_genre}] 역대 인기 상업영화 리스트")

display_df = df[
    ["장르내순위", "movieNm", "movieNmEn", "prdtYear", "genreAlt", "nationAlt", "directors_str"]
].copy()

display_df.columns = [
    "순위",
    "영화 제목(한글)",
    "영화 제목(영문)",
    "제작년도",
    "장르",
    "제작국가",
    "감독",
]

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
)
