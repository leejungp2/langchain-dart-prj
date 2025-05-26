# 📘 LangChain-DART 프로젝트
## 📌 프로젝트 소개
이 프로젝트는 LangChain을 활용하여 DART 전자공시 시스템의 데이터를 분석하고 질의응답할 수 있는 AI 인터페이스를 제공합니다.  
사용자는 특정 기업의 공시 데이터를 업로드하거나 조회하고, 자연어로 질문을 입력하여 필요한 정보를 빠르게 얻을 수 있습니다.

## 📂 폴더 구성
```
├── backend/ # 데이터 처리 및 분석 로직
│ └── company_analysis_tools.py # 기업 분석 도구 함수 모음
│
├── frontend/ # 사용자 인터페이스 (예: Streamlit 등)
│ └── company_analysis_ui.py # UI 구성 스크립트
│
├── pages/ # 페이지 단위 모듈 (Streamlit 전용)
│ └── 01_Company_Analysis.py # 기업 분석 페이지
│
├── prompts/ # 프롬프트 설계 및 LLM 설정
│ └── general.yaml # 프롬프트 및 시스템 설정 파일
│
├── dart_api.py # DART API 연동 함수
├── corpCode.xml # 기업 고유번호 매핑용 XML 파일
├── main.py # 앱 실행 엔트리포인트
├── requirements.txt # 의존성 패키지 목록
├── .env # API 키 및 환경 변수 설정
├── .gitignore # Git 추적 제외 파일 목록
└── README.md # 프로젝트 설명 문서
```

## ⚙️ 환경 설정
```bash
# 가상환경 생성 및 활성화
conda create -n langchain-dart python=3.11
conda activate langchain-dart

# 패키지 설치
pip install -r requirements.txt
```

## 🔑 API 키 발급

이 프로젝트는 DART API와 OpenAI API를 사용합니다.  
다음 절차에 따라 API 키를 발급받고 `.env` 파일에 등록해 주세요.

---

### 1️⃣ DART API 키 발급

1. [DART 오픈 API 신청 페이지](https://opendart.fss.or.kr/) 접속  
2. 회원가입 후 로그인  
3. **마이페이지 → API 신청 → API Key 발급**

---

### 2️⃣ OpenAI API 키 발급 (선택)

1. [OpenAI 플랫폼](https://platform.openai.com/account/api-keys) 접속  
2. 로그인 후 **Create new secret key** 클릭  
3. 생성된 키를 복사하여 `.env` 파일에 다음과 같이 추가:

```ini
# .env 예시
DART_API_KEY=your_dart_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

## 🚀 실행 방법

가상환경이 활성화되고 필요한 패키지가 설치되었다면, 아래 명령어로 앱을 실행할 수 있습니다:

```bash
streamlit run main.py