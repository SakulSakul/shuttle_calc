import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="셔틀버스 정산 자동화", layout="wide")
st.title("🚌 신세계면세점 셔틀버스 정산 자동화 시스템")

st.subheader("💰 지원금액 설정")
support_amount = st.number_input("이번 달 1명당 지원금액을 입력하세요 (원):", value=41935, step=1)

st.subheader("📁 파일 업로드")
uploaded_file = st.file_uploader("탑승 기록 파일(CSV 또는 엑셀)을 여기에 끌어다 놓으세요.", type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        cols = ['운영사', '태그ID', '탑승자', '협력회사명', '사업자등록번호', '기업규모']
        unique_passengers = df[cols].drop_duplicates().reset_index(drop=True)
        
        pivot_df = unique_passengers.pivot_table(index=['협력회사명', '사업자등록번호', '기업규모'], columns='운영사', values='태그ID', aggfunc='count', fill_value=0).reset_index()
        pivot_df.columns.name = None
        
        if '스위스관광' not in pivot_df.columns: pivot_df['스위스관광'] = 0
        if '신백승여행사' not in pivot_df.columns: pivot_df['신백승여행사'] = 0
        
        pivot_df['총 인원'] = pivot_df['스위스관광'] + pivot_df['신백승여행사']
        pivot_df['스위스관광 지원금액'] = pivot_df['스위스관광'] * support_amount
        pivot_df['신백승여행사 지원금액'] = pivot_df['신백승여행사'] * support_amount
        pivot_df['총 지원금액'] = pivot_df['총 인원'] * support_amount
        
        final_cols = ['협력회사명', '사업자등록번호', '기업규모', '스위스관광', '스위스관광 지원금액', '신백승여행사', '신백승여행사 지원금액', '총 인원', '총 지원금액']
        final_df = pivot_df[final_cols]
        
        total_row = pd.DataFrame([{'협력회사명': '총계', '사업자등록번호': '-', '기업규모': '-', '스위스관광': final_df['스위스관광'].sum(), '스위스관광 지원금액': final_df['스위스관광 지원금액'].sum(), '신백승여행사': final_df['신백승여행사'].sum(), '신백승여행사 지원금액': final_df['신백승여행사 지원금액'].sum(), '총 인원': final_df['총 인원'].sum(), '총 지원금액': final_df['총 지원금액'].sum()}])
        final_df = pd.concat([final_df, total_row], ignore_index=True)
        
        st.subheader("📊 정산 결과 미리보기")
        st.dataframe(final_df)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            unique_passengers.to_excel(writer, sheet_name='실제_탑승인원_명단', index=False)
            final_df.to_excel(writer, sheet_name='협력사별_지원금액_총계', index=False)
        processed_data = output.getvalue()
        
        st.download_button(label="📥 완성된 정산 엑셀 파일 다운로드", data=processed_data, file_name="셔틀버스_정산_완료.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.error(f"오류가 발생했습니다. (상세내용: {e})")