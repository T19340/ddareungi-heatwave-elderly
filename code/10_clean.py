# -*- coding: utf-8 -*-
"""
10_clean.py — 원자료 정리와 집계 3종 (data_proc/)

입력: data_raw/따릉이/서울특별시 공공자전거 이용정보(시간대별)_YYYYMM.csv (cp949, 월 9개), 공공자전거 대여소 정보(26.6월 기준).xlsx,
      data_raw/기상/asos_seoul108_daily_2024_2026.csv, data_raw/기상/heatwave_chart_stn108_*.html
출력:
  data_proc/daily_hour_age_pass.csv  일 × 시간 × 연령대 × 이용권 (rent 이용건수, dist 이동거리 m, mins 이용시간 분; 2025-06은 mins 없음)
  data_proc/daily_station.csv        일 × 대여소번호 (rent)
  data_proc/daily_total_weather.csv  일 총량 + ASOS 일자료 + 달력 변수(요일·주말·공휴일·월·연도) + 기온·강수 구간
  data_proc/stations.csv             대여소 마스터(번호·이름·자치구·주소·위경도·설치시기·거치대수)
  data_proc/heatwave_seoul.csv       서울(108) 연도별 폭염일수 1973~2026
  data_proc/clean_summary.json       행수·합계·범주 목록·예비 집계와의 대조 결과
규칙: 대여구분코드는 괄호 안을 뗀 뒤 정기권/일일권/가족권. 연령대코드는 원문 그대로(~10대…70대이상·기타).
      대여소번호는 앞의 0을 뗀 정수. 열 이름은 월마다 조금 달라(이동거리(M)/이동거리, 이용시간(분) 유무) 정규화한다.
      예비 집계(data_proc/prelim/*.csv, 메인 작업자)가 있으면 같은 키로 합계를 대조해 clean_summary.json 에 적는다.

실행: python -P -E -X utf8 code/10_clean.py   (월 파일 9개 약 3.4 GB, 5~10분)
"""
import glob
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data_raw", ROOT / "data_proc"
PROC.mkdir(exist_ok=True)
PRELIM = PROC / "prelim"
MONTHS = ["202406", "202407", "202408", "202409", "202506", "202507", "202508", "202509", "202606"]

# 공휴일(관공서의 공휴일에 관한 규정 제2조; 선거일 포함). 분석 기간 2024-06~09, 2025-06~09, 2026-06.
HOLIDAYS = {
    "2024-06-06": "현충일", "2024-08-15": "광복절", "2024-09-16": "추석 연휴", "2024-09-17": "추석", "2024-09-18": "추석 연휴",
    "2025-06-03": "제21대 대통령선거일(임시공휴일)", "2025-06-06": "현충일", "2025-08-15": "광복절",
    "2026-06-03": "제9회 전국동시지방선거일", "2026-06-06": "현충일",
}
HOUR_BANDS = [(0, 4, "00-04"), (5, 9, "05-09"), (10, 15, "10-15"), (16, 19, "16-19"), (20, 23, "20-23")]


def hour_band(h: int) -> str:
    for lo, hi, name in HOUR_BANDS:
        if lo <= h <= hi:
            return name
    raise ValueError(h)


def norm_pass(s: str) -> str:
    return re.sub(r"\(.*?\)", "", str(s)).strip()


def read_month(m: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    f = RAW / "따릉이" / f"서울특별시 공공자전거 이용정보(시간대별)_{m}.csv"
    head = pd.read_csv(f, encoding="cp949", nrows=0).columns.tolist()
    rename = {}
    for c in head:
        if c.startswith("이동거리"):
            rename[c] = "dist"
        elif c.startswith("이용시간"):
            rename[c] = "mins"
    use = ["대여일자", "대여시간", "대여소번호", "대여구분코드", "연령대코드", "이용건수"] + list(rename)
    t0 = time.time()
    df = pd.read_csv(f, encoding="cp949", usecols=use, dtype={"대여일자": str, "대여소번호": str, "대여구분코드": str, "연령대코드": str})
    df = df.rename(columns=rename)
    if "mins" not in df.columns:
        df["mins"] = np.nan
    df["date"] = df["대여일자"].str.slice(0, 10)
    df["hour"] = df["대여시간"].astype(int)
    df["stn"] = df["대여소번호"].str.lstrip("0").replace("", "0").astype(int)
    df["pass"] = df["대여구분코드"].map(norm_pass)
    df["age"] = df["연령대코드"].str.strip()
    df["rent"] = df["이용건수"].astype(int)
    info = {"month": m, "rows": int(len(df)), "rent_sum": int(df["rent"].sum()), "cols": head,
            "pass_codes": {k: int(v) for k, v in df["대여구분코드"].value_counts().items()},
            "age_codes": {k: int(v) for k, v in df["age"].value_counts().items()},
            "dates": [df["date"].min(), df["date"].max()], "n_dates": int(df["date"].nunique()),
            "n_stations": int(df["stn"].nunique()), "read_sec": round(time.time() - t0, 1)}
    a = df.groupby(["date", "hour", "age", "pass"], as_index=False).agg(rent=("rent", "sum"), dist=("dist", "sum"), mins=("mins", "sum"))
    if df["mins"].isna().all():
        a["mins"] = np.nan
    b = df.groupby(["date", "stn"], as_index=False).agg(rent=("rent", "sum"))
    return a, b, info


def main() -> int:
    infos, A, B = [], [], []
    for m in MONTHS:
        a, b, info = read_month(m)
        print(f"  {m}: {info['rows']:,}행, 이용건수 {info['rent_sum']:,}, 날짜 {info['n_dates']}일, 대여소 {info['n_stations']}곳, {info['read_sec']}초", flush=True)
        infos.append(info)
        A.append(a)
        B.append(b)
    hap = pd.concat(A, ignore_index=True).sort_values(["date", "hour", "age", "pass"]).reset_index(drop=True)
    stn = pd.concat(B, ignore_index=True).sort_values(["date", "stn"]).reset_index(drop=True)
    hap["dist"] = hap["dist"].round(2)
    hap.to_csv(PROC / "daily_hour_age_pass.csv", index=False, encoding="utf-8-sig")
    stn.to_csv(PROC / "daily_station.csv", index=False, encoding="utf-8-sig")

    # ---- 일 총량 + 기상 + 달력
    daily = hap.groupby("date", as_index=False)["rent"].sum()
    w = pd.read_csv(RAW / "기상" / "asos_seoul108_daily_2024_2026.csv", encoding="utf-8-sig")
    w["sumRn"] = pd.to_numeric(w["sumRn"], errors="coerce").fillna(0.0)
    for c in ["avgTa", "minTa", "maxTa", "avgRhm", "sumSsHr", "avgWs"]:
        w[c] = pd.to_numeric(w[c], errors="coerce")
    w = w.rename(columns={"tm": "date"})[["date", "avgTa", "minTa", "maxTa", "sumRn", "avgRhm", "sumSsHr", "avgWs"]]
    d = daily.merge(w, on="date", how="left")
    assert d["maxTa"].notna().all(), "기상 결측일: " + ",".join(d.loc[d["maxTa"].isna(), "date"])
    dt = pd.to_datetime(d["date"])
    d["dow"] = dt.dt.dayofweek
    d["wkend"] = (d["dow"] >= 5).astype(int)
    d["hol"] = d["date"].isin(HOLIDAYS).astype(int)
    d["hol_name"] = d["date"].map(HOLIDAYS).fillna("")
    d["month"] = dt.dt.month
    d["year"] = dt.dt.year
    d["tbin"] = pd.cut(d["maxTa"], [-np.inf, 27, 30, 33, 35, np.inf], right=False, labels=["<27", "27-30", "30-33", "33-35", ">=35"]).astype(str)
    d["rainbin"] = pd.cut(d["sumRn"], [-np.inf, 0, 5, 20, np.inf], right=True, labels=["0", "0-5", "5-20", ">20"]).astype(str)
    d.to_csv(PROC / "daily_total_weather.csv", index=False, encoding="utf-8-sig")

    # ---- 대여소 마스터 (머리글 5행 건너뜀)
    wb = openpyxl.load_workbook(RAW / "따릉이" / "공공자전거 대여소 정보(26.6월 기준).xlsx", read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = [r for r in ws.iter_rows(min_row=6, values_only=True) if r[0] is not None]
    st = pd.DataFrame([{"stn": int(r[0]), "name": str(r[1]).strip(), "gu": str(r[2]).strip() if r[2] else "",
                        "addr": str(r[3]).strip() if r[3] else "", "lat": r[4], "lon": r[5],
                        "installed": str(r[6])[:10] if r[6] else "", "racks_lcd": r[7], "racks_qr": r[8], "op": r[9]} for r in rows])
    st.to_csv(PROC / "stations.csv", index=False, encoding="utf-8-sig")

    # ---- 서울 폭염일수 표 파싱 (기상자료개방포털 화면 HTML)
    hw_files = sorted(glob.glob(str(RAW / "기상" / "heatwave_chart_stn108_*.html")))
    hw_note = ""
    if hw_files:
        html = open(hw_files[-1], encoding="utf-8").read()
        hw = None
        for t in re.findall(r"<table[^>]*>(.*?)</table>", html, re.S):
            rows_t = []
            for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S):
                cells = [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S)]
                if cells:
                    rows_t.append(cells)
            if rows_t and rows_t[0][:2] == ["연도", "1월"]:
                hw = pd.DataFrame(rows_t[1:], columns=rows_t[0])
        assert hw is not None, "폭염일수 표를 찾지 못함"
        hw = hw[hw["연도"].str.fullmatch(r"\d{4}")].copy()
        for c in hw.columns[1:]:
            hw[c] = pd.to_numeric(hw[c], errors="coerce")
        hw["연도"] = hw["연도"].astype(int)
        hw = hw.drop(columns=[c for c in hw.columns if c == "순위"])  # 순위 열은 쓰지 않는다(순위 표현 금지)
        hw["stn"] = "서울(108)"
        hw["note"] = np.where(hw["연도"] == date.today().year, f"연중 미완({date.today():%Y-%m-%d} 조회)", "")
        hw.to_csv(PROC / "heatwave_seoul.csv", index=False, encoding="utf-8-sig")
        hw_note = f"{int(hw['연도'].min())}~{int(hw['연도'].max())}, {len(hw)}개년"
    else:
        hw_note = "미확보(01_weather.py 실행 필요)"

    # ---- 예비 집계와 대조
    cmp = {}
    if PRELIM.exists():
        p1 = pd.read_csv(PRELIM / "daily_hour_age_pass.csv")
        m1 = hap.merge(p1, on=["date", "hour", "age", "pass"], how="outer", suffixes=("", "_p"), indicator=True)
        cmp["daily_hour_age_pass"] = {"rows_new": int(len(hap)), "rows_prelim": int(len(p1)),
                                      "rows_only_new": int((m1["_merge"] == "left_only").sum()), "rows_only_prelim": int((m1["_merge"] == "right_only").sum()),
                                      "rent_mismatch_rows": int(((m1["_merge"] == "both") & (m1["rent"] != m1["rent_p"])).sum()),
                                      "rent_sum_new": int(hap["rent"].sum()), "rent_sum_prelim": int(p1["rent"].sum())}
        p2 = pd.read_csv(PRELIM / "daily_station.csv")
        m2 = stn.merge(p2, on=["date", "stn"], how="outer", suffixes=("", "_p"), indicator=True)
        cmp["daily_station"] = {"rows_new": int(len(stn)), "rows_prelim": int(len(p2)),
                                "rows_only_new": int((m2["_merge"] == "left_only").sum()), "rows_only_prelim": int((m2["_merge"] == "right_only").sum()),
                                "rent_mismatch_rows": int(((m2["_merge"] == "both") & (m2["rent"] != m2["rent_p"])).sum())}
        p3 = pd.read_csv(PRELIM / "daily_total_weather.csv")
        m3 = d.merge(p3[["date", "rent", "maxTa", "sumRn", "hol", "tbin"]], on="date", how="outer", suffixes=("", "_p"), indicator=True)
        cmp["daily_total_weather"] = {"days_new": int(len(d)), "days_prelim": int(len(p3)),
                                      "rent_mismatch_days": int(((m3["_merge"] == "both") & (m3["rent"] != m3["rent_p"])).sum()),
                                      "maxTa_mismatch_days": int(((m3["_merge"] == "both") & (m3["maxTa"] != m3["maxTa_p"])).sum()),
                                      "hol_diff_days": [str(x) for x in m3.loc[(m3["_merge"] == "both") & (m3["hol"] != m3["hol_p"]), "date"]],
                                      "tbin_mismatch_days": int(((m3["_merge"] == "both") & (m3["tbin"] != m3["tbin_p"])).sum())}
    summary = {"months": infos, "rows_hour_age_pass": int(len(hap)), "rows_station": int(len(stn)), "days": int(len(d)),
               "rent_total": int(d["rent"].sum()), "stations_in_rentals": int(stn["stn"].nunique()), "stations_master": int(len(st)),
               "stations_with_coord": int(st["lat"].notna().sum()),
               "stations_in_rentals_without_master": int((~stn["stn"].isin(st["stn"])).sum() and stn.loc[~stn["stn"].isin(st["stn"]), "stn"].nunique()),
               "pass_values": sorted(hap["pass"].unique().tolist()), "age_values": sorted(hap["age"].unique().tolist()),
               "holidays_used": HOLIDAYS, "days_by_year": {int(k): int(v) for k, v in d.groupby("year").size().items()},
               "days_by_year_tbin": {f"{int(y)}|{t}": int(c) for (y, t), c in d.groupby(["year", "tbin"]).size().items()},
               "days_by_year_rainbin": {f"{int(y)}|{t}": int(c) for (y, t), c in d.groupby(["year", "rainbin"]).size().items()},
               "heatwave_seoul": hw_note, "prelim_compare": cmp}
    (PROC / "clean_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "months"}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
