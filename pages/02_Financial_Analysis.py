import streamlit as st
import pandas as pd
import os
import sys
import re
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dart_api import DartAPI
from frontend.financial_analysis_display import pretty_financial_table, financial_df_to_context_text, render_financial_table
from backend.company_analysis_tools import answer_from_page_context
from langchain_openai import ChatOpenAI
from serpapi import GoogleSearch

st.title("재무 분석")

# 1. UI 기반 주요 기능
st.header("빠른 재무 분석")
# 우리나라 10대 기업 리스트 + 직접 입력 옵션
company_list = [
    "직접 입력", "삼성전자", "SK하이닉스", "LG화학", "삼성바이오로직스", "현대차", "기아", "POSCO홀딩스", "삼성SDI", "NAVER", "카카오"
]
selected_company = st.selectbox("기업 선택", company_list)

# 직접 입력 선택 시 텍스트 입력창 노출
if selected_company == "직접 입력":
    custom_company = st.text_input("기업명을 직접 입력하세요")
    final_company = custom_company.strip() if custom_company else None
else:
    final_company = selected_company

# 연도 선택 추가 (2024, 2023, 2022, 2021)
year_list = ["2024", "2023", "2022", "2021"]
selected_year = st.selectbox("연도 선택", year_list, index=0)

# 재무제표 종류 선택 추가
sj_div_map = {
    "손익계산서(IS)": "IS",
    "재무상태표(BS)": "BS",
    "현금흐름표(CF)": "CF"
}
sj_div_label = st.selectbox("재무제표 종류", list(sj_div_map.keys()))
sj_div = sj_div_map[sj_div_label]

# Initialize display mode for each sj_div if not already present
if f'display_mode_{sj_div}' not in st.session_state:
    st.session_state[f'display_mode_{sj_div}'] = 'summary'

if st.button("재무제표 보기"):
    # Set initial display mode to summary when a new financial statement is viewed
    st.session_state[f'display_mode_{sj_div}'] = 'summary'
    if final_company:
        corp_code = DartAPI().find_corp_code(final_company)
        if corp_code and isinstance(corp_code, str) and corp_code.isdigit() and len(corp_code) == 8:
            # 1. 기업 기본 정보 먼저 보여주기 (재무 분석 페이지에서는 간단히 표시)
            info = DartAPI().get_company_info(corp_code)
            if info.get('corp_name'):
                st.info(f"기업명: {info.get('corp_name')}\n대표자명: {info.get('ceo_nm')}\n주소: {info.get('adres')}")
            # 2. 재무제표 시도
            fs = DartAPI().get_financial_statements(corp_code, bsns_year=selected_year, fs_div=sj_div)
            if fs.get('list'):
                df = pretty_financial_table(fs, sj_div=sj_div)
                st.session_state['financial_analysis_result'] = financial_df_to_context_text(
                    df, company=final_company, year=selected_year, sj_div=sj_div
                )
                # Store financial data and display mode in session state
                st.session_state['current_fs_data'] = fs
                st.session_state['current_company'] = final_company
                st.session_state['current_year'] = selected_year
                st.session_state['current_sj_div'] = sj_div
                
            else:
                st.warning("재무 데이터가 없습니다.")
        else:
            st.warning(f"기업명을 정확히 입력해 주세요.\n{corp_code if isinstance(corp_code, str) else ''}")
    else:
        st.warning("기업명을 입력하세요.")

# Render financial table and buttons if data is available in session state
if 'current_fs_data' in st.session_state and 'current_sj_div' in st.session_state:
    fs = st.session_state['current_fs_data']
    final_company = st.session_state['current_company']
    selected_year = st.session_state['current_year']
    sj_div = st.session_state['current_sj_div']
    
    # Render based on current display mode
    render_financial_table(fs, final_company, selected_year, sj_div=sj_div, display_mode=st.session_state[f'display_mode_{sj_div}'])
    
    # Add expand/collapse button
    if sj_div == 'IS': # For Income Statement
        if st.session_state[f'display_mode_{sj_div}'] == 'summary':
            if st.button("🔍 손익계산서 상세보기", key=f"expand_is_{selected_year}"):
                st.session_state[f'display_mode_{sj_div}'] = 'full'
                st.rerun()
        else: # 'full' mode
            if st.button("[+ 손익계산서 ▾] 접기", key=f"collapse_is_{selected_year}"):
                st.session_state[f'display_mode_{sj_div}'] = 'summary'
                st.rerun()
    elif sj_div == 'BS': # For Balance Sheet
        if st.session_state[f'display_mode_{sj_div}'] == 'summary':
            if st.button("🔍 재무상태표 상세보기", key=f"expand_bs_{selected_year}"):
                st.session_state[f'display_mode_{sj_div}'] = 'full'
                st.rerun()
        else: # 'full' mode
            if st.button("[+ 재무상태표 ▾] 접기", key=f"collapse_bs_{selected_year}"):
                st.session_state[f'display_mode_{sj_div}'] = 'summary'
                st.rerun()
    elif sj_div == 'CF': # For Cash Flow Statement
        if st.session_state[f'display_mode_{sj_div}'] == 'summary':
            if st.button("🔍 현금흐름표 상세보기", key=f"expand_cf_{selected_year}"):
                st.session_state[f'display_mode_{sj_div}'] = 'full'
                st.rerun()
        else: # 'full' mode
            if st.button("[+ 현금흐름표 ▾] 접기", key=f"collapse_cf_{selected_year}"):
                st.session_state[f'display_mode_{sj_div}'] = 'summary'
                st.rerun()

# 예시: 분석 결과를 생성하는 부분(실제 결과 변수로 대체)
financial_analysis_result = st.session_state.get("financial_analysis_result", "아직 분석 결과가 없습니다.")



def get_financial_info_from_dart(company, year, item):
    try:
        corp_code = DartAPI().find_corp_code(company)
        if not corp_code:
            return None
        fs = DartAPI().get_financial_statements(corp_code, bsns_year=year, fs_div="IS")
        if not fs or not fs.get('list'):
            return None
        df = pretty_financial_table(fs, sj_div="IS")
        row = df[df['계정명'].str.contains(item, na=False)]
        if not row.empty:
            return row.iloc[0].to_dict()
        return None
    except Exception:
        return None

def web_search(query, num_results=3):
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

# --- 사이드바: Q&A 챗봇 ---
st.sidebar.header("Q&A 챗봇")
st.sidebar.info("재무 분석 결과에 대해 궁금한 점을 질문해 보세요!")
chat_input = st.sidebar.text_input("질문을 입력하세요", key="financial_chat_input")

def parse_financial_query_with_llm(user_input):
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    prompt = f"""
아래 사용자의 질문에서 비교하고자 하는 기업명(여러 개면 모두), 연도(없으면 '없음'), 항목(예: 매출, 영업이익 등)을 반드시 JSON만 반환해줘. 설명은 하지 마.

예시 입력: "2023년 삼성전자와 LG전자 매출 비교해줘"
예시 출력: {{"companies": ["삼성전자", "LG전자"], "year": "2023", "item": "매출"}}

입력: "{user_input}"
출력:
"""
    result = llm.invoke(prompt)
    st.write("LLM 원본 응답:", result.content)  # 응답 확인
    for line in result.content.strip().split('\n'):
        try:
            parsed = json.loads(line)
            return parsed
        except Exception:
            continue
    return None

if st.sidebar.button("질문하기", key="financial_qa_btn"):
    with st.spinner("질문 해석중..."):
        parsed = parse_financial_query_with_llm(chat_input)
    st.write("LLM 파싱 결과:", parsed)

    if not parsed:
        st.sidebar.info("질문에서 기업명, 연도, 항목을 추출하지 못했습니다. 다시 입력해 주세요.")
    else:
        companies = parsed.get("companies", [])
        year = parsed.get("year", None)
        item = parsed.get("item", None)
        st.write(f"파싱된 기업명: {companies}, 연도: {year}, 항목: {item}")
        company = companies[0] if companies else None
        # 이후 기존 로직(DART API, 웹 검색 등) 실행

        # 2. DART API에서 정보 조회
        dart_result = None
        if company and year and item:
            dart_result = get_financial_info_from_dart(company, year, item)
        page_context = st.session_state.get("financial_analysis_result", "")
        if dart_result:
            st.sidebar.success(f"{company} {year}년 {item}: {dart_result.get('당기', '정보 없음')}")
        else:
            # 3. 웹 검색 (RAG)
            web_results = web_search(f"{company} {year}년 {item}")
            if web_results and web_results[0].get('snippet'):
                snippet = web_results[0]['snippet']
                if snippet and snippet.strip():
                    st.sidebar.success(f"웹 검색 결과: {snippet}")
                else:
                    st.sidebar.info("웹 검색 결과가 없습니다.")
            else:
                st.sidebar.info("웹 검색 결과가 없습니다.")
            # 4. 마지막으로 ChatGPT(OpenAI LLM) 답변 시도 (page_context 포함)
            llm = ChatOpenAI(model="gpt-4o", temperature=0)
            prompt = f"""아래는 현재 페이지에서 제공하는 재무제표 요약 데이터입니다.

{page_context}

질문: {chat_input}
위 데이터를 참고해서, 또는 일반적인 재무 지식을 바탕으로 답변해줘. 만약 정보가 없으면 솔직하게 모른다고 답해줘.
"""
            with st.spinner("작성중..."):
                try:
                    result = llm.invoke(prompt)
                    if not result or not getattr(result, "content", "").strip():
                        st.sidebar.info("AI가 답변을 생성하지 못했습니다.")
                    else:
                        st.sidebar.success(f"ChatGPT 답변: {result.content.strip()}")
                except Exception as e:
                    st.sidebar.error(f"답변 실패: {e}")
