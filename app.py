import streamlit as st
import pandas as pd
from io import BytesIO

from settlement import (
    MissingColumnsError,
    build_settlement,
    read_csv_with_fallback,
)

st.set_page_config(page_title="셔틀버스 정산 자동화", layout="wide")
st.title("🚌 신세계면세점 셔틀버스 정산 자동화 시스템")

st.subheader("💰 지원금액 설정")
support_amount = st.number_input("이번 달 1명당 지원금액을 입력하세요 (원):", value=41935, step=1)

st.subheader("📁 파일 업로드")
st.caption("필요한 컬럼: 운영사 / 태그ID / 탑승자 / 협력회사명 / 사업자등록번호 / 기업규모")
uploaded_file = st.file_uploader("탑승 기록 파일(CSV 또는 엑셀)을 여기에 끌어다 놓으세요.", type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = read_csv_with_fallback(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        try:
            unique_passengers, final_df = build_settlement(df, support_amount)
        except MissingColumnsError as e:
            st.error(
                "다음 필수 컬럼이 파일에 없습니다: "
                + ", ".join(e.missing)
                + "\n\n필요한 컬럼: 운영사 / 태그ID / 탑승자 / 협력회사명 / 사업자등록번호 / 기업규모"
            )
            st.stop()

        st.subheader("📊 정산 결과 미리보기")
        st.dataframe(final_df)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            unique_passengers.to_excel(writer, sheet_name='실제_탑승인원_명단', index=False)
            final_df.to_excel(writer, sheet_name='협력사별_지원금액_총계', index=False)
        processed_data = output.getvalue()

        st.download_button(
            label="📥 완성된 정산 엑셀 파일 다운로드", data=processed_data,
            file_name="셔틀버스_정산_완료.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        st.error(f"오류가 발생했습니다. (상세내용: {e})")
