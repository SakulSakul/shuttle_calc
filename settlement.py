"""셔틀버스 정산 계산 핵심 로직 (UI와 분리하여 단위 테스트 가능하도록 구성)."""
import pandas as pd

# pivot 시 index가 되는 컬럼 (운영사가 아님)
INDEX_COLS = ['협력회사명', '사업자등록번호', '기업규모']
# 중복 제거 정확도를 위해 정규화할 텍스트 키 컬럼
KEY_COLS = ['태그ID', '탑승자', '협력회사명', '운영사']
# 입력 파일에 반드시 존재해야 하는 컬럼
REQUIRED_COLS = ['운영사', '태그ID', '탑승자', '협력회사명', '사업자등록번호', '기업규모']

# pivot index 키가 비어있을 때 사용할 명시 라벨 (NaN 그룹 누락 방지용)
INDEX_FILL = {'협력회사명': '미상', '사업자등록번호': '미상', '기업규모': '미확인'}
# 빈 값으로 간주하는 토큰 (문자열화 후 소문자 비교)
_MISSING_TOKENS = {'', 'nan', 'none', 'nat', '<na>', 'null'}


def _normalize_index_key(series, label):
    """index 키 컬럼을 정규화한다.

    문자열로 보고 앞뒤 공백을 제거한 뒤, 빈 문자열·'nan'·NaN 등 결측 토큰을
    명시 라벨로 치환한다. pivot_table/groupby 가 NaN 그룹을 통째로 제외하는
    사일런트 드롭을 차단하기 위함이며, 값은 '라벨'로만 남고 계산엔 영향이 없다.
    """
    s = series.astype(str).str.strip()
    # pandas 3.0의 astype(str)는 결측을 'nan' 문자열로 바꾸지 않고 NA로 보존하므로,
    # 원본 NaN과 결과 NA를 명시적으로 함께 결측으로 잡아야 한다.
    is_missing = series.isna() | s.isna() | s.str.lower().isin(_MISSING_TOKENS).fillna(True)
    return s.mask(is_missing, label)


class MissingColumnsError(ValueError):
    """필수 컬럼이 누락되었을 때 발생."""

    def __init__(self, missing):
        self.missing = missing
        super().__init__("다음 필수 컬럼이 파일에 없습니다: " + ", ".join(missing))


def read_csv_with_fallback(file):
    """UTF-8로 먼저 시도하고, 실패하면 cp949(euc-kr)로 재시도한다."""
    try:
        return pd.read_csv(file)
    except UnicodeDecodeError:
        file.seek(0)  # 파일 포인터를 처음으로 되돌린 뒤 재시도
        return pd.read_csv(file, encoding='cp949')


def build_settlement(df, support_amount):
    """탑승 기록 DataFrame으로부터 (실제 탑승인원 명단, 협력사별 정산표)를 만든다.

    운영사 컬럼은 하드코딩하지 않고 pivot 결과에서 동적으로 탐지한다.
    """
    missing_cols = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing_cols:
        raise MissingColumnsError(missing_cols)

    df = df.copy()
    # 중복 제거 정확도를 위해 키 텍스트 컬럼의 앞뒤 공백을 정규화
    for c in KEY_COLS:
        df[c] = df[c].astype(str).str.strip()

    # pivot index 키(협력회사명/사업자등록번호/기업규모)는 NaN·공백이면 그룹에서
    # 통째로 누락되므로, 클러스터 전체를 명시 라벨로 정규화한다.
    # (협력회사명은 위 KEY_COLS 처리로 NaN→'nan'이 되었던 것도 여기서 함께 정리됨)
    for c in INDEX_COLS:
        df[c] = _normalize_index_key(df[c], INDEX_FILL[c])

    unique_passengers = df[REQUIRED_COLS].drop_duplicates().reset_index(drop=True)

    pivot_df = unique_passengers.pivot_table(
        index=INDEX_COLS, columns='운영사', values='태그ID',
        aggfunc='count', fill_value=0
    ).reset_index()
    pivot_df.columns.name = None

    # 운영사 컬럼을 동적으로 탐지: index 컬럼을 제외한 나머지가 모두 운영사
    operator_cols = [c for c in pivot_df.columns if c not in INDEX_COLS]

    # 총 인원: 모든 운영사 컬럼을 합산 (특정 운영사명을 코드에 박지 않음)
    pivot_df['총 인원'] = pivot_df[operator_cols].sum(axis=1)

    # 운영사별 지원금액 컬럼을 운영사 목록을 순회하며 동적으로 생성
    for op in operator_cols:
        pivot_df[f'{op} 지원금액'] = pivot_df[op] * support_amount

    pivot_df['총 지원금액'] = pivot_df['총 인원'] * support_amount

    # 최종 컬럼 순서: index → (운영사, 운영사 지원금액) 반복 → 총계
    final_cols = list(INDEX_COLS)
    for op in operator_cols:
        final_cols.append(op)
        final_cols.append(f'{op} 지원금액')
    final_cols += ['총 인원', '총 지원금액']
    final_df = pivot_df[final_cols]

    # 총계 행: 숫자 컬럼은 모두 합산, index 컬럼은 라벨 처리
    total_row = {'협력회사명': '총계', '사업자등록번호': '-', '기업규모': '-'}
    for c in final_cols:
        if c not in INDEX_COLS:
            total_row[c] = final_df[c].sum()
    final_df = pd.concat([final_df, pd.DataFrame([total_row])], ignore_index=True)

    return unique_passengers, final_df
