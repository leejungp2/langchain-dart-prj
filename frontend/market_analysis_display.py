import streamlit as st

def render_market_summary(summary):
    st.markdown(summary)
    st.divider()

def render_web_results(web_results):
    if web_results:
        with st.expander("웹 검색 결과 보기"):
            for item in web_results:
                st.markdown(f"- [{item['title']}]({item['link']})<br>{item['snippet']}", unsafe_allow_html=True) 