"""신세계면세점 셔틀버스 정산 — tkinter 네이티브 데스크톱 앱.

streamlit/pywebview 없이 동작하며, 계산/서식 로직은 기존 모듈을 그대로 재사용한다.
미리보기 탭 2개(명단/정산)가 곧 저장될 2개 시트와 동일하다 — "보이는 것 = 저장되는 것".
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pandas as pd

from settlement import build_settlement, read_csv_with_fallback, MissingColumnsError
from excel_format import build_styled_xlsx

REQUIRED_HINT = "필요한 컬럼: 운영사 / 태그ID / 탑승자 / 협력회사명 / 사업자등록번호 / 기업규모"


def _resource_path(name):
    """개발 환경과 PyInstaller(frozen) 환경 양쪽에서 리소스 경로를 찾는다."""
    candidates = []
    if hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, name))
    candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), name))
    candidates.append(name)
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


class ShuttleApp:
    def __init__(self, root):
        self.root = root
        self.file_path = None
        # 정산 결과 보관 (저장 시 재사용)
        self.unique_passengers = None
        self.final_df = None
        self.support_amount = None

        root.title("신세계면세점 셔틀버스 정산 자동화")
        root.geometry("980x640")
        root.minsize(760, 520)

        ico = _resource_path("icon.ico")
        if ico:
            try:
                root.iconbitmap(ico)
            except Exception:
                pass  # 아이콘 실패는 무시

        self._build_widgets()

    # ── UI 구성 ──────────────────────────────────────────────
    def _build_widgets(self):
        pad = {"padx": 8, "pady": 4}

        top = ttk.Frame(self.root)
        top.pack(fill="x", **pad)

        # 1인당 지원금액
        ttk.Label(top, text="1인당 지원금액(원)").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.amount_var = tk.StringVar(value="41935")
        ttk.Entry(top, textvariable=self.amount_var, width=14).grid(row=0, column=1, sticky="w", padx=4, pady=4)

        # 파일 선택
        ttk.Label(top, text="탑승 기록 파일").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.path_var = tk.StringVar(value="")
        ttk.Entry(top, textvariable=self.path_var, width=70, state="readonly").grid(
            row=1, column=1, sticky="we", padx=4, pady=4)
        ttk.Button(top, text="파일 선택", command=self.on_pick_file).grid(row=1, column=2, padx=4, pady=4)
        top.columnconfigure(1, weight=1)

        # 실행 / 저장 버튼
        btns = ttk.Frame(self.root)
        btns.pack(fill="x", **pad)
        ttk.Button(btns, text="정산 실행", command=self.on_calculate).pack(side="left", padx=4)
        self.save_btn = ttk.Button(btns, text="저장", command=self.on_save, state="disabled")
        self.save_btn.pack(side="left", padx=4)

        # 미리보기 노트북 (저장될 2개 시트와 동일)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=4)

        self.tree1, tab1 = self._make_tree_tab("실제 탑승인원 명단")
        self.tree2, tab2 = self._make_tree_tab("협력사별 지원금액 총계")
        self.notebook.add(tab1, text="실제 탑승인원 명단")
        self.notebook.add(tab2, text="협력사별 지원금액 총계")

        # 하단 상태 표시
        self.status_var = tk.StringVar(value="파일을 선택하고 [정산 실행]을 눌러주세요.")
        ttk.Label(self.root, textvariable=self.status_var, justify="left", anchor="w").pack(
            fill="x", padx=12, pady=8)

    def _make_tree_tab(self, _title):
        frame = ttk.Frame(self.notebook)
        tree = ttk.Treeview(frame, show="headings")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="we")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        return tree, frame

    @staticmethod
    def _fill_tree(tree, df):
        """Treeview 의 컬럼·행을 모두 비우고 DataFrame 으로 다시 채운다."""
        tree.delete(*tree.get_children())
        cols = [str(c) for c in df.columns]
        tree["columns"] = cols
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=max(80, min(220, len(c) * 14 + 40)), anchor="center")
        for _, row in df.iterrows():
            tree.insert("", "end", values=[row[c] for c in df.columns])

    # ── 이벤트 핸들러 ────────────────────────────────────────
    def on_pick_file(self):
        path = filedialog.askopenfilename(
            title="탑승 기록 파일 선택",
            filetypes=[("CSV/Excel", "*.csv *.xlsx")],
        )
        if path:
            self.file_path = path
            self.path_var.set(path)

    def on_calculate(self):
        try:
            # 1) 입력 검증
            raw = self.amount_var.get().strip().replace(",", "")
            try:
                amount = int(raw)
            except ValueError:
                messagebox.showwarning("입력 확인", "1인당 지원금액에 정수를 입력하세요.")
                return
            if amount <= 0:
                messagebox.showwarning("입력 확인", "1인당 지원금액은 0보다 커야 합니다.")
                return
            if not self.file_path:
                messagebox.showwarning("입력 확인", "탑승 기록 파일을 먼저 선택하세요.")
                return

            # 2) 파일 읽기 (csv 는 seek 가능한 바이너리 핸들 필요)
            if self.file_path.lower().endswith(".csv"):
                with open(self.file_path, "rb") as f:
                    df = read_csv_with_fallback(f)
            else:
                df = pd.read_excel(self.file_path)

            # 3) 정산 계산
            try:
                unique_passengers, final_df = build_settlement(df, amount)
            except MissingColumnsError as e:
                messagebox.showerror(
                    "필수 컬럼 누락",
                    "다음 필수 컬럼이 파일에 없습니다: " + ", ".join(e.missing)
                    + "\n\n" + REQUIRED_HINT,
                )
                return

            # 4) 미리보기 두 탭 채우기 (보이는 것 = 저장되는 것)
            self._fill_tree(self.tree1, unique_passengers)
            self._fill_tree(self.tree2, final_df)

            # 5) 요약 + 결과 보관 + 저장 버튼 활성화
            total_people = int(final_df.loc[final_df["협력회사명"] == "총계", "총 인원"].iloc[0])
            total_amount = int(final_df.loc[final_df["협력회사명"] == "총계", "총 지원금액"].iloc[0])
            self.status_var.set(
                f"정산 완료 — 총 인원: {total_people:,}명 / 총 지원금액: ₩{total_amount:,}\n"
                f"[저장] 버튼으로 엑셀(2시트)을 저장할 수 있습니다."
            )
            self.unique_passengers = unique_passengers
            self.final_df = final_df
            self.support_amount = amount
            self.save_btn.config(state="normal")
        except Exception as e:
            messagebox.showerror("오류", f"정산 중 오류가 발생했습니다.\n\n{e}")

    def on_save(self):
        try:
            if self.final_df is None:
                messagebox.showwarning("저장 불가", "먼저 [정산 실행]을 해주세요.")
                return
            data = build_styled_xlsx(self.unique_passengers, self.final_df, self.support_amount)
            path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                initialfile="셔틀버스_정산_완료.xlsx",
                filetypes=[("Excel 파일", "*.xlsx")],
                title="정산 엑셀 저장",
            )
            if not path:
                self.status_var.set("저장이 취소되었습니다.")
                return
            with open(path, "wb") as f:
                f.write(data)
            self.status_var.set(f"저장 완료: {path}")
            messagebox.showinfo("저장 완료", f"엑셀 파일을 저장했습니다.\n\n{path}")
            try:
                os.startfile(os.path.dirname(path))  # 저장 폴더 열기 (Windows 전용)
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("오류", f"저장 중 오류가 발생했습니다.\n\n{e}")


def main():
    root = tk.Tk()
    ShuttleApp(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # 시작 단계 치명적 예외: 메시지 + error_log.txt 기록
        try:
            messagebox.showerror("실행 오류", f"앱을 시작할 수 없습니다.\n\n{e}")
        except Exception:
            pass
        try:
            base = os.path.dirname(os.path.abspath(sys.argv[0])) or os.path.expanduser("~")
            log_path = os.path.join(base, "error_log.txt")
        except Exception:
            log_path = os.path.join(os.path.expanduser("~"), "error_log.txt")
        try:
            import traceback
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(traceback.format_exc())
        except Exception:
            pass
        raise
