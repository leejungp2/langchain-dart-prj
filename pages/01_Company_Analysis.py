import sys
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
from dotenv import load_dotenv
import pandas as pd
import PyPDF2
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent
from dart_api import DartAPI
import re
from deep_translator import GoogleTranslator
import openai
import datetime

# --- 분리된 프론트엔드/백엔드 함수 import ---
from frontend.company_analysis_ui import render_info_message, render_search_box
from frontend.financial_analysis_display import render_financial_table
from backend.company_analysis_tools import (
    get_company_info_tool,
    get_financial_statements_tool,
    analyze_csv_tool,
    summarize_pdf_tool,
    plot_financials_tool,
    answer_from_page_context
)

# .env에서 API 키 불러오기
load_dotenv()

# OpenAI API 키 설정
openai.api_key = os.getenv("OPENAI_API_KEY")

# DART API 키 안내 메시지
if not os.getenv("DART_API_KEY"):
    st.warning(".env 파일에 DART_API_KEY를 반드시 입력하세요! 예시: DART_API_KEY=여기에_발급받은_키")

# LangChain Agent 세팅
TOOLS = [
    get_company_info_tool,
    get_financial_statements_tool,
    analyze_csv_tool,
    summarize_pdf_tool,
    plot_financials_tool,
]
llm = ChatOpenAI(model="gpt-4o", temperature=0)
agent = initialize_agent(
    TOOLS,
    llm,
    agent_type="openai-functions",
    verbose=True,
    handle_parsing_errors=True,  # 파싱 에러 발생 시 LLM 답변을 그대로 반환
    max_iterations=5,  # 반복 횟수 더 늘림
    agent_kwargs={
        "system_message": (
            """
            당신은 다양한 툴을 사용하여 1) 사용자의 자연어 input을 토대로 2) 기업 관련 정보를 찾는 '한국어' AI 에이전트입니다.
            모든 답변, Thought, Observation은 **반드시 한국어로** 작성하세요. 영어로 작성하지 마세요.
            각 툴의 설명과 예시를 참고하세요.\n
            
            툴을 사용하여 1) 사용자가 요청한 기업 {company_name}에 대한 정보를 파악하여 2) {corp_code}로 반환하도록 하세요.
            만약 툴에서 완전히 일치하는 {company_name}이 없으면, 유사한 기업명 후보 {candidates}를 찾아서 2) {corp_code}로 매핑하세요.
            {candidate}는 1) 사용자가 입력한 기업명과 같은 글자를 공유하거나 2) 사용자가 입력한 기업의 영어/한국어 번역을 포함합니다.
            예를 들어, "기아차", "기아자동차", "KIA" 등은 모두 "기아"로 매핑되어야 합니다.\n

            예시:
            입력: "기아차"
            후보: ["기아", "기아(주)", "기아자동차", "KIA", "기아차(주)"]

            1) LLM이 공식 기업명 선택: "기아"
            2) "기아"에 해당하는 corp_code: "00106641"
            3) get_company_info("00106641") 호출

            예시 질문: 기아차 {company_name} 기본 정보 알려줘.
            예시 툴 호출: find_corp_code(query='기아차') get_company_info(corp_code='00106641')
"""
        )
    }
)

# Streamlit UI
st.title("AI 기업 분석")

# 번역 함수 정의
def translate_to_ko(text):
    client = openai.OpenAI()  # openai.api_key는 환경변수로 자동 인식
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Translate the following text to Korean."},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content.strip()

def log_page1_nl_search(user_input, output):
    print("[DEBUG] log_page1_nl_search called", user_input, output)
    log_path = "logs/page1_nl_search.log"
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\nINPUT: {user_input}\nOUTPUT: {output}\n---\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print(f"[ERROR] log_page1_nl_search: {e}")

def log_page1_qa(user_input, output):
    log_path = "logs/page1_qa.log"  # 최상단에서 바로 선언
    print("[DEBUG] log_page1_qa called", user_input, output)
    print("[DEBUG] cwd:", os.getcwd())
    print("[DEBUG] abs log_path:", os.path.abspath(log_path))
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\nINPUT: {user_input}\nOUTPUT: {output}\n---\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print(f"[ERROR] log_page1_qa: {e}")


def is_english(text):
    # 알파벳 비율이 30% 이상이면 영어로 간주
    if not text:
        return False
    return len(re.findall(r'[a-zA-Z]', text)) / max(1, len(text)) > 0.3

# 1. 자연어 챗봇
st.header("자연어 검색")
render_info_message()
# 검색창 + 버튼 UI
user_input = st.text_input("AI에게 질문하세요!", key="ai_query_input")
search_clicked = st.button("검색")
if search_clicked and user_input:
    st.session_state['ai_query'] = user_input
    print(f"[DEBUG] 새로운 입력 저장: {user_input}")

# PDF/CSV 업로드 UI를 챗봇 바로 아래로 이동
uploaded_file = st.file_uploader("자료 업로드 (PDF, CSV)", type=["pdf", "csv"])
pdf_path = None
if uploaded_file:
    st.success("파일 업로드 완료!")
    if uploaded_file.type == "application/pdf" or uploaded_file.name.endswith(".pdf"):
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.read())
            pdf_path = tmp_file.name
    elif uploaded_file.type == "text/csv" or uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        st.subheader("CSV 데이터 미리보기")
        st.dataframe(df)
        st.write("컬럼 정보:", list(df.columns))
        st.write("기초 통계:")
        st.write(df.describe())

if st.session_state.get('ai_query', ''):
    import traceback
    from langchain.schema import OutputParserException
    try:
        agent_input = {"input": st.session_state['ai_query']}
        print(f"[DEBUG] agent.invoke 실행: {agent_input}")
        if pdf_path:
            agent_input["pdf_path"] = pdf_path
        result = agent.invoke(agent_input, return_intermediate_steps=True)
        answer = result.get("output", None)
        steps = result.get("intermediate_steps", [])
        last_obs = None
        last_thought = None
        if steps:
            last_thought = steps[-1][0].log if hasattr(steps[-1][0], 'log') else None
            last_obs = steps[-1][1]
        # 반복 제한 메시지에도 반드시 마지막 Thought/Observation 출력
        if answer and not (isinstance(answer, str) and "Agent stopped due to iteration limit or time limit." in answer):
            # 영어로 시작하면 자동 번역
            if is_english(answer):
                answer_ko = translate_to_ko(answer)
                st.write(answer_ko)
                log_page1_nl_search(st.session_state['ai_query'], answer_ko)
            else:
                st.write(answer)
                log_page1_nl_search(st.session_state['ai_query'], answer)
        elif last_obs:
            st.write(f"Observation(툴 반환값): {last_obs}")
            log_page1_nl_search(st.session_state['ai_query'], str(last_obs))
        elif last_thought:
            if re.match(r"[A-Za-z]", last_thought.strip()):
                last_thought_kr = translate_to_ko(last_thought)
            else:
                last_thought_kr = last_thought
            st.info(f"AI의 참고 설명:\n{last_thought_kr}\n\n한글/영문으로 바꿔서 입력을 다시 시도해 보세요.")
            log_page1_nl_search(st.session_state['ai_query'], str(last_thought_kr))
        else:
            st.warning("결과가 없습니다. 입력값을 다시 확인해 주세요.")
            log_page1_nl_search(st.session_state['ai_query'], "결과 없음")
    except OutputParserException:
        if 'last_obs' in locals() and last_obs:
            st.write(last_obs)
            log_page1_nl_search(st.session_state['ai_query'], str(last_obs))
        if 'last_thought' in locals() and last_thought:
            if re.match(r"[A-Za-z]", last_thought.strip()):
                try:
                    last_thought_kr = GoogleTranslator(source='auto', target='ko').translate(last_thought)
                except Exception:
                    last_thought_kr = last_thought
            else:
                last_thought_kr = last_thought
            st.info(f"AI의 참고 설명:\n{last_thought_kr}\n\n한글/영문으로 바꿔서 입력을 다시 시도해 보세요.")
            log_page1_nl_search(st.session_state['ai_query'], str(last_thought_kr))
        else:
            st.error("에이전트가 반복 제한 또는 시간 제한에 걸렸습니다. 입력을 더 구체적으로 해보세요.")
            log_page1_nl_search(st.session_state['ai_query'], "에이전트 반복/시간 제한")
    except Exception as e:
        st.error(f"에이전트 실행 중 오류 발생: {e}")
        st.text(traceback.format_exc())
        log_page1_nl_search(st.session_state['ai_query'], f"[ERROR] {e}")
    finally:
        st.session_state['ai_query'] = ''  # 반드시 마지막에 초기화

st.divider()

# 2. UI 기반 주요 기능


# 분석 결과 생성 후
company_analysis_result = "여기에 회사 분석 결과가 들어갑니다."
st.session_state["company_analysis_result"] = company_analysis_result

# --- 사이드바: Q&A 챗봇 ---
st.sidebar.header("Q&A 챗봇")
st.sidebar.info("회사 분석 결과에 대해 궁금한 점을 질문해 보세요!")
chat_input = st.sidebar.text_input("질문을 입력하세요", key="company_chat_input")
if st.sidebar.button("질문하기", key="company_qa_btn"):
    page_context = st.session_state.get("company_analysis_result", "")
    answer = answer_from_page_context(chat_input, page_context)
    if answer:
        st.sidebar.success(f"페이지 내 답변: {answer}")
        log_page1_qa(chat_input, answer)
    else:
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        prompt = f"다음 회사 분석 결과를 참고해서 질문에 답변해줘.\n\n분석 결과: {page_context}\n\n질문: {chat_input}"
        try:
            result = llm.invoke(prompt)
            st.sidebar.success(f"외부 답변: {result.content.strip()}")
            log_page1_qa(chat_input, result.content.strip())
        except Exception as e:
            st.sidebar.error(f"답변 실패: {e}")
            log_page1_qa(chat_input, f"[ERROR] {e}")