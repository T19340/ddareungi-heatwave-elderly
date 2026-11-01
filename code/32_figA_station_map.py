# -*- coding: utf-8 -*-
"""부록 그림 A: 서울 전체 대여소의 폭염기 대여 유지 비율 지도.
자료: results/station_ratio_2025.csv (21_station.py 산출; 2025년 7~8월 폭염 평일 8일 ÷ 기준 평일 10일, 좌표가 있는 대여소만).
보고서 본문 폭(170mm)에 들어갈 크기 그대로 300dpi로 저장한다(Word 에서 늘이거나 줄이지 않음).
실행: python -P -E -X utf8 code/32_figA_station_map.py"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures_print"
OUT.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "Malgun Gothic", "axes.unicode_minus": False, "font.size": 7.5})

d = pd.read_csv(ROOT / "results" / "station_ratio_2025.csv").dropna(subset=["lat", "lon"])
n = len(d)
W_MM, H_MM = 170.0, 128.0
fig, ax = plt.subplots(figsize=(W_MM / 25.4, H_MM / 25.4), layout="constrained")
norm = TwoSlopeNorm(vmin=0.6, vcenter=1.0, vmax=1.25)
size = np.clip(d.mean_ref / 6.0, 2, 80)
order = d.mean_ref.sort_values(ascending=False).index   # 큰 점을 먼저 그려 작은 점이 가리지 않게
sc = ax.scatter(d.lon[order], d.lat[order], s=size[order], c=d.ratio[order], cmap="RdYlBu", norm=norm,
                edgecolors="#555", linewidths=0.2, alpha=0.9)
ax.set_aspect(1 / np.cos(np.deg2rad(37.55)))
ax.set_xlabel("경도")
ax.set_ylabel("위도")
for s_ in ["top", "right"]:
    ax.spines[s_].set_visible(False)
cb = fig.colorbar(sc, ax=ax, shrink=0.7, pad=0.01)
cb.set_label("대여 유지 비율 (폭염 평일 ÷ 기준 평일)")
cb.set_ticks([0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2])
for v in (30, 100, 300):
    ax.scatter([], [], s=np.clip(v / 6.0, 2, 80), c="#bbb", edgecolors="#555", linewidths=0.2, label=f"{v}건/일")
ax.legend(title="기준 평일 일평균 대여", loc="lower right", frameon=False, fontsize=6.5, title_fontsize=6.5, labelspacing=0.8)
ax.text(0.01, 0.99, f"2025년 7~8월 평일, 대여소 {n:,}곳 (중앙값 {d.ratio.median():.2f})", transform=ax.transAxes,
        va="top", ha="left", fontsize=7)
fig.savefig(OUT / "figA_station_map.png", dpi=300)
print("n =", n, "median =", round(d.ratio.median(), 3), "saved", OUT / "figA_station_map.png")
