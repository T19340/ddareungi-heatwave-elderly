# -*- coding: utf-8 -*-
"""
30_figures.py — 보고서 그림 6장 + 부록 2장 (figures/), v3 구성(고령 생활교통 축)
논문양식_지침 3절·시인성 지침 C절: 그림 안 제목 없음(패널 (a)(b) 소제목만), 축 이름·단위·범례, 글꼴 Pretendard(없으면 Malgun Gothic),
색은 강조색(진청 #1f4e79) 계열 + 회색 2~3단계, 격자는 연한 회색 점선. 수치는 모두 results/·data_proc/ 에서 읽는다.

  fig1_flow.png          분석 흐름도 (전체 폭, 가로세로비 약 7:1)
  fig2_heat_effects.png  (a) 서울 폭염일수 1973~2026과 35℃ 이상인 날(6~9월, ASOS), (b) 기온·강수 구간 효과(통제 전·후)
  fig3_profile.png       (a) 연령대별 시간별 이용 비중(비교 평일), (b) 고령·청장년 대여소 유형 구성
  fig4_adjust.png        (a) 시간별 유지 비율(고령·청장년 굵은 선, 연령대 연한 선), (b) 고령 이용자의 시간별 대여
  fig5_who.png           (a) 이용권·연령대별 모형 효과, (b) 연령군×시간대 노출 시간
  fig6_where.png         (a) 자치구별 고령 낮 이용, (b) 고령 이용 상위 12 대여소
  figA_type.png(유형별 유지 비율), figB_top_map.png(상위 대여소 지도)  부록
전체 폭 그림은 보고서의 표시 상자(172×55mm, 가로세로비 약 3.1)에 맞춰 크기를 정해 축소 비율이 0.9 안팎이 되게 한다.
그림 2(a)의 35℃ 이상 일수는 results/heat35_days_by_year.json 에도 적어 40_verify.py 가 대조한다.
실행: python -P -E -X utf8 code/30_figures.py
"""
import glob
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC, RES, FIG = ROOT / "data_proc", ROOT / "results", ROOT / "figures"
FIG.mkdir(parents=True, exist_ok=True)
FONT_DIR = ROOT / "공통_논문양식" / "fonts"
font_name = "Malgun Gothic"
for f in sorted(glob.glob(str(FONT_DIR / "Pretendard-*.otf"))):
    try:
        fm.fontManager.addfont(f)
        font_name = fm.FontProperties(fname=f).get_name()
    except Exception as e:
        print("font skip", f, e)
plt.rcParams.update({"font.family": font_name, "axes.unicode_minus": False, "font.size": 8.5, "axes.labelsize": 8.3,
                     "legend.fontsize": 7.3, "xtick.labelsize": 7.6, "ytick.labelsize": 7.6, "axes.edgecolor": "#444",
                     "axes.linewidth": 0.7, "axes.titlesize": 8.2})
ACC, ACC_L, ACC_D, ACC_XL = "#1f4e79", "#8fb0d1", "#12304d", "#d6e2ee"
G1, G2, G3 = "#d0d0d0", "#8d8d8d", "#4d4d4d"
CMAP = LinearSegmentedColormap.from_list("acc_seq", ["#e8eef5", "#8fb0d1", "#1f4e79", "#0b1f33"])
print("font:", font_name)


def grid(ax, axis="both"):
    ax.grid(color="#cfcfcf", linestyle=":", linewidth=0.6, axis=axis)
    ax.set_axisbelow(True)


def save(fig, name):
    fig.savefig(FIG / name, dpi=200, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    print("saved", name)


def eff(df, model, term):
    r = df[(df.model == model) & (df.term == term)].iloc[0]
    return r["pct"], r["pct_lo"], r["pct_hi"], r["p"]


def bars_with_ci(ax, x, v, color, width=0.34, label=None, fs=6.6, star=True, below=True, fmt="{:+.0f}"):
    y = [e[0] for e in v]
    err = [[e[0] - e[1] for e in v], [e[2] - e[0] for e in v]]
    ax.bar(x, y, width=width, color=color, label=label, edgecolor="#333", linewidth=0.4)
    ax.errorbar(x, y, yerr=err, fmt="none", ecolor="#222", elinewidth=0.7, capsize=2)
    for xi, e in zip(x, v):
        s = fmt.format(e[0]) + ("*" if (star and e[3] < 0.05) else "")
        if below:
            ax.text(xi, e[1] - 1.0, s, ha="center", va="top", fontsize=fs, color="#222")
        else:
            ax.text(xi, e[2] + 1.0, s, ha="center", va="bottom", fontsize=fs, color="#222")


S = json.loads((RES / "summary_stats.json").read_text(encoding="utf-8"))
E = json.loads((RES / "exposure_gap_summary.json").read_text(encoding="utf-8"))
EL = json.loads((RES / "elderly_summary.json").read_text(encoding="utf-8"))
D = pd.read_csv(PROC / "daily_total_weather.csv", parse_dates=["date"])
main = pd.read_csv(RES / "model_main.csv")
noc = pd.read_csv(RES / "model_noctrl.csv")
age = pd.read_csv(RES / "model_age.csv")
pas = pd.read_csv(RES / "model_pass.csv")
hsh = pd.read_csv(RES / "hour_share_by_age_2025.csv")
hr4 = pd.read_csv(RES / "hour_ratio_by_age4_2025.csv")
comp = pd.read_csv(RES / "type_composition_2025.csv")
ab = pd.read_csv(RES / "exposure_age_band_2025.csv")
gu = pd.read_csv(RES / "gu_exposure_2025.csv")
gu = gu[gu.gu != "미상"]
eld = pd.read_csv(RES / "station_elderly_2025_typed.csv")
fac = pd.read_csv(RES / "station_elderly_facility_2025.csv")
sty = pd.read_csv(RES / "station_type_2025.csv")
hw = pd.read_csv(PROC / "heatwave_seoul.csv")
# 두 패널 그림은 constrained 배치로 캔버스를 꽉 채워 저장 크기 = figsize 가 되게 한다(표시 상자 172×55mm 와 가로세로비를 맞춤)
FIG2_SIZE = FIG3_SIZE = FIG4_SIZE = FIG5_SIZE = FIG6_SIZE = (6.8, 2.2)


def two_panels(size, ratios):
    fig_, axs = plt.subplots(1, 2, figsize=size, layout="constrained", gridspec_kw={"width_ratios": ratios})
    fig_.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.05)
    return fig_, axs
TB = {"<27": "27℃ 미만", "30-33": "30~33℃", "33-35": "33~35℃", ">=35": "35℃ 이상"}
BANDS = ["00-04", "05-09", "10-15", "16-19", "20-23"]
BL = {"00-04": "0~4시", "05-09": "5~9시", "10-15": "10~15시", "16-19": "16~19시", "20-23": "20~23시"}
NH, NR = E["n_hot_weekdays_2025"], E["n_ref_weekdays_2025"]
AGE4 = [("20대", G2, 1.0), ("40대", G3, 1.0), ("60대", ACC, 1.6), ("70대이상", ACC_L, 1.3)]
AL4 = {"20대": "20대", "40대": "40대", "60대": "60대", "70대이상": "70대 이상"}

# ------------------------------------------------------------ 그림 1. 흐름도
steps = [("① 수집 00·01", "이용정보 9개월\n대여소 정보\nASOS·폭염일수"),
         ("② 정리 10", "열 이름 통일\n이용권·연령 구분\n집계 3종"),
         ("③ 결합 10", "일 총량 × 기상\n× 달력\n기온·강수 구간"),
         ("④ 회귀 20", "식 (1) 로그 선형\n일조·습도 통제\n연도 고정효과"),
         ("⑤ 분해 21~24", "연령대 성격·시간\n폭염 평일 조정\n자치구·대여소"),
         ("⑥ 검증 40", "원자료 재계산\n2026년 6월\n표본 외 예측")]
fig, ax = plt.subplots(figsize=(7.0, 1.0))
fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
ax.set_xlim(0, 6)
ax.set_ylim(0, 1)
ax.axis("off")
for i, (t, d) in enumerate(steps):
    x0 = i + 0.03
    ax.add_patch(FancyBboxPatch((x0, 0.04), 0.86, 0.92, boxstyle="round,pad=0.01,rounding_size=0.04",
                                fc="#eef3f8", ec=ACC, lw=0.9))
    ax.text(x0 + 0.43, 0.80, t, ha="center", va="center", fontsize=7.6, fontweight="bold", color=ACC_D)
    ax.text(x0 + 0.43, 0.37, d, ha="center", va="center", fontsize=6.9, color="#222", linespacing=1.35)
    if i < 5:
        ax.annotate("", xy=(x0 + 1.02, 0.5), xytext=(x0 + 0.89, 0.5), arrowprops=dict(arrowstyle="-|>", color=G3, lw=0.9))
save(fig, "fig1_flow.png")

# ------------------------------------------------------------ 그림 2. 폭염일수 추세 + 기온·강수 효과(통제 전·후)
fig, (ax, ax2) = two_panels(FIG2_SIZE, [0.9, 1.3])
hwy = hw.sort_values("연도")
cur = int(hwy["연도"].max())
col = np.where(hwy["연도"] == cur, ACC_XL, np.where(hwy["연도"] >= 2016, ACC, G2))
ax.bar(hwy["연도"], hwy["연합계"], color=col, width=0.8, edgecolor=np.where(hwy["연도"] == cur, ACC, "none"), linewidth=0.8)
normal = hwy[(hwy["연도"] >= 1991) & (hwy["연도"] <= 2020)]["연합계"].mean()
ax.axhline(normal, color=G3, ls="--", lw=0.8)
for y in [2018, 2024, 2025, cur]:
    v_ = hwy.loc[hwy["연도"] == y, "연합계"].iloc[0]
    ax.text(y, v_ + 0.8, f"{int(v_)}" + ("*" if y == cur else ""), ha="center", fontsize=6.6, fontweight="bold", color="#222")
# 35℃ 이상인 날(6~9월)은 ASOS 일자료[3]에서 직접 센다(2024·2025년 6~9월, 2026-06-01~10-19 수집; 6~9월은 세 해 모두 빠짐없음)
asos = pd.read_csv(ROOT / "data_raw" / "기상" / "asos_seoul108_daily_2024_2026.csv", encoding="utf-8-sig")
asos["y"], asos["m"] = asos.tm.str[:4].astype(int), asos.tm.str[5:7].astype(int)
js = asos[asos.m.between(6, 9)]
d35 = js.groupby("y").maxTa.apply(lambda v: int((v >= 35).sum()))
recent = hwy[(hwy["연도"] >= 2016) & (hwy["연도"] <= 2025)]["연합계"].mean()
(RES / "heat35_days_by_year.json").write_text(json.dumps({
    "ge35_jun_sep": {str(k): int(v) for k, v in d35.items()}, "rows_jun_sep": {str(k): int(v) for k, v in js.groupby("y").size().items()},
    "missing_maxTa_jun_sep": int(js.maxTa.isna().sum()), "ge35_after_sep_2026": int((asos[(asos.y == 2026) & (asos.m >= 10)].maxTa >= 35).sum()),
    "asos_first": str(asos.tm.min()), "asos_last": str(asos.tm.max()), "heatwave_normal_1991_2020": float(normal), "heatwave_mean_2016_2025": float(recent)},
    ensure_ascii=False, indent=1), encoding="utf-8")
ax.scatter(d35.index, d35.values, marker="D", s=22, facecolors="white", edgecolors="#111", linewidths=0.9, zorder=5)
for y_, v_ in d35.items():
    if y_ == cur:
        ax.text(y_ + 1.0, v_, f"{v_}", ha="left", va="center", fontsize=6.6, fontweight="bold", color="#111")
    else:
        ax.text(y_ - 1.2, v_, f"{v_}", ha="right", va="center", fontsize=6.6, fontweight="bold", color="#111", bbox=dict(fc="white", ec="none", pad=0.4))
ax.set_xlabel("연도")
ax.set_ylabel("일수 (일)")
ax.set_xlim(1972, cur + 3)
ax.set_ylim(0, 57)
ax.legend(handles=[Patch(color=G2, label="폭염일수 1973~2015"), Patch(color=ACC, label=f"폭염일수 2016~{cur - 1} (평균 {recent:.1f}일)"),
                   Patch(facecolor=ACC_XL, edgecolor=ACC, label=f"폭염일수 {cur}* (10월 21일 조회)"),
                   plt.Line2D([], [], color=G3, ls="--", lw=0.8, label=f"폭염일수 평년(1991~2020) {normal:.1f}일"),
                   plt.Line2D([], [], marker="D", markerfacecolor="white", markeredgecolor="#111", linestyle="", markersize=4.5, label="35℃ 이상인 날(6~9월)")],
          loc="upper left", fontsize=6.1, frameon=True, framealpha=0.95, edgecolor="#aaa", borderaxespad=0.3, handlelength=1.4)
ax.set_title("(a) 서울 폭염일수와 35℃ 이상인 날", loc="left")
grid(ax, "y")
bins = ["<27", "30-33", "33-35", ">=35"]
x = np.arange(len(bins))
bars_with_ci(ax2, x - 0.18, [eff(noc, "noctrl_HAC7", f"tbin:{b}") for b in bins], G1, label="기온: 통제 전(일조·습도 없음)", star=False, below=False, fmt="{:+.1f}", fs=5.8)
bars_with_ci(ax2, x + 0.18, [eff(main, "main_HAC7", f"tbin:{b}") for b in bins], ACC, label="기온: 통제 후(주 모형)", star=False, below=True, fmt="{:+.1f}", fs=5.8)
rains = [("rainbin:0-5", "비 5mm\n이하"), ("rainbin:5-20", "비 5~\n20mm"), ("rainbin:>20", "비 20mm\n초과")]
xr = np.arange(len(bins) + 0.6, len(bins) + 0.6 + len(rains))
bars_with_ci(ax2, xr, [eff(main, "main_HAC7", t) for t, _ in rains], G3, width=0.5, label="강수(주 모형)", star=False, below=True, fmt="{:+.1f}", fs=5.8)
ax2.axhline(0, color="#333", lw=0.7)
ax2.axvline(len(bins) - 0.2, color=G2, lw=0.6, ls=":")
ax2.set_xticks(list(x) + list(xr))
TB2 = {"<27": "27℃\n미만", "30-33": "30~\n33℃", "33-35": "33~\n35℃", ">=35": "35℃\n이상"}
ax2.set_xticklabels([TB2[b] for b in bins] + [l for _, l in rains], fontsize=6.6)
ax2.set_ylabel("기준(27~30℃·무강수) 대비 변화 (%)")
ax2.set_ylim(-60, 24)
ax2.legend(loc="lower left", frameon=True, framealpha=0.95, edgecolor="#aaa", fontsize=6.5)
ax2.set_title(f"(b) 최고기온·강수 구간별 효과 (95% 신뢰구간, 두 해 여름 n={S['main']['n']})", loc="left")
grid(ax2, "y")
save(fig, "fig2_heat_effects.png")

# ------------------------------------------------------------ 그림 4. 고령 이용의 성격: 시간별 비중 + 유형 구성
fig, (ax, ax2) = two_panels(FIG3_SIZE, [1.35, 1])
for a, c, lw in AGE4:
    g = hsh[hsh.age == a].sort_values("hour")
    ax.plot(g.hour, g.ref_share_pct, color=c, lw=lw, marker="o", ms=2.2, label=AL4[a])
ax.set_xlabel("대여 시각 (시)")
ax.set_ylabel("하루 대여 중 비중 (%)")
ax.set_xticks(range(0, 24, 3))
ax.set_ylim(0, 13)
ax.legend(loc="upper center", bbox_to_anchor=(0.53, 1.0), frameon=True, framealpha=0.95, edgecolor="#aaa", ncol=1, fontsize=6.4, handlelength=1.6)
ax.set_title(f"(a) 연령대별 시간별 이용 비중 (2025년 7~8월 비교 평일 {NR}일)", loc="left")
grid(ax)
types = ["역세권형", "주거형", "생활시설형", "공원·강변형", "기타"]
tcol = [ACC_D, ACC, ACC_L, G2, G1]
groups = [("60+", "60대 이상"), ("20-50대", "20~50대")]
y = np.arange(len(groups))
left = np.zeros(len(groups))
for t, c in zip(types, tcol):
    vals = np.array([comp[(comp.cls == "ref") & (comp.group == g) & (comp.type == t)].share_pct.iloc[0] for g, _ in groups])
    ax2.barh(y, vals, left=left, color=c, height=0.55, edgecolor="#333", linewidth=0.3, label=t)
    for yi, (l0, v_) in enumerate(zip(left, vals)):
        if v_ >= 6:
            ax2.text(l0 + v_ / 2, yi, f"{v_:.0f}%", ha="center", va="center", fontsize=6.6, color="white" if c in (ACC_D, ACC) else "#222")
    left += vals
ax2.set_yticks(y)
ax2.set_yticklabels([lab for _, lab in groups])
ax2.set_xlim(0, 100)
ax2.set_xlabel("비교 평일 대여의 대여소 유형 구성 (%)")
ax2.legend(loc="upper center", bbox_to_anchor=(0.45, -0.3), ncol=5, fontsize=6.3, frameon=False, handlelength=1.0, columnspacing=0.8)
ax2.set_title("(b) 대여소 유형 구성 (이름 낱말로 추정)", loc="left")
grid(ax2, "x")
save(fig, "fig3_profile.png")

# ------------------------------------------------------------ 그림 5. 폭염일의 조정 방식
fig, (ax, ax2) = two_panels(FIG4_SIZE, [1.25, 1])
# 본문 5.3의 수치는 묶음(고령 이용자 60대 이상, 청장년층 20~50대) 기준이라 두 묶음을 굵게, 연령대 선은 연하게 둔다
for a, c in [("20대", "#c9c9c9"), ("40대", "#a8a8a8"), ("60대", "#9fbad6"), ("70대이상", "#c5d6e8")]:
    g = hr4[(hr4.age == a) & hr4.hour.between(5, 22)].sort_values("hour")
    ax.plot(g.hour, g.ratio, color=c, lw=0.8, label=AL4[a])
for a, c, lab in [("20-50대", G3, "청장년층(20~50대)"), ("60+", ACC, "고령 이용자(60대 이상)")]:
    g = hr4[(hr4.age == a) & hr4.hour.between(5, 22)].sort_values("hour")
    ax.plot(g.hour, g.ratio, color=c, lw=1.9, marker="o", ms=2.4, label=lab, zorder=4)
ax.axhline(1, color="#333", lw=0.7)
ax.axvspan(11.6, 16.4, color=ACC_XL, alpha=0.6, lw=0)
ax.text(14, 1.14, "12~16시", ha="center", fontsize=6.8, color=ACC_D)
ax.set_xlabel("대여 시각 (시, 5~22시)")
ax.set_ylabel("유지 비율 (폭염 평일 ÷ 비교 평일)")
ax.set_xticks(range(5, 23, 3))
ax.set_ylim(0.5, 1.2)
ax.legend(loc="lower left", frameon=True, framealpha=0.95, edgecolor="#aaa", ncol=3, fontsize=6.1, handlelength=1.4, columnspacing=0.9)
ax.set_title(f"(a) 시간별 유지 비율 (폭염 평일 {NH}일 ÷ 비교 평일 {NR}일)", loc="left")
grid(ax)
g = hsh[hsh.age == "60+"].sort_values("hour")
ax2.plot(g.hour, g.ref_per_day, color=G2, lw=1.2, marker="o", ms=2.2, label=f"비교 평일 ({NR}일 평균)")
ax2.plot(g.hour, g.hot_per_day, color=ACC, lw=1.5, marker="o", ms=2.2, label=f"폭염 평일 ({NH}일 평균)")
ax2.fill_between(g.hour, g.hot_per_day, g.ref_per_day, where=g.hot_per_day < g.ref_per_day, color=ACC_XL, interpolate=True)
ax2.set_xlabel("대여 시각 (시)")
ax2.set_ylabel("60대 이상 시간당 대여건수 (건)")
ax2.set_xticks(range(0, 24, 3))
ax2.set_ylim(0, g.ref_per_day.max() * 1.25)
ax2.legend(loc="upper left", frameon=True, framealpha=0.95, edgecolor="#aaa")
ax2.set_title("(b) 60대 이상의 시간별 대여: 폭염 평일과 비교 평일", loc="left")
grid(ax2)
save(fig, "fig4_adjust.png")

# ------------------------------------------------------------ 그림 6. 누가 남는가: 이용권·연령 효과 + 노출 시간
fig, (ax, ax2) = two_panels(FIG5_SIZE, [1.35, 1])
cats = [("pass", "정기권", "정기권"), ("pass", "일일권", "일일권"), ("age", "~10대", "10대\n이하"), ("age", "20대", "20대"), ("age", "30대", "30대"),
        ("age", "40대", "40대"), ("age", "50대", "50대"), ("age", "60대", "60대"), ("age", "70대이상", "70대\n이상")]
v = [eff(pas if k == "pass" else age, f"{k}:{c}", "tbin:>=35") for k, c, _ in cats]
x = np.array([0, 1, 2.4, 3.4, 4.4, 5.4, 6.4, 7.4, 8.4])
cols = [ACC_D, G2, ACC_L, ACC_L, ACC_L, ACC_L, ACC_L, ACC, ACC]
bars_with_ci(ax, x, v, cols, width=0.68, star=False, below=True)
ax.axhline(0, color="#333", lw=0.7)
ax.axvline(1.7, color=G2, lw=0.6, ls=":")
ax.set_xticks(x)
ax.set_xticklabels([l for _, _, l in cats], fontsize=6.8)
ax.set_ylabel("27~30℃ 날 대비 변화 (%)")
ax.set_ylim(-52, 10)
ax.text(0.5, 6, "이용권별", ha="center", fontsize=7, color="#222")
ax.text(5.4, 6, "연령대별", ha="center", fontsize=7, color="#222")
ax.set_title("(a) 35℃ 이상인 날의 모형 효과 (2024·2025년 6~9월, 모두 p<0.01)", loc="left")
grid(ax, "y")
AG = [("10대", "10대 이하", ACC_L), ("20-50대", "20~50대", G2), ("60+", "60대 이상", ACC)]
x = np.arange(len(BANDS))
bottom = np.zeros(len(BANDS))
for a, lab, c in AG:
    g = ab[ab.agegrp == a].set_index("band").reindex(BANDS)
    vals = g["ph_per_day_hot"].values / 1000
    ax2.bar(x, vals, bottom=bottom, color=c, width=0.62, edgecolor="#333", linewidth=0.3, label=lab)
    bottom += vals
g60 = ab[ab.agegrp == "60+"].set_index("band").reindex(BANDS)
for xi, (ph, mpt) in enumerate(zip(g60["ph_per_day_hot"], g60["min_per_trip_hot"])):
    ax2.text(xi, bottom[xi] + 0.25, f"{ph:,.0f}\n({mpt:.0f}분/회)", ha="center", va="bottom", fontsize=6.2, color=ACC_D)
ax2.set_xticks(x)
ax2.set_xticklabels([BL[b] for b in BANDS])
ax2.set_ylabel("하루 노출 시간 (천 명시간)")
ax2.set_ylim(0, bottom.max() * 1.5)
ax2.legend(loc="upper left", frameon=True, framealpha=0.95, edgecolor="#aaa")
ax2.set_title(f"(b) 폭염 평일 노출 시간 ({NH}일 평균, 숫자는 60대 이상)", loc="left")
grid(ax2, "y")
save(fig, "fig5_who.png")

# ------------------------------------------------------------ 그림 7. 어디에 남는가: 자치구 + 상위 15 대여소
TC5 = {"역세권형": ACC_D, "주거형": ACC, "생활시설형": ACC_L, "공원·강변형": G2, "기타": G1}
fig, (ax, ax2) = two_panels(FIG6_SIZE, [1, 1.2])
g = gu.sort_values("eld_day_hot_per_day", ascending=False).head(12).iloc[::-1]
ax.barh(g.gu, g.eld_day_hot_per_day, color=ACC, height=0.65)
for i, (v_, r_) in enumerate(zip(g.eld_day_hot_per_day, g.eld_day_ratio)):
    ax.text(v_ + 4, i, f"{v_:,.0f} ({r_:.2f})", va="center", fontsize=6.8, color="#222")
ax.set_xlim(0, g.eld_day_hot_per_day.max() * 1.35)
ax.set_xlabel("60대 이상 낮(10~19시) 대여 (건/일, 괄호는 유지 비율)")
ax.tick_params(axis="y", labelsize=7.4)
ax.set_title("(a) 자치구 상위 12, 폭염 평일", loc="left")
grid(ax, "x")
t15 = eld.head(12).iloc[::-1]
labels = [f"{n.strip()[:11].strip().rstrip(',')} ({g_[:-1] if g_.endswith('구') else g_})" for n, g_ in zip(t15.name, t15.gu)]
ax2.barh(labels, t15.hot60_per_day, color=[TC5[t] for t in t15.type5], height=0.65, edgecolor="#333", linewidth=0.3)
for i, (v_, r_) in enumerate(zip(t15.hot60_per_day, t15.ratio60)):
    ax2.text(v_ + 0.3, i, f"{v_:.1f} ({r_:.2f})", va="center", fontsize=6.6, color="#222")
ax2.set_xlim(0, t15.hot60_per_day.max() * 1.4)
ax2.set_xlabel("60대 이상 대여 (건/일, 괄호는 유지 비율)")
ax2.tick_params(axis="y", labelsize=7.0)
ax2.legend(handles=[Patch(color=c, label=t) for t, c in TC5.items()], loc="lower right", fontsize=6.4, frameon=True, framealpha=0.95, edgecolor="#aaa", title="유형(추정)", title_fontsize=6.4)
ax2.set_title("(b) 대여소 상위 12, 폭염 평일", loc="left")
grid(ax2, "x")
save(fig, "fig6_where.png")

# ------------------------------------------------------------ 부록 그림 B. 지도: 상위 30 + 생활시설형 상위 20
fig, ax = plt.subplots(figsize=(8.5, 6.4))
ax.scatter(eld.lon, eld.lat, s=np.clip(eld.hot60_per_day * 4, 1.5, 90), c=G1, linewidths=0, zorder=2)
top30 = eld.head(30)
ax.scatter(top30.lon, top30.lat, s=np.clip(top30.hot60_per_day * 4, 16, 110), c=[TC5[t] for t in top30.type5], edgecolors="#222", linewidths=0.5, zorder=4)
f20 = fac.head(20)
ax.scatter(f20.lon, f20.lat, s=70, marker="s", facecolors="none", edgecolors=ACC_D, linewidths=1.0, zorder=5)
ax.set_aspect(1 / np.cos(np.radians(37.55)))
ax.set_xlabel("경도 (°E)")
ax.set_ylabel("위도 (°N)")
handles = [plt.Line2D([], [], marker="o", color=c, markeredgecolor="#222", linestyle="", markersize=6, label=f"상위 30: {t}") for t, c in TC5.items()]
handles.append(plt.Line2D([], [], marker="s", markerfacecolor="none", markeredgecolor=ACC_D, linestyle="", markersize=6, label="생활시설형 상위 20"))
ax.legend(handles=handles, loc="lower right", fontsize=8, frameon=True, framealpha=0.95, edgecolor="#aaa", ncol=2)
OFF = {1: (10, 8), 2: (-26, 22), 3: (10, 8), 4: (-34, -6), 5: (6, 24), 6: (10, 8), 7: (10, 8), 8: (10, -14), 9: (-22, -26), 10: (20, -20)}
for _, r in top30.head(10).iterrows():
    k_ = int(r["rank"])
    ax.annotate(str(k_), (r.lon, r.lat), fontsize=10, fontweight="bold", xytext=OFF.get(k_, (10, 8)), textcoords="offset points", color="#111", zorder=6,
                ha="center", va="center", bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="#777", lw=0.5),
                arrowprops=dict(arrowstyle="-", color="#444", lw=0.6, shrinkA=0, shrinkB=3))
grid(ax)
save(fig, "figB_top_map.png")

# ------------------------------------------------------------ 부록 그림 A. 유형별 분포
order = ["공원·강변형", "생활시설형", "기타", "역세권형", "주거형"]
fig, ax = plt.subplots(figsize=(4.4, 2.6))
data = [sty.loc[sty.type == t, "ratio"].values for t in order]
bp = ax.boxplot(data, positions=range(len(order)), widths=0.55, patch_artist=True, showfliers=False,
                medianprops=dict(color="#111", lw=1.1), boxprops=dict(linewidth=0.7), whiskerprops=dict(linewidth=0.7), capprops=dict(linewidth=0.7))
for patch, t in zip(bp["boxes"], order):
    patch.set_facecolor(ACC if t == "공원·강변형" else ACC_XL)
rng = np.random.default_rng(0)
for i, vals in enumerate(data):
    ax.scatter(i + rng.uniform(-0.2, 0.2, len(vals)), vals, s=3, c=G2, alpha=0.5, linewidths=0, zorder=1)
for i, t in enumerate(order):
    ax.text(i, 1.19, f"n={len(data[i])}\n중앙값 {np.median(data[i]):.2f}", ha="center", va="top", fontsize=6.3, color="#222")
ax.axhline(1, color="#333", lw=0.6, ls=":")
ax.set_xticks(range(len(order)))
ax.set_xticklabels(order, fontsize=6.8)
ax.set_ylabel("유지 비율 (폭염 평일 ÷ 비교 평일)")
ax.set_ylim(0.55, 1.2)
grid(ax, "y")
save(fig, "figA_type.png")
for old in ["figA_top_map.png", "figB_type.png", "fig7_map.png", "figA_station_map_large.png", "fig2_heat_series.png", "fig3_effects.png", "fig4_profile.png", "fig5_adjust.png", "fig6_who.png", "fig7_where.png", "fig8_map.png", "fig4_hourly.png", "fig6_gu.png", "fig7_stations.png", "fig8_type.png"]:
    (FIG / old).unlink(missing_ok=True)
print("done")
sys.exit(0)
