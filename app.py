import sys
import os
import datetime

import streamlit as st
import pandas as pd

from settlement import (
    MissingColumnsError,
    build_settlement,
    read_csv_with_fallback,
)
from excel_format import build_styled_xlsx

# PyInstaller exe(데스크톱) 여부: frozen 또는 _MEIPASS 존재로 판별
IS_DESKTOP = getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS")


def save_excel(data, default_name):
    """데스크톱에서 정산 엑셀을 저장한다.

    1) tkinter 네이티브 '다른 이름으로 저장' 대화상자를 우선 시도.
       - 저장 시 (path, "dialog"), 취소 시 (None, "cancelled") 반환.
    2) 대화상자 자체가 실패하면 홈\\Downloads 로 폴백 저장 후 (path, "fallback").
    """
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[("Excel 파일", "*.xlsx")],
            title="정산 엑셀 저장",
        )
        root.destroy()

        if not path:
            return None, "cancelled"
        with open(path, "wb") as f:
            f.write(data)
        return path, "dialog"
    except Exception:
        # 대화상자 실패 시 Downloads 폴더로 폴백
        save_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(save_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(save_dir, f"셔틀버스_정산_완료_{ts}.xlsx")
        with open(path, "wb") as f:
            f.write(data)
        return path, "fallback"


st.set_page_config(page_title="셔틀버스 정산 자동화", layout="wide")
st.title("🚌 신세계면세점 셔틀버스 정산 자동화 시스템")
st.caption(f"실행 모드: {'데스크톱' if IS_DESKTOP else '웹'}")

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

        processed_data = build_styled_xlsx(unique_passengers, final_df, support_amount)

        if IS_DESKTOP:
            # PyInstaller exe(데스크톱 웹뷰): 브라우저 다운로드가 동작하지 않으므로
            # 네이티브 '다른 이름으로 저장' 대화상자로 디스크에 저장한다.
            if st.button("💾 다른 이름으로 저장"):
                path, how = save_excel(processed_data, "셔틀버스_정산_완료.xlsx")
                if how == "cancelled":
                    st.info("저장이 취소되었습니다.")
                else:
                    st.success(f"저장 완료\n\n{path}")
                    if how == "fallback":
                        st.caption("저장 대화상자를 열 수 없어 Downloads 폴더에 저장했습니다.")
                    try:
                        os.startfile(os.path.dirname(path))  # 저장 폴더 열기 (Windows 전용)
                    except Exception:
                        pass
        else:
            # streamlit run / Streamlit Cloud: 기존 브라우저 다운로드 유지
            st.download_button(
                label="📥 완성된 정산 엑셀 파일 다운로드", data=processed_data,
                file_name="셔틀버스_정산_완료.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception as e:
        st.error(f"오류가 발생했습니다. (상세내용: {e})")
