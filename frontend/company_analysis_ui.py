import streamlit as st
import pandas as pd

def render_info_message():
    """AI 챗봇에서 질문 가능한 범위 안내 메시지 출력"""
    st.info("""
    아래와 같은 질문이 가능합니다:
    - 선택한 기업의 기본 정보(예: '삼성전자 CEO가 누구야?')
    - 선택한 연도/보고서의 재무제표(예: '2024년 삼성전자 매출액 알려줘')
    - 업로드한 PDF 내 주요 내용 요약/질문(예: '이 보고서 요약해줘', '주요 리스크는?')
    - 기타 기업 관련 일반 질문
    ※ 너무 구체적이거나 DART API/업로드 파일에 없는 정보는 답변이 제한될 수 있습니다.
    """)

def render_search_box():
    """Streamlit 기본 입력창을 사용하여 입력값을 st.session_state['ai_query']에 저장"""
    user_input = st.text_input("AI에게 질문하세요!", key="ai_query_input")
    if user_input:
        st.session_state['ai_query'] = user_input

def render_financial_table(fs, company, year, sj_div='BS'):
    """특정 재무제표만 예쁘게 표로 출력"""
    st.subheader(f"{company} {year}년 재무제표")
    df = pretty_financial_table(fs, sj_div=sj_div)
    st.dataframe(df)

def pretty_financial_table(fs_data, sj_div='BS'):
    """
    fs_data: DART API에서 받아온 재무제표 dict (list of dict)
    sj_div: 'BS'(재무상태표), 'IS'(손익계산서), 'CIS'(포괄손익계산서), 'CF'(현금흐름표)
    """
    if not fs_data or 'list' not in fs_data or not fs_data['list']:
        return pd.DataFrame([{'계정명': '데이터 없음'}])
    df = pd.DataFrame(fs_data['list'])
    df = df[df['sj_div'] == sj_div]
    if df.empty:
        return pd.DataFrame([{'계정명': '데이터 없음'}])
    cols = ['account_nm', 'thstrm_amount', 'frmtrm_amount', 'bfefrmtrm_amount']
    cols = [c for c in cols if c in df.columns]
    df = df[cols]
    rename_map = {
        'account_nm': '계정명',
        'thstrm_amount': '당기',
        'frmtrm_amount': '전기',
        'bfefrmtrm_amount': '전전기'
    }
    df = df.rename(columns=rename_map)
    for col in ['당기', '전기', '전전기']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f'{int(str(x).replace(",", "")):,}' if pd.notnull(x) and str(x).replace(',','').isdigit() else x)
    df = df.reset_index(drop=True)
    return df 