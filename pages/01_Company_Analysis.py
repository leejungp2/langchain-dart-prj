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
            "당신은 다양한 툴을 사용할 수 있는 AI 비서입니다. "
            "툴에서 '찾을 수 없습니다' 또는 '유사한 기업명 후보'가 반환되면, "
            "그 메시지를 바로 사용자에게 Final Answer로 보여주세요. "
            "모든 답변과 설명(Thought)은 반드시 한국어로 작성하세요. "
            "툴을 사용할 수 없는 경우에만 'Final Answer:'로 답변하세요. "
            "각 툴의 설명과 예시를 참고하세요.\n"
            "예시 질문: 삼성전자 2023년 재무제표 보여줘\n"
            "예시 툴 호출: get_financial_statements_tool(query='삼성전자 2023 사업보고서')\n"
        )
    }
)

# Streamlit UI
st.title("AI 기업 분석 (하이브리드)")

# 번역 함수 정의
def translate_to_ko(text):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Translate the following text to Korean."},
            {"role": "user", "content": text}
        ]
    )
    return response['choices'][0]['message']['content'].strip()

# 1. 자연어 챗봇
st.header("AI 챗봇")
render_info_message()
# 검색창 + 버튼 UI
user_input = st.text_input("AI에게 질문하세요!", key="ai_query_input")
search_clicked = st.button("검색")
if search_clicked and user_input:
    st.session_state['ai_query'] = user_input

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
        # PDF가 업로드되어 있으면 항상 agent에 pdf_path를 함께 전달
        agent_input = {"input": st.session_state['ai_query']}
        if pdf_path:
            agent_input["pdf_path"] = pdf_path
        result = agent.invoke(agent_input, return_intermediate_steps=True)
        answer = result["output"]
        steps = result.get("intermediate_steps", [])
        last_obs = None
        last_thought = None
        if steps:
            last_thought = steps[-1][0].log if hasattr(steps[-1][0], 'log') else None
            last_obs = steps[-1][1]
        if isinstance(answer, str) and answer.endswith(".png") and os.path.exists(answer):
            st.image(answer)
        elif not answer or (
            re.match(r"[A-Za-z]", answer.strip())
            or "unable" in answer.lower()
            or "not available" in answer.lower()
            or "cannot" in answer.lower()
            or "없습니다" in answer
        ):
            if last_obs:
                st.write(f"Observation(툴 반환값): {last_obs}")
            if last_thought:
                if re.match(r"[A-Za-z]", last_thought.strip()):
                    last_thought_kr = translate_to_ko(last_thought)
                else:
                    last_thought_kr = last_thought
                st.info(f"AI의 참고 설명:\n{last_thought_kr}\n\n한글/영문으로 바꿔서 입력을 다시 시도해 보세요.")
            elif not last_obs:
                st.warning("결과가 없습니다. 입력값을 다시 확인해 주세요.")
        else:
            st.write(answer)
    except OutputParserException:
        if 'last_obs' in locals() and last_obs:
            st.write(last_obs)
        if 'last_thought' in locals() and last_thought:
            if re.match(r"[A-Za-z]", last_thought.strip()):
                try:
                    last_thought_kr = GoogleTranslator(source='auto', target='ko').translate(last_thought)
                except Exception:
                    last_thought_kr = last_thought
            else:
                last_thought_kr = last_thought
            st.info(f"AI의 참고 설명:\n{last_thought_kr}\n\n한글/영문으로 바꿔서 입력을 다시 시도해 보세요.")
        else:
            st.error("에이전트가 반복 제한 또는 시간 제한에 걸렸습니다. 입력을 더 구체적으로 해보세요.")
    except Exception as e:
        st.error(f"에이전트 실행 중 오류 발생: {e}")
        st.text(traceback.format_exc())
    st.session_state['ai_query'] = ''

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
    else:
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        prompt = f"다음 회사 분석 결과를 참고해서 질문에 답변해줘.\n\n분석 결과: {page_context}\n\n질문: {chat_input}"
        try:
            result = llm.invoke(prompt)
            st.sidebar.success(f"외부 답변: {result.content.strip()}")
        except Exception as e:
            st.sidebar.error(f"답변 실패: {e}")