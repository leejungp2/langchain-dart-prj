import streamlit as st
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from serpapi import GoogleSearch
from backend.company_analysis_tools import answer_from_page_context  # 추가
import datetime
from frontend.market_analysis_display import render_market_summary, render_web_results

# 환경변수 로드 및 LLM 세팅
load_dotenv()
llm = ChatOpenAI(model="gpt-4o", temperature=0)

st.set_page_config(page_title="시장/산업 분석", layout="wide")

st.title("시장 분석")

# --- 사이드바: Q&A 챗봇 ---
st.sidebar.header("Q&A 챗봇")
st.sidebar.info("산업/시장 정보에 대해 궁금한 점을 질문해 보세요!")
chat_input = st.sidebar.text_input("질문을 입력하세요", key="market_chat_input")
if st.sidebar.button("질문하기", key="market_qa_btn"):
    # 1. 페이지 내 결과값에서 답변 시도
    # summary는 아래에서 생성됨. 없으면 빈 문자열.
    page_context = st.session_state.get("market_summary", "")
    answer = answer_from_page_context(chat_input, page_context)
    if answer:
        st.sidebar.success(f"페이지 내 답변: {answer}")
    else:
        # 2. 외부 API 호출 (OpenAI)
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        prompt = f"다음 시장/산업 분석 결과를 참고해서 질문에 답변해줘.\n\n분석 결과: {page_context}\n\n질문: {chat_input}"
        try:
            result = llm.invoke(prompt)
            st.sidebar.success(f"외부 답변: {result.content.strip()}")
        except Exception as e:
            st.sidebar.error(f"답변 실패: {e}")

# --- 웹 검색 함수 ---
def web_search(query, num_results=5):
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return []
    params = {
        "q": query,
        "hl": "ko",
        "gl": "kr",
        "api_key": api_key,
        "num": num_results
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    organic_results = results.get("organic_results", [])
    return [
        {
            "title": item.get("title"),
            "snippet": item.get("snippet"),
            "link": item.get("link")
        }
        for item in organic_results[:num_results]
    ]

# --- 메인: 산업/기업명 입력 ---
st.header("카테고리 선택 또는 기업명 검색")
industry_list = [
    "반도체", "2차전지", "자동차", "게임", "바이오", "IT", "금융", "유통", "조선", "항공", "기타"
]
company_to_industry = {
    "삼성전자": "반도체",
    "SK하이닉스": "반도체",
    "LG화학": "2차전지",
    "현대차": "자동차",
    "기아": "자동차",
    "NAVER": "IT",
    "카카오": "IT",
    "삼성바이오로직스": "바이오",
    "POSCO홀딩스": "2차전지",
    "삼성SDI": "2차전지",
}
col1, col2 = st.columns([2, 2])
with col1:
    selected_industry = st.selectbox("산업/시장 카테고리 선택", industry_list, index=0)
with col2:
    company_name = st.text_input("특정 기업명으로 검색 (예: 삼성전자)")

search_clicked = st.button("검색")

# --- 결과 영역 ---
def get_industry_name(company_name, selected_industry):
    if company_name:
        # 1. 사전 매핑 우선
        for k, v in company_to_industry.items():
            if k.replace(" ", "").lower() in company_name.replace(" ", "").lower():
                return v
        # 2. LLM에게 산업명 추정 요청
        prompt = f"""
        '{company_name}'라는 한국 기업이 속한 대표 산업(시장)명을 한 단어로 알려줘. (예: 반도체, 2차전지, 자동차, 게임, 바이오, IT, 금융, 유통, 조선, 항공 등)
        답변은 산업명만 반환해줘.
        """
        try:
            result = llm.invoke(prompt)
            return result.content.strip().split("\n")[0]
        except Exception:
            return selected_industry
    else:
        return selected_industry

def get_market_summary(industry_name, web_results=None):
    # 웹 검색 결과를 프롬프트에 포함
    web_context = ""
    if web_results:
        web_context = "\n\n[웹 검색 결과]\n" + "\n".join([
            f"- {item['title']}\n  {item['snippet']}\n  {item['link']}" for item in web_results if item.get('title')
        ])
    prompt = f"""
    '{industry_name}' 산업(시장)에 대해 아래 항목별로 한국어로 간결하게 요약해줘.{web_context}

    1. 시장 개념
    2. 국내 산업 규모 및 현황\
    3. Value Chain
    4. Key Players
    5. 산업 이슈
    각 항목별로 소제목과 내용을 구분해서 5줄 이내로 요약해줘.
    """
    try:
        result = llm.invoke(prompt)
        return result.content.strip()
    except Exception as e:
        return f"[요약 실패] {e}"

def log_page3_category_search(input_val, output):
    log_path = "logs/page3_category_search.log"
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\nINPUT: {input_val}\nOUTPUT: {output}\n---\n")

def log_page3_qa(user_input, output):
    log_path = "logs/page3_qa.log"
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\nINPUT: {user_input}\nOUTPUT: {output}\n---\n")

if search_clicked:
    # 1. 산업명 추정
    industry_name = get_industry_name(company_name, selected_industry)
    st.subheader(f"[검색 결과] {industry_name} 시장 분석")
    # 2. 웹 검색
    with st.spinner("웹 검색 중..."):
        web_results = web_search(f"{industry_name} 산업 시장 동향")
    render_web_results(web_results)
    # 3. LLM 요약
    with st.spinner("시장 기본 정보 요약 중..."):
        summary = get_market_summary(industry_name, web_results)
    st.session_state["market_summary"] = summary  # Q&A 챗봇에서 사용
    render_market_summary(summary)
    log_page3_category_search(f"company_name: {company_name}, selected_industry: {selected_industry}", summary)
else:
    st.info("산업을 선택하거나 기업명을 입력 후 '검색'을 눌러주세요.")