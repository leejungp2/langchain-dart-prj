from dart_api import DartAPI

def test_dart_api(company, year="2023", item="매출액"):
    print(f"입력값: company={company}, year={year}, item={item}")

    # 1. 기업 코드 찾기
    corp_code = DartAPI().find_corp_code(company)
    print(f"find_corp_code('{company}') 결과: {corp_code}")

    if not corp_code:
        print("기업 코드를 찾지 못했습니다.")
        return

    # 2. 재무제표 데이터 가져오기
    fs = DartAPI().get_financial_statements(corp_code, bsns_year=year, fs_div="IS")
    if not fs or not fs.get('list'):
        print("재무제표 데이터가 없습니다.")
        return

    # 3. 항목명 리스트 출력
    import pandas as pd
    df = pd.DataFrame(fs['list'])
    print("재무제표 항목명 리스트:")
    print(df['account_nm'].unique())

    # 4. 원하는 항목 row 찾기
    row = df[df['account_nm'].str.contains(item, na=False)]
    if not row.empty:
        print(f"'{item}' 항목 데이터:")
        print(row)
    else:
        print(f"'{item}' 항목을 찾지 못했습니다.")

# 테스트 실행
test_dart_api("LG전자", "2023", "매출액")