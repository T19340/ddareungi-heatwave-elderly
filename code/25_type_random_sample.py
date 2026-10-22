# -*- coding: utf-8 -*-
"""유형 규칙 검증용 무작위 표본 100곳을 다시 뽑아 results/type_random_check.csv 와 같은지 확인한다.

틀: 대여소 정보(2026-06 기준) 전체에서 규칙을 정할 때 본 45곳(results/type_manual_check.csv)을 뺀 곳.
추출: pandas DataFrame.sample(n=100, random_state=2026). 대여소 정보 파일의 행 순서를 그대로 쓴다.
실행: python -P -E -X utf8 code/25_type_random_sample.py
"""
from pathlib import Path
import glob
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
src = glob.glob(str(ROOT / "data_raw" / "따릉이" / "공공자전거 대여소 정보*.xlsx"))[0]
st = pd.read_excel(src, header=None, skiprows=5).iloc[:, [0, 1]]
st.columns = ["stn", "name"]
st["stn"] = pd.to_numeric(st["stn"], errors="coerce")
st = st.dropna(subset=["stn"])
st["stn"] = st["stn"].astype(int)
manual = set(pd.read_csv(ROOT / "results" / "type_manual_check.csv")["stn"])
frame = st[~st["stn"].isin(manual)].reset_index(drop=True)
sample = frame.sample(n=100, random_state=2026)
published = set(pd.read_csv(ROOT / "results" / "type_random_check.csv")["stn"])
same = set(sample["stn"]) == published
print(f"틀 {len(frame)}곳, 표본 {len(sample)}곳, 공개 표본과 일치: {same}")
raise SystemExit(0 if same else 1)
