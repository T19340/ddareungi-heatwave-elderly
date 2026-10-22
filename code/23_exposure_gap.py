# -*- coding: utf-8 -*-
"""
23_exposure_gap.py — 폭염일에 누가·어디서 노출이 남는가 (연령군·이용권·시간대·자치구·대여소)

비교 틀(같은 해 안): 2025년 7~8월, 무강수·비공휴일·평일. 폭염일 = 최고기온 35℃ 이상(8일), 기준일 = 27~33℃(10일).
  - 원자료 월 CSV(2024-07·08, 2025-07·08)를 다시 읽어 일 × 대여소 × 연령군(10대·20~50대·60+) × 이용권 × 시간대 집계를 만든다
    (연령 '기타'는 연령군 비교에서만 제외; mins = 이용시간(분) 합).
  - 노출 시간(명시간) = Σ 이용시간(분) ÷ 60. 회당 시간 = Σ 이용시간 ÷ Σ 이용건수. 낮 = 10~19시(시간대 10-15 + 16-19).
  - 대여소 목록은 비교 기간 평일 18일 전부에 대여 기록이 있는 '전일 운영' 대여소만(신설·폐쇄 대여소 제외).
  - 대여소 유형은 이름의 낱말로 추정: 공원·강변형(공원·한강·나루·강변·둔치·수변·천변·호수·체육) → 주거형(아파트·빌라·주공·단지·연립)
    → 역세권형(역) → 기타. 분류는 '추정'이며 보조 결과로만 쓴다.
출력(data_proc/, results/):
  data_proc/hot_ref_station_age_pass_band.csv, results/exposure_age_2025.csv, exposure_age_band_2025.csv, hour_ratio_by_age_2025.csv,
  gu_exposure_2025.csv, station_commute_2025.csv, station_elderly_2025.csv, station_type_2025.csv, type_summary_2025.csv, exposure_gap_summary.json
실행: python -P -E -X utf8 code/23_exposure_gap.py  (약 1분)
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, RES = ROOT / "data_raw", ROOT / "data_proc", ROOT / "results"
MONTHS = ["202407", "202408", "202507", "202508"]
BANDS = [(0, 4, "00-04"), (5, 9, "05-09"), (10, 15, "10-15"), (16, 19, "16-19"), (20, 23, "20-23")]
AGEGRP = {"~10대": "10대", "20대": "20-50대", "30대": "20-50대", "40대": "20-50대", "50대": "20-50대", "60대": "60+", "70대이상": "60+"}
TOPN = 30


def band(h):
    for lo, hi, nm in BANDS:
        if lo <= h <= hi:
            return nm


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


def read_month(m: str, keep_dates: set) -> pd.DataFrame:
    f = RAW / "따릉이" / f"서울특별시 공공자전거 이용정보(시간대별)_{m}.csv"
    head = pd.read_csv(f, encoding="cp949", nrows=0).columns.tolist()
    mins_col = [c for c in head if c.startswith("이용시간")][0]
    use = ["대여일자", "대여시간", "대여소번호", "대여구분코드", "연령대코드", "이용건수", mins_col]
    df = pd.read_csv(f, encoding="cp949", usecols=use, dtype={"대여일자": str, "대여소번호": str, "대여구분코드": str, "연령대코드": str})
    df["date"] = df["대여일자"].str.slice(0, 10)
    df = df[df["date"].isin(keep_dates)]
    df["hour"] = df["대여시간"].astype(int)
    df["stn"] = df["대여소번호"].str.lstrip("0").replace("", "0").astype(int)
    df["pass"] = df["대여구분코드"].str.replace(r"\(.*?\)", "", regex=True).str.strip()
    df["agegrp"] = df["연령대코드"].str.strip().map(AGEGRP).fillna("기타")
    df["rent"] = df["이용건수"].astype(int)
    df["mins"] = pd.to_numeric(df[mins_col], errors="coerce").fillna(0).astype(int)
    return df[["date", "hour", "stn", "pass", "agegrp", "rent", "mins"]]


def main() -> int:
    D = pd.read_csv(PROC / "daily_total_weather.csv")
    D = D[(D.month.isin([7, 8])) & (D.sumRn == 0) & (D.hol == 0)].copy()
    D["cls"] = np.where(D.maxTa >= 35, "hot", np.where((D.maxTa >= 27) & (D.maxTa < 33), "ref", ""))
    D = D[D.cls != ""]
    keep = set(D.date)
    raw = pd.concat([read_month(m, keep) for m in MONTHS], ignore_index=True)
    raw = raw.merge(D[["date", "cls", "year", "wkend"]], on="date")
    raw["band"] = raw["hour"].map(band)
    st = pd.read_csv(PROC / "stations.csv")
    name_of = st.set_index("stn")["name"]
    agg = raw.groupby(["date", "stn", "agegrp", "pass", "band"], as_index=False).agg(rent=("rent", "sum"), mins=("mins", "sum"))
    agg = agg.merge(D[["date", "cls", "year", "wkend"]], on="date")
    agg["name"] = agg["stn"].map(name_of)
    agg.to_csv(PROC / "hot_ref_station_age_pass_band.csv", index=False, encoding="utf-8-sig")
    S = {"days": {}}
    for y in (2024, 2025):
        for c in ("hot", "ref"):
            for w, nm in ((0, "weekday"), (1, "weekend")):
                S["days"][f"{y}|{c}|{nm}"] = sorted(D[(D.year == y) & (D.cls == c) & (D.wkend == w)].date.tolist())

    # ---------------- 2025년 평일
    A = agg[(agg.year == 2025) & (agg.wkend == 0)].copy()
    hot_days = S["days"]["2025|hot|weekday"]
    ref_days = S["days"]["2025|ref|weekday"]
    nh, nr = len(hot_days), len(ref_days)
    assert nh and nr
    H, R = A[A.cls == "hot"], A[A.cls == "ref"]
    S["n_hot_weekdays_2025"], S["n_ref_weekdays_2025"] = nh, nr

    def per_day(df, n, by):
        g = df.groupby(by).agg(rent=("rent", "sum"), mins=("mins", "sum"))
        g["rent_per_day"] = g["rent"] / n
        g["ph_per_day"] = g["mins"] / 60 / n
        g["min_per_trip"] = g["mins"] / g["rent"]
        return g

    # (a) 연령군
    H3, R3 = H[H.agegrp != "기타"], R[R.agegrp != "기타"]
    ha, ra = per_day(H3, nh, "agegrp"), per_day(R3, nr, "agegrp")
    day = per_day(H3[H3.band.isin(["10-15", "16-19"])], nh, "agegrp")
    rday = per_day(R3[R3.band.isin(["10-15", "16-19"])], nr, "agegrp")
    age = pd.DataFrame({"agegrp": ha.index, "hot_rent_per_day": ha.rent_per_day.values, "ref_rent_per_day": ra.reindex(ha.index).rent_per_day.values,
                        "ratio": (ha.rent_per_day / ra.reindex(ha.index).rent_per_day).values,
                        "hot_min_per_trip": ha.min_per_trip.values, "ref_min_per_trip": ra.reindex(ha.index).min_per_trip.values,
                        "hot_ph_per_day": ha.ph_per_day.values, "ref_ph_per_day": ra.reindex(ha.index).ph_per_day.values,
                        "hot_day_ph_per_day": day.reindex(ha.index).ph_per_day.values, "ref_day_ph_per_day": rday.reindex(ha.index).ph_per_day.values,
                        "hot_day_rent_per_day": day.reindex(ha.index).rent_per_day.values, "hot_day_min_per_trip": day.reindex(ha.index).min_per_trip.values})
    age["hot_day_share_pct"] = 100 * age["hot_day_ph_per_day"] / age["hot_day_ph_per_day"].sum()
    age.to_csv(RES / "exposure_age_2025.csv", index=False, encoding="utf-8-sig")
    S["age_2025"] = age.set_index("agegrp").to_dict("index")
    S["total_2025"] = {"hot_rent_per_day": float(H.rent.sum() / nh), "ref_rent_per_day": float(R.rent.sum() / nr),
                       "hot_ph_per_day": float(H.mins.sum() / 60 / nh), "hot_day_ph_per_day": float(H[H.band.isin(["10-15", "16-19"])].mins.sum() / 60 / nh),
                       "hot_rent_per_day_excl_etc": float(H3.rent.sum() / nh), "hot_ph_per_day_excl_etc": float(H3.mins.sum() / 60 / nh),
                       "etc_share_pct": float(100 * H[H.agegrp == "기타"].rent.sum() / H.rent.sum())}
    # (b) 연령군 × 시간대
    hb, rb = per_day(H3, nh, ["agegrp", "band"]), per_day(R3, nr, ["agegrp", "band"])
    ab = hb.join(rb, lsuffix="_hot", rsuffix="_ref")
    ab["ratio"] = ab["rent_per_day_hot"] / ab["rent_per_day_ref"]
    ab.reset_index().to_csv(RES / "exposure_age_band_2025.csv", index=False, encoding="utf-8-sig")
    S["age_band_2025"] = {f"{a}|{b}": {"hot_rent_per_day": float(r.rent_per_day_hot), "ratio": float(r.ratio), "hot_ph_per_day": float(r.ph_per_day_hot),
                                        "hot_min_per_trip": float(r.min_per_trip_hot)} for (a, b), r in ab.iterrows()}
    # (c) 이용권 × 시간대 (정기권 05~09시 등)
    hp, rp = per_day(H, nh, ["pass", "band"]), per_day(R, nr, ["pass", "band"])
    pb = hp.join(rp, lsuffix="_hot", rsuffix="_ref")
    pb["ratio"] = pb["rent_per_day_hot"] / pb["rent_per_day_ref"]
    pb.reset_index().to_csv(RES / "exposure_pass_band_2025.csv", index=False, encoding="utf-8-sig")
    S["pass_band_2025"] = {f"{p}|{b}": {"hot_rent_per_day": float(r.rent_per_day_hot), "ratio": float(r.ratio)} for (p, b), r in pb.iterrows()}
    hp2, rp2 = per_day(H, nh, "pass"), per_day(R, nr, "pass")
    S["pass_2025"] = {p: {"hot_rent_per_day": float(hp2.loc[p, "rent_per_day"]), "ratio": float(hp2.loc[p, "rent_per_day"] / rp2.loc[p, "rent_per_day"])} for p in hp2.index}
    # (d) 시간별 비율 곡선 (연령군)
    rw = raw[(raw.year == 2025) & (raw.wkend == 0)]
    hh = rw[(rw.cls == "hot") & (rw.agegrp != "기타")].groupby(["agegrp", "hour"]).rent.sum() / nh
    rh = rw[(rw.cls == "ref") & (rw.agegrp != "기타")].groupby(["agegrp", "hour"]).rent.sum() / nr
    hr = pd.DataFrame({"hot_per_day": hh, "ref_per_day": rh}).reset_index()
    hr["ratio"] = hr["hot_per_day"] / hr["ref_per_day"]
    hr.to_csv(RES / "hour_ratio_by_age_2025.csv", index=False, encoding="utf-8-sig")
    S["hour_ratio_min"] = {a: {"hour": int(g.loc[g.ratio.idxmin(), "hour"]), "ratio": float(g.ratio.min())} for a, g in hr.groupby("agegrp")}
    S["hour_ratio_13_16"] = {a: float(g[g.hour.between(13, 16)].ratio.mean()) for a, g in hr.groupby("agegrp")}
    S["hour_ratio_13_16_minmax"] = {a: [float(g[g.hour.between(13, 16)].ratio.min()), float(g[g.hour.between(13, 16)].ratio.max())] for a, g in hr.groupby("agegrp")}
    hall = rw[rw.cls == "hot"].groupby("hour").rent.sum() / nh
    rall = rw[rw.cls == "ref"].groupby("hour").rent.sum() / nr
    pd.DataFrame({"hour": hall.index, "hot_per_day": hall.values, "ref_per_day": rall.reindex(hall.index).values,
                  "ratio": (hall / rall.reindex(hall.index)).values}).to_csv(RES / "hour_ratio_all_2025.csv", index=False, encoding="utf-8-sig")

    # ---------------- 전일 운영 대여소 (평일 20일 전부 기록)
    cov = A.groupby("stn").date.nunique()
    full = set(cov[cov == nh + nr].index)
    S["stations"] = {"n_in_period": int(A.stn.nunique()), "n_full_operation": len(full),
                     "n_all_31_days_incl_weekend": int((agg[agg.year == 2025].groupby("stn").date.nunique() == agg[agg.year == 2025].date.nunique()).sum())}
    AF = A[A.stn.isin(full)]
    HF, RF = AF[AF.cls == "hot"], AF[AF.cls == "ref"]
    meta = st.set_index("stn")[["name", "gu", "lat", "lon"]]

    def station_table(hsub, rsub, label):
        h = hsub.groupby("stn").rent.sum() / nh
        r = rsub.groupby("stn").rent.sum() / nr
        t = pd.DataFrame({"hot_per_day": h}).join(pd.DataFrame({"ref_per_day": r}), how="outer").fillna(0)
        t["ratio"] = t["hot_per_day"] / t["ref_per_day"].replace(0, np.nan)
        t = t.join(meta, how="left")
        t["in_master"] = t["name"].notna()
        return t.sort_values("hot_per_day", ascending=False)

    com = station_table(HF[(HF["pass"] == "정기권") & (HF.band == "05-09")], RF[(RF["pass"] == "정기권") & (RF.band == "05-09")], "commute")
    com["rank"] = np.arange(1, len(com) + 1)
    com.reset_index().to_csv(RES / "station_commute_2025.csv", index=False, encoding="utf-8-sig")
    eld = station_table(HF[HF.agegrp == "60+"], RF[RF.agegrp == "60+"], "elderly")
    tot_h = HF.groupby("stn").rent.sum() / nh
    eld["station_hot_per_day"] = tot_h.reindex(eld.index)
    eld["share60_pct"] = 100 * eld["hot_per_day"] / eld["station_hot_per_day"]
    eld["rank"] = np.arange(1, len(eld) + 1)
    eld.reset_index().to_csv(RES / "station_elderly_2025.csv", index=False, encoding="utf-8-sig")
    topc, tope = com.head(TOPN), eld.head(TOPN)
    S["commute_top"] = {"n_stations": int(len(com)), "top30_hot_sum_per_day": float(topc.hot_per_day.sum()), "top30_share_pct": float(100 * topc.hot_per_day.sum() / com.hot_per_day.sum()),
                        "top30_ratio_median": float(topc.ratio.median()), "top30_ratio_min": float(topc.ratio.min()), "top30_ratio_max": float(topc.ratio.max()),
                        "top30_n_ratio_ge_0_9": int((topc.ratio >= 0.9).sum()), "top30_gu": topc.gu.value_counts().to_dict(),
                        "top5": topc.head(5)[["name", "gu", "hot_per_day", "ratio"]].reset_index().to_dict("records"),
                        "all_commute_ratio": float(com.hot_per_day.sum() / com.ref_per_day.sum())}
    S["elderly_top"] = {"top30_hot_sum_per_day": float(tope.hot_per_day.sum()), "top30_share_pct": float(100 * tope.hot_per_day.sum() / eld.hot_per_day.sum()),
                        "top30_ratio_median": float(tope.ratio.median()), "top30_gu": tope.gu.value_counts().to_dict(),
                        "top5": tope.head(5)[["name", "gu", "hot_per_day", "ratio", "share60_pct"]].reset_index().to_dict("records"),
                        "n_stations_ge_10_per_day": int((eld.hot_per_day >= 10).sum()), "n_stations_ge_5_per_day": int((eld.hot_per_day >= 5).sum())}
    # ---------------- 자치구
    AFg = AF.merge(st[["stn", "gu"]], on="stn", how="left")
    AFg["gu"] = AFg["gu"].fillna("미상")

    def gu_table(mask_fn, label):
        h = AFg[(AFg.cls == "hot") & mask_fn(AFg)].groupby("gu").agg(rent=("rent", "sum"), mins=("mins", "sum"))
        r = AFg[(AFg.cls == "ref") & mask_fn(AFg)].groupby("gu").agg(rent=("rent", "sum"), mins=("mins", "sum"))
        t = pd.DataFrame({f"{label}_hot_per_day": h.rent / nh, f"{label}_ref_per_day": r.rent / nr, f"{label}_hot_ph_per_day": h.mins / 60 / nh})
        t[f"{label}_ratio"] = t[f"{label}_hot_per_day"] / t[f"{label}_ref_per_day"]
        return t

    gu = gu_table(lambda d: (d.agegrp == "60+") & d.band.isin(["10-15", "16-19"]), "eld_day")
    gu = gu.join(gu_table(lambda d: d.agegrp == "60+", "eld_all"))
    gu = gu.join(gu_table(lambda d: (d["pass"] == "정기권") & (d.band == "05-09"), "commute"))
    gu = gu.join(gu_table(lambda d: d.rent >= 0, "all"))
    gu = gu.sort_values("eld_day_hot_per_day", ascending=False)
    gu.reset_index().to_csv(RES / "gu_exposure_2025.csv", index=False, encoding="utf-8-sig")
    gu_known = gu[gu.index != "미상"]
    S["gu"] = {"top4_eld_day": gu_known.head(4)[["eld_day_hot_per_day", "eld_day_ratio"]].round(3).reset_index().to_dict("records"),
               "top4_eld_day_share_pct": float(100 * gu_known.head(4).eld_day_hot_per_day.sum() / gu_known.eld_day_hot_per_day.sum()),
               "top4_commute": gu_known.sort_values("commute_hot_per_day", ascending=False).head(4)[["commute_hot_per_day", "commute_ratio"]].round(3).reset_index().to_dict("records"),
               "eld_day_total": float(gu_known.eld_day_hot_per_day.sum()), "n_gu": int(len(gu_known)),
               "unknown_gu_share_pct": float(100 * gu.loc["미상", "all_hot_per_day"] / gu.all_hot_per_day.sum()) if "미상" in gu.index else 0.0}

    # ---------------- 대여소 유형 (21_station.py 의 전체 이용 비율에 4유형 적용)
    sr = pd.read_csv(RES / "station_ratio_2025.csv")
    sr = sr[sr.in_master].copy()
    sr["type"] = sr["name"].map(classify)
    sr.to_csv(RES / "station_type_2025.csv", index=False, encoding="utf-8-sig")
    ts = sr.groupby("type").agg(n=("stn", "size"), median_ratio=("ratio", "median"), q25=("ratio", lambda x: x.quantile(0.25)),
                                q75=("ratio", lambda x: x.quantile(0.75)), share_lt_0_8=("ratio", lambda x: 100 * (x < 0.8).mean()),
                                share_gt_1=("ratio", lambda x: 100 * (x > 1).mean()), sum_ref=("mean_ref", "sum")).reset_index()
    ts["total_ratio"] = sr.groupby("type").apply(lambda g: g.mean_hot.sum() / g.mean_ref.sum(), include_groups=False).reindex(ts.type).values
    ts = ts.sort_values("median_ratio")
    ts.to_csv(RES / "type_summary_2025.csv", index=False, encoding="utf-8-sig")
    kw = stats.kruskal(*[sr.loc[sr.type == k, "ratio"] for k in ts.type])
    mw = stats.mannwhitneyu(sr.loc[sr.type == "공원·강변형", "ratio"], sr.loc[sr.type == "주거형", "ratio"])
    S["type"] = {"summary": ts.round(4).to_dict("records"), "kruskal_p": float(kw.pvalue), "park_vs_resid_mw_p": float(mw.pvalue), "n": int(len(sr))}
    (RES / "exposure_gap_summary.json").write_text(json.dumps(S, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(json.dumps({k: S[k] for k in ["n_hot_weekdays_2025", "n_ref_weekdays_2025", "total_2025", "stations", "hour_ratio_13_16", "hour_ratio_min", "gu", "type", "pass_2025"]}, ensure_ascii=False, indent=1, default=float))
    print(age.round(2).to_string())
    print(ab.reset_index()[["agegrp", "band", "rent_per_day_hot", "ratio", "ph_per_day_hot", "min_per_trip_hot"]].round(2).to_string())
    print(topc[["name", "gu", "hot_per_day", "ref_per_day", "ratio"]].head(12).round(2).to_string())
    print(tope[["name", "gu", "hot_per_day", "ratio", "share60_pct"]].head(12).round(2).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
