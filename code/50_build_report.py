# -*- coding: utf-8 -*-
"""
50_build_report.py — 분석보고서 HTML 생성 (논문 양식 + 시인성·논증구조 지침 + 기준 요약문 ⑤ v5, report/보고서.html)

- 조판: 교통공모전_2026/논문양식_지침.md, 시인성_시각화_지침.md, 지침_추가_논증구조.md, 기준_요약문.md(⑤ v5 문단을 요약에 그대로, 수치만 재계산값)
- 검토 반영: report/review_findings_A.md·B.md(1차), review_findings_A_r2.md·B_r2.md(2차), 2026-10-21
- 숫자는 results/*.json·*.csv, data_proc/*.csv 에서 읽어 넣는다. 외부 출처 수치(EXT)는 참고문헌 [8]~[10] 원문의 값이다.
- 숫자 바로 뒤 조사는 J(값, 조사)가 받침에 맞춰 고른다(0.83으로, 0.88이다, 0.66은). 60_readability_check.py 가 전수 검사한다.
- 숫자·단위·참조 묶음과 뒤에 붙은 조사는 wrap_nb() 가 <span class="nb">로 감싼다(표·style 안은 제외).
- 팀명·대표자·GitHub URL 은 자리표시자. --team/--lead/--url 을 주면 치환본과 PDF 를 따로 만든다.

실행: python -P -E -X utf8 code/50_build_report.py [--css ../../공통_논문양식/paper.css] [--pdf]
"""
import argparse
import csv
import json
import math
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES, REP, PROC = ROOT / "results", ROOT / "report", ROOT / "data_proc"
REP.mkdir(exist_ok=True)


def rcsv(path):
    return list(csv.DictReader(open(path, encoding="utf-8-sig")))


S = json.loads((RES / "summary_stats.json").read_text(encoding="utf-8"))
SS = json.loads((RES / "station_summary.json").read_text(encoding="utf-8"))
E = json.loads((RES / "exposure_gap_summary.json").read_text(encoding="utf-8"))
EL = json.loads((RES / "elderly_summary.json").read_text(encoding="utf-8"))
CS = json.loads((PROC / "clean_summary.json").read_text(encoding="utf-8"))
H35 = json.loads((RES / "heat35_days_by_year.json").read_text(encoding="utf-8"))  # 30_figures.py 가 ASOS 일자료에서 센 35℃ 이상 일수(6~9월)
hw = {int(r["연도"]): float(r["연합계"]) for r in rcsv(PROC / "heatwave_seoul.csv")}
eld = rcsv(RES / "station_elderly_2025_typed.csv")
fac = rcsv(RES / "station_elderly_facility_2025.csv")
rob = rcsv(RES / "model_robust.csv")
gu = [r for r in rcsv(RES / "gu_exposure_2025.csv") if r["gu"] != "미상"]
ab = rcsv(RES / "exposure_age_band_2025.csv")
prof = {r["age"]: r for r in rcsv(RES / "age_profile_2025.csv")}
TS = {r["type"]: r for r in rcsv(RES / "type_summary_2025.csv")}
MC = rcsv(RES / "type_manual_check.csv")    # 규칙을 정할 때 본 45곳(고령 상위 30 + 생활시설형 상위 20)
RC = rcsv(RES / "type_random_check.csv")    # 그 밖에서 무작위로 뽑은 100곳(seed 2026)
DHP = rcsv(PROC / "daily_hour_age_pass.csv")
TEAM, LEAD, GIT = "{{팀명}}", "{{대표자}}", "{{GitHub URL}}"
ACCESS = "접속 2026-10-21"
ACCENT = "#1f4e79"
FG = "../figures"
KNUM = {1: "한", 2: "두", 3: "세", 4: "네", 5: "다섯", 6: "여섯", 7: "일곱", 8: "여덟", 9: "아홉", 10: "열"}
# 외부 1차 출처의 수치(원문 그대로, 2026-10-21 접속해 확인). 근거 문장은 참고문헌 [8]~[10].
EXT = {"emp6064": 65.0,     # [8] 만 15~64세 고용률 해설의 연령별 문장 "20대와 60대의 경우에는 각각 60.2%와 65.0%에 그친다"(2025년) → 지표 범위상 60~64세
       "heat25_old": 30,    # [9] 2025년 온열질환자 중 65세 이상 노년층 30%
       "heat25_out": 79.2,  # [9] 발생 장소 실외 79.2%
       "heat26_old": 34.9}  # [10] 2026년 65세 이상 비중 34.9%

# ------------------------------------------------------------------ 숫자 뒤 조사(받침에 맞춤)
_DIGIT_JONG = {"0": "x", "1": "l", "2": "", "3": "x", "4": "", "5": "", "6": "x", "7": "l", "8": "l", "9": ""}   # 영 일 이 삼 사 오 육 칠 팔 구
_UNIT_JONG = (("km/h", ""), ("km", ""), ("mm", ""), ("%", ""), ("℃", ""))   # 킬로미터·밀리미터·퍼센트·도
_PARTICLE = {"은": ("는", "은", "은"), "이": ("가", "이", "이"), "을": ("를", "을", "을"), "과": ("와", "과", "과"),
             "으로": ("로", "로", "으로"), "이다": ("다", "이다", "이다"), "이고": ("고", "이고", "이고"), "이며": ("며", "이며", "이며"), "이나": ("나", "이나", "이나")}


def jong(s) -> str:
    """끝 글자 읽기의 받침: '' 없음, 'l' ㄹ받침, 'x' 그 밖의 받침. 숫자는 한자어 읽기(10=십, 100=백, 소수 끝자리는 한 자씩)."""
    t = re.sub(r"<[^>]+>", "", str(s)).rstrip().rstrip("])*")
    for u, j in _UNIT_JONG:
        if t.endswith(u):
            return j
    c = t[-1]
    if "가" <= c <= "힣":
        k = (ord(c) - 0xAC00) % 28
        return "" if k == 0 else ("l" if k == 8 else "x")
    if c.isdigit():
        num = re.search(r"[\d,]*\.?\d+$", t).group(0)
        if "." not in num:
            digits = num.replace(",", "")
            if digits.strip("0") and digits.endswith("0"):
                return "x"   # 십(ㅂ)·백(ㄱ)·천(ㄴ)·만(ㄴ)
        return _DIGIT_JONG[c]
    if c in "ABCDEabcde":
        return ""
    raise ValueError(f"받침을 정할 수 없음: {s!r}")


def J(s, p):
    no, l_, x = _PARTICLE[p]
    j = jong(s)
    return f"{s}{no if j == '' else l_ if j == 'l' else x}"


def n(x, d=0):
    return f"{float(x):,.{d}f}"


def a(x, d=0):
    return f"{abs(float(x)):,.{d}f}"


def f2(x):
    return f"{float(x):.2f}"


def pv(p):
    p = float(p)
    return "p&lt;0.001" if p < 0.001 else f"p={p:.3f}" if p < 0.01 else f"p={p:.2f}"


def url_wbr(u):
    """표 1 URL 줄바꿈 자리: / 뒤, 마지막 조각의 . 앞(selectHeatWaveChart.do 가 글자 중간에서 끊기지 않게)"""
    head, _, last = u.rpartition("/")
    return (head + "/").replace("/", "/<wbr>") + last.replace(".", "<wbr>.")


assert J("0.83", "으로") == "0.83으로" and J("0.88", "이다") == "0.88이다" and J("0.66", "은") == "0.66은" and J("0.89", "이다") == "0.89다"
assert J("0.88", "으로") == "0.88로" and J("1,705곳", "이") == "1,705곳이" and J("10", "은") == "10은" and J("35%", "을") == "35%를"

M = S["main"]
T35, T33, T30, T27 = M["tbin"][">=35"], M["tbin"]["33-35"], M["tbin"]["30-33"], M["tbin"]["<27"]
R20, R5, R0 = M["rain"][">20"], M["rain"]["5-20"], M["rain"]["0-5"]
N35 = S["noctrl"]["tbin"][">=35"]
HB = {k: v["tbin"][">=35"] for k, v in S["hourband"].items()}
PS = {k: v["tbin"][">=35"] for k, v in S["pass"].items()}
AG = {k: v["tbin"][">=35"] for k, v in S["age"].items()}
A60, A2050 = E["age_2025"]["60+"], E["age_2025"]["20-50대"]
TOT, GU = E["total_2025"], E["gu"]
NH, NR = E["n_hot_weekdays_2025"], E["n_ref_weekdays_2025"]
P = EL["profile"]
P60, P2050 = P["60+"], P["20-50대"]
HRS, HRF, SH, PK = EL["hour_ratio_summary"], EL["hour_ratio"], EL["hour_share_ref"], EL["peaks"]
TC, ET, FT = EL["type_composition_ref"], EL["elderly_top30"], EL["facility_top"]
SEN, DRR = EL["sensitivity"], EL["daily_ratio_range_60+"]
S33 = SEN["thr33"]


def hr_rng(grp, hours):
    vals = [HRF[grp][str(h)] for h in hours]
    return min(vals), max(vals)


r60_mid, r60_eve, ry_mid = hr_rng("60+", range(12, 17)), hr_rng("60+", (17, 18)), hr_rng("20-50대", range(12, 17))
raw_young = [P[k]["ratio_hot_ref"] for k in ("20대", "30대", "40대", "50대")]
mod_young = [abs(AG[k]["pct"]) for k in ("20대", "30대", "40대", "50대")]
mod_old = [abs(AG[k]["pct"]) for k in ("60대", "70대이상")]
ratio_all = TOT["hot_rent_per_day"] / TOT["ref_rent_per_day"]
gap_min = int(A60["hot_min_per_trip"] - A2050["hot_min_per_trip"])
share60_rent = 100 * A60["hot_rent_per_day"] / TOT["hot_rent_per_day_excl_etc"]
gu_eld = sorted(gu, key=lambda r: -float(r["eld_day_hot_per_day"]))
gu_ph = sorted(gu, key=lambda r: -float(r["eld_day_hot_ph_per_day"]))
top4 = [r["gu"] for r in gu_eld[:4]]
GU4 = "·".join(g[:-1] for g in top4)
top4_ph_share = 100 * sum(float(r["eld_day_hot_ph_per_day"]) for r in gu if r["gu"] in top4) / sum(float(r["eld_day_hot_ph_per_day"]) for r in gu)
st_share = 100 * EL["type_counts_master"]["역세권형"] / CS["stations_master"]
mc_n, mc_ok = len(MC), sum(int(r["match"]) for r in MC)
_mc30 = [r for r in MC if str(r.get("list", "")).startswith("고령 상위")]
mc30_n, mc30_ok = len(_mc30), sum(int(r["match"]) for r in _mc30)
rc_n, rc_ok = len(RC), sum(int(r["match"]) for r in RC)
rc_miss = [r for r in RC if r["match"] == "0"]
rc_miss_etc = sum(1 for r in rc_miss if r["rule_type"] == "기타")
rc_miss_etc_res = sum(1 for r in rc_miss if r["rule_type"] == "기타" and r["manual_type"] == "주거형")
top_e, top_f = eld[:30], fac[:20]
d35 = {int(k): int(v) for k, v in H35["ge35_jun_sep"].items()}
d35_other = [v for y, v in d35.items() if y != 2025]
normal = statistics.mean(hw[y] for y in range(1991, 2021))
mean_recent = statistics.mean(hw[y] for y in range(2016, 2026))
hw2425 = (min(hw[2024], hw[2025]), max(hw[2024], hw[2025]))
daily25 = S["daily_mean_by_year"]["2025"]
rent_total = CS["rent_total"]
mean35, mean2730 = S["tbin_means"][">=35"], S["tbin_means"]["27-30"]
oos, cf = S["oos_2026"], S["counterfactual_2025"]
rob_by = {r["spec"]: r for r in rob}
rob_ctrl = [float(r["ge35_pct"]) for r in rob if r["spec"] not in ("기준 구간 30~33℃", "일조·습도 제외")]
n_full, n_full_master, n_list = EL["n_full_operation"], EL["n_full_in_master"], EL["n_full_in_master_with60"]
hot_days = SS["2025"]["hot_days"]
n_hot_late = sum(1 for d in hot_days if "2025-07-25" <= d <= "2025-08-01")   # 7월 말~8월 초
sens_vals = [SEN["ref_late"]["60+"], SEN["mid_window"]["60+"]]
fam60 = [0, 0]
for r_ in DHP:
    if r_["age"] in ("60대", "70대이상"):
        fam60[1] += int(r_["rent"])
        fam60[0] += int(r_["rent"]) if r_["pass"] == "가족권" else 0
fam60_pct = 100 * fam60[0] / fam60[1]
ab_rent60 = sum(float(r["rent_per_day_hot"]) for r in ab if r["agegrp"] == "60+")
vtxt = (RES / "verification.md").read_text(encoding="utf-8") if (RES / "verification.md").exists() else ""
mv = re.search(r"(\d+)개 항목 중 불일치 (\d+)개\. 입력 구분: 원자료 (\d+)개, 집계 파일 (\d+)개, 결과 파일\(독립 아님\) (\d+)개", vtxt)
n_verify, n_verify_bad, n_raw, n_proc, n_dep = (int(x) for x in mv.groups()) if mv else (0, 0, 0, 0, 0)
# 문장의 범위·비교 표현이 재계산값과 맞는지 확인(맞지 않으면 빌드를 멈춘다)
assert 10 <= abs(T35["pct"]) <= 20 and all(10 <= v <= 20 for v in mod_old), "요약 '10~20% 줄지만' 범위 불일치"
assert gap_min == 6 and A60["hot_min_per_trip"] - A2050["hot_min_per_trip"] < 7, "요약 '청장년층보다 6분 길다' 불일치"
assert GU4 == "강서·영등포·송파·노원" and {r["gu"] for r in gu_ph[:4]} == set(top4), "자치구 네 곳(건수·명시간 모두 상위 4)"
assert max(ET["types"], key=ET["types"].get) == "역세권형" and 2 * ET["types"]["역세권형"] == 30, "'역세권 앞에 몰린다'·그림 B '절반'"
assert mean_recent / normal >= 2 and hw2425[0] / normal >= 3, "'평년의 두 배'·'세 배'"
assert d35[2024] == S["ge35_days"]["2024"] and d35[2025] == S["ge35_days"]["2025"] and all(1.7 <= d35[2025] / v <= 2.3 for v in d35_other), "'다른 두 해의 두 배 안팎'"
assert 1.8 <= mean35["sumSsHr"] / mean2730["sumSsHr"] <= 2.3, "3.2 일조 '두 배'"
assert min(r60_mid) == HRS["60+"]["min_ratio"] and HRS["60+"]["min_hour"] in range(12, 17), "'12~16시에 가장 낮다'"
assert abs(PS["정기권"]["pct"]) < abs(PS["일일권"]["pct"]) / 2, "'그 절반에 못 미친다'"
assert 24 <= A60["hot_min_per_trip"] < 25, "6.4 '25분 가까이'"
assert fam60_pct < 0.1 and abs(ab_rent60 - A60["hot_rent_per_day"]) < 0.5, "주 1 가족권 비중, 표 A 하루 대여"
assert n_hot_late == 5 and S33["ratio60"] > P60["ratio_hot_ref"], "3.3 '여덟 날 중 다섯 날', 33℃ 경계"
TITLE = "따릉이는 폭염에 멈추지 않는다: 서울 공공자전거 3,600만 건으로 본 고령 이용자의 생활 이동과 폭염 노출"
SUBTITLE = "시간대별·연령별·이용권별 이용 집계와 기상청 서울 관측 자료의 결합 (2024·2025년 여름, 2026년 6월)"
RUNNING = "따릉이는 폭염에 멈추지 않는다: 고령 이용자의 생활 이동과 폭염 노출"


def sec(num, title):
    return f'<h2><span class="num">{num}.</span>{title}</h2>'


def fig(cls, src, cap):
    return f'<figure class="{cls}"><img src="{src}" alt=""><figcaption>{cap}</figcaption></figure>'


FN = lambda k: f'<sup class="fn">{k})</sup>'  # noqa: E731

# ------------------------------------------------------------------ 요약 (기준_요약문.md ⑤ v5 문단, 수치만 재계산값)
ABSTRACT = (f"서울의 공공자전거 따릉이는 탄소중립 수단으로 알려져 있지만, 60대 이상 이용자의 쓰임새는 동네 생활 교통수단으로 읽힌다. "
            f"이들의 이용은 {P60['ref_seasonal_pass_pct']:.0f}%가 정기권이고, 한 번에 {P60['ref_km_per_trip']:.1f}km를 {int(P60['ref_min_per_trip'])}분 넘게 천천히 달리며, 아침과 저녁에 봉우리가 있고 낮에도 고르게 이어진다. "
            f"폭염은 이 이동을 멈추게 하지 못한다. 일조와 습도를 통제하면 최고기온 35℃ 이상인 날의 따릉이 이용은 전체도 고령 이용자도 10~20% 줄지만, "
            f"고령 이용자는 그래도 평일 하루 {int(A60['hot_rent_per_day'] // 100 + 1) * 100:,}번 가까이 타고 한 번의 노출이 청장년층보다 {gap_min}분 길다. "
            f"그들은 아침 6~7시 이용은 그대로 두고 낮 12~16시에 가장 많이 줄인 뒤 밤 8시 이후 다시 타는 방식으로 더위에 맞춘다. "
            f"그 결과 폭염 평일 하루 낮 시간 노출만 {int(A60['hot_day_ph_per_day'] // 100) * 100:,}명시간을 넘고, 이 노출은 자치구로는 {GU4}에, 대여소로는 역세권 앞에 몰린다. "
            f"서울의 폭염일수는 최근 10년 평균 {mean_recent:.1f}일로 평년 {normal:.1f}일의 두 배를 넘는다. "
            f"따라서 공공자전거의 폭염 대책에는 고령 교통약자의 생활 이동을 지키는 조치가 들어가야 한다. "
            f"노출이 몰리는 자치구와 대여소부터 그늘·급수·안전 안내를 두고, 폭염특보 때 낮 이동을 이른 아침이나 밤 8시 이후로 옮기도록 안내하며, 고령 정기권 이용자에게 맞춘 메시지를 보내는 것이다. "
            f"그 우선 대여소와 자치구 목록, 그리고 고령 이용이 많은 생활시설형 대여소 목록을 제시한다.")
KEYWORDS = "공공자전거, 고령 교통약자, 폭염 노출, 기후적응, 생활 교통"

titleblock = f"""
<div class="titleblock">
  <h1>{TITLE}</h1>
  <div class="subtitle">{SUBTITLE}</div>
  <div class="authors">{LEAD} ({TEAM})</div>
  <div class="meta">제출일 2026년 10월 22일 · 「AI와 함께하는 교통문제 해결을 위한 데이터 분석 공모전」 분석보고서 · 분석 코드: {GIT}</div>
  <div class="teamline">팀명: {TEAM} | 주제: {TITLE}</div>
</div>
<div class="abstract"><b>요약</b>&nbsp; {ABSTRACT}</div>
<div class="keywords"><b>핵심어</b>&nbsp; {KEYWORDS}</div>
"""

# ------------------------------------------------------------------ 1절
sec1 = f"""
{sec(1, '분석 배경 및 목적')}
<p>이 분석은 폭염이 서울 고령 이용자의 따릉이 이용을 어떻게 바꾸는지 재어 우선 대응 대여소 목록을 만든다. 폭염일수(최고기온 33℃ 이상인 날 수)는 2024·2025년에 평년의 세 배를 넘었다(5.1절)[4]. 확인한 범위에서 기존 자료·연구[5][11]는 날씨로 수요를 예측했고 자료에 연령 변수는 없다. 그래서 '고령 이용자는 어떻게 타고 더위에 어떻게 맞추나', '노출은 어디에 남나'에 답한다.</p>
<p>서울을 고른 이유는 시간·연령·이용권별 집계가 달 단위 파일로 공개되기 때문이다(반년마다 갱신)[1]. 따릉이는 서울시가 운영하는 공공자전거이며, 2025년 여름 이용은 하루 {daily25 / 10000:.0f}만 건이었다[1]. 이용 집계가 건마다 탄소 절감량을 기록할 만큼 따릉이는 탄소 감축 수단으로 다뤄진다[1]. 분석 기간은 집계가 공개된 2024·2025년 여름과 2026년 6월이다.</p>
<p>시급성의 근거는 고령층의 취약성이다. 온열질환 응급실감시에서 2025년 환자의 {EXT['heat25_old']}%는 노년층이었다[9]. 환자의 {EXT['heat25_out']:.1f}%가 실외에서 생겼고 14~17시에 몰렸다[9]. 2026년에는 노년층 비중이 {EXT['heat26_old']:.1f}%로 커졌다[10].{FN(1)}</p>
"""

# ------------------------------------------------------------------ 2절
sec2 = f"""
{sec(2, '활용 데이터')}
<p>이 절은 활용 자료와 수집 방법을 밝힌다. 자료는 표 1의 네 가지이며 공식 다운로드 파일과 공식 API, 화면 조회 요청으로 받았다. 이용 집계는 아홉 달 3,600만 건({n(rent_total)}건)이다[1]. 기상은 서울 관측소 한 곳의 일자료라 시간 단위 기온은 쓰지 못했다[3].</p>
<p class="tcap">표 1. 활용 데이터</p>
<table class="three small flow">
<colgroup><col style="width:20%"><col style="width:9%"><col style="width:10%"><col style="width:19%"><col style="width:10%"><col style="width:13%"><col style="width:19%"></colgroup>
<thead><tr><th>활용 데이터</th><th>제공기관</th><th>출처 플랫폼</th><th>URL</th><th>기준시점</th><th>라이선스 · 수집 방법</th><th>선정 이유 · 한계</th></tr></thead>
<tbody>
<tr><td>서울시 공공자전거 따릉이 이용정보(시간대별): 일자·시간·대여소·이용권·성별·연령대·건수·거리·시간 [1]</td><td>서울특별시 자전거PM과</td><td>서울 열린데이터광장 OA-15245</td><td class="url">{url_wbr('data.seoul.go.kr/dataList/OA-15245/F/1/datasetView.do')}</td><td>2024-06~09, 2025-06~09, 2026-06</td><td>공공누리 1유형 · 월별 CSV 9개 파일 다운로드</td><td>날·시간·대여소·연령·이용권 묶음 집계. 2025-06 파일은 이용시간 열 없음{FN(1)}</td></tr>
<tr><td>서울시 공공자전거 따릉이 대여소 정보: 번호·이름·자치구·위경도 [2]</td><td>서울특별시 자전거PM과</td><td>서울 열린데이터광장 OA-13252</td><td class="url">{url_wbr('data.seoul.go.kr/dataList/OA-13252/F/1/datasetView.do')}</td><td>2026-06</td><td>공공누리 1유형 · XLSX</td><td>{n(CS['stations_master'])}곳의 좌표·자치구. 2026-06 목록에 없는 {CS['stations_in_rentals_without_master']}곳(폐쇄·번호 변경 추정; 비교 기간 전일 운영 대여소 중 {n_full - n_full_master}곳)은 지도·목록에서 뺌</td></tr>
<tr><td>기상청_지상(종관, ASOS) 일자료 조회서비스: 서울(108) 기온·강수·습도·일조 [3]</td><td>기상청</td><td>공공데이터포털 오픈API</td><td class="url">{url_wbr('data.go.kr/data/15059093/openapi.do')}</td><td>2024·2025년 6~9월, 2026-06-01~10-19</td><td>공공누리 1유형 · API(인증키)</td><td>일 단위라 시간별 기온은 없음. 2025-09-13 일조 결측</td></tr>
<tr><td>기후통계분석 &gt; 기상현상일수 &gt; 폭염일수(지점 서울 108) [4]</td><td>기상청</td><td>기상자료개방포털</td><td class="url">{url_wbr('data.kma.go.kr/climate/heatWave/selectHeatWaveChart.do')}</td><td>1973~2026 (10/21 조회)</td><td>출처 표시 · 화면 조회와 같은 POST 1회로 표 저장</td><td>폭염 추세. 2026년은 연중 미완</td></tr>
</tbody>
</table>
<p class="tnote">주: 선행 자료로 UCI 저장소의 「Seoul Bike Sharing Demand」[5]와 그 자료로 날씨 기반 수요 예측 모형을 만든 논문[11]을 확인했다. 공휴일은 「관공서의 공휴일에 관한 규정」[6]과 인사혁신처 안내[7]로 정했다(주 2). 대괄호 번호는 7절 참고문헌, URL은 https://를 생략했다.</p>
"""

# ------------------------------------------------------------------ 3절
sec3 = f"""
{sec(3, '분석과정 및 방법')}
<h3>3.1 여섯 단계로 집계·기상·달력 자료를 하나로 묶었다</h3>
{fig('flow', f'{FG}/fig1_flow.png', '<b>그림 1.</b> 분석 흐름 여섯 단계. 상자 제목 옆 숫자는 그 단계를 맡은 코드 번호다.')}
<p>분석은 그림 1의 여섯 단계로 진행했다. 월 파일 아홉 개는 열 이름을 통일해 읽었다. 이용권은 세 종류(정기권·일일권·가족권), 연령대는 여덟 종류로 두었다.{FN(1)} 일 총량과 시간대·연령·이용권별, 대여소별 집계를 만들어 기상·달력 변수와 붙였다. 공휴일은 규정의 공휴일[6]과 임시공휴일[7]로 정했다.{FN(2)}</p>
<p>'폭염 평일'은 최고기온 35℃ 이상인 평일이며 기상청 폭염일수(33℃ 이상)와 다르다. 33~35℃인 날의 감소는 작고 뚜렷하지 않아(주 3) 35℃를 경계로 삼았다. '비교 평일'은 27~33℃인 평일이고, 식 (1)의 기준은 27~30℃인 날이다.</p>
<p>60대 이상은 '고령 이용자', 20~50대는 '청장년층'이라 부른다. 고령 이용자는 자료의 연령 구간을 따른 것이라 법령·통계의 65세 이상 기준과 다르다. '생활 이동'은 출퇴근·통원·장보기처럼 정해진 곳을 되풀이해 오가는 일상 이동 전체를 가리킨다. 이런 이동에 쓰는 수단을 '생활 교통수단'이라 부른다.</p>
<h3>3.2 일조와 습도를 통제해야 폭염 효과가 드러난다</h3>
<div class="eq"><span class="body">log(일 대여건수) = 기온 구간 + 강수 구간 + 주말 + 공휴일 + 월 + 연도 + 일조시간 + 평균습도 + 오차</span><span class="no">(1)</span></div>
<p>식 (1)은 일 대여건수의 로그를 기온·강수 구간과 달력·일조·습도 변수로 설명한다. 일조와 습도를 넣는 이유는 35℃ 이상인 날이 맑고 건조한 날이기도 해서다. 그런 날의 일조는 하루 {mean35['sumSsHr']:.0f}시간으로 27~30℃인 날의 두 배다[3]. 이를 빼면 맑은 날의 이용 증가가 폭염 효과를 가린다(5.1절). 연도 고정효과는 해마다 다른 이용 총량을 따로 흡수하는 항이다.</p>
<p>표본은 두 해 여름의 {M['n']}일이다.{FN(3)} 표준오차는 뉴이-웨스트 방식(날짜가 가까운 오차끼리의 상관을 감안한 방식)으로 구했다. 효과는 계수를 백분율 변화로 바꿔 기준 대비 차이로만 읽는다. 2026년 6월은 적합에 넣지 않고 표본 외 예측 검증에만 썼다. 같은 식을 시간대·연령·이용권별 일 집계에 적용해 하위 모형을 만들었다.</p>
<h3>3.3 고령 이용의 성격과 폭염 평일의 조정은 같은 해 안에서 원자료로 잰다</h3>
<div class="eq"><span class="body">유지 비율 = 폭염 평일의 일평균 대여건수 ÷ 비교 평일의 일평균 대여건수</span><span class="no">(2)</span></div>
<p>식 (2)의 비교는 2025년 7~8월 평일 중 비가 없고 공휴일이 아닌 날로 한정했다. 폭염 평일 {NH}일과 비교 평일 {NR}일을 같은 해 여름 안에서 견주었다. 폭염 평일 {KNUM[NH]} 날 중 {KNUM[n_hot_late]} 날이 7월 말~8월 초여서 방학·휴가철이 섞일 수 있다. 비교 기간을 좁혀도 고령 이용자의 유지 비율은 {J(f'{min(sens_vals):.2f}~{max(sens_vals):.2f}', '이다')}. 폭염 평일을 33℃ 이상으로 넓혀도 {J(f2(S33['ratio60']), '이다')}.{FN(4)}</p>
<p>이용 성격은 비교 평일에서 정기권 비율, 회당 거리·시간, 평균속도, 성별 구성, 시간별 비중으로 잰다.{FN(8)} 노출 시간은 이용시간(분)의 합을 60으로 나눈 명시간이고 낮은 10~19시다. 대여소 유형은 이름 낱말로 추정한 다섯 종류다.{FN(7)} 대여소 목록에는 전일 운영 대여소 {n(n_full)}곳 중 대여소 정보와 고령 이용 기록이 있는 {n(n_list)}곳만 썼다.{FN(4)}</p>
"""

# ------------------------------------------------------------------ 4절
sec4 = f"""
{sec(4, 'AI 기술 활용')}
<p>이 절은 AI를 어디에 썼고 무엇을 사람이 맡았는지 밝힌다. 사용 서비스는 Claude Code(Anthropic)이다. 모델은 Claude Fable 5.1이며 검토 반영 일부는 Claude Opus 5.5다. 활용 범위는 주제 선정(후보 비교와 자료 확보 여부 점검)과 데이터 탐색이다. 수집·집계·회귀·시각화·검증 코드와 보고서 초안, 저장소 문서도 AI가 작성했으며 머신러닝은 쓰지 않았다. 보고서 전수 검토도 별도의 AI 작업자가 세 차례 맡았다.</p>
<p>참가자는 분석 축과 요약문을 정하고 검증표의 표본 수치와 최종 문안을 직접 확인한다(제출 전). AI가 작성한 검증표는 수치 {n_verify}개를 다른 코드로 다시 계산했고 불일치는 {n_verify_bad}개였다. 그중 {n_raw}개는 원자료에서, 나머지는 집계·결과 파일에서 계산했다.{FN(6)} 개인정보나 비공개 자료는 입력하지 않았고 프롬프트 원문은 주 5에 적었다.</p>
"""

# ------------------------------------------------------------------ 5절
prof_rows = ""
for key, label in [("20대", "20대"), ("40대", "40대"), ("60대", "60대"), ("70대이상", "70대 이상"), ("60+", "고령 이용자(60대 이상)"), ("20-50대", "청장년층(20~50대)")]:
    r = prof[key]
    prof_rows += (f'<tr><td>{label}</td><td class="num">{float(r["ref_seasonal_pass_pct"]):.0f}</td><td class="num">{float(r["ref_km_per_trip"]):.2f}</td>'
                  f'<td class="num">{float(r["ref_min_per_trip"]):.1f}</td><td class="num">{float(r["ref_kmh"]):.1f}</td><td class="num">{float(r["ref_male_pct"]):.0f}</td>'
                  f'<td class="num">{float(r["ref_rent_per_day"]):,.0f}</td><td class="num">{float(r["ratio_hot_ref"]):.2f}</td></tr>')
al = EL["profile_all_ref"]
prof_rows += (f'<tr><td>전체</td><td class="num">{al["seasonal_pass_pct"]:.0f}</td><td class="num">{al["km_per_trip"]:.2f}</td><td class="num">{al["min_per_trip"]:.1f}</td>'
              f'<td class="num">{al["kmh"]:.1f}</td><td class="num">{al["male_pct"]:.0f}</td><td class="num">{al["rent_per_day"]:,.0f}</td><td class="num">{ratio_all:.2f}</td></tr>')
types_by_med = sorted(TS, key=lambda t: float(TS[t]["median_ratio"]))
assert types_by_med[0] == "공원·강변형" and types_by_med[-1] == "주거형", "5.4 '공원·강변형이 가장 크게 꺾인다', '주거형은 가장 높다'"
assert P60["ref_km_per_trip"] > P2050["ref_km_per_trip"], "5.2 '청장년층보다 거리가 길다'"
assert f"{min(mod_old):.0f}" == f"{max(mod_old):.0f}", "5.4 '고령 이용자 14%'(60대·70대 이상 같은 값)"
mod_old_txt = f"{min(mod_old):.0f}%"
young_raw_txt = J(f"청장년층({min(raw_young):.2f}~{max(raw_young):.2f})", "과")
gu_rest = "·".join(g[:-1] for g in top4[1:])

sec5 = f"""
{sec(5, '분석 내용 및 결과')}
<p>이 절은 발견 다섯 가지를 효과, 성격, 조정, 노출과 대비, 장소 순으로 보인다. 고령 이용자는 폭염 평일에도 하루 {n(A60['hot_rent_per_day'])}번을 탄다. 한 번에 {A60['hot_min_per_trip']:.1f}분을 타 청장년층보다 {gap_min}분 길다. 그래서 낮 노출이 하루 {n(A60['hot_day_ph_per_day'])}명시간 남고, 이 노출은 {J(GU4, '과')} 역세권 대여소에 몰린다.</p>
<h3>5.1 최근 10년 폭염일수는 평년의 두 배를 넘고 35℃ 이상인 날의 이용은 {a(T35['pct'])}% 적다</h3>
{fig('wide', f'{FG}/fig2_heat_effects.png', f'<b>그림 2.</b> 폭염일수는 최근 10년 평균이 평년의 두 배를 넘고, 일조·습도를 통제해야 35℃ 이상인 날의 감소가 드러난다. (a) 서울 폭염일수(막대)와 35℃ 이상인 날(마름모, 6~9월)[3][4], (b) 최고기온·강수 구간별 효과(95% 신뢰구간, 기준 27~30℃·무강수)[1][3].')}
<p class="noindent">서울 폭염일수의 평년값은 {normal:.1f}일이다[4]. 최근 10년 평균은 {J(f'{mean_recent:.1f}일', '으로')} 그 두 배를 넘는다[4]. 2024·2025년은 {J(f'{hw2425[0]:.0f}~{hw2425[1]:.0f}일', '으로')} 평년의 세 배를 넘었다[4]. 이 보고서가 따로 세는 35℃ 이상인 날(6~9월)은 해마다 크게 오르내린다[3]. 2025년은 {J(f'{d35[2025]}일', '으로')} 다른 두 해의 두 배 안팎이다(그림 2(a)).</p>
<p>일조와 습도를 통제하면 35℃ 이상인 날의 이용은 {a(T35['pct'])}% 적다(그림 2(b)). 통제하지 않으면 그 차이는 {a(N35['pct'], 1)}%에 그쳐 드러나지 않는다. 35℃ 이상인 날은 맑고 건조해 맑은 날의 이용 증가가 효과를 가리기 때문이다. 비가 20mm를 넘는 날의 이용은 {a(R20['pct'])}% 적어 비가 더 큰 변수다.{FN(3)}</p>
<h3>5.2 고령 이용자는 정기권으로 {P60['ref_km_per_trip']:.1f}km를 {int(P60['ref_min_per_trip'])}분 넘게 천천히 탄다</h3>
<p>고령 이용자는 정기권으로 비교적 먼 거리를 천천히 탄다. 이용의 {P60['ref_seasonal_pass_pct']:.0f}%가 정기권이다(표 2). 한 번에 {P60['ref_km_per_trip']:.1f}km를 {int(P60['ref_min_per_trip'])}분 넘게 타 청장년층보다 거리가 길다. 평균 시속은 {P60['ref_kmh']:.1f}km로 청장년층의 {P2050['ref_kmh']:.1f}km보다 느리다.{FN(8)}</p>
<p>시간 분포는 정해진 곳을 오가는 이동으로 읽힌다. 60대는 아침·저녁에 봉우리가 있고 70대 이상은 봉우리와 낮의 차이가 작다(그림 3). 유형 구성은 청장년층과 거의 같고 역세권형이 {J(f"{TC['60+']['역세권형']:.0f}%", '으로')} 가장 많다(기타 {TC['60+']['기타']:.0f}% 제외).</p>
<p>이런 모양은 생활 교통수단으로 읽힌다. 60대의 아침·저녁 봉우리에는 출퇴근이 섞여 있을 수 있다. 2025년 60~64세 고용률은 {J(f"{EXT['emp6064']:.1f}%", '이다')}[8]. 출퇴근이든 통원이든 폭염 속에도 미루기 어려운 이동으로 읽힌다.</p>
{fig('wide', f'{FG}/fig3_profile.png', f'<b>그림 3.</b> 60대는 아침과 저녁에 봉우리가 있고 70대 이상은 봉우리와 낮 시간의 차이가 작으며, 대여소 유형 구성은 청장년층과 거의 같다. (a) 연령대별 시간별 이용 비중(비교 평일 {NR}일), (b) 60대 이상과 20~50대의 대여소 유형 구성(추정)[1][2][3].')}
<p class="tcap">표 2. 연령대별 이용 성격 (2025년 7~8월 비교 평일 {NR}일, 원자료 집계)</p>
<table class="three small">
<thead><tr><th>연령대</th><th>정기권<br>비율(%)</th><th>회당 거리<br>(km)</th><th>회당 시간<br>(분)</th><th>평균속도<br>(km/h)</th><th>남성<br>비율(%)</th><th>하루 대여<br>(건/일)</th><th>폭염 평일÷<br>비교 평일</th></tr></thead>
<tbody>{prof_rows}</tbody>
</table>
<p class="tnote">주: 평균속도 = 이동거리 합 ÷ 이용시간 합(정차 포함, 주 8). 남성 비율의 분모에는 성별 미상(고령 이용자 {P60['ref_sex_unknown_pct']:.0f}%)이 포함된다. 20·40대는 청장년층의 예다. 자료 [1][3].</p>
<h3>5.3 폭염 평일에 고령 이용자는 아침을 지키고 낮을 더 깊게 비운 뒤 밤 8시 이후 돌아온다</h3>
<p>고령 이용자는 아침 이용을 지키고 낮을 더 깊게 비운 뒤 밤 8시 이후 돌아온다. 아침 6~7시 비율은 {J(f2(HRS['60+']['06-07']), '으로')} 날짜 간 변동 안에서 평소와 같다(그림 4). 이후 줄기 시작해 12~16시에 {J(f'{r60_mid[0]:.2f}~{r60_mid[1]:.2f}', '으로')} 가장 낮다. 저녁 봉우리인 17~18시도 {J(f'{r60_eve[0]:.2f}~{r60_eve[1]:.2f}', '으로')} 줄어든다. 밤 8시에는 {J(f2(HRS['60+']['20']), '으로')} 평소 수준에 돌아온다.{FN(8)}</p>
<p>청장년층과 견주면 고령 이용자의 낮 감소는 더 깊고 저녁 이후 회복은 더 온전하다. 청장년층의 낮 바닥은 {J(f'{ry_mid[0]:.2f}~{ry_mid[1]:.2f}', '이다')}. 밤 8시에도 청장년층은 {f2(HRS['20-50대']['20'])}에 머문다.</p>
{fig('wide', f'{FG}/fig4_adjust.png', f'<b>그림 4.</b> 고령 이용자는 아침 6~7시 이용을 지키고 12~16시에 가장 많이 줄인 뒤 밤 8시(20시) 이후 돌아온다. (a) 시간별 유지 비율(굵은 선은 고령 이용자와 청장년층, 연한 선은 연령대), (b) 60대 이상의 시간별 대여건수; 폭염 평일 {NH}일과 비교 평일 {NR}일[1][3].')}
<h3>5.4 폭염 평일에도 고령 이용은 대부분 남고 하루 {int(A60['hot_day_ph_per_day'] // 100) * 100:,}명시간이 넘는 낮 노출이 생긴다</h3>
<p>폭염 평일에도 고령 이용은 대부분 남는다. 폭염 평일 {NH}일 평균으로 고령 이용자는 하루 {n(A60['hot_rent_per_day'])}번을 탔다(부록 표 A). 비교 평일 대비 비율은 {J(f2(P60['ratio_hot_ref']), '으로')} 전체 {J(f2(ratio_all), '과')} 같은 수준이다. 모형으로 잰 감소는 고령 {mod_old_txt}, 청장년층 {min(mod_young):.0f}~{max(mod_young):.0f}%로 신뢰구간이 겹친다(그림 5(a)). 원시 비율로도 {young_raw_txt} 비슷하다. 어느 기준이든 핵심은 감소폭이 아니라 남는 양과 한 번의 길이다.</p>
<p>고령 이용자는 거리가 길고 속도가 느려 한 번의 노출이 길다. 폭염 평일에는 한 번에 {A60['hot_min_per_trip']:.1f}분을 타 청장년층보다 {gap_min}분 길다. 그래서 낮 시간 노출은 하루 {n(A60['hot_day_ph_per_day'])}명시간으로 전체의 {J(f"{A60['hot_day_share_pct']:.1f}%", '이다')}. 이는 건수 비중 {share60_rent:.1f}%보다 크다.</p>
<p>감소는 일일권처럼 미룰 수 있는 이용으로 보이는 쪽에서 크다. 35℃ 이상인 날의 하위 모형에서 일일권 이용은 {a(PS['일일권']['pct'])}% 적다(그림 5(a)). 정기권은 {a(PS['정기권']['pct'])}% 적어 그 절반에 못 미친다. 고령 이용은 {P60['ref_seasonal_pass_pct']:.0f}%가 정기권이어서 일일권의 큰 감소와는 거리가 멀다.</p>
<p>대여소로 봐도 공원·강변처럼 여가 이용이 많을 법한 곳이 더 크게 줄었다. 대여소 {n(SS['2025']['n'])}곳의 전체 이용 유지 비율은 중앙값이 {J(f2(SS['2025']['median_ratio']), '이다')}.{FN(4)} 유형 가운데 공원·강변형이 {J(f2(TS['공원·강변형']['median_ratio']), '으로')} 가장 크게 꺾인다(부록 그림 A). 주거형은 {J(f2(TS['주거형']['median_ratio']), '으로')} 가장 높고 생활시설형은 {J(f2(TS['생활시설형']['median_ratio']), '이다')}. 다섯 유형의 차이는 작지만 통계적으로 뚜렷하다.{FN(7)}</p>
{fig('wide', f'{FG}/fig5_who.png', f'<b>그림 5.</b> 35℃ 이상인 날 일일권은 크게 줄고 정기권은 조금 줄며, 고령 이용자는 한 번에 길게 타 낮 노출 시간이 하루 {n(A60["hot_day_ph_per_day"])}명시간이다. (a) 이용권·연령대별 하위 모형의 35℃ 이상 효과, (b) 2025년 폭염 평일 {NH}일의 연령군×시간대 노출 시간(부록 표 A)[1][3].')}
<h3>5.5 고령 이용은 {J(GU4, '과')} 역세권 대여소에 몰린다</h3>
<p>고령 이용자의 낮 이용은 네 자치구와 역세권 대여소에 몰린다. {J(top4[0], '이')} 하루 {J(n(gu_eld[0]['eld_day_hot_per_day']) + '건', '으로')} 가장 많고 {J(gu_rest, '이')} 뒤따른다(그림 6). 네 구가 25개 구 합계의 {J(f"{GU['top4_eld_day_share_pct']:.0f}%", '을')} 차지한다. 명시간으로 세도 같은 네 구가 상위이며 합계의 {J(f'{top4_ph_share:.0f}%', '이다')}.</p>
<p>대여소로는 상위 30곳 중 {ET['types'].get('역세권형', 0)}곳이 역세권형이다(부록 표 B·그림 B). 역세권형은 전체 대여소의 {st_share:.0f}%라 이 쏠림은 뚜렷하다. 고령 이용이 많은 생활시설형 대여소 목록은 따로 제시한다(부록 표 C).</p>
{fig('wide', f'{FG}/fig6_where.png', f'<b>그림 6.</b> 고령 이용자의 낮 이용은 {GU4}에 몰리고 상위 대여소는 역세권형이 많다. (a) 자치구별 60대 이상 낮(10~19시) 대여 상위 12(25개 구는 부록 표 D), (b) 60대 이상 대여 상위 12 대여소; 괄호는 유지 비율, 폭염 평일 {NH}일 평균[1][2][3].')}
"""

# ------------------------------------------------------------------ 6절
sec6 = f"""
{sec(6, '정책제안 및 기대효과')}
<p>이 절의 제안 다섯 가지는 각각 5절의 어느 발견에서 나왔는지 밝힌다. 적용 대상은 서울시 자전거 부서와 운영 기관, 자치구다. 구체 지점은 부록 표 B·C와 그림 6이다.</p>
<h3>6.1 ① 노출이 몰리는 자치구와 대여소부터 안전 안내를 두고 그늘·급수를 잇는다 (단기·중기)</h3>
<p>5.5절의 발견에 따라 {J(GU4, '과')} 고령 이용 상위 30곳을 첫 대상으로 둔다. 폭염 안내판과 안내 문자는 즉시 시작할 수 있다. 거치대 위 그늘막과 급수대는 다음 예산에 반영한다. 이용이 유지되는 곳이라 효과가 이용자에게 닿을 가능성이 크며, 설치 적지는 현장 확인이 먼저다.</p>
<h3>6.2 ② 폭염특보 때 고령 정기권 이용자에게 이동 시간대 안내를 보낸다 (단기)</h3>
<p>5.3절의 발견에 따라 폭염특보가 내린 날 고령 정기권 회원에게 앱·문자로 낮 이동 자제를 안내한다. 온열질환자가 14~17시에 몰린다는 점도 낮 이동을 줄일 근거다[9]. 고령 이용자가 이미 지키는 이른 아침(6~7시)을 먼저 권한다. 밤 8시 이후는 야간 안전 안내와 함께 권한다. 분석 기준은 35℃ 이상인 날이라 특보일 전체로 넓히면 낮 이용 감소 폭이 이보다 작을 수 있다. 효과는 시간별 비율 곡선으로 이듬해 평가할 수 있다.</p>
<h3>6.3 ③ 고령 이용이 많은 생활시설형 대여소를 정비한다 (중기)</h3>
<p>5.5절의 목록에 따라 생활시설형 대여소 20곳(부록 표 C)의 그늘과 거치 환경을 정비한다. 구청·주민센터·도서관·보건소 앞은 관리 주체가 공공이라 협의 상대가 분명하다. 마트 같은 민간 시설 앞은 운영자와 따로 협의한다.</p>
<h3>6.4 ④ 고령 이용자에게 폭염 안전 수칙과 이용 시간 안내를 준다 (단기)</h3>
<p>5.4절의 발견에 따라 고령 회원에게 폭염특보일 대여 시 안전 수칙을 띄운다. 폭염 평일에도 한 번에 {math.ceil(A60['hot_min_per_trip'])}분 가까이 타므로 중간 휴식과 급수를 권한다. 노출 시간이 주는지는 이용시간 집계로 확인한다.</p>
<h3>6.5 ⑤ 공공자전거를 기후적응 계획에서 다루고 같은 집계를 공개하는 도시로 넓힌다 (장기)</h3>
<p>5.1절과 5.4절의 발견에 따라 공공자전거를 폭염 대책과 기후적응 계획에서 다룰 시설로 제안한다. 폭염이 잦고 고령 이용은 폭염 평일에도 대부분 남으므로 노출 관리가 계획에 들어가야 한다. 다른 도시로 넓히는 조건은 시간대·연령·이용권별 집계의 공개 하나다. 코드를 공개 저장소({GIT})에 두어 자료만 바꾸면 그대로 돌아가게 했다.</p>
<h3>6.6 한계: 공공자전거만 보았고 목적은 추론이며 두 여름의 관찰이다</h3>
<p>첫째, 공공자전거만 보았으므로 개인 자전거나 도보 노출은 담지 못한다. 둘째, 연령은 가입자 기준이고 성별 결측이 많으며 이용 목적은 관측하지 못해 '생활 교통수단'은 추론이다. 셋째, 기온이 일 단위라 시간대별 효과는 하루 최고기온으로 잰 것이다. 넷째, 두 여름의 관찰이며 효과는 상관이지 인과가 아니다. 다섯째, 명시간은 노출의 양이지 건강 영향 자체가 아니다. 여섯째, 대여소 유형은 이름으로 추정해 무작위 {rc_n}곳 대조에서 {rc_ok}곳만 맞았다(주 7). 다만 5.5절의 주장에 쓴 고령 이용 상위 {mc30_n}곳은 {mc30_ok}곳이 맞았다.</p>
"""

# ------------------------------------------------------------------ 7절 + 미주
_hol = []
for d_, v_ in CS["holidays_used"].items():
    v_ = f"임시공휴일, {v_.replace('(임시공휴일)', '')}" if "(임시공휴일)" in v_ else v_
    _hol.append(f"{d_}({v_})")
hol_txt = ", ".join(_hol)
rob_hol = float(rob_by["공휴일에 선거일 제외"]["ge35_pct"])
rob_sun_r = rob_by["일조 결측일(2025-09-13) 일조 0으로 대체"]
rob_sun = float(rob_sun_r["ge35_pct"])
rob30 = float(rob_by["기준 구간 30~33℃"]["ge35_pct"])
P60s, P70, P20, P30, P40, P50 = P["60대"], P["70대이상"], P["20대"], P["30대"], P["40대"], P["50대"]
sh70_mid = [SH["70대이상"][str(h)] for h in range(11, 16)]
pa_over = 100 * (oos["pred_sum"] / oos["actual_sum"] - 1)
TCM = EL["type_counts_master"]
# 주 7의 낱말 목록은 24_elderly.py 의 classify5 정규식에서 그대로 읽는다(규칙과 글이 어긋나지 않게)
_src24 = (ROOT / "code" / "24_elderly.py").read_text(encoding="utf-8")
KW = {t: p for p, t in re.findall(r'if re\.search\(r"([^"]+)", n\):\s+return "([^"]+)"', _src24)}
assert list(KW) == ["주거형", "공원·강변형", "역세권형", "생활시설형"], KW


def kw_txt(t):
    p = KW[t].replace("(?<!디지털)(?<!산업)(?<!공)단지", "단지(디지털·산업단지 제외)")
    return "·".join(p.split("|"))


sec7 = f"""
{sec(7, '분석도구 및 참고문헌')}
<p class="tools noindent"><b>분석도구.</b> Python 3.14.2, pandas 3.0.1, numpy 2.4.2, scipy 1.17.1, statsmodels 0.14.6, matplotlib 3.10.8, openpyxl 3.1.5, requests 2.32.5, PyMuPDF 1.27.2; PDF 렌더 Chrome headless. 코드·실행 순서·검증표는 {GIT} (code/00_download.py → 60_readability_check.py, results/verification.md).</p>
<p class="noindent" style="margin-top:4pt"><b>참고문헌</b></p>
<div class="refs"><ol>
<li><span class="lab">[1]</span>서울특별시, 「서울시 공공자전거 따릉이 이용정보(시간대별)」, 2024-06~09·2025-06~09·2026-06 월별 파일 9개(데이터 갱신 2026-07-15), 서울 열린데이터광장(OA-15245), https://data.seoul.go.kr/dataList/OA-15245/F/1/datasetView.do ({ACCESS}).</li>
<li><span class="lab">[2]</span>서울특별시, 「서울시 공공자전거 따릉이 대여소 정보」, 2026-06 기준, 서울 열린데이터광장(OA-13252), https://data.seoul.go.kr/dataList/OA-13252/F/1/datasetView.do ({ACCESS}).</li>
<li><span class="lab">[3]</span>기상청, 「기상청_지상(종관, ASOS) 일자료 조회서비스」(지점 서울 108), 2024·2025년 6~9월과 2026-06-01~10-19, 공공데이터포털 오픈API, https://www.data.go.kr/data/15059093/openapi.do ({ACCESS}).</li>
<li><span class="lab">[4]</span>기상청, 「기후통계분석 &gt; 기상현상일수 &gt; 폭염일수(지점 서울 108)」, 1973~2026, 기상자료개방포털, https://data.kma.go.kr/climate/heatWave/selectHeatWaveChart.do ({ACCESS}). 폭염일수 = 일최고기온 33℃ 이상인 날의 수.</li>
<li><span class="lab">[5]</span>UCI Machine Learning Repository, 「Seoul Bike Sharing Demand」(시간별 대여 수·기상·휴일, 8,760행, 2020-02-29 등록, CC BY 4.0), https://archive.ics.uci.edu/dataset/560/seoul+bike+sharing+demand (DOI 10.24432/C5F62R, {ACCESS}).</li>
<li><span class="lab">[6]</span>「관공서의 공휴일에 관한 규정」(대통령령 제36290호, 2026-04-30 일부개정, 2026-05-11 시행) 제2조, 국가법령정보센터, https://www.law.go.kr/법령/관공서의공휴일에관한규정 ({ACCESS}).</li>
<li><span class="lab">[7]</span>인사혁신처, 「공휴일 제도」 안내(임시공휴일은 정부가 수시로 지정), 인사혁신처 누리집, https://www.mpm.go.kr/mpm/info/infoService/BizService02 ({ACCESS}).</li>
<li><span class="lab">[8]</span>국가데이터처, 「고용률」(만 15~64세) 지표 해설의 연령별 고용률(2025년 기준, 최근갱신 2026-06-16), e-나라지표, https://www.index.go.kr/unify/idx-info.do?idxCd=4212 ({ACCESS}).</li>
<li><span class="lab">[9]</span>질병관리청 기후보건·건강위해대비과, 「폭염대비 온열질환 발생 감시 시작!」(2025년 온열질환 응급실감시체계 결과 수록), 2026-05-14 게시, 질병관리청 누리집, https://www.kdca.go.kr/bbs/kdca/42/311060/artclView.do ({ACCESS}).</li>
<li><span class="lab">[10]</span>질병관리청 기후보건·건강위해대비과, 「올해 온열질환자 8.8% 감소했지만 추정 사망자는 증가, 고령층 보호 강화 필요」(2026년 온열질환 응급실감시체계 결과), 2026-10-12 게시, 질병관리청 누리집, https://www.kdca.go.kr/bbs/kdca/42/312898/artclView.do ({ACCESS}).</li>
<li><span class="lab">[11]</span>Sathishkumar V E, Cho, Y. (2020). A rule-based model for Seoul Bike sharing demand prediction using weather data. European Journal of Remote Sensing, 53(sup1), 166–183. https://doi.org/10.1080/22797254.2020.1725789 (서지 정보는 Crossref 등록 메타데이터로 확인, {ACCESS}).</li>
</ol></div>
<p class="noindent" style="margin-top:6pt"><b>주</b></p>
<div class="notes">
<p>1) 이용정보[1]의 한 행은 날·시간·대여소·이용권·성별·연령대가 같은 대여의 묶음이며 이용건수·이동거리·이용시간은 그 합이다. 대여구분코드 다섯 가지는 괄호를 떼어 세 가지로 묶었고, 고령 이용자의 가족권 비중은 0.1% 미만이라 가입자와 탑승자가 다를 여지는 작다. 연령 '기타'(미상)는 2025년 폭염 평일 대여의 {TOT['etc_share_pct']:.1f}%로 연령 비교에서만 뺐다. 2025-06 파일에는 이용시간 열이 없어 성격·노출 분석은 7~8월만 쓴다. '하루 {daily25 / 10000:.0f}만 건'은 2025년 6~9월 일평균 {n(daily25)}건이다. [9][10]의 노년층은 65세 이상이라 이 보고서의 고령 이용자(60대 이상)와 범위가 다르다.</p>
<p>2) 공휴일은 규정 제2조의 공휴일[6]과 임시공휴일[7]로, {J(hol_txt, '이다')}. 주 모형 표본 안의 선거일은 2025-06-03 하나이며, 이를 공휴일에서 빼도 35℃ 이상 효과는 {rob_hol:+.1f}%로 거의 같다(부록 표 E).</p>
<p>3) 2025-09-13의 일조시간이 결측이라 주 모형은 {M['n']}일로 적합했다(주 모형 R²={M['r2']:.3f}; 일조를 0으로 대체하면 효과 {rob_sun:+.1f}%). 35℃ 이상 효과 {T35['pct']:+.1f}%의 95% 신뢰구간은 {T35['pct_lo']:+.1f}~{T35['pct_hi']:+.1f}%({pv(T35['p'])}), 33~35℃는 {T33['pct']:+.1f}%({pv(T33['p'])}), 30~33℃는 {T30['pct']:+.1f}%, 27℃ 미만은 {T27['pct']:+.1f}%다. 강수 효과는 20mm 초과 {R20['pct']:+.1f}%, 5~20mm {R5['pct']:+.1f}%, 5mm 이하 {R0['pct']:+.1f}%이고, 통제 전 35℃ 이상 효과는 {N35['pct']:+.1f}%({pv(N35['p'])})다. 일조·습도를 통제한 {len(rob_ctrl)}개 사양에서 35℃ 이상 효과는 {min(rob_ctrl):+.1f}~{max(rob_ctrl):+.1f}%였다(부록 표 E; 기준을 30~33℃로 바꾼 사양은 {rob30:+.1f}%). 하위 모형의 35℃ 이상 효과는 0~4시 {HB['00-04']['pct']:+.1f}, 5~9시 {HB['05-09']['pct']:+.1f}, 10~15시 {HB['10-15']['pct']:+.1f}, 16~19시 {HB['16-19']['pct']:+.1f}, 20~23시 {HB['20-23']['pct']:+.1f}%(10~15시·16~19시만 p&lt;0.05), 10대 이하 {AG['~10대']['pct']:+.1f}, 20대 {AG['20대']['pct']:+.1f}, 30대 {AG['30대']['pct']:+.1f}, 40대 {AG['40대']['pct']:+.1f}, 50대 {AG['50대']['pct']:+.1f}, 60대 {AG['60대']['pct']:+.1f}, 70대 이상 {AG['70대이상']['pct']:+.1f}%(모두 p&lt;0.01), 정기권 {PS['정기권']['pct']:+.1f}%, 일일권 {PS['일일권']['pct']:+.1f}%다. 연도별 모형은 2024년 {S['year']['2024']['tbin']['>=35']['pct']:+.1f}%({pv(S['year']['2024']['tbin']['>=35']['p'])}), 2025년 {S['year']['2025']['tbin']['>=35']['pct']:+.1f}%({pv(S['year']['2025']['tbin']['>=35']['p'])})다.</p>
<p>4) 대여소 유지 비율(식 2)은 비교 평일 평균 30건 이상이고 폭염 평일 전부와 비교 평일의 6분의 5 이상에 기록이 있는 {n(SS['2025']['n'])}곳에서 계산했고(없는 날은 0건), 유형 분석은 그중 대여소 정보에 있는 {n(E['type']['n'])}곳으로 했다. 폭염 평일은 {', '.join(d[5:].replace('-', '/') for d in SS['2025']['hot_days'])}, 비교 평일은 {', '.join(d[5:].replace('-', '/') for d in SS['2025']['ref_days'])}이다. 이 18일 전부에 기록이 있는 전일 운영 대여소는 {n(n_full)}곳이고, 그중 2026-06 대여소 정보에 있는 {n(n_full_master)}곳 가운데 60대 이상 이용 기록이 있는 {n(n_list)}곳을 지도·목록에 썼다. 방학·휴가철 혼재를 보려고 비교 평일을 7/21 이후 {len(SEN['ref_late_days'])}일로 줄이면 유지 비율은 고령 이용자 {f2(SEN['ref_late']['60+'])}, 전체 {J(f2(SEN['ref_late']['all']), '이다')}. 폭염 평일 {len(SEN['hot_mid_days'])}일과 비교 평일 {len(SEN['ref_mid_days'])}일을 7/21~8/11 안에서만 견주면 고령 이용자 {f2(SEN['mid_window']['60+'])}, 전체 {J(f2(SEN['mid_window']['all']), '이다')}. 폭염 평일을 최고기온 33℃ 이상인 평일 {S33['n_hot33']}일(33~35℃ {len(S33['mid_days'])}일 추가)로 넓히면 고령 이용자의 유지 비율은 {f2(S33['ratio60'])}, 낮 노출은 하루 {n(S33['day_ph60_per_day'])}명시간이다(35℃ 경계는 {f2(P60['ratio_hot_ref'])}, {n(A60['hot_day_ph_per_day'])}명시간). 방학 영향을 가늠하려고 본 10대 이하의 7시 비율은 {J(f2(SEN['teen_7h_ratio']), '이며')}, 방학 효과가 섞인 값이라 해석하지 않았다. 낮(10~19시)은 시간별 기온 자료가 없어 관행적으로 정한 구간이다. 2024년(폭염 평일 {len(SS['2024']['hot_days'])}일)으로 같은 비율을 구하면 중앙값 {f2(SS['2024']['median_ratio'])}, 2025년 비율과의 스피어만 상관은 {J(f"{f2(SS['consistency_2024_2025']['spearman_rho'])}(n={SS['consistency_2024_2025']['n_both']:,})", '이다')}.</p>
<p>5) 참가자가 AI에 준 지시 원문: "숲과나눔에서 주최하는 'AI와 함께하는 교통문제 해결을 위한 데이터 분석 공모전'의 주제로는 어떤 것들이 적합할까" / "(발췌) 예전 수상작들을 살펴봐서 이 대회가 원하는 작품의 느낌이 어떤건지 살펴보는것도 나쁘지 않을 것 같아. … 후보 4개를 선정해서 직접 병렬적으로 만들어가보면 어떨까?" / "(발췌) &lt;막차 이후의 도시&gt; 말고도 &lt;따릉이는 여름에 멈춘다&gt; 주제로도 사용가능한 데이터 살펴보고 보고해". 분석 결과를 본 뒤 참가자가 보고서의 축을 고령 생활교통 중심으로 정했다(원문: "좋아 그렇게 하자"). 이후 공통 규칙(BRIEF.md, 저장소에는 발췌본)·과제 명세(SPEC.md)·기준 요약문을 작업 지시문으로 썼고 저장소 docs/에 둔다. 명세의 요지는 공식 다운로드·API만 쓰고, 가상 데이터를 만들지 않으며, 숫자 문장을 계산과 대조하고, 결과를 방향과 무관하게 보고하라는 것이다.</p>
<p>6) 검증표(저장소 results/verification.md)는 수치 {n_verify}개를 다른 코드로 다시 계산했다(원자료 {n_raw}개, 집계 파일 {n_proc}개, 결과 파일을 그대로 읽은 항목 {n_dep}개). 표 E의 사양별 모형은 재적합하지 않았다. 2026년 6월 30일분의 표본 외 예측은 평균 절대 백분율 오차 {oos['mape']:.1f}%였고, 예측 합이 실제보다 {pa_over:.1f}% 많았다(로그 오차 평균 {oos['mean_log_err']:+.3f}). 그달에는 35℃ 이상인 날이 없어 폭염 효과 자체는 검증하지 못한다. 2025년 여름의 33℃ 이상인 {cf['hot_days']}일을 27~30℃로 바꾼 반사실 예측은 계절 총량의 {cf['loss_share_of_season_pct']:.1f}% 증가이며 보조 수치다.</p>
<p>7) 유형은 대여소 이름의 낱말로 추정했다(앞 규칙 우선). {kw_txt('주거형')} → 주거형, {kw_txt('공원·강변형')} → 공원·강변형, {kw_txt('역세권형')} → 역세권형, {kw_txt('생활시설형')} → 생활시설형(민간 매장 포함), 그 밖은 기타다. 대여소 정보 {n(CS['stations_master'])}곳은 역세권형 {TCM['역세권형']}, 주거형 {TCM['주거형']}, 생활시설형 {TCM['생활시설형']}, 공원·강변형 {TCM['공원·강변형']}, 기타 {TCM['기타']}곳이다. 규칙을 정할 때 본 {mc_n}곳(고령 이용 상위 30곳과 생활시설형 상위 20곳, 중복 제외)은 {mc_ok}곳({100 * mc_ok / mc_n:.0f}%)이 이름·좌표 대조와 맞았고 어긋난 {mc_n - mc_ok}곳은 안양천 변이었다. 그 밖의 대여소에서 무작위로 뽑은(pandas sample, random_state=2026, 저장소 code/25_type_random_sample.py) {rc_n}곳은 {rc_ok}곳({100 * rc_ok / rc_n:.0f}%)이 이름·주소 대조와 맞았고, 어긋난 {rc_n - rc_ok}곳 중 {rc_miss_etc}곳은 규칙이 기타로 둔 곳이다(그중 {rc_miss_etc_res}곳은 이름에 낱말이 없는 아파트). 두 대조는 AI 작업자가 했다(저장소 results/type_manual_check.csv·type_random_check.csv). 그래서 유형 결과는 보조 근거로만 쓴다. 비교 평일 대여의 유형 구성은 고령 이용자가 역세권형 {TC['60+']['역세권형']:.1f}·주거형 {TC['60+']['주거형']:.1f}·생활시설형 {TC['60+']['생활시설형']:.1f}·공원·강변형 {TC['60+']['공원·강변형']:.1f}·기타 {TC['60+']['기타']:.1f}%, 청장년층이 {TC['20-50대']['역세권형']:.1f}·{TC['20-50대']['주거형']:.1f}·{TC['20-50대']['생활시설형']:.1f}·{TC['20-50대']['공원·강변형']:.1f}·{TC['20-50대']['기타']:.1f}%다. 유형별 유지 비율 중앙값은 공원·강변형 {float(TS['공원·강변형']['median_ratio']):.3f}(n={TS['공원·강변형']['n']}), 생활시설형 {float(TS['생활시설형']['median_ratio']):.3f}({TS['생활시설형']['n']}), 기타 {float(TS['기타']['median_ratio']):.3f}({TS['기타']['n']}), 역세권형 {float(TS['역세권형']['median_ratio']):.3f}({TS['역세권형']['n']}), 주거형 {float(TS['주거형']['median_ratio']):.3f}({TS['주거형']['n']})다. 다섯 유형의 분포 차이는 크루스칼-월리스 검정(여러 집단의 분포가 같은지 보는 비모수 검정) {pv(E['type']['kruskal_p'])}, 공원·강변형 대 주거형은 맨-휘트니 검정 {pv(E['type']['park_vs_resid_mw_p'])}이다. 고령 이용 상위 30곳의 유형은 {', '.join(f"{k} {v}" for k, v in ET['types'].items())}곳이다.</p>
<p>8) 평균속도는 이동거리 합 ÷ 이용시간 합이며 정차·대기 시간이 포함돼 실제 주행 속도보다 낮다. 비교 평일 기준 60대 {P60s['ref_kmh']:.1f}km/h·{P60s['ref_min_per_trip']:.1f}분·{P60s['ref_km_per_trip']:.2f}km, 70대 이상 {P70['ref_kmh']:.1f}km/h·{P70['ref_min_per_trip']:.1f}분·{P70['ref_km_per_trip']:.2f}km, 20대 {P20['ref_kmh']:.1f}km/h·{P20['ref_min_per_trip']:.1f}분, 40대 {P40['ref_kmh']:.1f}km/h·{P40['ref_min_per_trip']:.1f}분이다. 폭염 평일÷비교 평일 원시 비율은 60대 {f2(P60s['ratio_hot_ref'])}, 70대 이상 {f2(P70['ratio_hot_ref'])}, 20대 {f2(P20['ratio_hot_ref'])}, 30대 {f2(P30['ratio_hot_ref'])}, 40대 {f2(P40['ratio_hot_ref'])}, 50대 {J(f2(P50['ratio_hot_ref']), '이다')}. 고령 이용자의 시간별 비율은 6~7시 {f2(HRS['60+']['06-07'])}(날짜별 {f2(DRR['06-07']['min'])}~{f2(DRR['06-07']['max'])}), 12~16시 {f2(r60_mid[0])}~{f2(r60_mid[1])}(날짜별 {f2(DRR['12-16']['min'])}~{f2(DRR['12-16']['max'])}), 20시 {f2(HRS['60+']['20'])}(날짜별 {f2(DRR['20']['min'])}~{f2(DRR['20']['max'])})다. 60대의 시간별 비중은 7시 {PK['60대_am']['7']:.1f}%·8시 {PK['60대_am']['8']:.1f}%·17시 {PK['60대_pm']['17']:.1f}%·18시 {PK['60대_pm']['18']:.1f}%이고, 70대 이상은 8시 {SH['70대이상']['8']:.1f}%·17시 {SH['70대이상']['17']:.1f}%이며 11~15시에도 {min(sh70_mid):.1f}~{max(sh70_mid):.1f}%다. {J('[8]', '은')} 만 15~64세 지표라 해설의 연령별 문장이 적은 '60대' 고용률 {EXT['emp6064']:.1f}%는 60~64세 값이다. '생활 교통수단'은 이 수치에서 읽어 낸 추론이며 이용 목적은 관측하지 않았다.</p>
</div>
"""


def eld_rows(rows, kind):
    out = []
    for i, r in enumerate(rows, 1):
        if kind == "e":
            out.append(f'<tr><td class="c">{i}</td><td class="c">{r["stn"]}</td><td>{r["name"].strip()}</td><td class="c">{r["gu"]}</td><td class="c">{r["type5"]}</td>'
                       f'<td class="num">{float(r["hot60_per_day"]):.1f}</td><td class="num">{float(r["ratio60"]):.2f}</td><td class="num">{float(r["share60_pct"]):.1f}</td></tr>')
        else:
            out.append(f'<tr><td class="c">{i}</td><td class="c">{r["stn"]}</td><td>{r["name"].strip()}</td><td class="c">{r["gu"]}</td>'
                       f'<td class="num">{float(r["hot60_per_day"]):.1f}</td><td class="num">{float(r["ref60_per_day"]):.1f}</td><td class="num">{float(r["ratio60"]):.2f}</td></tr>')
    return "\n".join(out)


BANDS = ["00-04", "05-09", "10-15", "16-19", "20-23"]
abm = {(r["agegrp"], r["band"]): r for r in ab}
exp_rows = ""
for g, lab in [("10대", "10대 이하"), ("20-50대", "20~50대"), ("60+", "60대 이상")]:
    cells = "".join(f'<td class="num">{float(abm[(g, b)]["ph_per_day_hot"]):,.0f}</td>' for b in BANDS)
    tot = sum(float(abm[(g, b)]["ph_per_day_hot"]) for b in BANDS)
    day = sum(float(abm[(g, b)]["ph_per_day_hot"]) for b in ("10-15", "16-19"))
    rpd = sum(float(abm[(g, b)]["rent_per_day_hot"]) for b in BANDS)
    mpt = sum(float(abm[(g, b)]["mins_hot"]) for b in BANDS) / sum(float(abm[(g, b)]["rent_hot"]) for b in BANDS)
    exp_rows += f'<tr><td>{lab}</td>{cells}<td class="num">{tot:,.0f}</td><td class="num">{day:,.0f}</td><td class="num">{rpd:,.0f}</td><td class="num">{mpt:.1f}</td></tr>'


def pfmt(p):
    p = float(p)
    return "&lt;0.001" if p < 0.001 else f"{p:.3f}"


rob_rows = "\n".join(f'<tr><td>{r["spec"]}</td><td class="num">{int(float(r["n"]))}</td><td class="num">{float(r["ge35_pct"]):+.1f}</td>'
                     f'<td class="num">{float(r["ge35_lo"]):+.1f}~{float(r["ge35_hi"]):+.1f}</td><td class="num">{pfmt(r["ge35_p"])}</td><td class="num">{float(r["b33_35_pct"]):+.1f}</td></tr>' for r in rob)
gu_rows = "\n".join(f'<tr><td class="c">{i}</td><td class="c">{r["gu"]}</td><td class="num">{float(r["eld_day_hot_per_day"]):,.1f}</td><td class="num">{float(r["eld_day_hot_ph_per_day"]):,.1f}</td>'
                    f'<td class="num">{float(r["eld_day_ratio"]):.2f}</td><td class="num">{float(r["eld_all_hot_per_day"]):,.1f}</td><td class="num">{float(r["all_hot_per_day"]):,.0f}</td><td class="num">{float(r["all_ratio"]):.2f}</td></tr>'
                    for i, r in enumerate(gu_eld, 1))

appendix = f"""
<section class="appendix">
{sec('부록', '표 A~E, 그림 A·B')}
<p class="tcap">표 A. 폭염 평일 하루 노출 시간과 대여건수 (연령군 × 시간대)</p>
<table class="three small">
<thead><tr><th>연령군</th><th>0~4시</th><th>5~9시</th><th>10~15시</th><th>16~19시</th><th>20~23시</th><th>하루 전체</th><th>낮(10~19시)</th><th>하루 대여<br>(건/일)</th><th>회당 시간<br>(분)</th></tr></thead>
<tbody>{exp_rows}</tbody>
</table>
<p class="tnote">주: 2025년 폭염 평일 {NH}일 평균. 시간대 열과 하루 전체·낮 열은 노출 시간(명시간/일)이며, 명시간 = 이용시간(분) 합 ÷ 60. 연령 미상은 제외. 자료 [1][3], 저장소 results/exposure_age_band_2025.csv.</p>
{fig('half', f'{FG}/figA_type.png', f'<b>그림 A.</b> 공원·강변형 대여소의 유지 비율이 가장 낮다. 2025년 7~8월 폭염 평일 대 비교 평일의 대여소별 유지 비율 분포(전체 이용, 이름 낱말로 추정한 5유형, n={E["type"]["n"]:,}, 상자는 사분위 범위)[1][2][3].')}
<p class="tcap">표 B. 폭염 평일 60대 이상 이용 상위 30 대여소</p>
<table class="three small flow">
<thead><tr><th>순위</th><th>대여소 번호</th><th>대여소명</th><th>자치구</th><th>유형(추정)</th><th>60대 이상 대여<br>(건/일)</th><th>유지 비율</th><th>대여소 이용 중<br>60대 이상 비중(%)</th></tr></thead>
<tbody>{eld_rows(top_e, 'e')}</tbody>
</table>
<p class="tnote">주: 2025년 7~8월 평일·무강수·비공휴일 중 최고기온 35℃ 이상 {NH}일(폭염 평일)의 60대 이상 하루 평균 대여건수[1][3]. 전일 운영 대여소 중 2026-06 대여소 정보[2]에 있는 곳. 유지 비율 = 60대 이상 대여의 폭염 평일 ÷ 비교 평일(27~33℃ {NR}일). 유형은 이름 낱말 규칙이며(주 7) 11·12위는 대조 결과 안양천 변이다. 전체 표는 저장소 results/station_elderly_2025_typed.csv.</p>
{fig('mid', f'{FG}/figB_top_map.png', f'<b>그림 B.</b> 고령 이용 상위 30곳 가운데 {ET["gu"].get("강서구", 0)}곳이 강서구에 있고 절반이 역세권형이다. 전일 운영 대여소 {n(n_list)}곳(회색) 중 60대 이상 폭염 평일 대여 상위 30(색은 추정 유형, 숫자는 표 B 순위 1~10)과 생활시설형 상위 20(사각형)[1][2][3].')}
<p class="tcap">표 C. 생활시설형(추정) 대여소 중 폭염 평일 60대 이상 이용 상위 20</p>
<table class="three small flow">
<thead><tr><th>순위</th><th>대여소 번호</th><th>대여소명</th><th>자치구</th><th>60대 이상 폭염 평일 대여<br>(건/일)</th><th>60대 이상 비교 평일 대여<br>(건/일)</th><th>유지 비율</th></tr></thead>
<tbody>{eld_rows(top_f, 'f')}</tbody>
</table>
<p class="tnote">주: 표 B와 같은 날·같은 대여소 조건. 생활시설형은 이름에 주 7의 낱말(구청·주민센터·도서관·보건소·체육·시장·병원·학교·마트·스포츠 등)이 든 대여소이며 민간 매장 앞도 포함한다. 전체 표는 저장소 results/station_elderly_facility_2025.csv.</p>
<p class="tcap">표 D. 자치구별 60대 이상 폭염 평일 이용 (25개 구)</p>
<table class="three small flow">
<thead><tr><th>순위</th><th>자치구</th><th>60대 이상 낮(10~19시)<br>대여(건/일)</th><th>60대 이상 낮<br>노출(명시간/일)</th><th>낮 유지 비율</th><th>60대 이상 하루<br>대여(건/일)</th><th>전체 하루 대여<br>(건/일)</th><th>전체 유지 비율</th></tr></thead>
<tbody>{gu_rows}</tbody>
</table>
<p class="tnote">주: 2025년 폭염 평일 {NH}일 평균, 전일 운영 대여소 기준. 유지 비율은 폭염 평일 ÷ 비교 평일. 자치구는 대여소 정보[2]의 값이며 대여소 정보에 없는 곳은 뺐다. 자료 [1][2][3], 저장소 results/gu_exposure_2025.csv.</p>
<p class="tcap">표 E. 35℃ 이상 효과의 사양별 비교</p>
<table class="three small flow">
<thead><tr><th>사양</th><th>n</th><th>35℃ 이상 효과(%)</th><th>95% 신뢰구간</th><th>p</th><th>33~35℃ 효과(%)</th></tr></thead>
<tbody>{rob_rows}</tbody>
</table>
<p class="tnote">주: 식 (1)의 변형. 효과는 27~30℃·무강수 날 대비 백분율 변화이며, 기준 구간 30~33℃ 행만 30~33℃ 대비다. 2026년 6월 포함 행과 주 모형은 일조 결측일(2025-09-13)을 뺀 값이다. HAC는 뉴이-웨스트 표준오차이며 숫자는 시차다. 자료 [1][3].</p>
</section>
"""
# ------------------------------------------------------------------ nb 자동 감싸기(숫자·단위·참조와 뒤에 붙은 조사)
NB_RE = re.compile("|".join([
    r"\[\d+\][가-힣]*",
    r"(?:그림|표)\s?(?:[A-E]|\d+)(?:[·,]\s?(?:그림|표)?\s?(?:[A-E]|\d+))*[가-힣]*",
    r"식\s?\(\d\)",
    r"주\s?\d\)",
    r"\d{4}-\d{2}-\d{2}",
    r"\d{4}년\s?\d{1,2}월(?:\s?\d{1,2}일)?[가-힣]*",
    r"[+\-−]?\d[\d,\.]*(?:[~·]\d[\d,\.]*)*\s?(?:만\s?)?(?:명시간|명/일|건/일|km/h|km|명|곳|%|mm|일|년|월|개|대|세|배|행|종|회|쪽|점|℃|시간|분|시|건|번)[가-힣]*",
    r"\((?:n|p|ρ)\s?[=<>≈][^()]{0,24}\)",
    r"p\s?[<=>]\s?[^\s)]{1,12}",
    r"R²=\S+",
]))


def wrap_nb(html_body: str):
    out, count, depth_skip = [], 0, 0
    for seg in re.split(r"(<[^>]+>)", html_body):
        if seg.startswith("<"):
            low = seg.lower()
            if re.match(r"<(table|style|script)\b", low):
                depth_skip += 1
            elif re.match(r"</(table|style|script)\b", low):
                depth_skip = max(0, depth_skip - 1)
            out.append(seg)
            continue
        if depth_skip or not seg.strip():
            out.append(seg)
            continue

        def rep(m):
            nonlocal count
            count += 1
            return f'<span class="nb">{m.group(0)}</span>'
        out.append(NB_RE.sub(rep, seg))
    return "".join(out), count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--css", default="../../공통_논문양식/paper.css", help="report/보고서.html 에서 본 공통 CSS 상대경로 (공개 저장소: ../공통_논문양식/paper.css)")
    ap.add_argument("--wide", type=float, default=52, help="전체 폭 그림 최대 높이(mm)")
    ap.add_argument("--map", type=float, default=48, help="지도 그림 최대 높이(mm)")
    ap.add_argument("--flow", type=float, default=26, help="흐름도 최대 높이(mm)")
    ap.add_argument("--half", type=float, default=56, help="반 폭 그림 최대 높이(mm)")
    ap.add_argument("--team")
    ap.add_argument("--lead")
    ap.add_argument("--url")
    ap.add_argument("--out")
    ap.add_argument("--pdf", action="store_true")
    ap.add_argument("--chrome", default=r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    a_ = ap.parse_args()
    body = titleblock + sec1 + sec2 + sec3 + sec4 + sec5 + sec6 + sec7 + appendix
    body, n_nb = wrap_nb(body)
    tpl = (REP / "template.html").read_text(encoding="utf-8")
    html = (tpl.replace("[[TITLE_TAG]]", TITLE).replace("[[ACCENT]]", ACCENT).replace("[[RUNNING_TITLE]]", RUNNING).replace("[[CSS]]", a_.css)
            .replace("[[FIG_WIDE_H]]", f"{a_.wide:g}").replace("[[FIG_MAP_H]]", f"{a_.map:g}").replace("[[FIG_FLOW_H]]", f"{a_.flow:g}")
            .replace("[[FIG_HALF_H]]", f"{a_.half:g}").replace("[[BODY]]", body))
    filled = any([a_.team, a_.lead, a_.url])
    if filled:
        for ph, val in ((TEAM, a_.team), (LEAD, a_.lead), (GIT, a_.url)):
            if val:
                html = html.replace(ph, val)
        out_pdf = Path(a_.out) if a_.out else REP / f"{a_.team or '보고서'}_분석보고서.pdf"
        out_pdf = out_pdf if out_pdf.is_absolute() else ROOT / out_pdf
        out = out_pdf.with_suffix(".html")
    else:
        out_pdf = Path(a_.out) if a_.out else REP / "보고서.pdf"
        out_pdf = out_pdf if out_pdf.is_absolute() else ROOT / out_pdf
        out = REP / "보고서.html"
    out.write_text(html, encoding="utf-8")
    print(f"saved {out} ({len(html):,} chars); 요약 {len(ABSTRACT)}자; nb 감싸기 {n_nb}개; 검증 {n_verify}개(불일치 {n_verify_bad})")
    if filled or a_.pdf:
        render_pdf(out, out_pdf, a_.chrome)


def render_pdf(html_path: Path, pdf_path: Path, chrome: str) -> None:
    import subprocess
    import time
    if not Path(chrome).exists():
        print(f"[실패] Chrome 을 찾지 못함: {chrome}")
        return
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    if pdf_path.exists():
        pdf_path.unlink()
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
           "--virtual-time-budget=8000", f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri()]
    subprocess.run(cmd, check=False, capture_output=True, timeout=240)
    time.sleep(1)
    if not pdf_path.exists():
        print(f"[실패] PDF 가 생성되지 않음: {pdf_path}")
        return
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        n_pages = len(doc)
        pages = pdf_path.parent / "pages"
        pages.mkdir(exist_ok=True)
        for f in pages.glob("page*.png"):
            f.unlink()
        for i, pg in enumerate(doc):
            pg.get_pixmap(dpi=70).save(str(pages / f"page{i + 1:02d}.png"))
    except Exception as e:
        n_pages = f"? ({e})"
    print(f"PDF 저장: {pdf_path} ({pdf_path.stat().st_size:,} B, {n_pages}쪽); 쪽 이미지 report/pages/")


if __name__ == "__main__":
    main()
    sys.exit(0)
