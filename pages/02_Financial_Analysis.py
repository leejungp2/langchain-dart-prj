import streamlit as st
import pandas as pd
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dart_api import DartAPI
from frontend.financial_analysis_display import render_financial_table

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