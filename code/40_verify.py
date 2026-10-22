# -*- coding: utf-8 -*-
"""
40_verify.py — 보고서 핵심 수치의 독립 재계산 (results/verification.md)

10_clean(pandas)·20_model(statsmodels)·21_station·23_exposure_gap·24_elderly(pandas) 과 다른 코드 경로로 다시 센다:
  - 원자료 월 CSV 3개(2024-08, 2025-07, 2025-08)를 csv 모듈로 한 줄씩 읽어 dict 로 집계(일 총량, 대여소별, 연령군·시간대별 건수·분)
  - ASOS 일자료 CSV 를 csv 모듈로 읽어 기온·강수 구간을 다시 매기고 numpy.linalg.lstsq 로 식 (1)을 다시 적합(계수 비교)
  - 폭염일수 표는 html.parser 로 파싱, 대여소 정보는 openpyxl 로 센다
비교 대상: results/summary_stats.json, station_summary.json, exposure_gap_summary.json, elderly_summary.json, heat35_days_by_year.json,
          표 B·C·D 의 results/station_elderly_2025_typed.csv·station_elderly_facility_2025.csv·gu_exposure_2025.csv, type_summary_2025.csv, data_proc/clean_summary.json
허용 오차: 계수(%)는 0.05%p(최소제곱 해는 같아야 함), 그 밖은 반올림 자리까지.
실행: python -P -E -X utf8 code/40_verify.py  (약 2~3분)
"""
import csv
import glob
import json
import math
import statistics
import sys
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path

import numpy as np
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, RES = ROOT / "data_raw", ROOT / "data_proc", ROOT / "results"
S = json.loads((RES / "summary_stats.json").read_text(encoding="utf-8"))
SS = json.loads((RES / "station_summary.json").read_text(encoding="utf-8"))
E = json.loads((RES / "exposure_gap_summary.json").read_text(encoding="utf-8"))
EL = json.loads((RES / "elderly_summary.json").read_text(encoding="utf-8"))
CS = json.loads((PROC / "clean_summary.json").read_text(encoding="utf-8"))
HOL = set(CS["holidays_used"])
AGEGRP = {"~10대": "10대", "20대": "20-50대", "30대": "20-50대", "40대": "20-50대", "50대": "20-50대", "60대": "60+", "70대이상": "60+"}
rows = []


def add(item, reported, source, method, recomputed, tol=0.0, kind="원자료"):
    """kind: '원자료' = data_raw 파일을 직접 읽어 재계산, '집계 파일' = data_proc/results 산출물을 입력으로 다른 코드로 재계산"""
    try:
        ok = abs(float(reported) - float(recomputed)) <= tol + 1e-9
    except (TypeError, ValueError):
        ok = str(reported) == str(recomputed)
    rows.append((item, reported, source, method, recomputed, "일치" if ok else "**불일치**", kind))
    return ok


# ------------------------------------------------------------------ 1. ASOS 일자료 (csv 모듈)
W = {}
with open(RAW / "기상" / "asos_seoul108_daily_2024_2026.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        W[r["tm"]] = {"maxTa": float(r["maxTa"]), "sumRn": float(r["sumRn"]) if r["sumRn"] else 0.0,
                      "avgRhm": float(r["avgRhm"]) if r["avgRhm"] else None, "sumSsHr": float(r["sumSsHr"]) if r["sumSsHr"] else None}


def tbin(t):
    return "<27" if t < 27 else "27-30" if t < 30 else "30-33" if t < 33 else "33-35" if t < 35 else ">=35"


def rbin(r):
    return "0" if r <= 0 else "0-5" if r <= 5 else "5-20" if r <= 20 else ">20"


def in_sample(d):
    y, m = int(d[:4]), int(d[5:7])
    return (y in (2024, 2025) and 6 <= m <= 9) or (y == 2026 and m == 6)


ge35 = {y: sum(1 for d, w in W.items() if in_sample(d) and d.startswith(str(y)) and w["maxTa"] >= 35) for y in (2024, 2025, 2026)}
b33 = {y: sum(1 for d, w in W.items() if in_sample(d) and d.startswith(str(y)) and 33 <= w["maxTa"] < 35) for y in (2024, 2025)}
ge33 = {y: sum(1 for d, w in W.items() if d.startswith(str(y)) and w["maxTa"] >= 33) for y in (2024, 2025, 2026)}
add("35℃ 이상인 날 2024년(6~9월)", S["ge35_days"]["2024"], "ASOS CSV maxTa", "csv 모듈, maxTa>=35 세기", ge35[2024])
add("35℃ 이상인 날 2025년(6~9월)", S["ge35_days"]["2025"], "ASOS CSV maxTa", "같음", ge35[2025])
add("35℃ 이상인 날 2026년 6월", S["ge35_days"]["2026-06"], "ASOS CSV maxTa", "같음", ge35[2026])
add("33~35℃인 날 2024년", S["b33_35_days"]["2024"], "ASOS CSV maxTa", "33<=maxTa<35", b33[2024])
add("33~35℃인 날 2025년", S["b33_35_days"]["2025"], "ASOS CSV maxTa", "같음", b33[2025])


# ------------------------------------------------------------------ 2. 폭염일수 표 (html.parser)
class TP(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self.cur, self.row, self.cell, self.in_cell = [], None, None, "", False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.cur = []
        elif tag == "tr" and self.cur is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.in_cell, self.cell = True, ""

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.in_cell:
            self.row.append(self.cell.strip())
            self.in_cell = False
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.cur.append(self.row)
            self.row = None
        elif tag == "table" and self.cur is not None:
            self.tables.append(self.cur)
            self.cur = None

    def handle_data(self, data):
        if self.in_cell:
            self.cell += data


hw_file = sorted(glob.glob(str(RAW / "기상" / "heatwave_chart_stn108_*.html")))[-1]
tp = TP()
tp.feed(open(hw_file, encoding="utf-8").read())
hw = {}
for t in tp.tables:
    if t and t[0][:2] == ["연도", "1월"]:
        hdr = t[0]
        for r in t[1:]:
            if r[0].isdigit():
                hw[int(r[0])] = {hdr[i]: r[i] for i in range(len(hdr))}
hw_csv = {}
with open(PROC / "heatwave_seoul.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        hw_csv[int(r["연도"])] = r
add("서울 폭염일수 2024년", hw_csv[2024]["연합계"], "기상청 폭염일수 화면 표", "html.parser '연합계'", hw[2024]["연합계"])
add("서울 폭염일수 2025년", hw_csv[2025]["연합계"], "같음", "같음", hw[2025]["연합계"])
add("서울 폭염일수 2026년(연중 미완)", hw_csv[2026]["연합계"], "같음", "같음", hw[2026]["연합계"])
normal = statistics.mean(int(hw[y]["연합계"]) for y in range(1991, 2021))
normal_csv = statistics.mean(float(hw_csv[y]["연합계"]) for y in range(1991, 2021))
add("평년(1991~2020) 평균 폭염일수", round(normal_csv, 1), "같음", "1991~2020 평균", round(normal, 1))
add("ASOS 33℃ 이상 일수 = 폭염일수 표 (2024)", hw[2024]["연합계"], "ASOS CSV vs 화면 표", "maxTa>=33 세기", ge33[2024])
add("ASOS 33℃ 이상 일수 = 폭염일수 표 (2025)", hw[2025]["연합계"], "같음", "같음", ge33[2025])
add("폭염일수 30일 이상인 해의 수(1973~2025)", sum(1 for y in range(1973, 2026) if float(hw_csv[y]["연합계"]) >= 30), "같음", "연합계>=30 세기",
    sum(1 for y in range(1973, 2026) if int(hw[y]["연합계"]) >= 30))
add("2016~2025년 평균 폭염일수", round(statistics.mean(float(hw_csv[y]["연합계"]) for y in range(2016, 2026)), 1), "같음", "평균",
    round(statistics.mean(int(hw[y]["연합계"]) for y in range(2016, 2026)), 1))


# ------------------------------------------------------------------ 3. 원자료 월 CSV 3개 (csv 모듈)
def band(h):
    return "00-04" if h <= 4 else "05-09" if h <= 9 else "10-15" if h <= 15 else "16-19" if h <= 19 else "20-23"


daily, stn_daily, agg, prof = {}, {}, {}, {}
for m in ["202408", "202507", "202508"]:
    f = RAW / "따릉이" / f"서울특별시 공공자전거 이용정보(시간대별)_{m}.csv"
    t0 = datetime.now()
    with open(f, encoding="cp949", newline="") as fh:
        rd = csv.reader(fh)
        hdr = next(rd)
        iD, iH, iS, iP, iA, iN, iX = [hdr.index(c) for c in ("대여일자", "대여시간", "대여소번호", "대여구분코드", "연령대코드", "이용건수", "성별")]
        iM = [i for i, c in enumerate(hdr) if c.startswith("이용시간")][0]
        iL = [i for i, c in enumerate(hdr) if c.startswith("이동거리")][0]
        for r in rd:
            d, n = r[iD][:10], int(r[iN])
            daily[d] = daily.get(d, 0) + n
            s = r[iS].lstrip("0") or "0"
            stn_daily[(d, s)] = stn_daily.get((d, s), 0) + n
            ag = AGEGRP.get(r[iA].strip(), "기타")
            p = r[iP].split("(")[0].strip()
            b = band(int(r[iH]))
            mins = int(float(r[iM])) if r[iM] else 0
            if m.startswith("2025"):
                a_raw = r[iA].strip()
                pr = prof.get((d, a_raw))
                if pr is None:
                    pr = prof[(d, a_raw)] = [0, 0, 0.0, 0, 0, int(r[iH]) * 0]  # rent, mins, dist, seasonal, male, (unused)
                pr[0] += n
                pr[1] += mins
                pr[2] += float(r[iL]) if r[iL] else 0.0
                if p == "정기권":
                    pr[3] += n
                if r[iX].strip().upper() == "M":
                    pr[4] += n
                hk = (d, a_raw, int(r[iH]))
                prof[hk] = prof.get(hk, 0) + n
            key = (d, s, ag, p, b)
            a = agg.get(key)
            if a is None:
                agg[key] = [n, mins]
            else:
                a[0] += n
                a[1] += mins
    print(f"  {m}: {len(set(k for k in daily if k.startswith(m[:4] + '-' + m[4:])))}일, {(datetime.now() - t0).seconds}초", flush=True)
DT = {}
with open(PROC / "daily_total_weather.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        DT[r["date"]] = r
for d in ["2024-08-04", "2024-08-13", "2025-07-27", "2025-07-09", "2025-08-02"]:
    add(f"일 대여건수 {d}", DT[d]["rent"], f"원자료 {d[:4]}{d[5:7]} CSV 이용건수", "csv 모듈 합계", daily[d])
add("2025년 7월 월 합계(원자료 행 합)", CS["months"][5]["rent_sum"], "원자료 202507 CSV", "csv 모듈 합계", sum(v for d, v in daily.items() if d.startswith("2025-07")))
add("9개월 이용건수 합계", CS["rent_total"], "clean_summary 월별 합", "월별 rent_sum 합", sum(m_["rent_sum"] for m_ in CS["months"]), kind="집계 파일")
hot_days_all = [d for d in DT if DT[d]["year"] in ("2024", "2025") and W[d]["maxTa"] >= 35]
add("35℃ 이상인 날 하루 평균 대여건수(2024·2025)", round(S["mean_rent_ge35"]), "daily_total_weather.csv × ASOS", "평균", round(statistics.mean(int(DT[d]["rent"]) for d in hot_days_all)), kind="집계 파일")


# ------------------------------------------------------------------ 4. 2025년 7~8월 평일 폭염일·기준일 (dict)
def wk_ok(d):
    dt = date.fromisoformat(d)
    return dt.weekday() < 5 and d not in HOL and W[d]["sumRn"] == 0


hot = sorted(d for d in W if d[:7] in ("2025-07", "2025-08") and wk_ok(d) and W[d]["maxTa"] >= 35)
ref = sorted(d for d in W if d[:7] in ("2025-07", "2025-08") and wk_ok(d) and 27 <= W[d]["maxTa"] < 33)
nh, nr = len(hot), len(ref)
add("2025년 폭염 평일 수", E["n_hot_weekdays_2025"], "ASOS + 달력 + 공휴일", "평일·무강수·비공휴일·>=35", nh)
add("2025년 기준 평일 수", E["n_ref_weekdays_2025"], "같음", "27<=maxTa<33", nr)
# 대여소 유지 비율(전체 이용, 21_station 규칙: 기준 30건 이상, 폭염일 전부·기준일 5/6 이상 기록)
stns = {s for (d, s) in stn_daily if d in hot or d in ref}
ratios = {}
need_ref = math.ceil(nr * 5 / 6)
for s in stns:
    hv = [stn_daily.get((d, s), 0) for d in hot]
    rv = [stn_daily.get((d, s), 0) for d in ref]
    mr = sum(rv) / nr
    if mr >= 30 and all(v > 0 for v in hv) and sum(1 for v in rv if v > 0) >= need_ref:
        ratios[s] = (sum(hv) / nh) / mr
vals = sorted(ratios.values())
add("유지 비율 계산 대여소 수(2025)", SS["2025"]["n"], "원자료 202507·202508 CSV", f"dict 집계, 기준 30건·폭염일 전부·기준일 {need_ref}/{nr} 이상", len(ratios))
add("유지 비율 중앙값(2025)", round(SS["2025"]["median_ratio"], 3), "같음", "statistics.median", round(statistics.median(vals), 3))
add("비율 0.8 미만 대여소 비율(%)", round(SS["2025"]["share_lt_0_8"], 1), "같음", "비율", round(100 * sum(1 for v in vals if v < 0.8) / len(vals), 1))
add("비율 1 초과 대여소 비율(%)", round(SS["2025"]["share_gt_1"], 1), "같음", "비율", round(100 * sum(1 for v in vals if v > 1) / len(vals), 1))
# 전일 운영 대여소 (평일 폭염일+기준일 전부 기록)
full = {s for s in stns if all(stn_daily.get((d, s), 0) > 0 for d in hot + ref)}
add("전일 운영 대여소 수(2025 평일 비교 기간)", E["stations"]["n_full_operation"], "같음", "폭염일·기준일 전부 기록>0", len(full))
# 연령군별: 60+ 폭염 평일 하루 건수, 회당 분, 낮 명시간
def sum_agg(filt):
    n_, m_ = 0, 0
    for (d, s, ag, p, b), (cnt, mins) in agg.items():
        if filt(d, s, ag, p, b):
            n_ += cnt
            m_ += mins
    return n_, m_


n60, m60 = sum_agg(lambda d, s, ag, p, b: d in hot and ag == "60+")
add("60대 이상 폭염 평일 하루 대여건수", round(E["age_2025"]["60+"]["hot_rent_per_day"], 1), "원자료 연령대코드", "60대+70대이상 합 ÷ 8일", round(n60 / nh, 1))
add("60대 이상 폭염 평일 회당 이용시간(분)", round(E["age_2025"]["60+"]["hot_min_per_trip"], 1), "원자료 이용시간(분)", "Σ분 ÷ Σ건수", round(m60 / n60, 1))
n2050, m2050 = sum_agg(lambda d, s, ag, p, b: d in hot and ag == "20-50대")
add("20~50대 폭염 평일 회당 이용시간(분)", round(E["age_2025"]["20-50대"]["hot_min_per_trip"], 1), "같음", "같음", round(m2050 / n2050, 1))
n60d, m60d = sum_agg(lambda d, s, ag, p, b: d in hot and ag == "60+" and b in ("10-15", "16-19"))
add("60대 이상 낮(10~19시) 노출 시간(명시간/일)", round(E["age_2025"]["60+"]["hot_day_ph_per_day"]), "같음", "Σ분 ÷ 60 ÷ 8일", round(m60d / 60 / nh))
add("60대 이상 하루 전체 노출 시간(명시간/일)", round(E["age_2025"]["60+"]["hot_ph_per_day"]), "같음", "같음", round(m60 / 60 / nh))
nall, mall = sum_agg(lambda d, s, ag, p, b: d in hot)
add("폭염 평일 전체 노출 시간(명시간/일)", round(E["total_2025"]["hot_ph_per_day"]), "같음", "같음", round(mall / 60 / nh))
add("폭염 평일 전체 하루 대여건수(2025)", round(E["total_2025"]["hot_rent_per_day"], 1), "같음", "Σ건수 ÷ 8일", round(nall / nh, 1))
# 60+ 유지 비율(평일): hot/ref
r60, _ = sum_agg(lambda d, s, ag, p, b: d in ref and ag == "60+")
add("60대 이상 평일 유지 비율", round(E["age_2025"]["60+"]["ratio"], 3), "같음", "(건수/8) ÷ (건수/10)", round((n60 / nh) / (r60 / nr), 3))
# (정기권 아침 통근 대여소 항목은 보고서에서 빠져 검증표에서도 뺐다)
# 자치구(강서구) 60+ 낮 — 대여소→자치구는 stations.csv
gu_of = {}
with open(PROC / "stations.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        gu_of[r["stn"]] = r["gu"]
gs, _ = sum_agg(lambda d, s, ag, p, b: d in hot and s in full and ag == "60+" and b in ("10-15", "16-19") and gu_of.get(s) == "강서구")
add("강서구 60대 이상 낮 폭염 평일 대여(건/일)", round(E["gu"]["top4_eld_day"][0]["eld_day_hot_per_day"], 2), "원자료 + 대여소 정보 자치구", "dict 합 ÷ 8일", round(gs / nh, 2))

# 고령 이용의 성격 (기준 평일, 60대+70대이상)
def prof_sum(ages, days):
    tot = [0, 0, 0.0, 0, 0]
    for (k0, k1, *rest), v in list(prof.items()):
        if rest or not isinstance(v, list):
            continue
        if k0 in days and k1 in ages:
            for i in range(5):
                tot[i] += v[i]
    return tot


p60 = prof_sum(("60대", "70대이상"), set(ref))
p2050 = prof_sum(("20대", "30대", "40대", "50대"), set(ref))
add("고령 이용자 정기권 비율(%), 기준 평일", round(EL["profile"]["60+"]["ref_seasonal_pass_pct"], 1), "원자료 대여구분코드·연령대코드", "정기권 건수 ÷ 전체", round(100 * p60[3] / p60[0], 1))
add("고령 이용자 회당 거리(km), 기준 평일", round(EL["profile"]["60+"]["ref_km_per_trip"], 2), "원자료 이동거리(M)", "Σ거리 ÷ Σ건수 ÷ 1000", round(p60[2] / p60[0] / 1000, 2))
add("고령 이용자 회당 시간(분), 기준 평일", round(EL["profile"]["60+"]["ref_min_per_trip"], 1), "원자료 이용시간(분)", "Σ분 ÷ Σ건수", round(p60[1] / p60[0], 1))
add("고령 이용자 평균속도(km/h), 기준 평일", round(EL["profile"]["60+"]["ref_kmh"], 2), "같음", "Σ거리(km) ÷ Σ시간(h)", round((p60[2] / 1000) / (p60[1] / 60), 2))
add("청장년층 평균속도(km/h), 기준 평일", round(EL["profile"]["20-50대"]["ref_kmh"], 2), "같음", "같음", round((p2050[2] / 1000) / (p2050[1] / 60), 2))
add("고령 이용자 남성 비율(%), 기준 평일", round(EL["profile"]["60+"]["ref_male_pct"], 1), "원자료 성별", "M 건수 ÷ 전체(미상 포함)", round(100 * p60[4] / p60[0], 1))
add("고령 이용자 기준 평일 하루 대여건수", round(EL["profile"]["60+"]["ref_rent_per_day"], 1), "원자료", "Σ건수 ÷ 10일", round(p60[0] / nr, 1))


def hour_sum(ages, days, hours):
    return sum(v for (k0, k1, *rest), v in prof.items() if rest and k0 in days and k1 in ages and rest[0] in hours)


h60_ref = {h: hour_sum(("60대", "70대이상"), set(ref), (h,)) / nr for h in range(24)}
h60_hot = {h: hour_sum(("60대", "70대이상"), set(hot), (h,)) / nh for h in range(24)}
add("고령 이용자 시간별 유지 비율 6~7시 평균", round(EL["hour_ratio_summary"]["60+"]["06-07"], 3), "원자료 대여시간", "(폭염일 건/8) ÷ (기준일 건/10), 6·7시 평균", round((h60_hot[6] / h60_ref[6] + h60_hot[7] / h60_ref[7]) / 2, 3))
add("고령 이용자 시간별 유지 비율 12~14시 평균", round(EL["hour_ratio_summary"]["60+"]["12-14"], 3), "같음", "12·13·14시 평균", round(sum(h60_hot[h] / h60_ref[h] for h in (12, 13, 14)) / 3, 3))
add("고령 이용자 시간별 유지 비율 20시", round(EL["hour_ratio_summary"]["60+"]["20"], 3), "같음", "20시", round(h60_hot[20] / h60_ref[20], 3))
s60 = {h: hour_sum(("60대",), set(ref), (h,)) for h in range(24)}
add("60대 18시 이용 비중(%), 기준 평일", round(EL["peaks"]["60대_pm"]["18"], 2), "같음", "18시 건수 ÷ 하루 건수", round(100 * s60[18] / sum(s60.values()), 2))
add("고령 이용자 낮(10~19시) 비중(%), 기준 평일", round(EL["peaks"]["60+_day_share_10_19"], 1), "같음", "10~19시 건수 ÷ 하루 건수", round(100 * sum(h60_ref[h] for h in range(10, 20)) / sum(h60_ref.values()), 1))

# 표 2 나머지 행 (20대·40대·70대이상·전체): 정기권 비율·회당 거리·시간·속도
for ag_, lab_ in [("20대", "20대"), ("40대", "40대"), ("70대이상", "70대 이상")]:
    pk = prof_sum((ag_,), set(ref))
    add(f"{lab_} 정기권 비율(%)", round(EL["profile"][ag_]["ref_seasonal_pass_pct"], 1), "원자료", "정기권 ÷ 전체", round(100 * pk[3] / pk[0], 1))
    add(f"{lab_} 회당 거리(km)", round(EL["profile"][ag_]["ref_km_per_trip"], 2), "원자료", "Σ거리 ÷ Σ건수", round(pk[2] / pk[0] / 1000, 2))
    add(f"{lab_} 회당 시간(분)", round(EL["profile"][ag_]["ref_min_per_trip"], 1), "원자료", "Σ분 ÷ Σ건수", round(pk[1] / pk[0], 1))
    add(f"{lab_} 평균속도(km/h)", round(EL["profile"][ag_]["ref_kmh"], 2), "원자료", "Σkm ÷ Σh", round((pk[2] / 1000) / (pk[1] / 60), 2))
pall = prof_sum(tuple(AGEGRP) + ("기타",), set(ref))
add("전체 정기권 비율(%), 비교 평일", round(EL["profile_all_ref"]["seasonal_pass_pct"], 1), "원자료", "정기권 ÷ 전체(연령 미상 포함)", round(100 * pall[3] / pall[0], 1))
add("전체 비교 평일 하루 대여건수", round(EL["profile_all_ref"]["rent_per_day"], 1), "원자료", "Σ건수 ÷ 10일", round(pall[0] / nr, 1))
# 자치구 2~4위와 네 구 비중
gu_vals = {}
for (d, s_, ag, p, b), (cnt, mins) in agg.items():
    if d in hot and s_ in full and ag == "60+" and b in ("10-15", "16-19"):
        g_ = gu_of.get(s_, "미상")
        gu_vals[g_] = gu_vals.get(g_, 0) + cnt
for k_, name_ in enumerate(["영등포구", "송파구", "노원구"], start=1):
    add(f"{name_} 60대 이상 낮 폭염 평일 대여(건/일)", round(E["gu"]["top4_eld_day"][k_]["eld_day_hot_per_day"], 2), "원자료 + 대여소 정보", "dict 합 ÷ 8일", round(gu_vals.get(name_, 0) / nh, 2))
known = {k: v for k, v in gu_vals.items() if k != "미상"}
top4 = sum(sorted(known.values(), reverse=True)[:4])
add("상위 네 구가 60대 이상 낮 이용에서 차지하는 비중(%)", round(E["gu"]["top4_eld_day_share_pct"], 1), "같음", "상위 4 합 ÷ 25개 구 합", round(100 * top4 / sum(known.values()), 1))
# 유형 구성(비교 평일, 60+): 이름 규칙을 그대로 적용
import re as _re
def _cls(name):
    n_ = str(name)
    if _re.search(r"아파트|빌라|주공|연립|APT|주택|오피스텔|(?<!디지털)(?<!산업)(?<!공)단지", n_):
        return "주거형"
    if _re.search(r"공원|한강|강변|둔치|수변|천변|호수|선착장|유원지|쉼터|청계천|안양천|중랑천|탄천|홍제천|불광천|도림천|양재천|성북천|정릉천|우이천|당현천|묵동천|고덕천|여의나루", n_):
        return "공원·강변형"
    if _re.search(r"역", n_):
        return "역세권형"
    if _re.search(r"시장|병원|의료원|주민센터|구청|도서관|복지관|보건소|우체국|경로당|노인|보건|학교|체육|스포츠|수련관|세무서|구민|문화센터|복지센터|복지|관공서|시청|경찰서|소방서|법원|교회|성당|마트", n_):
        return "생활시설형"
    return "기타"
name_of = {}
with open(PROC / "stations.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        name_of[r["stn"]] = r["name"]
tc = {}
for (d, s_, ag, p, b), (cnt, mins) in agg.items():
    if d in ref and ag == "60+" and s_ in name_of:
        t_ = _cls(name_of[s_])
        tc[t_] = tc.get(t_, 0) + cnt
add("고령 이용자 비교 평일 대여의 역세권형 몫(%)", round(EL["type_composition_ref"]["60+"]["역세권형"], 1), "원자료 + 대여소 이름 규칙", "유형별 합 ÷ 전체(이름 있는 대여소)", round(100 * tc.get("역세권형", 0) / sum(tc.values()), 1))
add("고령 이용자 비교 평일 대여의 기타 몫(%)", round(EL["type_composition_ref"]["60+"]["기타"], 1), "같음", "같음", round(100 * tc.get("기타", 0) / sum(tc.values()), 1))
e60 = {}
for (d, s_, ag, p, b), (cnt, mins) in agg.items():
    if d in hot and s_ in full and ag == "60+" and s_ in name_of:
        e60[s_] = e60.get(s_, 0) + cnt
top30_s = sorted(e60, key=lambda k: -e60[k])[:30]
add("고령 이용 상위 30 대여소 중 역세권형 수", EL["elderly_top30"]["types"].get("역세권형", 0), "같음", "상위 30 이름 규칙 분류", sum(1 for k in top30_s if _cls(name_of[k]) == "역세권형"))
add("장한평역 8번 출구 앞(529) 60대 이상 폭염 평일 대여(건/일)", round(EL["elderly_top30"]["top5"][0]["hot60_per_day"], 2), "원자료", "dict 합 ÷ 8일", round(e60.get("529", 0) / nh, 2))
has60 = {s_ for (d, s_, ag, p, b), (cnt, mins) in agg.items() if ag == "60+" and cnt > 0 and (d in hot or d in ref)}
add("전일 운영 대여소 중 대여소 정보에 있는 곳", EL["n_full_in_master"], "원자료 + 대여소 XLSX", "전일 운영 ∩ 대여소 정보", len([k for k in full if k in name_of]))
add("지도·목록에 쓴 대여소 수(위 가운데 60대 이상 이용 기록이 있는 곳)", len([1 for _ in csv.DictReader(open(RES / "station_elderly_2025_typed.csv", encoding="utf-8-sig"))]), "같음", "전일 운영 ∩ 대여소 정보 ∩ 60대 이상 기록", len([k for k in full if k in name_of and k in has60]))

# ------------------------------------------------------------------ 4b. 2차 검토에서 빠졌다고 지적된 보고서 수치
H35 = json.loads((RES / "heat35_days_by_year.json").read_text(encoding="utf-8"))
for y_ in (2024, 2025, 2026):
    add(f"그림 2(a) 35℃ 이상인 날 {y_}년(6~9월)", H35["ge35_jun_sep"][str(y_)], "ASOS CSV maxTa", "csv 모듈, 6~9월 maxTa>=35 세기",
        sum(1 for d, w in W.items() if d.startswith(str(y_)) and 6 <= int(d[5:7]) <= 9 and w["maxTa"] >= 35))
# 3.2 일조: 35℃ 이상인 날과 27~30℃인 날의 평균 일조(두 해 여름 표본)
ss_by = {}
for d in DT:
    if DT[d]["year"] in ("2024", "2025") and W[d]["sumSsHr"] is not None:
        ss_by.setdefault(tbin(W[d]["maxTa"]), []).append(W[d]["sumSsHr"])
add("35℃ 이상인 날 평균 일조(시간)", round(S["tbin_means"][">=35"]["sumSsHr"], 1), "ASOS CSV sumSsHr", "구간별 평균(결측 제외)", round(statistics.mean(ss_by[">=35"]), 1))
add("27~30℃인 날 평균 일조(시간)", round(S["tbin_means"]["27-30"]["sumSsHr"], 1), "같음", "같음", round(statistics.mean(ss_by["27-30"]), 1))
# 주 1: 2025년 6~9월 일평균, 연령 미상 비중, 고령 이용자 가족권 비중
add("2025년 6~9월 일평균 대여건수('하루 12만 건')", round(S["daily_mean_by_year"]["2025"]), "daily_total_weather.csv", "2025년 일 총량 평균", round(statistics.mean(int(r["rent"]) for r in DT.values() if r["year"] == "2025")), kind="집계 파일")
n_etc, _ = sum_agg(lambda d, s, ag, p, b: d in hot and ag == "기타")
add("연령 '기타' 비중(%), 2025년 폭염 평일", round(E["total_2025"]["etc_share_pct"], 1), "원자료 연령대코드", "기타 건수 ÷ 전체", round(100 * n_etc / nall, 1))
n_fam, _ = sum_agg(lambda d, s, ag, p, b: (d in hot or d in ref) and ag == "60+" and p == "가족권")
n60_18 = n60 + r60
add("고령 이용자 가족권 비중(%), 18일(보고서 '0.1% 미만')", 0.0, "원자료 대여구분코드", "가족권 ÷ 전체, 소수 첫째 자리", round(100 * n_fam / n60_18, 1))
# 표 2: 60대 행 전체와 20·40·70대 이상 남성 비율
pk60 = prof_sum(("60대",), set(ref))
pk60h = prof_sum(("60대",), set(hot))
add("표 2 60대 정기권 비율(%)", round(EL["profile"]["60대"]["ref_seasonal_pass_pct"], 1), "원자료", "정기권 ÷ 전체", round(100 * pk60[3] / pk60[0], 1))
add("표 2 60대 회당 거리(km)", round(EL["profile"]["60대"]["ref_km_per_trip"], 2), "원자료", "Σ거리 ÷ Σ건수", round(pk60[2] / pk60[0] / 1000, 2))
add("표 2 60대 회당 시간(분)", round(EL["profile"]["60대"]["ref_min_per_trip"], 1), "원자료", "Σ분 ÷ Σ건수", round(pk60[1] / pk60[0], 1))
add("표 2 60대 평균속도(km/h)", round(EL["profile"]["60대"]["ref_kmh"], 2), "원자료", "Σkm ÷ Σh", round((pk60[2] / 1000) / (pk60[1] / 60), 2))
add("표 2 60대 남성 비율(%)", round(EL["profile"]["60대"]["ref_male_pct"], 1), "원자료 성별", "M ÷ 전체", round(100 * pk60[4] / pk60[0], 1))
add("표 2 60대 하루 대여(건/일)", round(EL["profile"]["60대"]["ref_rent_per_day"], 1), "원자료", "Σ건수 ÷ 10일", round(pk60[0] / nr, 1))
add("표 2 60대 폭염 평일÷비교 평일", round(EL["profile"]["60대"]["ratio_hot_ref"], 3), "원자료", "(건/8) ÷ (건/10)", round((pk60h[0] / nh) / (pk60[0] / nr), 3))
for ag_, lab_ in [("20대", "20대"), ("40대", "40대"), ("70대이상", "70대 이상")]:
    pk = prof_sum((ag_,), set(ref))
    add(f"표 2 {lab_} 남성 비율(%)", round(EL["profile"][ag_]["ref_male_pct"], 1), "원자료 성별", "M ÷ 전체(미상 포함)", round(100 * pk[4] / pk[0], 1))
# 5.4: 전체 유지 비율, 낮 노출 비중, 건수 비중
rall, _ = sum_agg(lambda d, s, ag, p, b: d in ref)
add("전체 유지 비율(폭염 평일÷비교 평일, 2025)", round(E["total_2025"]["hot_rent_per_day"] / E["total_2025"]["ref_rent_per_day"], 3), "원자료", "(건/8) ÷ (건/10)", round((nall / nh) / (rall / nr), 3))
_, mknown_day = sum_agg(lambda d, s, ag, p, b: d in hot and ag != "기타" and b in ("10-15", "16-19"))
add("고령 이용자 낮 노출이 연령 미상 제외 낮 노출에서 차지하는 비중(%)", round(E["age_2025"]["60+"]["hot_day_share_pct"], 1), "원자료", "60대 이상 낮 분 ÷ 연령 확인 낮 분", round(100 * m60d / mknown_day, 1))
nknown, _ = sum_agg(lambda d, s, ag, p, b: d in hot and ag != "기타")
add("고령 이용자 건수 비중(%, 연령 미상 제외)", round(100 * E["age_2025"]["60+"]["hot_rent_per_day"] / E["total_2025"]["hot_rent_per_day_excl_etc"], 1), "원자료", "60대 이상 건수 ÷ 연령 확인 건수", round(100 * n60 / nknown, 1))
# 표 A: 20~50대·10대 이하 하루 대여
ABr = list(csv.DictReader(open(RES / "exposure_age_band_2025.csv", encoding="utf-8-sig")))
for g_, lab_ in [("20-50대", "20~50대"), ("10대", "10대 이하")]:
    ng_, _ = sum_agg(lambda d, s, ag, p, b, g_=g_: d in hot and ag == g_)
    add(f"표 A {lab_} 하루 대여(건/일)", round(sum(float(r["rent_per_day_hot"]) for r in ABr if r["agegrp"] == g_), 1), "원자료", "Σ건수 ÷ 8일", round(ng_ / nh, 1))
# 5.3·주 8: 시간별 비율의 범위(고령 이용자 12~16시·17~18시, 청장년층 12~16시·20시)와 날짜별 범위
YA = ("20대", "30대", "40대", "50대")
hy_ref = {h: hour_sum(YA, set(ref), (h,)) / nr for h in range(24)}
hy_hot = {h: hour_sum(YA, set(hot), (h,)) / nh for h in range(24)}
for lab_, grp, hs, hot_d, ref_d in [("고령 이용자 12~16시", "60+", range(12, 17), h60_hot, h60_ref), ("고령 이용자 17~18시", "60+", (17, 18), h60_hot, h60_ref),
                                    ("청장년층 12~16시", "20-50대", range(12, 17), hy_hot, hy_ref)]:
    rv = [hot_d[h] / ref_d[h] for h in hs]
    rep_ = [EL["hour_ratio"][grp][str(h)] for h in hs]
    add(f"{lab_} 유지 비율 최솟값~최댓값", f"{min(rep_):.2f}~{max(rep_):.2f}", "원자료 대여시간", "시간별 (건/8) ÷ (건/10)", f"{min(rv):.2f}~{max(rv):.2f}")
add("청장년층 20시 유지 비율", round(EL["hour_ratio_summary"]["20-50대"]["20"], 3), "원자료 대여시간", "20시", round(hy_hot[20] / hy_ref[20], 3))
for lab_, hs in [("06-07", (6, 7)), ("12-16", (12, 13, 14, 15, 16)), ("20", (20,))]:
    base_ = hour_sum(("60대", "70대이상"), set(ref), hs) / nr
    vals_ = [hour_sum(("60대", "70대이상"), {d}, hs) / base_ for d in hot]
    add(f"고령 이용자 {lab_}시 날짜별 비율 범위", f"{EL['daily_ratio_range_60+'][lab_]['min']:.2f}~{EL['daily_ratio_range_60+'][lab_]['max']:.2f}", "원자료 대여시간", "폭염 평일 날마다 ÷ 비교 평일 평균",
        f"{min(vals_):.2f}~{max(vals_):.2f}")
# 주 4: 방학·휴가철 민감도와 33℃ 경계 민감도, 10대 이하 7시 비율
SEN = EL["sensitivity"]


def ratio_days(days_h, days_r, filt):
    a_, _ = sum_agg(lambda d, s, ag, p, b: d in days_h and filt(ag))
    b_, _ = sum_agg(lambda d, s, ag, p, b: d in days_r and filt(ag))
    return (a_ / len(days_h)) / (b_ / len(days_r))


old_ = lambda ag: ag == "60+"  # noqa: E731
any_ = lambda ag: True  # noqa: E731
ref_late = [d for d in ref if d >= "2025-07-21"]
hot_mid = [d for d in hot if "2025-07-21" <= d <= "2025-08-11"]
ref_mid = [d for d in ref if "2025-07-21" <= d <= "2025-08-11"]
add("민감도: 비교 평일 7/21 이후, 고령 이용자", round(SEN["ref_late"]["60+"], 3), "원자료", "(폭염 8일) ÷ (비교 7일)", round(ratio_days(set(hot), set(ref_late), old_), 3))
add("민감도: 비교 평일 7/21 이후, 전체", round(SEN["ref_late"]["all"], 3), "원자료", "같음", round(ratio_days(set(hot), set(ref_late), any_), 3))
add("민감도: 7/21~8/11 창, 고령 이용자", round(SEN["mid_window"]["60+"], 3), "원자료", "(폭염 5일) ÷ (비교 3일)", round(ratio_days(set(hot_mid), set(ref_mid), old_), 3))
add("민감도: 7/21~8/11 창, 전체", round(SEN["mid_window"]["all"], 3), "원자료", "같음", round(ratio_days(set(hot_mid), set(ref_mid), any_), 3))
mid33 = sorted(d for d in W if d[:7] in ("2025-07", "2025-08") and wk_ok(d) and 33 <= W[d]["maxTa"] < 35)
add("33℃ 경계 민감도: 추가되는 33~35℃ 평일 수", len(SEN["thr33"]["mid_days"]), "ASOS + 달력 + 공휴일", "평일·무강수·비공휴일·33<=maxTa<35", len(mid33))
h33 = set(hot) | set(mid33)
add("33℃ 경계 민감도: 고령 이용자 유지 비율", round(SEN["thr33"]["ratio60"], 3), "원자료", "(33℃ 이상 평일) ÷ (비교 10일)", round(ratio_days(h33, set(ref), old_), 3))
_, m33d = sum_agg(lambda d, s, ag, p, b: d in h33 and ag == "60+" and b in ("10-15", "16-19"))
add("33℃ 경계 민감도: 고령 이용자 낮 노출(명시간/일)", round(SEN["thr33"]["day_ph60_per_day"]), "원자료", "Σ분 ÷ 60 ÷ 일수", round(m33d / 60 / len(h33)))
add("10대 이하 7시 유지 비율(방학 참고)", round(SEN["teen_7h_ratio"], 3), "원자료 대여시간", "7시 (건/8) ÷ (건/10)",
    round((hour_sum(("~10대",), set(hot), (7,)) / nh) / (hour_sum(("~10대",), set(ref), (7,)) / nr), 3))
# 표 B 2~5위, 표 C 1~3위(순서 포함)
EB = list(csv.DictReader(open(RES / "station_elderly_2025_typed.csv", encoding="utf-8-sig")))
for k_ in range(1, 5):
    r_ = EB[k_]
    add(f"표 B {k_ + 1}위 {r_['name'].strip()}({r_['stn']}) 60대 이상 대여(건/일)", round(float(r_["hot60_per_day"]), 2), "원자료", "dict 합 ÷ 8일", round(e60.get(r_["stn"], 0) / nh, 2))
add("표 B 1~5위 대여소 번호 순서", "/".join(r["stn"] for r in EB[:5]), "원자료", "60대 이상 폭염 평일 대여 내림차순", "/".join(top30_s[:5]))
FC = list(csv.DictReader(open(RES / "station_elderly_facility_2025.csv", encoding="utf-8-sig")))
fac_s = sorted((k for k in e60 if _cls(name_of[k]) == "생활시설형"), key=lambda k: -e60[k])
for k_ in range(3):
    r_ = FC[k_]
    add(f"표 C {k_ + 1}위 {r_['name'].strip()}({r_['stn']}) 60대 이상 대여(건/일)", round(float(r_["hot60_per_day"]), 2), "원자료 + 이름 규칙", "생활시설형 중 dict 합 ÷ 8일", round(e60.get(r_["stn"], 0) / nh, 2))
add("표 C 1~3위 대여소 번호 순서", "/".join(r["stn"] for r in FC[:3]), "같음", "생활시설형 중 내림차순", "/".join(fac_s[:3]))
# 표 D 5~8위, 네 구의 낮 노출(명시간)과 비중
GD = sorted((r for r in csv.DictReader(open(RES / "gu_exposure_2025.csv", encoding="utf-8-sig")) if r["gu"] != "미상"), key=lambda r: -float(r["eld_day_hot_per_day"]))
for k_ in range(4, 8):
    r_ = GD[k_]
    add(f"표 D {k_ + 1}위 {r_['gu']} 60대 이상 낮 대여(건/일)", round(float(r_["eld_day_hot_per_day"]), 2), "원자료 + 대여소 정보", "dict 합 ÷ 8일", round(gu_vals.get(r_["gu"], 0) / nh, 2))
gu_min = {}
for (d, s_, ag, p, b), (cnt, mins) in agg.items():
    if d in hot and s_ in full and ag == "60+" and b in ("10-15", "16-19"):
        g_ = gu_of.get(s_, "미상")
        gu_min[g_] = gu_min.get(g_, 0) + mins
gk = {k: v for k, v in gu_min.items() if k != "미상"}
top4n = [r["gu"] for r in GD[:4]]
for r_ in GD[:4]:
    add(f"표 D {r_['gu']} 60대 이상 낮 노출(명시간/일)", round(float(r_["eld_day_hot_ph_per_day"]), 1), "원자료 + 대여소 정보", "Σ분 ÷ 60 ÷ 8일", round(gk.get(r_["gu"], 0) / 60 / nh, 1))
add("명시간 상위 네 구(가나다순)", "/".join(sorted(top4n)), "같음", "낮 노출 내림차순 상위 4", "/".join(sorted(sorted(gk, key=lambda k: -gk[k])[:4])))
add("네 구가 60대 이상 낮 노출에서 차지하는 비중(%)", round(100 * sum(float(r["eld_day_hot_ph_per_day"]) for r in GD if r["gu"] in top4n) / sum(float(r["eld_day_hot_ph_per_day"]) for r in GD), 1),
    "같음", "네 구 합 ÷ 25개 구 합", round(100 * sum(gk[g] for g in top4n) / sum(gk.values()), 1))
# 주 7: 유형별 대여소 수, 유형별 유지 비율 중앙값과 검정(원자료로 다시 만든 대여소 비율에 같은 이름 규칙)
from scipy import stats as _st  # noqa: E402
T5 = ["역세권형", "주거형", "생활시설형", "공원·강변형", "기타"]
tcm = {}
for nm in name_of.values():
    tcm[_cls(nm)] = tcm.get(_cls(nm), 0) + 1
add("대여소 정보 유형별 대여소 수(역세권·주거·생활시설·공원강변·기타)", "/".join(str(EL["type_counts_master"][t]) for t in T5), "data_proc/stations.csv 이름", "이름 규칙(csv 모듈)",
    "/".join(str(tcm.get(t, 0)) for t in T5), kind="집계 파일")
by_t = {}
for s_, v in ratios.items():
    if s_ in name_of:
        by_t.setdefault(_cls(name_of[s_]), []).append(v)
TSr = {r["type"]: r for r in csv.DictReader(open(RES / "type_summary_2025.csv", encoding="utf-8-sig"))}
add("유형 분석 대여소 수(유지 비율 계산 ∩ 대여소 정보)", E["type"]["n"], "원자료 + 대여소 정보", "dict", sum(len(v) for v in by_t.values()))
for t_ in T5:
    add(f"유형별 유지 비율 중앙값: {t_}", round(float(TSr[t_]["median_ratio"]), 3), "원자료 + 이름 규칙", "statistics.median", round(statistics.median(by_t[t_]), 3))
add("유형 간 크루스칼-월리스 p", round(E["type"]["kruskal_p"], 4), "같음", "scipy.stats.kruskal(원자료로 다시 만든 비율)", round(float(_st.kruskal(*[by_t[t] for t in T5]).pvalue), 4), tol=0.0005)
add("공원·강변형 대 주거형 맨-휘트니 p", round(E["type"]["park_vs_resid_mw_p"], 4), "같음", "scipy.stats.mannwhitneyu(양측)",
    round(float(_st.mannwhitneyu(by_t["공원·강변형"], by_t["주거형"], alternative="two-sided").pvalue), 4), tol=0.0005)
for fn_, lab_ in [("type_manual_check.csv", "규칙을 정할 때 본 45곳"), ("type_random_check.csv", "무작위 100곳")]:
    rows_t = list(csv.DictReader(open(RES / fn_, encoding="utf-8-sig")))
    add(f"유형 대조 일치 수: {lab_}", sum(int(r["match"]) for r in rows_t), f"results/{fn_}(수작업 판정 열)", "이름 규칙을 다시 적용해 판정 열과 같은 곳을 셈",
        sum(1 for r in rows_t if _cls(r["name"]) == r["manual_type"]), kind="결과 파일(독립 아님)")

# ------------------------------------------------------------------ 5. 식 (1) 재적합 (numpy lstsq)
def design(rows_, with_ctrl=True):
    X, y = [], []
    for r in rows_:
        d = r["date"]
        w = W[d]
        if with_ctrl and (w["sumSsHr"] is None or w["avgRhm"] is None):
            continue
        tb, rb = tbin(w["maxTa"]), rbin(w["sumRn"])
        dt = date.fromisoformat(d)
        x = [1.0] + [1.0 if tb == b else 0.0 for b in ["<27", "30-33", "33-35", ">=35"]] + [1.0 if rb == b else 0.0 for b in ["0-5", "5-20", ">20"]]
        x += [1.0 if dt.weekday() >= 5 else 0.0, 1.0 if d in HOL else 0.0] + [1.0 if dt.month == m else 0.0 for m in (7, 8, 9)] + [1.0 if dt.year == 2025 else 0.0]
        if with_ctrl:
            x += [w["sumSsHr"], w["avgRhm"]]
        X.append(x)
        y.append(np.log(float(r["rent"])))
    return np.array(X), np.array(y)


pct = lambda b: round(100 * (np.exp(b) - 1), 2)
main_rows = [r for d, r in DT.items() if r["year"] in ("2024", "2025")]
X, y = design(main_rows)
beta, *_ = np.linalg.lstsq(X, y, rcond=None)
r2 = 1 - ((y - X @ beta) ** 2).sum() / ((y - y.mean()) ** 2).sum()
add("주 모형 표본 수 n", S["main"]["n"], "daily_total_weather + ASOS", "일조·습도 결측일 제외", len(y), kind="집계 파일")
add("주 모형 R²", round(S["main"]["r2"], 3), "같음", "numpy lstsq", round(float(r2), 3), kind="집계 파일")
add("35℃ 이상 효과(%)", round(S["main"]["tbin"][">=35"]["pct"], 2), "같음", "lstsq 계수 → 100(e^b−1)", pct(beta[4]), tol=0.05, kind="집계 파일")
add("33~35℃ 효과(%)", round(S["main"]["tbin"]["33-35"]["pct"], 2), "같음", "같음", pct(beta[3]), tol=0.05, kind="집계 파일")
add("30~33℃ 효과(%)", round(S["main"]["tbin"]["30-33"]["pct"], 2), "같음", "같음", pct(beta[2]), tol=0.05, kind="집계 파일")
add("강수 20mm 초과 효과(%)", round(S["main"]["rain"][">20"]["pct"], 2), "같음", "같음", pct(beta[7]), tol=0.05, kind="집계 파일")
add("강수 5~20mm 효과(%)", round(S["main"]["rain"]["5-20"]["pct"], 2), "같음", "같음", pct(beta[6]), tol=0.05, kind="집계 파일")
add("강수 5mm 이하 효과(%)", round(S["main"]["rain"]["0-5"]["pct"], 2), "같음", "같음", pct(beta[5]), tol=0.05, kind="집계 파일")
add("주말 효과(%)", round(S["main"]["wkend"]["pct"], 2), "같음", "같음", pct(beta[8]), tol=0.05, kind="집계 파일")
X0, y0 = design(main_rows, with_ctrl=False)
b0, *_ = np.linalg.lstsq(X0, y0, rcond=None)
add("통제 전(일조·습도 없음) 35℃ 이상 효과(%)", round(S["noctrl"]["tbin"][">=35"]["pct"], 2), "같음", "lstsq(통제 변수 제외, n=244)", pct(b0[4]), tol=0.05, kind="집계 파일")
sub = {}
with open(PROC / "daily_hour_age_pass.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        d, h, n_ = r["date"], int(r["hour"]), int(r["rent"])
        if d[:4] not in ("2024", "2025"):
            continue
        for key in [("band", band(h)), ("pass", r["pass"]), ("age", r["age"])]:
            sub[(key, d)] = sub.get((key, d), 0) + n_
for key, label, rep in [(("band", "10-15"), "10~15시 35℃ 이상 효과(%)", S["hourband"]["10-15"]["tbin"][">=35"]["pct"]),
                        (("band", "16-19"), "16~19시 35℃ 이상 효과(%)", S["hourband"]["16-19"]["tbin"][">=35"]["pct"]),
                        (("band", "05-09"), "5~9시 35℃ 이상 효과(%)", S["hourband"]["05-09"]["tbin"][">=35"]["pct"]),
                        (("pass", "정기권"), "정기권 35℃ 이상 효과(%)", S["pass"]["정기권"]["tbin"][">=35"]["pct"]),
                        (("pass", "일일권"), "일일권 35℃ 이상 효과(%)", S["pass"]["일일권"]["tbin"][">=35"]["pct"]),
                        (("age", "60대"), "60대 35℃ 이상 효과(%)", S["age"]["60대"]["tbin"][">=35"]["pct"]),
                        (("age", "70대이상"), "70대 이상 35℃ 이상 효과(%)", S["age"]["70대이상"]["tbin"][">=35"]["pct"]),
                        (("age", "20대"), "20대 35℃ 이상 효과(%)", S["age"]["20대"]["tbin"][">=35"]["pct"]),
                        (("age", "30대"), "30대 35℃ 이상 효과(%)", S["age"]["30대"]["tbin"][">=35"]["pct"]),
                        (("age", "40대"), "40대 35℃ 이상 효과(%)", S["age"]["40대"]["tbin"][">=35"]["pct"]),
                        (("age", "50대"), "50대 35℃ 이상 효과(%)", S["age"]["50대"]["tbin"][">=35"]["pct"])]:
    rows_k = [{"date": d, "rent": v, "year": d[:4]} for (k, d), v in sub.items() if k == key]
    Xk, yk = design(rows_k)
    bk, *_ = np.linalg.lstsq(Xk, yk, rcond=None)
    add(label, round(rep, 2), "daily_hour_age_pass.csv × ASOS", "csv 집계 + lstsq", pct(bk[4]), tol=0.05, kind="집계 파일")

# ------------------------------------------------------------------ 6. 대여소 마스터·표본 크기·표본 외
wb = openpyxl.load_workbook(RAW / "따릉이" / "공공자전거 대여소 정보(26.6월 기준).xlsx", read_only=True, data_only=True)
ws = wb[wb.sheetnames[0]]
n_master = sum(1 for r in ws.iter_rows(min_row=6, values_only=True) if r[0] is not None)
add("대여소 정보 행수(2026-06 기준)", CS["stations_master"], "대여소 XLSX", "openpyxl, 6행부터 비지 않은 행", n_master)
add("분석 기간 일수(2024·2025년 6~9월 + 2026년 6월)", CS["days"], "daily_total_weather.csv", "len", len(DT), kind="집계 파일")
add("2026년 6월 표본 외 예측 MAPE(%)", round(S["oos_2026"]["mape"], 1), "results/oos_2026.csv(모형 예측값 포함)", "절댓값(실제−예측)÷실제의 평균(예측값은 재적합하지 않음)",
    round(statistics.mean(float(r["ape"]) for r in csv.DictReader(open(RES / "oos_2026.csv", encoding="utf-8-sig"))), 1), kind="결과 파일(독립 아님)")

# ------------------------------------------------------------------ 출력
n_bad = sum(1 for r in rows if r[5] != "일치")
n_raw = sum(1 for r in rows if r[6] == "원자료")
n_dep = sum(1 for r in rows if r[6].startswith("결과 파일"))
n_proc = len(rows) - n_raw - n_dep
md = ["# results/verification.md — 핵심 수치 독립 재계산", "",
      f"실행 {datetime.now():%Y-%m-%d %H:%M} · 스크립트 `code/40_verify.py` · 비교 대상 `results/summary_stats.json`·`station_summary.json`·`exposure_gap_summary.json`·`elderly_summary.json`·`heat35_days_by_year.json`·표 B·C·D·유형 요약 CSV·`data_proc/clean_summary.json`", "",
      "재계산은 원자료(월 CSV 3개, ASOS CSV, 폭염일수 HTML, 대여소 XLSX)를 csv·html.parser·openpyxl 로 직접 읽어 dict 로 집계했다. 이 '원자료' 항목은 10_clean·21~24 의 pandas 경로와 독립이다. 식 (1)과 하위 모형은 10_clean 이 만든 일 총량·시간대 집계를 입력으로 numpy.linalg.lstsq 로 다시 적합했으므로 '집계 파일' 항목으로 따로 센다. 허용 오차는 표에 명시(계수 0.05%p, p값 0.0005, 그 밖은 반올림 자리).", "",
      f"**결과: {len(rows)}개 항목 중 불일치 {n_bad}개. 입력 구분: 원자료 {n_raw}개, 집계 파일 {n_proc}개, 결과 파일(독립 아님) {n_dep}개.**", "",
      "입력 구분 '원자료'는 data_raw의 월 CSV·ASOS CSV·폭염일수 HTML·대여소 XLSX를 직접 읽은 항목, '집계 파일'은 data_proc 산출물(일 총량·시간대 집계)을 입력으로 다른 코드(csv·numpy.lstsq)로 다시 계산한 항목, '결과 파일(독립 아님)'은 모형 예측값이나 수작업 유형 판정처럼 결과 파일의 값을 그대로 읽어 세기만 한 항목이다. 보고서 표 E의 사양별 모형은 statsmodels 결과를 그대로 쓰며 여기서 재적합하지 않았다. 유형 간 검정 p값은 원자료로 다시 만든 대여소 비율에 scipy 검정을 다시 적용했다.", "",
      "| # | 항목 | 보고서 값 | 입력 | 원자료·열 | 재계산 방법 | 재계산 값 | 판정 |", "|---|---|---|---|---|---|---|---|"]
for i, r in enumerate(rows, 1):
    md.append(f"| {i} | {r[0]} | {r[1]} | {r[6]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |")
md += ["", "## 그림·캡션 점검 (사람이 다시 볼 것)",
       "- 그림 2(a)의 폭염일수·35℃ 이상 일수는 위 표의 폭염일수·ASOS 항목, (b)의 막대는 model_noctrl.csv·model_main.csv 의 pct.",
       "- 그림 3(a)는 hour_share_by_age_2025.csv, (b)는 type_composition_2025.csv. 그림 4(a)는 hour_ratio_by_age4_2025.csv, (b)는 hour_share_by_age_2025.csv 의 hot/ref_per_day.",
       "- 그림 5(a)는 model_pass.csv·model_age.csv 의 pct, (b)는 exposure_age_band_2025.csv. 그림 6(a)는 gu_exposure_2025.csv, (b)와 부록 그림 B는 station_elderly_2025_typed.csv·station_elderly_facility_2025.csv.",
       "- 부록 그림 A는 station_type_2025.csv(5유형). 효과는 모두 '기준 대비 차이'로만 적고 인과로 쓰지 않는다."]
(RES / "verification.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md[:8]))
for r in rows:
    if r[5] != "일치":
        print("불일치:", r)
sys.exit(0 if n_bad == 0 else 1)
