import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# 1. 페이지 레이아웃 및 웅장한 시네마틱 테마 설정
st.set_page_config(
    page_title="ALL-TIME CINEMA REALM | 역대 영화 장르별 랭킹",
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
    .genre-card {
        background-color: #141414;
        border: 1px solid #333;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.6);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<p class="main-title">🔥 ALL-TIME CINEMA REALM</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-title">날짜 선택 필요 없이, 역대 모든 영화를 장르별로 통합하여 순위를 분석합니다.</p>',
    unsafe_allow_html=True,
)

# 2. Secrets에서 KOBIS API 키 불러오기
try:
    api_key = st.secrets["KOBIS_KEY"]
except KeyError:
    st.error("🚨 Secrets에서 'KOBIS_KEY'를 찾을 수 없습니다. Streamlit Cloud 설정을 확인해 주세요.")
    st.stop()


# 3. KOBIS 영화 목록 API 호출 함수 (장르/국가/키워드 통합)
@st.cache_data(ttl=3600)
def fetch_all_time_movies(genre_name, nation_code="", item_per_page=100):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/movie/searchMovieList.json"
    params = {
        "key": api_key,
        "genreNm": "" if genre_name == "전체 장르" else genre_name,
        "repNationCd": nation_code,
        "itemPerPage": item_per_page,
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

    except requests.exceptions.RequestException as e:
        return None, "네트워크 통신 오류가 발생했습니다."


# 4. 사이드바 제어판 (장르 및 필터 선택)
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
    max_count = st.slider("📊 불러올 역대 영화 수", min_value=10, max_value=100, value=30, step=10)

    st.markdown("---")
    search_keyword = st.text_input("🔍 결과 내 영화명 검색", placeholder="예: 아바타, 범죄도시").strip()


# 5. 데이터 요청 및 처리
with st.spinner(f"🏛️ 역대 [{selected_genre}] 영화 목록을 통합 집계 중입니다..."):
    movies, error_message = fetch_all_time_movies(selected_genre, nation_code, max_count)

if error_message:
    st.error(error_message)
    st.info("💡 Secrets의 'KOBIS_KEY' 값이 올바른지 확인해 주세요.")
    st.stop()

if not movies:
    st.warning("조회된 역대 영화 데이터가 없습니다.")
    st.info("💡 다른 장르나 필터 조건을 선택해 보세요.")
    st.stop()

# 6. 데이터프레임 변환 및 전처리
df = pd.DataFrame(movies)

# 감독 정보 정리 (리스트 형태 추출)
df["directors_str"] = df["directors"].apply(
    lambda x: ", ".join([d.get("peopleNm", "") for d in x]) if isinstance(x, list) and len(x) > 0 else "미상"
)

# 키워드 검색 적용
if search_keyword:
    df = df[df["movieNm"].str.contains(search_keyword, case=False, na=False)]

if df.empty:
    st.warning(f"선택한 장르 내에 '{search_keyword}' 검색 결과가 없습니다.")
    st.stop()

# 제작년도 정렬 기준 상대 순위 부여
df["prdtYear_num"] = pd.to_numeric(df["prdtYear"], errors="coerce").fillna(0)
df = df.sort_values(by=["prdtYear_num", "movieNm"], ascending=[False, True]).reset_index(drop=True)
df["장르내순위"] = df.index + 1

# ==========================================
# 메인 뷰 구성
# ==========================================

# 👑 HERO SECTION: 장르 대표 하이라이트
top_movie = df.iloc[0]

st.markdown(
    f"""
    <div class="genre-card">
        <h2 style="color: #FFD700; margin:0;">👑 [{selected_genre}] 역대 탐색 대표작: {top_movie['movieNm']}</h2>
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

# 지표 카드 세 장
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="🎭 선택한 장르", value=selected_genre)
with col2:
    st.metric(label="🎬 검색된 총 영화 수", value=f"{len(df)} 편")
with col3:
    st.metric(label="🌏 선택한 국가", value=nation_option)

st.markdown("---")

# 📊 시각화: 연도별 대표 영화 개수 분포 (Plotly)
st.subheader(f"📊 [{selected_genre}] 역대 영화들의 제작 연도별 분포")

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

# 📋 장르별 역대 통합 순위 표
st.subheader(f"🏆 [{selected_genre}] 역대 영화 통합 순위 리스트")

display_df = df[
    ["장르내순위", "movieNm", "movieNmEn", "prdtYear", "genreAlt", "nationAlt", "directors_str"]
].copy()

display_df.columns = [
    "장르 내 순위",
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
