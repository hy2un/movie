import streamlit as st
from openai import OpenAI

# 페이지 기본 설정
st.set_page_config(page_title="셰프의 기분 맞춤 빗장", page_icon="🍳")

# 스타일 설정: 배경에 다양한 음식 이모지를 바둑판 형태로 패턴화
st.markdown(
    """
    <style>
    .stApp {
        background-color: #fafafa;
        background-image: radial-gradient(#e5e7eb 1px, transparent 1px);
        background-size: 16px 16px;
    }
    /* 배경 위에 흐리게 깔리는 음식 이모지 패턴 */
    .stApp::before {
        content: "🍕 🍱 🌮 🍣 🥘 🥗 🥟 🍲 🧆 🍳 🥙 🍕 🍱 🌮 🍣 🥘 🥗 🥟 🍲 🧆 🍳 🥙";
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        opacity: 0.07;
        font-size: 32px;
        line-height: 60px;
        word-wrap: break-word;
        pointer-events: none;
        z-index: 0;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🍳 셰프의 기분 맞춤 식탁")
st.caption("오늘 당신의 기분에 딱 맞는, 뜻밖의 이색 요리를 제안합니다.")

# API 클라이언트 설정
client = OpenAI(
    api_key=st.secrets["GEMINI_API_KEY"],
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

# 전문 셰프 페르소나 설정
SYSTEM_PROMPT = (
    "너는 3성급 레스토랑의 미식 경험을 안내하는 베테랑 수셰프야. "
    "사용자가 자신의 기분이나 상태를 말하면, 흔한 음식(김치찌개, 제육볶음 등) 대신 "
    "'어? 이런 음식도 있었어?' 싶을 만한 세계의 이색 요리나 매력적인 퓨전 음식을 1~2가지 추천해 줘. "
    "격식 있고 전문적이면서도 따뜻한 셰프의 어조(~셰프의 조언입니다, ~를 권해 드립니다)를 사용해. "
    "요리의 주요 재료, 풍미의 특징, 그리고 왜 이 기분에 어울리는지 이유를 미식학 관점에서 설명해 줘."
)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

# 이전 대화 출력
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# 사용자 입력
user_input = st.chat_input("오늘 기분이 어떠신가요? (예: 기운이 없어, 스트레스 받아)")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        try:
            stream = client.chat.completions.create(
                model="gemini-3.5-flash-lite",
                messages=st.session_state.messages,
                stream=True,
            )
            answer = st.write_stream(
                chunk.choices[0].delta.content or ""
                for chunk in stream if chunk.choices
            )
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception:
            st.error("주문 접수에 실패했습니다. 잠시 후 다시 시도해 주세요.")
