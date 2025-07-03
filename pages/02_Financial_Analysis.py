import streamlit as st
import pandas as pd
import os
import sys
import re
import json
import datetime

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

def log_page2_search(company, year, sj_div):
    print("[DEBUG] log_page2_search called", company, year, sj_div)
    log_path = "logs/page2_search.log"
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\nCOMPANY: {company}\nYEAR: {year}\nSJ_DIV: {sj_div}\n---\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print(f"[ERROR] log_page2_search: {e}")

def log_page2_qa(user_input, output):
    print("[DEBUG] log_page2_qa called", user_input, output)
    log_path = "logs/page2_qa.log"
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\nINPUT: {user_input}\nOUTPUT: {output}\n---\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print(f"[ERROR] log_page2_qa: {e}")

if st.button("재무제표 보기"):
    # Set initial display mode to summary when a new financial statement is viewed
    st.session_state[f'display_mode_{sj_div}'] = 'summary'
    if final_company:
        print(f"[LOG] [재무제표 보기] 입력 기업명: {final_company}")
        corp_code_info = DartAPI().find_corp_code(final_company)
        corp_code = corp_code_info.get('corp_code') if isinstance(corp_code_info, dict) else None
        print(f"[LOG] [재무제표 보기] 반환 corp_code: {corp_code_info}")
        if corp_code and isinstance(corp_code, str) and corp_code.isdigit() and len(corp_code) == 8:
            # 1. 기업 기본 정보 먼저 보여주기 (재무 분석 페이지에서는 간단히 표시)
            print(f"[LOG] [재무제표 보기] get_company_info({corp_code}) 호출")
            info = DartAPI().get_company_info(corp_code)
            if info.get('corp_name'):
                st.info(f"기업명: {info.get('corp_name')}\n대표자명: {info.get('ceo_nm')}\n주소: {info.get('adres')}")
            # 2. 재무제표 시도
            print(f"[LOG] [재무제표 보기] get_financial_statements({corp_code}, bsns_year={selected_year}, fs_div={sj_div}) 호출")
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
            log_page2_search(final_company, selected_year, sj_div)
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
        print(f"[LOG] [Q&A] get_financial_info_from_dart 호출: company={company}, year={year}, item={item}")
        corp_code_info = DartAPI().find_corp_code(company)
        corp_code = corp_code_info.get('corp_code') if isinstance(corp_code_info, dict) else None
        print(f"[LOG] [Q&A] 반환 corp_code: {corp_code}")
        if not corp_code:
            return None
        print(f"[LOG] [Q&A] get_financial_statements({corp_code}, bsns_year={year}, fs_div='IS') 호출")
        fs = DartAPI().get_financial_statements(corp_code, bsns_year=year, fs_div="IS")
        if not fs or not fs.get('list'):
            return None
        df = pretty_financial_table(fs, sj_div="IS")
        print(f"[LOG] [Q&A] 반환 재무제표 DataFrame columns: {df.columns.tolist()}")
        row = df[df['계정명'].str.contains(item, na=False)]
        print(f"[LOG] [Q&A] 계정명 매칭 row: {row}")
        if not row.empty:
            return row.iloc[0].to_dict()
        return None
    except Exception as e:
        print(f"[LOG] [Q&A] 예외 발생: {e}")
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
아래 사용자의 질문에서 비교하고자 하는 기업명(여러 개면 모두), 연도(없으면 '없음'), 항목(예: 매출, 영업이익 등)을 반드시 JSON만 반환해줘. 
만약 '경쟁사', '동종업계', '업계 1위' 등 일반명칭이 나오면, 한국 대표 상장사 기준으로 실제 기업명 리스트로 변환해서 반환해줘. 설명은 하지 마.

예시 입력: "2023년 삼성전자와 LG전자 매출 비교해줘"
예시 출력: {{"companies": ["삼성전자", "LG전자"], "year": "2023", "item": "매출"}}

예시 입력: "LG화학 경쟁사와 2023년 매출액 비교해줘"
예시 출력: {{"companies": ["LG화학", "삼성SDI", "SK이노베이션"], "year": "2023", "item": "매출액"}}

예시 입력: "2022년 현대차 동종업계 영업이익 비교"
예시 출력: {{"companies": ["현대차", "기아", "쌍용차"], "year": "2022", "item": "영업이익"}}

입력: "{user_input}"
출력:
"""
    result = llm.invoke(prompt)
    for line in result.content.strip().split('\n'):
        try:
            parsed = json.loads(line)
            return parsed
        except Exception:
            continue
    return None

if st.sidebar.button("질문하기", key="financial_qa_btn"):
    search_msg = st.sidebar.empty()
    search_msg.info("검색중 ...")
    # 1. page2 context에서 답변 시도
    context = st.session_state.get("financial_analysis_result", "")
    answer = answer_from_page_context(chat_input, context)
    if answer:
        search_msg.empty()
        st.sidebar.success(f"페이지 내 답변: {answer}")
        log_page2_qa(chat_input, answer)
    else:
        # 2. 외부 검색 + LLM 답변
        web_context = ""
        serp_results = web_search(chat_input, num_results=3)
        if serp_results:
            web_context += "[웹 검색 결과]\n"
            for r in serp_results:
                web_context += f"- {r['title']}\n  {r['snippet']}\n  {r['link']}\n"
        if web_context:
            llm = ChatOpenAI(model="gpt-4o", temperature=0)
            prompt = f"""
아래는 '{chat_input}'에 대한 웹 검색 결과입니다. 이 정보를 참고하여 한국어로 간결하게 요약해줘.\n\n{web_context}\n\n답변:
"""
            try:
                result = llm.invoke(prompt)
                search_msg.empty()
                st.sidebar.success(f"[외부 답변] {result.content.strip()}")
                log_page2_qa(chat_input, f"[외부 답변] {result.content.strip()}")
            except Exception as e:
                search_msg.empty()
                st.sidebar.error(f"[외부 답변 실패] {e}")
                log_page2_qa(chat_input, f"[외부 답변 실패] {e}")
        else:
            search_msg.empty()
            st.sidebar.info("외부 검색 결과 없음")
            log_page2_qa(chat_input, "[외부 검색 결과 없음]")

# --- get_market_summary 함수 추가 (03_Market_Analysis.py에서 복사) ---
def get_market_summary(industry_name, web_results=None):
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
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
