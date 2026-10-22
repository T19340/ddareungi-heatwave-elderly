# -*- coding: utf-8 -*-
"""
20_model.py — 폭염이 따릉이 이용을 얼마나·언제·누구에게서 줄이는지 (일 단위 회귀)

주 모형 (식 1): log(일 대여건수) = 최고기온 구간(<27, 27~30 기준, 30~33, 33~35, ≥35) + 강수 구간(0 기준, 0~5, 5~20, >20 mm)
                 + 주말 + 공휴일 + 월 + 연도 + 일조시간 + 평균상대습도 + 오차.
  - 표본: 2024·2025년 6~9월(n=244). 2026년 6월(30일)은 표본 밖 예측 검증에만 쓴다.
  - 표준오차: Newey-West HAC(시차 7). 일별 자료의 잔차 자기상관을 감안한 것. HC1·일반 OLS 표준오차도 함께 저장.
  - 효과 크기: 100·(exp(계수)−1) %, 기준 구간(27~30℃, 무강수) 대비.
하위 모형: 시간대(00~04·05~09·10~15·16~19·20~23), 연령대, 이용권, 연도별(2024·2025 각각, 월 고정효과만).
강건성: (a) 연도별, (b) 기준 구간 30~33, (c) 최고기온 자연 3차 스플라인, (d) 일조·습도 제외(통제의 중요성), (e) 2026-06 표본 외 예측,
        (f) 2026-06 포함(n=274) 적합, (g) 요일 고정효과, (h) HAC 시차 14.
반사실(보조): 2025년 6~9월에서 33℃ 이상인 날을 27~30℃로 두었을 때의 예측 대여건수 차이(가정 명시, 보조 수치).

출력: results/model_main.csv, model_noctrl.csv, model_hourband.csv, model_age.csv, model_pass.csv, model_year.csv,
      model_robust.csv, spline_curve.csv, oos_2026.csv, counterfactual_2025.csv, model_main_summary.txt, summary_stats.json(일부)
실행: python -P -E -X utf8 code/20_model.py
"""
import json
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
PROC, RES = ROOT / "data_proc", ROOT / "results"
RES.mkdir(exist_ok=True)
HAC = dict(cov_type="HAC", cov_kwds={"maxlags": 7})
TBINS = ["<27", "30-33", "33-35", ">=35"]
RBINS = ["0-5", "5-20", ">20"]
F_MAIN = "lrent ~ C(tbin, Treatment('27-30')) + C(rainbin, Treatment('0')) + wkend + hol + C(month) + C(year) + sumSsHr + avgRhm"
F_NOCTRL = "lrent ~ C(tbin, Treatment('27-30')) + C(rainbin, Treatment('0')) + wkend + hol + C(month) + C(year)"
F_YEAR = "lrent ~ C(tbin, Treatment('27-30')) + C(rainbin, Treatment('0')) + wkend + hol + C(month) + sumSsHr + avgRhm"
F_DOW = "lrent ~ C(tbin, Treatment('27-30')) + C(rainbin, Treatment('0')) + C(dow) + hol + C(month) + C(year) + sumSsHr + avgRhm"
F_REF30 = "lrent ~ C(tbin, Treatment('30-33')) + C(rainbin, Treatment('0')) + wkend + hol + C(month) + C(year) + sumSsHr + avgRhm"
F_SPLINE = "lrent ~ cr(maxTa, df=5) + C(rainbin, Treatment('0')) + wkend + hol + C(month) + C(year) + sumSsHr + avgRhm"
HOUR_BANDS = [(0, 4, "00-04"), (5, 9, "05-09"), (10, 15, "10-15"), (16, 19, "16-19"), (20, 23, "20-23")]


def term_name(t: str) -> str:
    m = re.match(r"C\((tbin|rainbin), Treatment\('[^']*'\)\)\[T\.(.+)\]$", t)
    if m:
        return f"{m.group(1)}:{m.group(2)}"
    m = re.match(r"C\((month|year|dow)\)\[T\.(.+)\]$", t)
    if m:
        return f"{m.group(1)}:{m.group(2)}"
    return t


def tidy(res, label: str, extra: dict | None = None) -> pd.DataFrame:
    ci = res.conf_int()
    rows = []
    for t in res.params.index:
        b, se, p = res.params[t], res.bse[t], res.pvalues[t]
        lo, hi = ci.loc[t, 0], ci.loc[t, 1]
        rows.append({"model": label, "term": term_name(t), "coef": b, "se": se, "p": p, "ci_lo": lo, "ci_hi": hi,
                     "pct": 100 * (np.exp(b) - 1), "pct_lo": 100 * (np.exp(lo) - 1), "pct_hi": 100 * (np.exp(hi) - 1),
                     "n": int(res.nobs), "r2": res.rsquared, **(extra or {})})
    return pd.DataFrame(rows)


def fit(formula: str, data: pd.DataFrame, **kw):
    kw = kw or HAC
    return smf.ols(formula, data=data).fit(**kw)


def effect(res, term: str) -> dict:
    """term 예: tbin:>=35"""
    for t in res.params.index:
        if term_name(t) == term:
            b = res.params[t]
            lo, hi = res.conf_int().loc[t]
            return {"coef": float(b), "pct": float(100 * (np.exp(b) - 1)), "pct_lo": float(100 * (np.exp(lo) - 1)),
                    "pct_hi": float(100 * (np.exp(hi) - 1)), "p": float(res.pvalues[t]), "se": float(res.bse[t])}
    return {"coef": np.nan, "pct": np.nan, "pct_lo": np.nan, "pct_hi": np.nan, "p": np.nan, "se": np.nan}


def prep(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    d["lrent"] = np.log(d["rent"])
    return d


def main() -> int:
    D = pd.read_csv(PROC / "daily_total_weather.csv")
    D = prep(D)
    main_d = D[D["year"].isin([2024, 2025])].reset_index(drop=True)
    oos = D[D["year"] == 2026].reset_index(drop=True)
    S = {}

    # ---------------- 주 모형
    r_main = fit(F_MAIN, main_d)
    r_main_hc1 = fit(F_MAIN, main_d, cov_type="HC1")
    r_main_ols = fit(F_MAIN, main_d, cov_type="nonrobust")
    r_noc = fit(F_NOCTRL, main_d)
    t_main = tidy(r_main, "main_HAC7")
    t_main = pd.concat([t_main, tidy(r_main_hc1, "main_HC1"), tidy(r_main_ols, "main_OLS")], ignore_index=True)
    t_main.to_csv(RES / "model_main.csv", index=False, encoding="utf-8-sig")
    tidy(r_noc, "noctrl_HAC7").to_csv(RES / "model_noctrl.csv", index=False, encoding="utf-8-sig")
    (RES / "model_main_summary.txt").write_text(
        "주 모형 (2024·2025년 6~9월, HAC 시차 7)\n" + str(r_main.summary()) + "\n\n일조·습도 제외 모형\n" + str(r_noc.summary()),
        encoding="utf-8")
    S["main"] = {"n": int(r_main.nobs), "r2": float(r_main.rsquared), "r2_adj": float(r_main.rsquared_adj),
                 "tbin": {b: effect(r_main, f"tbin:{b}") for b in TBINS},
                 "rain": {b: effect(r_main, f"rainbin:{b}") for b in RBINS},
                 "wkend": effect(r_main, "wkend"), "hol": effect(r_main, "hol"),
                 "sumSsHr": effect(r_main, "sumSsHr"), "avgRhm": effect(r_main, "avgRhm"),
                 "tbin_hc1": {b: effect(r_main_hc1, f"tbin:{b}") for b in TBINS},
                 "tbin_ols": {b: effect(r_main_ols, f"tbin:{b}") for b in TBINS}}
    S["noctrl"] = {"n": int(r_noc.nobs), "r2": float(r_noc.rsquared), "tbin": {b: effect(r_noc, f"tbin:{b}") for b in TBINS},
                   "rain": {b: effect(r_noc, f"rainbin:{b}") for b in RBINS}}
    # 통제 변수의 평균 차이: ≥35 날 vs 27~30 날 (왜 통제가 필요한지 설명용)
    g = main_d.groupby("tbin")[["sumSsHr", "avgRhm", "sumRn", "rent"]].mean()
    S["tbin_means"] = {b: {k: float(v) for k, v in g.loc[b].items()} for b in g.index}
    S["tbin_days"] = {f"{int(y)}": {b: int(c) for b, c in main_d[main_d.year == y]["tbin"].value_counts().items()} for y in [2024, 2025]}
    S["tbin_days"]["2026"] = {b: int(c) for b, c in oos["tbin"].value_counts().items()}
    S["rain_days"] = {f"{int(y)}": {b: int(c) for b, c in D[D.year == y]["rainbin"].value_counts().items()} for y in [2024, 2025, 2026]}
    raw = main_d.groupby("tbin")["rent"].mean()
    S["raw_mean_rent_by_tbin"] = {b: float(v) for b, v in raw.items()}
    S["raw_ratio_ge35_vs_27_30"] = float(raw[">=35"] / raw["27-30"])

    # ---------------- 시간대·연령·이용권 하위 모형
    H = pd.read_csv(PROC / "daily_hour_age_pass.csv")
    wcols = ["date", "tbin", "rainbin", "wkend", "hol", "month", "year", "sumSsHr", "avgRhm", "maxTa", "sumRn", "dow"]
    W = D[wcols]

    def band(h):
        for lo, hi, nm in HOUR_BANDS:
            if lo <= h <= hi:
                return nm
    H["band"] = H["hour"].map(band)

    def sub_models(key: str, label: str, order: list[str]) -> pd.DataFrame:
        out = []
        for k in order:
            dd = H[H[key] == k].groupby("date", as_index=False)["rent"].sum().merge(W, on="date")
            dd = prep(dd[dd["year"].isin([2024, 2025])])
            res = fit(F_MAIN, dd)
            t = tidy(res, f"{label}:{k}", {"group": k})
            out.append(t)
            S.setdefault(label, {})[k] = {"n": int(res.nobs), "r2": float(res.rsquared), "mean_rent": float(dd["rent"].mean()),
                                         "tbin": {b: effect(res, f"tbin:{b}") for b in TBINS},
                                         "rain": {b: effect(res, f"rainbin:{b}") for b in RBINS}}
        return pd.concat(out, ignore_index=True)

    sub_models("band", "hourband", [b[2] for b in HOUR_BANDS]).to_csv(RES / "model_hourband.csv", index=False, encoding="utf-8-sig")
    ages = ["~10대", "20대", "30대", "40대", "50대", "60대", "70대이상", "기타"]
    sub_models("age", "age", ages).to_csv(RES / "model_age.csv", index=False, encoding="utf-8-sig")
    passes = ["정기권", "일일권", "가족권"]
    sub_models("pass", "pass", passes).to_csv(RES / "model_pass.csv", index=False, encoding="utf-8-sig")
    # 60대 이상 묶음(60대+70대이상)
    H["age2"] = np.where(H["age"].isin(["60대", "70대이상"]), "60대이상", np.where(H["age"].isin(["20대", "30대", "40대"]), "20~40대", "그외"))
    sub_models("age2", "age2", ["60대이상", "20~40대"]).to_csv(RES / "model_age2.csv", index=False, encoding="utf-8-sig")
    # 시간대 × 이용권 (정기권 10~15시 등)
    H["bp"] = H["band"] + "|" + H["pass"]
    sub_models("bp", "band_pass", [f"{b}|{p}" for b in ["05-09", "10-15", "16-19"] for p in ["정기권", "일일권"]]).to_csv(
        RES / "model_band_pass.csv", index=False, encoding="utf-8-sig")

    # ---------------- 연도별
    out = []
    for y in [2024, 2025]:
        dd = main_d[main_d["year"] == y]
        res = fit(F_YEAR, dd)
        out.append(tidy(res, f"year:{y}", {"group": str(y)}))
        S.setdefault("year", {})[str(y)] = {"n": int(res.nobs), "r2": float(res.rsquared),
                                            "tbin": {b: effect(res, f"tbin:{b}") for b in TBINS},
                                            "rain": {b: effect(res, f"rainbin:{b}") for b in RBINS}}
        res_n = fit(F_NOCTRL.replace(" + C(year)", ""), dd)
        S["year"][str(y)]["noctrl_ge35"] = effect(res_n, "tbin:>=35")
    pd.concat(out, ignore_index=True).to_csv(RES / "model_year.csv", index=False, encoding="utf-8-sig")

    # ---------------- 강건성 표 (≥35, 33~35 효과)
    rob = []

    def add_rob(name, res, note=""):
        e35, e33 = effect(res, "tbin:>=35"), effect(res, "tbin:33-35")
        rob.append({"spec": name, "n": int(res.nobs), "r2": float(res.rsquared), "ge35_pct": e35["pct"], "ge35_lo": e35["pct_lo"],
                    "ge35_hi": e35["pct_hi"], "ge35_p": e35["p"], "b33_35_pct": e33["pct"], "b33_35_p": e33["p"], "note": note})

    add_rob("주 모형(HAC 7)", r_main)
    add_rob("주 모형, HC1 표준오차", r_main_hc1)
    add_rob("주 모형, 일반 OLS 표준오차", r_main_ols)
    add_rob("주 모형, HAC 14", fit(F_MAIN, main_d, cov_type="HAC", cov_kwds={"maxlags": 14}))
    add_rob("일조·습도 제외", r_noc)
    add_rob("요일 고정효과(주말 대신)", fit(F_DOW, main_d))
    r_ref = fit(F_REF30, main_d)
    add_rob("기준 구간 30~33℃", r_ref, "≥35 효과는 30~33℃ 대비")
    r_all = fit(F_MAIN, D)
    add_rob("2026년 6월 포함", r_all, "일조 결측일 제외")
    add_rob("2024년만", fit(F_YEAR, main_d[main_d.year == 2024]))
    add_rob("2025년만", fit(F_YEAR, main_d[main_d.year == 2025]))
    add_rob("비 온 35℃ 이상 날 제외(2025-07-08)", fit(F_MAIN, main_d[main_d.date != "2025-07-08"]))
    add_rob("공휴일에 선거일 제외", fit(F_MAIN, main_d.assign(hol=np.where(main_d.date.isin(["2025-06-03"]), 0, main_d.hol))))
    add_rob("일조 결측일(2025-09-13) 일조 0으로 대체", fit(F_MAIN, main_d.assign(sumSsHr=main_d.sumSsHr.fillna(0.0))), "주 모형은 결측일 제외(n=243)")
    S["missing_sunshine_days"] = [str(x) for x in D.loc[D.sumSsHr.isna(), "date"]]
    pd.DataFrame(rob).to_csv(RES / "model_robust.csv", index=False, encoding="utf-8-sig")
    S["robust"] = rob

    # ---------------- 스플라인 (최고기온 연속형)
    r_sp = fit(F_SPLINE, main_d)
    grid = pd.DataFrame({"maxTa": np.arange(22, 39.01, 0.5)})
    base = dict(rainbin="0", wkend=0, hol=0, month=7, year=2025, sumSsHr=float(main_d["sumSsHr"].mean()), avgRhm=float(main_d["avgRhm"].mean()))
    for k, v in base.items():
        grid[k] = v
    pred = r_sp.get_prediction(grid).summary_frame(alpha=0.05)
    ref_idx = int(np.argmin(np.abs(grid["maxTa"] - 28.5)))
    ref = pred["mean"].iloc[ref_idx]
    grid["pct_vs_28_5"] = 100 * (np.exp(pred["mean"] - ref) - 1)
    grid["pct_lo"] = 100 * (np.exp(pred["mean_ci_lower"] - ref) - 1)
    grid["pct_hi"] = 100 * (np.exp(pred["mean_ci_upper"] - ref) - 1)
    grid[["maxTa", "pct_vs_28_5", "pct_lo", "pct_hi"]].to_csv(RES / "spline_curve.csv", index=False, encoding="utf-8-sig")
    S["spline"] = {"r2": float(r_sp.rsquared), "pct_at_35": float(np.interp(35, grid["maxTa"], grid["pct_vs_28_5"])),
                   "pct_at_36": float(np.interp(36, grid["maxTa"], grid["pct_vs_28_5"])), "pct_at_37": float(np.interp(37, grid["maxTa"], grid["pct_vs_28_5"])),
                   "pct_at_33": float(np.interp(33, grid["maxTa"], grid["pct_vs_28_5"])), "pct_at_31": float(np.interp(31, grid["maxTa"], grid["pct_vs_28_5"])),
                   "pct_at_25": float(np.interp(25, grid["maxTa"], grid["pct_vs_28_5"]))}

    # ---------------- 2026-06 표본 외 예측 (연도 효과는 2025년 값으로)
    o = oos.copy()
    o["year"] = 2025
    o["pred_l"] = r_main.predict(o)
    o["pred"] = np.exp(o["pred_l"])
    o["year"] = 2026
    o["err_l"] = o["lrent"] - o["pred_l"]
    o["ape"] = np.abs(o["rent"] - o["pred"]) / o["rent"] * 100
    o[["date", "rent", "pred", "err_l", "ape", "maxTa", "sumRn", "tbin", "rainbin"]].to_csv(RES / "oos_2026.csv", index=False, encoding="utf-8-sig")
    S["oos_2026"] = {"n": int(len(o)), "mean_log_err": float(o["err_l"].mean()), "mape": float(o["ape"].mean()),
                     "median_ape": float(o["ape"].median()), "corr_log": float(np.corrcoef(o["lrent"], o["pred_l"])[0, 1]),
                     "r2_oos_log": float(1 - ((o["lrent"] - o["pred_l"]) ** 2).sum() / ((o["lrent"] - o["lrent"].mean()) ** 2).sum()),
                     "actual_sum": int(o["rent"].sum()), "pred_sum": float(o["pred"].sum())}

    # ---------------- 반사실 (2025년 6~9월, 33℃ 이상인 날을 27~30℃로)
    c = main_d[main_d["year"] == 2025].copy()
    c["pred_actual"] = np.exp(r_main.predict(c))
    cf = c.copy()
    cf.loc[cf["tbin"].isin(["33-35", ">=35"]), "tbin"] = "27-30"
    c["pred_cf"] = np.exp(r_main.predict(cf))
    c["hot"] = c["tbin"].isin(["33-35", ">=35"]).astype(int)
    c[["date", "rent", "tbin", "pred_actual", "pred_cf", "hot"]].to_csv(RES / "counterfactual_2025.csv", index=False, encoding="utf-8-sig")
    hot = c[c["hot"] == 1]
    S["counterfactual_2025"] = {"hot_days": int(len(hot)), "actual_sum_hot_days": int(hot["rent"].sum()),
                                "pred_actual_sum_hot_days": float(hot["pred_actual"].sum()), "pred_cf_sum_hot_days": float(hot["pred_cf"].sum()),
                                "loss_rentals": float((hot["pred_cf"] - hot["pred_actual"]).sum()),
                                "season_total_2025": int(c["rent"].sum()),
                                "loss_share_of_season_pct": float(100 * (hot["pred_cf"] - hot["pred_actual"]).sum() / c["rent"].sum()),
                                "assumption": "33℃ 이상인 날의 기온 구간만 27~30℃로 바꾸고 일조·습도·강수·달력 변수는 실제값 유지; 모형 예측치 합의 차이"}

    # ---------------- 폭염일에 남는 이용 (총량·몫) — 22_exposure.py 와 교차
    S["ge35_days"] = {"2024": int((main_d.year == 2024).sum() and ((main_d.year == 2024) & (main_d.tbin == ">=35")).sum()),
                      "2025": int(((main_d.year == 2025) & (main_d.tbin == ">=35")).sum()), "2026-06": int((oos.tbin == ">=35").sum())}
    S["b33_35_days"] = {"2024": int(((main_d.year == 2024) & (main_d.tbin == "33-35")).sum()),
                        "2025": int(((main_d.year == 2025) & (main_d.tbin == "33-35")).sum())}
    S["mean_rent_ge35"] = float(main_d.loc[main_d.tbin == ">=35", "rent"].mean())
    S["mean_rent_27_30"] = float(main_d.loc[main_d.tbin == "27-30", "rent"].mean())
    S["season_totals"] = {str(int(y)): int(v) for y, v in D.groupby("year")["rent"].sum().items()}
    S["daily_mean_by_year"] = {str(int(y)): float(v) for y, v in D.groupby("year")["rent"].mean().items()}
    (RES / "summary_stats.json").write_text(json.dumps(S, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    m = S["main"]
    print(f"n={m['n']} R2={m['r2']:.3f} | ≥35: {m['tbin']['>=35']['pct']:.1f}% (p={m['tbin']['>=35']['p']:.3f}) | 33-35: {m['tbin']['33-35']['pct']:.1f}% (p={m['tbin']['33-35']['p']:.3f}) | 30-33: {m['tbin']['30-33']['pct']:.1f}% | <27: {m['tbin']['<27']['pct']:.1f}%")
    print(f"rain >20: {m['rain']['>20']['pct']:.1f}%  5-20: {m['rain']['5-20']['pct']:.1f}%  0-5: {m['rain']['0-5']['pct']:.1f}%")
    print(f"noctrl ≥35: {S['noctrl']['tbin']['>=35']['pct']:.1f}% (p={S['noctrl']['tbin']['>=35']['p']:.3f})")
    for k, v in S["hourband"].items():
        print(f"band {k}: ≥35 {v['tbin']['>=35']['pct']:.1f}% (p={v['tbin']['>=35']['p']:.3f})")
    for k, v in S["pass"].items():
        print(f"pass {k}: ≥35 {v['tbin']['>=35']['pct']:.1f}% (p={v['tbin']['>=35']['p']:.3f})")
    for k, v in S["age"].items():
        print(f"age {k}: ≥35 {v['tbin']['>=35']['pct']:.1f}% (p={v['tbin']['>=35']['p']:.3f})")
    for k, v in S["year"].items():
        print(f"year {k}: ≥35 {v['tbin']['>=35']['pct']:.1f}% (p={v['tbin']['>=35']['p']:.3f}); noctrl {v['noctrl_ge35']['pct']:.1f}%")
    print("oos", {k: round(v, 3) if isinstance(v, float) else v for k, v in S["oos_2026"].items()})
    print("cf", S["counterfactual_2025"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
