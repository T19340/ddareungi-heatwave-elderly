# -*- coding: utf-8 -*-
"""
22_exposure.py — 폭염일에도 남는 이용: 35℃ 이상인 날의 하루 평균 대여건수와 그 구성(이용권·연령·시간대)

- 2024·2025년 6~9월의 35℃ 이상인 날(≥35)과 27~30℃인 날(기준)을 비교한다(원자료 평균, 모형 보정 없음).
- 몫(share)은 해당 집단 대여건수 ÷ 전체 대여건수.
출력: results/exposure_shares.csv, exposure_summary.json
실행: python -P -E -X utf8 code/22_exposure.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC, RES = ROOT / "data_proc", ROOT / "results"
HOUR_BANDS = [(0, 4, "00-04"), (5, 9, "05-09"), (10, 15, "10-15"), (16, 19, "16-19"), (20, 23, "20-23")]


def band(h):
    for lo, hi, nm in HOUR_BANDS:
        if lo <= h <= hi:
            return nm


def main() -> int:
    D = pd.read_csv(PROC / "daily_total_weather.csv")
    H = pd.read_csv(PROC / "daily_hour_age_pass.csv")
    H["band"] = H["hour"].map(band)
    H["age2"] = np.where(H["age"].isin(["60대", "70대이상"]), "60대이상", H["age"])
    D = D[D.year.isin([2024, 2025])]
    groups = {"ge35": D.loc[D.tbin == ">=35", "date"], "ref": D.loc[D.tbin == "27-30", "date"]}
    rows, S = [], {}
    for gname, dates in groups.items():
        h = H[H.date.isin(dates)]
        nd = len(dates)
        tot = h["rent"].sum() / nd
        S[gname] = {"days": int(nd), "mean_rent": float(tot)}
        for key, label in [("pass", "이용권"), ("age2", "연령대"), ("band", "시간대")]:
            s = h.groupby(key)["rent"].sum() / nd
            for k, v in s.items():
                rows.append({"group": gname, "dim": label, "cat": k, "mean_rent": float(v), "share_pct": float(100 * v / tot)})
                S[gname][f"{label}:{k}"] = {"mean_rent": float(v), "share_pct": float(100 * v / tot)}
    E = pd.DataFrame(rows)
    E.to_csv(RES / "exposure_shares.csv", index=False, encoding="utf-8-sig")
    # 폭염일 하루에 남는 이용: 정기권, 60대 이상, 10~15시, 정기권 05~09시
    h35 = H[H.date.isin(groups["ge35"])]
    nd = len(groups["ge35"])
    S["ge35_remaining"] = {"total": float(h35["rent"].sum() / nd),
                           "정기권": float(h35.loc[h35["pass"] == "정기권", "rent"].sum() / nd),
                           "60대이상": float(h35.loc[h35["age2"] == "60대이상", "rent"].sum() / nd),
                           "10-15시": float(h35.loc[h35["band"] == "10-15", "rent"].sum() / nd),
                           "10-15시_60대이상": float(h35.loc[(h35["band"] == "10-15") & (h35["age2"] == "60대이상"), "rent"].sum() / nd),
                           "정기권_05-09시": float(h35.loc[(h35["pass"] == "정기권") & (h35["band"] == "05-09"), "rent"].sum() / nd),
                           "정기권_16-19시": float(h35.loc[(h35["pass"] == "정기권") & (h35["band"] == "16-19"), "rent"].sum() / nd)}
    # 35℃ 이상 날의 시간대별 대여(그림용) vs 기준일
    hb = H[H.date.isin(groups["ge35"])].groupby("hour")["rent"].sum() / nd
    rb = H[H.date.isin(groups["ref"])].groupby("hour")["rent"].sum() / len(groups["ref"])
    pd.DataFrame({"hour": hb.index, "ge35": hb.values, "ref": rb.reindex(hb.index).values}).to_csv(RES / "hourly_profile.csv", index=False, encoding="utf-8-sig")
    (RES / "exposure_summary.json").write_text(json.dumps(S, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(S["ge35_remaining"], ensure_ascii=False, indent=1))
    print(E[E.dim == "이용권"].to_string())
    print(E[(E.dim == "연령대") & (E.cat == "60대이상")].to_string())
    print(E[E.dim == "시간대"].to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
