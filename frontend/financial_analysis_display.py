import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import platform
import matplotlib.ticker as ticker

# 한글 폰트 설정
if platform.system() == 'Darwin': # Mac OS
    plt.rcParams['font.family'] = 'AppleGothic'
elif platform.system() == 'Windows': # Windows
    plt.rcParams['font.family'] = 'Malgun Gothic'
else: # Linux or others
    # Check if a common Korean font is available, otherwise fall back
    if 'NanumGothic' in [f.name for f in fm.fontManager.ttflist]:
        plt.rcParams['font.family'] = 'NanumGothic'
    else:
        plt.rcParams['font.family'] = 'sans-serif'

plt.rcParams['axes.unicode_minus'] = False # 마이너스 폰트 깨짐 방지

# 매출액 유사 항목 리스트 (전역)
sales_keywords = ["매출액", "수익", "영업수익", "매출", "총수익"]

def format_amount_to_kr_unit(value):
    if pd.isna(value) or not isinstance(value, (int, float)):
        return 'N/A'
    value = int(value)
    sign = '-' if value < 0 else ''
    value = abs(value)
    if value >= 1_000_000_000_000:  # 1조 이상
        jo = value // 1_000_000_000_000
        eok = (value % 1_000_000_000_000) // 100_000_000
        man = (value % 100_000_000) // 10_000
        result = f"{sign}{jo}조"
        if eok > 0:
            result += f" {eok}억"
        if man > 0:
            result += f" {man}만"
        return result.strip()
    elif value >= 100_000_000:  # 1억 이상
        eok = value // 100_000_000
        man = (value % 100_000_000) // 10_000
        result = f"{sign}{eok}억"
        if man > 0:
            result += f" {man}만"
        return result.strip()
    elif value >= 10_000:  # 1만 이상
        man = value // 10_000
        return f"{sign}{man}만"
    else:
        return f"{sign}{value}"

def get_sj_div_label(sj_div_code):
    """sj_div 코드에 해당하는 한글 라벨을 반환합니다."""
    labels = {
        "IS": "손익계산서",
        "BS": "재무상태표",
        "CF": "현금흐름표"
    }
    return labels.get(sj_div_code, sj_div_code)

def generate_income_statement_chart(fs_data, company, year):
    """
    손익계산서 주요 항목에 대한 바 차트를 생성합니다.
    fs_data: DART API에서 받아온 재무제표 dict (list of dict)
    """
    df = pd.DataFrame(fs_data['list'])
    # IS(손익계산서), CIS(포괄손익계산서) 모두 포함
    df_is = df[df['sj_div'].isin(['IS', 'CIS'])]

    def to_float(val):
        try:
            return float(str(val).replace(',', ''))
        except (ValueError, AttributeError):
            return None

    def get_max_amount_for_keywords(df_filtered, keywords, col):
        max_val = None
        for kw in keywords:
            rows = df_filtered[df_filtered['account_nm'].str.contains(kw, na=False)]
            for val in rows[col]:
                try:
                    num = float(str(val).replace(",", ""))
                    if (max_val is None) or (num > max_val):
                        max_val = num
                except Exception:
                    continue
        return max_val

    def get_single_account_amounts(df_filtered, account_nm_str):
        row = df_filtered[df_filtered['account_nm'].str.contains(account_nm_str, na=False)]
        if not row.empty:
            return {
                'thstrm_amount': to_float(row['thstrm_amount'].iloc[0]),
                'frmtrm_amount': to_float(row['frmtrm_amount'].iloc[0]),
                'bfefrmtrm_amount': to_float(row['bfefrmtrm_amount'].iloc[0])
            }
        return {'thstrm_amount': None, 'frmtrm_amount': None, 'bfefrmtrm_amount': None}

    # 매출액, 영업이익, 당기순이익 데이터 추출
    매출액_data = {
        'thstrm_amount': get_max_amount_for_keywords(df_is, sales_keywords, 'thstrm_amount'),
        'frmtrm_amount': get_max_amount_for_keywords(df_is, sales_keywords, 'frmtrm_amount'),
        'bfefrmtrm_amount': get_max_amount_for_keywords(df_is, sales_keywords, 'bfefrmtrm_amount')
    }
    영업이익_data = get_single_account_amounts(df_is, '영업이익')
    당기순이익_data = get_single_account_amounts(df_is, '당기순이익')

    def to_eok(val):
        try:
            return float(val) / 100_000_000 if val is not None else None
        except Exception:
            return None

    # Prepare data for grouped bar chart
    chart_data = {
        '항목': ['매출액', '영업이익', '순이익'],
        '당기': [to_eok(매출액_data['thstrm_amount']), to_eok(영업이익_data['thstrm_amount']), to_eok(당기순이익_data['thstrm_amount'])],
        '전기': [to_eok(매출액_data['frmtrm_amount']), to_eok(영업이익_data['frmtrm_amount']), to_eok(당기순이익_data['frmtrm_amount'])],
        '전전기': [to_eok(매출액_data['bfefrmtrm_amount']), to_eok(영업이익_data['bfefrmtrm_amount']), to_eok(당기순이익_data['bfefrmtrm_amount'])]
    }
    chart_df = pd.DataFrame(chart_data)

    # Filter out rows where all values are None
    chart_df = chart_df.dropna(how='all', subset=['당기', '전기', '전전기'])

    if chart_df.empty:
        st.warning("시각화할 손익계산서 데이터가 부족합니다.")
        return

    # 변환 없이 원본 chart_df 사용
    fig, ax = plt.subplots(figsize=(10, 6))
    bar_width = 0.25
    index = range(len(chart_df['항목']))

    bar1 = ax.bar([i - bar_width for i in index], chart_df['당기'], bar_width, label=f'{year}년 (당기)', color='skyblue')
    bar2 = ax.bar(index, chart_df['전기'], bar_width, label=f'{int(year)-1}년 (전기)', color='lightcoral')
    bar3 = ax.bar([i + bar_width for i in index], chart_df['전전기'], bar_width, label=f'{int(year)-2}년 (전전기)', color='lightgreen')

    ax.set_xlabel('주요 항목')
    ax.set_ylabel('금액 (단위: 억)')
    ax.set_title(f'{company} 3개년 주요 손익 항목')
    ax.set_xticks(index)
    ax.set_xticklabels(chart_df['항목'], rotation=0)
    ax.legend()
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))  # 억 단위 숫자
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

def generate_income_statement_summary(fs_data):
    """
    손익계산서 요약본 데이터를 DataFrame으로 생성합니다.
    fs_data: DART API에서 받아온 재무제표 dict (list of dict)
    """
    df = pd.DataFrame(fs_data['list'])
    # IS(손익계산서), CIS(포괄손익계산서) 모두 포함
    df_is = df[df['sj_div'].isin(['IS', 'CIS'])]
    print("Debug IS account_nm unique values:", df_is['account_nm'].unique()) # Debugging print
    print("Debug IS head (account_nm, thstrm_amount):") # Debugging print
    print(df_is[['account_nm', 'thstrm_amount']].head().to_string()) # Debugging print

    def get_max_amount_for_keywords(df_filtered, keywords, col):
        max_val = None
        for kw in keywords:
            rows = df_filtered[df_filtered['account_nm'].str.contains(kw, na=False)]
            for val in rows[col]:
                try:
                    num = float(str(val).replace(",", ""))
                    if (max_val is None) or (num > max_val):
                        max_val = num
                except Exception:
                    continue
        return max_val

    def get_raw_amount(account_nm_str, col):
        row = df_is[df_is['account_nm'].str.contains(account_nm_str, na=False)]
        if not row.empty:
            val = row[col].iloc[0]
            try:
                return float(str(val).replace(",", ""))
            except (ValueError, AttributeError):
                return None
        return None

    def get_formatted_amount_max(account_nm_strs, col):
        raw_val = get_max_amount_for_keywords(df_is, account_nm_strs, col)
        return format_amount_to_kr_unit(raw_val)

    def get_formatted_amount(account_nm_str, col):
        raw_val = get_raw_amount(account_nm_str, col)
        return format_amount_to_kr_unit(raw_val)

    # '당기', '전기', '전전기' 데이터를 가져옴 (계산을 위해 raw 값 사용)
    매출액_당기_raw = get_max_amount_for_keywords(df_is, sales_keywords, 'thstrm_amount')
    매출액_전기_raw = get_max_amount_for_keywords(df_is, sales_keywords, 'frmtrm_amount')
    매출액_전전기_raw = get_max_amount_for_keywords(df_is, sales_keywords, 'bfefrmtrm_amount')

    영업이익_당기_raw = get_raw_amount("영업이익", 'thstrm_amount')
    영업이익_전기_raw = get_raw_amount("영업이익", 'frmtrm_amount')
    영업이익_전전기_raw = get_raw_amount("영업이익", 'bfefrmtrm_amount')

    당기순이익_당기_raw = get_raw_amount("당기순이익", 'thstrm_amount')
    당기순이익_전기_raw = get_raw_amount("당기순이익", 'frmtrm_amount')
    당기순이익_전전기_raw = get_raw_amount("당기순이익", 'bfefrmtrm_amount')

    # 표에 표시할 포맷팅된 값
    매출액_당기 = format_amount_to_kr_unit(매출액_당기_raw)
    매출액_전기 = format_amount_to_kr_unit(매출액_전기_raw)
    매출액_전전기 = format_amount_to_kr_unit(매출액_전전기_raw)

    영업이익_당기 = get_formatted_amount("영업이익", 'thstrm_amount')
    영업이익_전기 = get_formatted_amount("영업이익", 'frmtrm_amount')
    영업이익_전전기 = get_formatted_amount("영업이익", 'bfefrmtrm_amount')

    당기순이익_당기 = get_formatted_amount("당기순이익", 'thstrm_amount')
    당기순이익_전기 = get_formatted_amount("당기순이익", 'frmtrm_amount')
    당기순이익_전전기 = get_formatted_amount("당기순이익", 'bfefrmtrm_amount')

    영업이익률_pct = ""
    if 매출액_당기_raw is not None and 영업이익_당기_raw is not None and 매출액_당기_raw != 0:
        ratio = (영업이익_당기_raw / 매출액_당기_raw) * 100
        영업이익률_pct = f"{'+' if ratio >= 0 else ''}{ratio:.1f}%"

    순이익률_pct = ""
    if 매출액_당기_raw is not None and 당기순이익_당기_raw is not None and 매출액_당기_raw != 0:
        ratio = (당기순이익_당기_raw / 매출액_당기_raw) * 100
        순이익률_pct = f"{'+' if ratio >= 0 else ''}{ratio:.1f}%"

    전년대비매출_pct_str = ""
    if 매출액_당기_raw is not None and 매출액_전기_raw is not None and 매출액_전기_raw != 0:
        change_pct = ((매출액_당기_raw - 매출액_전기_raw) / 매출액_전기_raw) * 100
        전년대비매출_pct_str = f"{'+' if change_pct >= 0 else ''}{change_pct:.1f}%"

    data = [
        {"항목": "매출액", "당기": 매출액_당기, "전기": 매출액_전기, "전전기": 매출액_전전기, "비고": 전년대비매출_pct_str},
        {"항목": "영업이익", "당기": 영업이익_당기, "전기": 영업이익_전기, "전전기": 영업이익_전전기, "비고": 영업이익률_pct},
        {"항목": "순이익", "당기": 당기순이익_당기, "전기": 당기순이익_전기, "전전기": 당기순이익_전전기, "비고": 순이익률_pct}
    ]

    summary_df = pd.DataFrame(data)
    return summary_df

def generate_balance_sheet_summary(fs_data):
    """
    재무상태표 요약본 데이터를 DataFrame으로 생성합니다.
    fs_data: DART API에서 받아온 재무제표 dict (list of dict)
    """
    df = pd.DataFrame(fs_data['list'])
    df_bs = df[df['sj_div'] == 'BS']

    def get_raw_amount(account_nm_str, col):
        val = df_bs[df_bs['account_nm'].str.contains(account_nm_str, na=False)][col].iloc[0] if not df_bs[df_bs['account_nm'].str.contains(account_nm_str, na=False)].empty else None
        if val is None:
            return None
        try:
            return float(str(val).replace(",", ""))
        except (ValueError, AttributeError):
            return None

    def get_formatted_amount(account_nm_str, col):
        raw_val = get_raw_amount(account_nm_str, col)
        return format_amount_to_kr_unit(raw_val)

    # '당기', '전기', '전전기' 데이터를 가져옴 (계산을 위해 raw 값 사용)
    총자산_당기_raw = get_raw_amount("자산총계", 'thstrm_amount')
    총자산_전기_raw = get_raw_amount("자산총계", 'frmtrm_amount')
    총자산_전전기_raw = get_raw_amount("자산총계", 'bfefrmtrm_amount')

    총부채_당기_raw = get_raw_amount("부채총계", 'thstrm_amount')
    총부채_전기_raw = get_raw_amount("부채총계", 'frmtrm_amount')
    총부채_전전기_raw = get_raw_amount("부채총계", 'bfefrmtrm_amount')

    자기자본_당기_raw = get_raw_amount("자본총계", 'thstrm_amount')
    자기자본_전기_raw = get_raw_amount("자본총계", 'frmtrm_amount')
    자기자본_전전기_raw = get_raw_amount("자본총계", 'bfefrmtrm_amount')

    # 표에 표시할 포맷팅된 값
    총자산_당기 = get_formatted_amount("자산총계", 'thstrm_amount')
    총자산_전기 = get_formatted_amount("자산총계", 'frmtrm_amount')
    총자산_전전기 = get_formatted_amount("자산총계", 'bfefrmtrm_amount')

    총부채_당기 = get_formatted_amount("부채총계", 'thstrm_amount')
    총부채_전기 = get_formatted_amount("부채총계", 'frmtrm_amount')
    총부채_전전기 = get_formatted_amount("부채총계", 'bfefrmtrm_amount')

    자기자본_당기 = get_formatted_amount("자본총계", 'thstrm_amount')
    자기자본_전기 = get_formatted_amount("자본총계", 'frmtrm_amount')
    자기자본_전전기 = get_formatted_amount("자본총계", 'bfefrmtrm_amount')

    부채비율_pct = ""
    if 총부채_당기_raw is not None and 자기자본_당기_raw is not None and 자기자본_당기_raw != 0:
        ratio = (총부채_당기_raw / 자기자본_당기_raw * 100)
        부채비율_pct = f"{'+' if ratio >= 0 else ''}{ratio:.1f}%"
    else:
        부채비율_pct = "N/A"

    data = [
        {"항목": "총 자산", "당기": 총자산_당기, "전기": 총자산_전기, "전전기": 총자산_전전기},
        {"항목": "총 부채", "당기": 총부채_당기, "전기": 총부채_전기, "전전기": 총부채_전전기},
        {"항목": "자기자본", "당기": 자기자본_당기, "전기": 자기자본_전기, "전전기": 자기자본_전전기},
        {"항목": "부채비율", "당기": 부채비율_pct, "전기": "", "전전기": ""} # 부채비율은 당기만 표시
    ]

    summary_df = pd.DataFrame(data)
    return summary_df

def generate_cash_flow_summary(fs_data):
    """
    현금흐름표 요약본 데이터를 DataFrame으로 생성합니다.
    fs_data: DART API에서 받아온 재무제표 dict (list of dict)
    """
    df = pd.DataFrame(fs_data['list'])
    df_cf = df[df['sj_div'] == 'CF']

    def get_raw_amount(account_nm_str, col):
        val = df_cf[df_cf['account_nm'].str.contains(account_nm_str, na=False)][col].iloc[0] if not df_cf[df_cf['account_nm'].str.contains(account_nm_str, na=False)].empty else None
        if val is None:
            return None
        try:
            return float(str(val).replace(",", ""))
        except (ValueError, AttributeError):
            return None

    def get_formatted_amount(account_nm_str, col):
        raw_val = get_raw_amount(account_nm_str, col)
        return format_amount_to_kr_unit(raw_val)

    # '당기', '전기', '전전기' 데이터를 가져옴
    영업활동_현금흐름_당기 = get_formatted_amount("영업활동으로 인한 현금흐름", 'thstrm_amount')
    영업활동_현금흐름_전기 = get_formatted_amount("영업활동으로 인한 현금흐름", 'frmtrm_amount')
    영업활동_현금흐름_전전기 = get_formatted_amount("영업활동으로 인한 현금흐름", 'bfefrmtrm_amount')

    투자활동_현금흐름_당기 = get_formatted_amount("투자활동으로 인한 현금흐름", 'thstrm_amount')
    투자활동_현금흐름_전기 = get_formatted_amount("투자활동으로 인한 현금흐름", 'frmtrm_amount')
    투자활동_현금흐름_전전기 = get_formatted_amount("투자활동으로 인한 현금흐름", 'bfefrmtrm_amount')

    재무활동_현금흐름_당기 = get_formatted_amount("재무활동으로 인한 현금흐름", 'thstrm_amount')
    재무활동_현금흐름_전기 = get_formatted_amount("재무활동으로 인한 현금흐름", 'frmtrm_amount')
    재무활동_현금흐름_전전기 = get_formatted_amount("재무활동으로 인한 현금흐름", 'bfefrmtrm_amount')

    data = [
        {"항목": "영업활동 현금흐름", "당기": 영업활동_현금흐름_당기, "전기": 영업활동_현금흐름_전기, "전전기": 영업활동_현금흐름_전전기},
        {"항목": "투자활동 현금흐름", "당기": 투자활동_현금흐름_당기, "전기": 투자활동_현금흐름_전기, "전전기": 투자활동_현금흐름_전전기},
        {"항목": "재무활동 현금흐름", "당기": 재무활동_현금흐름_당기, "전기": 재무활동_현금흐름_전기, "전전기": 재무활동_현금흐름_전전기}
    ]

    summary_df = pd.DataFrame(data)
    return summary_df

def generate_cash_flow_chart(fs_data, company, year):
    """
    현금흐름표 주요 항목에 대한 바 차트를 생성합니다.
    fs_data: DART API에서 받아온 재무제표 dict (list of dict)
    """
    df = pd.DataFrame(fs_data['list'])
    df_cf = df[df['sj_div'] == 'CF']

    def to_float(val):
        try:
            return float(str(val).replace(',', ''))
        except (ValueError, AttributeError):
            return None

    def get_amounts_for_account(df_filtered, account_nm_str):
        row = df_filtered[df_filtered['account_nm'].str.contains(account_nm_str, na=False)]
        if not row.empty:
            return {
                'thstrm_amount': to_float(row['thstrm_amount'].iloc[0]),
                'frmtrm_amount': to_float(row['frmtrm_amount'].iloc[0]),
                'bfefrmtrm_amount': to_float(row['bfefrmtrm_amount'].iloc[0])
            }
        return {'thstrm_amount': None, 'frmtrm_amount': None, 'bfefrmtrm_amount': None}

    영업활동_현금흐름_data = get_amounts_for_account(df_cf, '영업활동으로 인한 현금흐름')
    투자활동_현금흐름_data = get_amounts_for_account(df_cf, '투자활동으로 인한 현금흐름')
    재무활동_현금흐름_data = get_amounts_for_account(df_cf, '재무활동으로 인한 현금흐름')

    # Prepare data for grouped bar chart
    chart_data = {
        '항목': ["영업활동 현금흐름", "투자활동 현금흐름", "재무활동 현금흐름"],
        '당기': [영업활동_현금흐름_data['thstrm_amount'], 투자활동_현금흐름_data['thstrm_amount'], 재무활동_현금흐름_data['thstrm_amount']],
        '전기': [영업활동_현금흐름_data['frmtrm_amount'], 투자활동_현금흐름_data['frmtrm_amount'], 재무활동_현금흐름_data['frmtrm_amount']],
        '전전기': [영업활동_현금흐름_data['bfefrmtrm_amount'], 투자활동_현금흐름_data['bfefrmtrm_amount'], 재무활동_현금흐름_data['bfefrmtrm_amount']]
    }
    chart_df = pd.DataFrame(chart_data)

    # Filter out rows where all values are None
    chart_df = chart_df.dropna(how='all', subset=['당기', '전기', '전전기'])

    if chart_df.empty:
        st.warning("시각화할 현금흐름표 데이터가 부족합니다.")
        return

    # 변환 없이 원본 chart_df 사용
    fig, ax = plt.subplots(figsize=(10, 6))
    bar_width = 0.25
    index = range(len(chart_df['항목']))

    bar1 = ax.bar([i - bar_width for i in index], chart_df['당기'], bar_width, label=f'{year}년 (당기)', color='purple')
    bar2 = ax.bar(index, chart_df['전기'], bar_width, label=f'{int(year)-1}년 (전기)', color='orange')
    bar3 = ax.bar([i + bar_width for i in index], chart_df['전전기'], bar_width, label=f'{int(year)-2}년 (전전기)', color='brown')

    ax.set_xlabel('주요 항목')
    ax.set_ylabel('금액 (단위: 억)')
    ax.set_title(f'{company} 3개년 주요 현금흐름')
    ax.set_xticks(index)
    ax.set_xticklabels(chart_df['항목'], rotation=0)
    ax.legend()
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))  # 억 단위 숫자
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

def generate_balance_sheet_chart(fs_data, company, year):
    """
    재무상태표 주요 항목에 대한 바 차트를 생성합니다.
    fs_data: DART API에서 받아온 재무제표 dict (list of dict)
    """
    df = pd.DataFrame(fs_data['list'])
    df_bs = df[df['sj_div'] == 'BS']

    def to_float(val):
        try:
            return float(str(val).replace(',', ''))
        except (ValueError, AttributeError):
            return None

    def get_amounts_for_account(df_filtered, account_nm_str):
        row = df_filtered[df_filtered['account_nm'].str.contains(account_nm_str, na=False)]
        if not row.empty:
            return {
                'thstrm_amount': to_float(row['thstrm_amount'].iloc[0]),
                'frmtrm_amount': to_float(row['frmtrm_amount'].iloc[0]),
                'bfefrmtrm_amount': to_float(row['bfefrmtrm_amount'].iloc[0])
            }
        return {'thstrm_amount': None, 'frmtrm_amount': None, 'bfefrmtrm_amount': None}

    총자산_data = get_amounts_for_account(df_bs, '자산총계')
    총부채_data = get_amounts_for_account(df_bs, '부채총계')
    자기자본_data = get_amounts_for_account(df_bs, '자본총계')

    # Prepare data for grouped bar chart
    chart_data = {
        '항목': ['총 자산', '총 부채', '자기자본'],
        '당기': [총자산_data['thstrm_amount'], 총부채_data['thstrm_amount'], 자기자본_data['thstrm_amount']],
        '전기': [총자산_data['frmtrm_amount'], 총부채_data['frmtrm_amount'], 자기자본_data['frmtrm_amount']],
        '전전기': [총자산_data['bfefrmtrm_amount'], 총부채_data['bfefrmtrm_amount'], 자기자본_data['bfefrmtrm_amount']]
    }
    chart_df = pd.DataFrame(chart_data)

    # Filter out rows where all values are None
    chart_df = chart_df.dropna(how='all', subset=['당기', '전기', '전전기'])

    if chart_df.empty:
        st.warning("시각화할 재무상태표 데이터가 부족합니다.")
        return

    # 변환 없이 원본 chart_df 사용
    fig, ax = plt.subplots(figsize=(10, 6))
    bar_width = 0.25
    index = range(len(chart_df['항목']))

    bar1 = ax.bar([i - bar_width for i in index], chart_df['당기'], bar_width, label=f'{year}년 (당기)', color='lightskyblue')
    bar2 = ax.bar(index, chart_df['전기'], bar_width, label=f'{int(year)-1}년 (전기)', color='lightsalmon')
    bar3 = ax.bar([i + bar_width for i in index], chart_df['전전기'], bar_width, label=f'{int(year)-2}년 (전전기)', color='lightgray')

    ax.set_xlabel('주요 항목')
    ax.set_ylabel('금액 (단위: 억)')
    ax.set_title(f'{company} 3개년 주요 재무상태 항목')
    ax.set_xticks(index)
    ax.set_xticklabels(chart_df['항목'], rotation=0)
    ax.legend()
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))  # 억 단위 숫자
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

def render_financial_table(fs, company, year, sj_div='BS', display_mode='summary'):
    """특정 재무제표를 요약 또는 전체 표로 출력"""
    st.subheader(f"{company} {year}년 {get_sj_div_label(sj_div)} 재무제표")
    
    if display_mode == 'summary':
        if sj_div == 'IS':
            generate_income_statement_chart(fs, company, year) # Chart first
            st.dataframe(generate_income_statement_summary(fs))
        elif sj_div == 'BS':
            generate_balance_sheet_chart(fs, company, year) # Chart first
            st.dataframe(generate_balance_sheet_summary(fs))
        elif sj_div == 'CF': # Handle CF summary
            generate_cash_flow_chart(fs, company, year) # Chart first
            st.dataframe(generate_cash_flow_summary(fs))
        else:
            df = pretty_financial_table(fs, sj_div=sj_div)
            st.dataframe(df)
    else: # display_mode == 'full'
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
    # 구분 컬럼이 있으면 추가
    if 'fs_div' in df.columns:
        cols.append('fs_div')
    elif 'fs_nm' in df.columns:
        cols.append('fs_nm')
    elif 'account_id' in df.columns:
        cols.append('account_id')
    df = df[cols]
    rename_map = {
        'account_nm': '계정명',
        'thstrm_amount': '당기',
        'frmtrm_amount': '전기',
        'bfefrmtrm_amount': '전전기',
        'fs_div': '구분',
        'fs_nm': '구분',
        'account_id': '구분'
    }
    df = df.rename(columns=rename_map)

    # 계정명+구분 label 생성 (구분 컬럼이 있을 때만)
    if '구분' in df.columns:
        df['계정명'] = df['계정명'] + ' (' + df['구분'].astype(str) + ')'
        df = df.drop(columns=['구분'])

    # Re-adding the numeric formatting and index reset
    for col in ['당기', '전기', '전전기']:
        if col in df.columns:
            def safe_format_for_table(val):
                if pd.isna(val) or val is None:
                    return 'N/A'
                try:
                    # Attempt to convert to float, handling commas and ensuring it's a number
                    numeric_val = float(str(val).replace(",", ""))
                    return format_amount_to_kr_unit(numeric_val)
                except (ValueError, TypeError):
                    # If it's not a numeric string (e.g., already 'N/A' or a percentage string),
                    # return it as is. This handles the '비고' column values as well if they pass through here.
                    return val
            df[col] = df[col].apply(safe_format_for_table)
    df = df.reset_index(drop=True)

    # New logic for BS to separate Assets, Liabilities, Equity
    if sj_div == 'BS':
        final_rows = []
        
        # Find the indices of the key total accounts
        insert_points = {}
        for i, r in df.iterrows():
            if "자산총계" in r['계정명'] and '자산총계' not in insert_points:
                insert_points['자산총계'] = i
            if "부채총계" in r['계정명'] and '부채총계' not in insert_points:
                insert_points['부채총계'] = i
            if "자본총계" in r['계정명'] and '자본총계' not in insert_points:
                insert_points['자본총계'] = i
        
        current_idx = 0
        
        # Add '자산' section
        if '자산총계' in insert_points:
            final_rows.append({'계정명': '--- 자산 ---', '당기': '', '전기': '', '전전기': ''})
            final_rows.extend(df.iloc[current_idx : insert_points['자산총계'] + 1].to_dict('records'))
            current_idx = insert_points['자산총계'] + 1
        
        # Add '부채' section
        if '부채총계' in insert_points:
            final_rows.append({'계정명': '--- 부채 ---', '당기': '', '전기': '', '전전기': ''})
            final_rows.extend(df.iloc[current_idx : insert_points['부채총계'] + 1].to_dict('records'))
            current_idx = insert_points['부채총계'] + 1
        
        # Add '자본' section
        if '자본총계' in insert_points:
            final_rows.append({'계정명': '--- 자본 ---', '당기': '', '전기': '', '전전기': ''})
            final_rows.extend(df.iloc[current_idx : insert_points['자본총계'] + 1].to_dict('records'))
            current_idx = insert_points['자본총계'] + 1
            
        # Add any remaining rows (should be empty for a clean BS)
        if current_idx < len(df):
            final_rows.extend(df.iloc[current_idx:].to_dict('records'))
        
        df = pd.DataFrame(final_rows, columns=df.columns)

    return df

def financial_df_to_context_text(df, company=None, year=None, sj_div=None):
    lines = []
    if company and year and sj_div:
        lines.append(f"{company} {year}년 {get_sj_div_label(sj_div)} 요약")
    for _, row in df.iterrows():
        항목 = row.get('계정명', '')
        당기 = row.get('당기', '')
        전기 = row.get('전기', '')
        전전기 = row.get('전전기', '')
        비고 = row.get('비고', '')
        if 비고:
            lines.append(f"{항목}: {전전기}(3년전), {전기}(2년전), {당기}(작년) | {비고}")
        else:
            lines.append(f"{항목}: {전전기}(3년전), {전기}(2년전), {당기}(작년)")
    return "\n".join(lines)