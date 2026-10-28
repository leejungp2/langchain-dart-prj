# 📘 LangChain-DART

## 📌 Project Overview

This project provides an AI interface for analyzing and asking questions about data from Korea's DART electronic disclosure system using LangChain. Users can upload or look up a company's disclosures, ask questions in natural language, and quickly find the information they need.

## 🎥 Demo

[Watch the demo video](./250704%20demo.mov)

## 📂 Project Structure

```
├── backend/ # Data processing and analysis logic
│ └── company_analysis_tools.py # Company analysis helper functions
│
├── frontend/ # User interface (e.g., Streamlit)
│ └── company_analysis_ui.py # UI implementation
│
├── pages/ # Page modules (for Streamlit)
│ └── 01_Company_Analysis.py # Company analysis page
│
├── prompts/ # Prompt design and LLM configuration
│ └── general.yaml # Prompt and system configuration
│
├── dart_api.py # DART API integration
├── corpCode.xml # XML mapping of company identifiers
├── main.py # Application entry point
├── requirements.txt # Project dependencies
├── .env # API keys and environment variables
├── .gitignore # Files excluded from Git
└── README.md # Project documentation
```

## ⚙️ Setup

```bash
# Create and activate a virtual environment
conda create -n langchain-dart python=3.11
conda activate langchain-dart

# Install dependencies
pip install -r requirements.txt
```

## 🔑 API Keys

This project uses the DART API and OpenAI API. Obtain API keys and add them to a `.env` file.

### 1️⃣ DART API Key

1. Visit the [DART Open API](https://opendart.fss.or.kr/).
2. Sign up and log in.
3. Go to **My Page → API Application → Issue API Key**.

### 2️⃣ OpenAI API Key

1. Visit the [OpenAI Platform](https://platform.openai.com/account/api-keys).
2. Log in and select **Create new secret key**.
3. Copy the key and add it to your `.env` file:

```ini
DART_API_KEY=your_dart_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

### 3️⃣ Serp API Key

Add your Serp API key to the `.env` file if required by your configuration.

## 🚀 Run the Application

With the virtual environment active and dependencies installed, run:

```bash
streamlit run main.py
```
