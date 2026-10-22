# -*- coding: utf-8 -*-
"""
21_station.py — 같은 해 안에서 대여소별 '폭염일 이용 유지 비율'

비율 = (최고기온 35℃ 이상인 평일·무강수·비공휴일의 대여소 일평균 대여건수) ÷ (같은 해 같은 기간의 27~33℃ 평일·무강수·비공휴일 일평균)
  - 주력: 2025년 7~8월(폭염일 8일, 기준일 10일). 보조: 2024년 6~9월(폭염일 4일; 기준일이 여러 달에 걸쳐 계절 차이가 섞임).
  - 대여소 조건: 기준일 평균 30건 이상, 폭염일 전부와 기준일의 5/6 이상에 대여 기록이 있는 곳(폐쇄·이전 대여소 제외). 없는 날은 0으로 센다.
  - 좌표·이름·자치구는 2026-06 기준 대여소 정보. 유형은 이름의 낱말로 '추정'(공원·강변형 → 주거형 → 역세권형 → 기타, 23_exposure_gap.py 와 같은 규칙).
출력: results/station_ratio_2025.csv, station_ratio_2024.csv, station_by_gu_2025.csv, station_by_type_2025.csv,
      station_top_bottom_2025.csv, station_summary.json
실행: python -P -E -X utf8 code/21_station.py
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
PROC, RES = ROOT / "data_proc", ROOT / "results"
RES.mkdir(exist_ok=True)
MIN_REF_MEAN = 30
BIG = 100  # 상·하위 목록은 기준일 평균 100건 이상인 큰 대여소만


def classify(name: str) -> str:
    """이름 낱말로 추정한 유형 5종(앞 규칙 우선): 주거형 → 공원·강변형 → 역세권형 → 생활시설형 → 기타."""
    n = str(name)
    if re.search(r"아파트|빌라|주공|연립|APT|주택|오피스텔|(?<!디지털)(?<!산업)(?<!공)단지", n):
        return "주거형"
    if re.search(r"공원|한강|강변|둔치|수변|천변|호수|선착장|유원지|쉼터|청계천|안양천|중랑천|탄천|홍제천|불광천|도림천|양재천|성북천|정릉천|우이천|당현천|묵동천|고덕천|여의나루", n):
        return "공원·강변형"
    if re.search(r"역", n):
        return "역세권형"
    if re.search(r"시장|병원|의료원|주민센터|구청|도서관|복지관|보건소|우체국|경로당|노인|보건|학교|체육|스포츠|수련관|세무서|구민|문화센터|복지센터|복지|관공서|시청|경찰서|소방서|법원|교회|성당|마트", n):
        return "생활시설형"
    return "기타"


def compute(year: int, months: list[int], D: pd.DataFrame, S: pd.DataFrame, st: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    w = D[(D.year == year) & (D.month.isin(months)) & (D.wkend == 0) & (D.hol == 0) & (D.sumRn == 0)]
    hot_days = sorted(w.loc[w.maxTa >= 35, "date"])
    ref_days = sorted(w.loc[(w.maxTa >= 27) & (w.maxTa < 33), "date"])
    sub = S[S.date.isin(hot_days + ref_days)]
    piv = sub.pivot_table(index="stn", columns="date", values="rent", aggfunc="sum").reindex(columns=hot_days + ref_days)
    has = piv.notna()
    piv = piv.fillna(0)
    out = pd.DataFrame({"stn": piv.index, "mean_hot": piv[hot_days].mean(axis=1).values, "mean_ref": piv[ref_days].mean(axis=1).values,
                        "n_hot_with_data": has[hot_days].sum(axis=1).values, "n_ref_with_data": has[ref_days].sum(axis=1).values})
    out["year"] = year
    out["ratio"] = out["mean_hot"] / out["mean_ref"]
    cond_ref = out["mean_ref"] >= MIN_REF_MEAN
    cond_cov = (out["n_hot_with_data"] == len(hot_days)) & (out["n_ref_with_data"] >= np.ceil(len(ref_days) * 5 / 6))
    info = {"year": year, "months": months, "hot_days": hot_days, "ref_days": ref_days, "n_stations_any": int(len(out)),
            "n_after_ref_mean": int(cond_ref.sum()), "n_after_coverage": int((cond_ref & cond_cov).sum())}
    out = out[cond_ref & cond_cov].merge(st[["stn", "name", "gu", "lat", "lon"]], on="stn", how="left")
    out["type"] = out["name"].map(classify)
    out["in_master"] = out["name"].notna()
    info["n_without_master"] = int((~out["in_master"]).sum())
    info["n"] = int(len(out))
    info["median_ratio"] = float(out["ratio"].median())
    info["mean_ratio"] = float(out["ratio"].mean())
    info["share_lt_0_8"] = float((out["ratio"] < 0.8).mean() * 100)
    info["share_gt_1"] = float((out["ratio"] > 1.0).mean() * 100)
    info["share_ge_0_9"] = float((out["ratio"] >= 0.9).mean() * 100)
    info["q10"], info["q25"], info["q75"], info["q90"] = [float(out["ratio"].quantile(q)) for q in (0.1, 0.25, 0.75, 0.9)]
    info["total_ratio"] = float(out["mean_hot"].sum() / out["mean_ref"].sum())
    return out.sort_values("ratio", ascending=False).reset_index(drop=True), info


def main() -> int:
    D = pd.read_csv(PROC / "daily_total_weather.csv")
    S = pd.read_csv(PROC / "daily_station.csv")
    st = pd.read_csv(PROC / "stations.csv")
    r25, i25 = compute(2025, [7, 8], D, S, st)
    r24, i24 = compute(2024, [6, 7, 8, 9], D, S, st)
    r25.to_csv(RES / "station_ratio_2025.csv", index=False, encoding="utf-8-sig")
    r24.to_csv(RES / "station_ratio_2024.csv", index=False, encoding="utf-8-sig")
    # 자치구별
    g = r25[r25.in_master].groupby("gu").agg(n=("stn", "size"), median_ratio=("ratio", "median"),
                                             share_lt_0_8=("ratio", lambda x: 100 * (x < 0.8).mean()),
                                             share_gt_1=("ratio", lambda x: 100 * (x > 1.0).mean()),
                                             sum_hot=("mean_hot", "sum"), sum_ref=("mean_ref", "sum")).reset_index()
    g["total_ratio"] = g["sum_hot"] / g["sum_ref"]
    g = g.sort_values("median_ratio", ascending=False)
    g.to_csv(RES / "station_by_gu_2025.csv", index=False, encoding="utf-8-sig")
    # 유형별(추정)
    t = r25[r25.in_master].groupby("type").agg(n=("stn", "size"), median_ratio=("ratio", "median"), q25=("ratio", lambda x: x.quantile(0.25)),
                                               q75=("ratio", lambda x: x.quantile(0.75)), share_lt_0_8=("ratio", lambda x: 100 * (x < 0.8).mean()),
                                               share_gt_1=("ratio", lambda x: 100 * (x > 1.0).mean())).reset_index()
    t.to_csv(RES / "station_by_type_2025.csv", index=False, encoding="utf-8-sig")
    kw = stats.kruskal(*[r25.loc[r25.type == k, "ratio"] for k in t["type"]])
    mw = stats.mannwhitneyu(r25.loc[r25.type == "공원·강변형", "ratio"], r25.loc[r25.type == "주거형", "ratio"])
    # 상·하위 목록 (큰 대여소)
    big = r25[(r25.mean_ref >= BIG) & r25.in_master]
    top = big.head(20).assign(group="유지(상위 20)")
    bot = big.tail(20).iloc[::-1].assign(group="감소(하위 20)")
    pd.concat([top, bot]).to_csv(RES / "station_top_bottom_2025.csv", index=False, encoding="utf-8-sig")
    # 2024 vs 2025 일관성
    both = r25.merge(r24[["stn", "ratio"]], on="stn", suffixes=("_25", "_24"))
    rho = stats.spearmanr(both["ratio_25"], both["ratio_24"])
    summ = {"2025": i25, "2024": i24, "by_gu_2025": g.to_dict("records"), "by_type_2025": t.to_dict("records"),
            "type_kruskal_p": float(kw.pvalue), "park_vs_resid_mw_p": float(mw.pvalue),
            "big_stations": {"threshold_ref_mean": BIG, "n": int(len(big)), "median_ratio": float(big["ratio"].median()),
                             "share_gt_1": float(100 * (big["ratio"] > 1).mean()), "share_lt_0_8": float(100 * (big["ratio"] < 0.8).mean())},
            "consistency_2024_2025": {"n_both": int(len(both)), "spearman_rho": float(rho.statistic), "p": float(rho.pvalue)},
            "top20": top[["stn", "name", "gu", "mean_ref", "mean_hot", "ratio", "type"]].to_dict("records"),
            "bottom20": bot[["stn", "name", "gu", "mean_ref", "mean_hot", "ratio", "type"]].to_dict("records")}
    (RES / "station_summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(json.dumps({k: summ[k] for k in ["2025", "2024", "by_type_2025", "type_kruskal_p", "park_vs_resid_mw_p", "big_stations", "consistency_2024_2025"]},
                     ensure_ascii=False, indent=1, default=float))
    print(g.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
