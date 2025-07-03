import requests
import os
import pandas as pd
import xml.etree.ElementTree as et
from io import BytesIO
from zipfile import ZipFile
import re
import streamlit as st
from sentence_transformers import SentenceTransformer, util
import openai
from fuzzywuzzy import process

class DartAPI:
    BASE_URL = "https://opendart.fss.or.kr/api"
    
    # 사전 기반 동의어/약칭 매핑
    """
    CORP_NAME_SYNONYMS = {
    "LG 화학": "LG화학",
        "삼바": "삼성바이오로직스",
        "현대자동차": "현대차",
        "hyundai": "현대차",
        "POSCO홀딩스": "POSCO홀딩스",
        "삼성SDI": "삼성SDI",
        "기아차": "기아",
        "기아자동차": "기아",
        "KIA": "기아",
        "삼성전자주식회사": "삼성전자",
        "삼성전자(주)": "삼성전자",
        "samsung": "삼성전자",
        "에스케이하이닉스": "SK하이닉스",
        "SK 하이닉스": "SK하이닉스",
        "SK HYNIX": "SK하이닉스",
        "SK하이닉스(주)": "SK하이닉스",
        "NAVER주식회사": "NAVER",
        "네이버": "NAVER",
        "카카오주식회사": "카카오",
        "kakao": "카카오"
        # 필요시 더 추가
    }
    """
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("DART_API_KEY")
        if not self.api_key:
            raise ValueError("DART API Key가 설정되어 있지 않습니다.")
        self.corp_code_df = self._load_corp_code_df()

    def _load_corp_code_df(self):
        cache_path = "corpCode_cache.csv"
        if os.path.exists(cache_path):
            df = pd.read_csv(cache_path, dtype=str)
        else:
            u = requests.get(f'{self.BASE_URL}/corpCode.xml', params={'crtfc_key': self.api_key})
            zipfile_obj = ZipFile(BytesIO(u.content))
            xml_str = zipfile_obj.read('CORPCODE.xml').decode('utf-8')
            xroot = et.fromstring(xml_str)
            df_cols = ["corp_code", "corp_name", "stock_code", "modify_date"]
            rows = []
            for node in xroot:
                res = []
                for el in df_cols:
                    res.append(node.find(el).text if node.find(el) is not None else None)
                rows.append({df_cols[i]: res[i] for i in range(len(df_cols))})
            df = pd.DataFrame(rows, columns=df_cols)
            df.to_csv(cache_path, index=False)
        def clean(name):
            return re.sub(r"[\s\(\)\'\"\.,주식회사]", "", str(name)).strip().lower()
        df['corp_name_clean'] = df['corp_name'].apply(clean)
        return df

    def get_similar_corp_names(self, input_name, top_n=5):
        names = self.corp_code_df['corp_name'].tolist()
        matches = process.extract(input_name, names, limit=top_n)
        candidates = [m[0] for m in matches]
        return candidates

    def ask_llm_for_corp_name(self, raw_input, candidates):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not candidates:
            return None
        openai.api_key = api_key
        prompt = f"""
        다음 입력에서 '공식 기업명(corp_name)'을 아래 후보 중 하나로 골라주세요.\n입력: "{raw_input}"\n후보: {candidates}\n출력: 정확한 후보 하나만
        """
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role":"system","content":"기업명 매핑 어시스턴트입니다."},
                          {"role":"user","content":prompt}],
                temperature=0
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            return None

    def clean_corp_name(self, name):
        # 괄호 및 괄호 안 내용 제거
        name = re.sub(r"\(.*?\)", "", name)
        # 불필요한 접미사 제거
        suffixes = ["주식회사", "㈜", "Co., Ltd.", "코퍼레이션", "유한회사", "INC", "INC.", "CORP", "CORPORATION", "CO.", "CO", "LIMITED", "COMPANY"]
        for s in suffixes:
            name = name.replace(s, "")
        return name.strip().lower()

    def find_corp_code(self, corp_name):
        clean_input = self.clean_corp_name(corp_name)
        names = self.corp_code_df['corp_name'].tolist()
        clean_names = [self.clean_corp_name(n) for n in names]
        stock_codes = self.corp_code_df['stock_code'].tolist()
        corp_code = None
        candidates = []
        llm_result = None
        # 1. fuzzywuzzy로 clean된 이름끼리 매칭 (상장사 우선)
        match, score = process.extractOne(clean_input, clean_names)
        if score >= 90:
            idx = clean_names.index(match)
            if stock_codes[idx] and str(stock_codes[idx]).strip() != '':
                corp_code = self.corp_code_df.iloc[idx]['corp_code']
            else:
                for i, cname in enumerate(clean_names):
                    if cname == match and stock_codes[i] and str(stock_codes[i]).strip() != '':
                        corp_code = self.corp_code_df.iloc[i]['corp_code']
                        break
                if not corp_code:
                    corp_code = self.corp_code_df.iloc[idx]['corp_code']
        else:
            matches = process.extract(clean_input, clean_names, limit=10)
            sorted_matches = sorted(matches, key=lambda m: (not (stock_codes[clean_names.index(m[0])] and str(stock_codes[clean_names.index(m[0])]).strip() != ''), -m[1]))
            top_matches = sorted_matches[:5]
            candidates = [names[clean_names.index(m[0])] for m in top_matches]
            llm_result = self.ask_llm_for_corp_name(corp_name, candidates)
            if llm_result:
                llm_clean = self.clean_corp_name(llm_result)
                for i, cname in enumerate(clean_names):
                    if cname == llm_clean and stock_codes[i] and str(stock_codes[i]).strip() != '':
                        corp_code = self.corp_code_df.iloc[i]['corp_code']
                        break
                if not corp_code and llm_clean in clean_names:
                    idx = clean_names.index(llm_clean)
                    corp_code = self.corp_code_df.iloc[idx]['corp_code']
        return {
            "corp_code": corp_code,
            "candidates": candidates,
            "llm_result": llm_result
        }

    def get_company_info(self, corp_code):
        """기업 개황 조회"""
        url = f"{self.BASE_URL}/company.json"
        params = {"crtfc_key": self.api_key, "corp_code": corp_code}
        try:
            res = requests.get(url, params=params, timeout=10)
            return res.json()
        except Exception as e:
            return {"status": "error", "message": f"DART API 요청 실패: {e}"}

    def get_financial_statements(self, corp_code, bsns_year, reprt_code="11011", fs_div="FSS"):
        """재무제표(단일회사 주요재무) 조회"""
        url = f"{self.BASE_URL}/fnlttSinglAcntAll.json"
        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code,  # 11011: 사업보고서, 11012: 반기, 11013: 1분기, 11014: 3분기
            "fs_div": fs_div,
        }
        try:
            res = requests.get(url, params=params, timeout=10)
            return res.json()
        except Exception as e:
            return {"status": "error", "message": f"DART API 요청 실패: {e}"}

    def get_notice_list(self, corp_code, bgn_de, end_de):
        """공시목록 조회"""
        url = f"{self.BASE_URL}/list.json"
        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "bgn_de": bgn_de,  # YYYYMMDD
            "end_de": end_de,
        }
        try:
            res = requests.get(url, params=params, timeout=10)
            return res.json()
        except Exception as e:
            return {"status": "error", "message": f"DART API 요청 실패: {e}"}

    def get_semiannual_reports_list(self, corp_code, year, half='상반기'):
        """
        특정 연도/반기의 반기보고서만 반환
        half: '상반기' 또는 '하반기'
        """
        if half == '상반기':
            bgn_de, end_de = f"{year}0101", f"{year}0630"
        else:
            bgn_de, end_de = f"{year}0701", f"{year}1231"
        data = self.get_notice_list(corp_code, bgn_de, end_de)
        if not data.get('list'):
            return []
        # '반기보고서'가 report_nm에 포함된 공시만 필터링
        semiannual_reports = [item for item in data['list'] if '반기보고서' in item.get('report_nm', '')]
        # 최신순 정렬
        semiannual_reports.sort(key=lambda x: x.get('rcept_dt', ''), reverse=True)
        return semiannual_reports

    # corp_code(고유코드) 매핑은 별도 유틸 함수로 구현 필요 (공식문서 참고) 

    def display_result(self, answer, last_obs):
        if isinstance(answer, str) and answer.endswith(".png") and os.path.exists(answer):
            st.image(answer)
        elif not answer:
            if last_obs:
                st.write(last_obs)
            else:
                st.warning("결과가 없습니다. 한글/영문으로 바꿔서 입력을 다시 시도해 보세요.")
        elif re.match(r"[A-Za-z]", answer.strip()):
            # answer가 영어로 시작하면 대신 last_obs(툴 반환값) 출력
            if last_obs:
                st.write(last_obs)
            else:
                st.write(answer)
        else:
            st.write(answer) 