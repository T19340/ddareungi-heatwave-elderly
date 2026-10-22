# -*- coding: utf-8 -*-
"""
24_elderly.py — 60대 이상 이용의 성격과 폭염일의 조정 방식 (2025년 7~8월 평일, 원자료 재집계)

비교 틀: 2025년 7~8월 무강수·비공휴일 평일. 폭염일 = 최고기온 35℃ 이상(8일), 기준일 = 27~33℃(10일). 23_exposure_gap.py 와 같다.
원자료 월 CSV(2025-07·08)를 다시 읽어 연령대(8종)·이용권·성별·이동거리·이용시간을 쓴다.
  (a) 연령대별 이용 성격(기준일): 정기권 비율, 회당 거리(km) = Σ이동거리 ÷ Σ건수, 회당 시간(분) = Σ이용시간 ÷ Σ건수,
      평균속도(km/h) = Σ거리 ÷ Σ시간(정차·대기 포함), 남성 비율(성별 미상 포함 분모), 하루 평균 건수(기준일·폭염일)와 비율.
  (b) 시간별 이용 비중 곡선(기준일, 각 연령대 하루 건수 대비 %)과 폭염일/기준일 비율 곡선 — 60대·70대이상·20대·40대 + 묶음.
  (c) 대여소 유형 5종(이름 낱말 추정: 주거형 → 공원·강변형 → 역세권형 → 생활시설형 → 기타)별 이용 구성 — 60+ vs 20~50대, 기준일.
  (d) 생활시설형 대여소 중 60+ 폭염 평일 이용 상위(전일 운영 대여소만), 60+ 상위 30 의 유형.
출력: results/age_profile_2025.csv, hour_share_by_age_2025.csv, hour_ratio_by_age4_2025.csv, type_composition_2025.csv,
      station_elderly_facility_2025.csv, station_elderly_2025_typed.csv, elderly_summary.json
실행: python -P -E -X utf8 code/24_elderly.py  (약 30초)
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, RES = ROOT / "data_raw", ROOT / "data_proc", ROOT / "results"
MONTHS = ["202507", "202508"]
AGES = ["~10대", "20대", "30대", "40대", "50대", "60대", "70대이상"]
A4 = ["20대", "40대", "60대", "70대이상"]
GROUPS = {"60+": ["60대", "70대이상"], "20-50대": ["20대", "30대", "40대", "50대"], "10대": ["~10대"]}


def classify5(name: str) -> str:
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


def read_month(m: str, keep: set) -> pd.DataFrame:
    f = RAW / "따릉이" / f"서울특별시 공공자전거 이용정보(시간대별)_{m}.csv"
    head = pd.read_csv(f, encoding="cp949", nrows=0).columns.tolist()
    dcol = [c for c in head if c.startswith("이동거리")][0]
    mcol = [c for c in head if c.startswith("이용시간")][0]
    use = ["대여일자", "대여시간", "대여소번호", "대여구분코드", "성별", "연령대코드", "이용건수", dcol, mcol]
    df = pd.read_csv(f, encoding="cp949", usecols=use, dtype={"대여일자": str, "대여소번호": str, "대여구분코드": str, "성별": str, "연령대코드": str})
    df["date"] = df["대여일자"].str.slice(0, 10)
    df = df[df["date"].isin(keep)].copy()
    df["hour"] = df["대여시간"].astype(int)
    df["stn"] = df["대여소번호"].str.lstrip("0").replace("", "0").astype(int)
    df["pass"] = df["대여구분코드"].str.replace(r"\(.*?\)", "", regex=True).str.strip()
    df["sex"] = df["성별"].fillna("").str.upper().str.strip().replace("", "미상")
    df["age"] = df["연령대코드"].str.strip()
    df["rent"] = df["이용건수"].astype(int)
    df["dist"] = pd.to_numeric(df[dcol], errors="coerce").fillna(0.0)
    df["mins"] = pd.to_numeric(df[mcol], errors="coerce").fillna(0).astype(int)
    return df[["date", "hour", "stn", "pass", "sex", "age", "rent", "dist", "mins"]]


def main() -> int:
    D = pd.read_csv(PROC / "daily_total_weather.csv")
    D = D[(D.year == 2025) & (D.month.isin([7, 8])) & (D.sumRn == 0) & (D.hol == 0) & (D.wkend == 0)].copy()
    # mid = 33~35℃ 평일: 본 분석에는 쓰지 않고 33℃ 경계 민감도(폭염 평일을 33℃ 이상으로 넓힘)에만 쓴다
    D["cls"] = np.where(D.maxTa >= 35, "hot", np.where((D.maxTa >= 27) & (D.maxTa < 33), "ref", np.where(D.maxTa >= 33, "mid", "")))
    D = D[D.cls != ""]
    hot_days, ref_days = sorted(D.loc[D.cls == "hot", "date"]), sorted(D.loc[D.cls == "ref", "date"])
    mid_days = sorted(D.loc[D.cls == "mid", "date"])
    nh, nr = len(hot_days), len(ref_days)
    raw = pd.concat([read_month(m, set(D.date)) for m in MONTHS], ignore_index=True).merge(D[["date", "cls"]], on="date")
    st = pd.read_csv(PROC / "stations.csv")
    name_of = st.set_index("stn")["name"]
    raw["agegrp"] = "기타"
    for g, members in GROUPS.items():
        raw.loc[raw.age.isin(members), "agegrp"] = g
    MID = raw[raw.cls == "mid"].copy()
    raw = raw[raw.cls != "mid"].copy()
    H, R = raw[raw.cls == "hot"], raw[raw.cls == "ref"]
    S = {"hot_days": hot_days, "ref_days": ref_days}

    # ---------------- (a) 연령대별 이용 성격
    def profile(sub, n_days, key_col, keys):
        rows = []
        for k in keys:
            g = sub[sub[key_col] == k] if key_col else sub
            rent, dist, mins = g.rent.sum(), g.dist.sum(), g.mins.sum()
            rows.append({key_col or "all": k, "rent_per_day": rent / n_days, "seasonal_pass_pct": 100 * g.loc[g["pass"] == "정기권", "rent"].sum() / rent,
                         "daily_pass_pct": 100 * g.loc[g["pass"] == "일일권", "rent"].sum() / rent,
                         "km_per_trip": dist / rent / 1000, "min_per_trip": mins / rent, "kmh": (dist / 1000) / (mins / 60),
                         "male_pct": 100 * g.loc[g.sex == "M", "rent"].sum() / rent, "female_pct": 100 * g.loc[g.sex == "F", "rent"].sum() / rent,
                         "sex_unknown_pct": 100 * g.loc[~g.sex.isin(["M", "F"]), "rent"].sum() / rent,
                         "ph_per_day": mins / 60 / n_days})
        return pd.DataFrame(rows)

    pr = profile(R, nr, "age", AGES).set_index("age")
    ph = profile(H, nh, "age", AGES).set_index("age")
    pg_r = profile(R, nr, "agegrp", ["60+", "20-50대", "10대"]).set_index("agegrp")
    pg_h = profile(H, nh, "agegrp", ["60+", "20-50대", "10대"]).set_index("agegrp")
    prof = pd.concat([pr, pg_r]).add_prefix("ref_").join(pd.concat([ph, pg_h]).add_prefix("hot_"))
    prof["ratio_hot_ref"] = prof["hot_rent_per_day"] / prof["ref_rent_per_day"]
    prof.index.name = "age"
    prof.reset_index().to_csv(RES / "age_profile_2025.csv", index=False, encoding="utf-8-sig")
    S["profile"] = {k: {c: float(v) for c, v in r.items()} for k, r in prof.iterrows()}
    allr = profile(R, nr, None, ["all"]).iloc[0]
    S["profile_all_ref"] = {c: float(v) for c, v in allr.items() if c != "all"}

    # ---------------- (b) 시간별 비중·비율 곡선
    def hourly(sub, n_days, key, keys):
        out = {}
        for k in keys:
            g = sub[sub[key] == k].groupby("hour").rent.sum().reindex(range(24), fill_value=0) / n_days
            out[k] = g
        return out

    hr_r, hr_h = hourly(R, nr, "age", AGES), hourly(H, nh, "age", AGES)
    gr_r, gr_h = hourly(R, nr, "agegrp", ["60+", "20-50대"]), hourly(H, nh, "agegrp", ["60+", "20-50대"])
    rows_share, rows_ratio = [], []
    for k in AGES + ["60+", "20-50대"]:
        r_ = hr_r[k] if k in hr_r else gr_r[k]
        h_ = hr_h[k] if k in hr_h else gr_h[k]
        for hh in range(24):
            rows_share.append({"age": k, "hour": hh, "ref_per_day": r_[hh], "ref_share_pct": 100 * r_[hh] / r_.sum(), "hot_per_day": h_[hh], "hot_share_pct": 100 * h_[hh] / h_.sum()})
            rows_ratio.append({"age": k, "hour": hh, "ratio": h_[hh] / r_[hh] if r_[hh] else np.nan})
    pd.DataFrame(rows_share).to_csv(RES / "hour_share_by_age_2025.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(rows_ratio).to_csv(RES / "hour_ratio_by_age4_2025.csv", index=False, encoding="utf-8-sig")
    S["hour_share_ref"] = {k: {str(hh): float(100 * (hr_r[k] if k in hr_r else gr_r[k])[hh] / (hr_r[k] if k in hr_r else gr_r[k]).sum()) for hh in range(24)} for k in A4 + ["60+", "20-50대"]}
    S["hour_ratio"] = {k: {str(hh): float((hr_h[k] if k in hr_h else gr_h[k])[hh] / (hr_r[k] if k in hr_r else gr_r[k])[hh]) for hh in range(24)} for k in A4 + ["60+", "20-50대"]}
    for k in ["60+", "60대", "70대이상", "20-50대"]:
        rr = S["hour_ratio"][k]
        S.setdefault("hour_ratio_summary", {})[k] = {"06-07": float(np.mean([rr["6"], rr["7"]])), "12-14": float(np.mean([rr["12"], rr["13"], rr["14"]])),
                                                     "13-16": float(np.mean([rr[str(h)] for h in range(13, 17)])), "20": rr["20"], "min_hour": int(min(range(5, 23), key=lambda h: rr[str(h)])),
                                                     "min_ratio": float(min(rr[str(h)] for h in range(5, 23)))}
    sh60, sh70 = S["hour_share_ref"]["60대"], S["hour_share_ref"]["70대이상"]
    S["peaks"] = {"60대_am": {h: sh60[h] for h in ("6", "7", "8")}, "60대_pm": {h: sh60[h] for h in ("16", "17", "18")}, "70대이상_am": {h: sh70[h] for h in ("7", "8", "9", "10")},
                  "60+_day_share_10_19": float(sum(S["hour_share_ref"]["60+"][str(h)] for h in range(10, 20))),
                  "20-50대_day_share_10_19": float(sum(S["hour_share_ref"]["20-50대"][str(h)] for h in range(10, 20)))}

    # ---------------- (c) 대여소 유형 구성 (기준일·폭염일)
    raw["name"] = raw["stn"].map(name_of)
    raw["type5"] = raw["name"].map(lambda x: classify5(x) if pd.notna(x) else "미상")
    comp = []
    for cls_, sub, nd in (("ref", R.assign(type5=raw.loc[R.index, "type5"]), nr), ("hot", H.assign(type5=raw.loc[H.index, "type5"]), nh)):
        for g in ["60+", "20-50대", "60대", "70대이상"]:
            gg = sub[sub.agegrp == g] if g in GROUPS else sub[sub.age == g]
            tot = gg.loc[gg.type5 != "미상", "rent"].sum()
            for t in ["역세권형", "주거형", "생활시설형", "공원·강변형", "기타"]:
                comp.append({"cls": cls_, "group": g, "type": t, "rent_per_day": gg.loc[gg.type5 == t, "rent"].sum() / nd, "share_pct": 100 * gg.loc[gg.type5 == t, "rent"].sum() / tot})
    comp = pd.DataFrame(comp)
    comp.to_csv(RES / "type_composition_2025.csv", index=False, encoding="utf-8-sig")
    S["type_composition_ref"] = {g: {r.type: float(r.share_pct) for _, r in comp[(comp.cls == "ref") & (comp.group == g)].iterrows()} for g in ["60+", "20-50대"]}
    S["type_composition_hot"] = {g: {r.type: float(r.share_pct) for _, r in comp[(comp.cls == "hot") & (comp.group == g)].iterrows()} for g in ["60+", "20-50대"]}
    S["n_stations_typed"] = int(st.name.map(classify5).value_counts().to_dict() and len(st))
    S["type_counts_master"] = {k: int(v) for k, v in st.name.map(classify5).value_counts().items()}

    # ---------------- (d) 전일 운영 대여소, 60+ 상위·생활시설형 상위
    cov = raw.groupby("stn").date.nunique()
    full = set(cov[cov == nh + nr].index)
    S["n_full_operation"] = len(full)
    S["n_full_in_master"] = int(len([x for x in full if x in set(st.stn)]))
    e_h = H[(H.agegrp == "60+") & H.stn.isin(full)].groupby("stn").rent.sum() / nh
    e_r = R[(R.agegrp == "60+") & R.stn.isin(full)].groupby("stn").rent.sum() / nr
    a_h = H[H.stn.isin(full)].groupby("stn").rent.sum() / nh
    t = pd.DataFrame({"hot60_per_day": e_h}).join(pd.DataFrame({"ref60_per_day": e_r}), how="outer").fillna(0)
    t["ratio60"] = t["hot60_per_day"] / t["ref60_per_day"].replace(0, np.nan)
    t["station_hot_per_day"] = a_h.reindex(t.index)
    t["share60_pct"] = 100 * t["hot60_per_day"] / t["station_hot_per_day"]
    t = t.join(st.set_index("stn")[["name", "gu", "lat", "lon"]], how="left")
    t["in_master"] = t["name"].notna()
    t["type5"] = t["name"].map(lambda x: classify5(x) if pd.notna(x) else "미상")
    t = t[t.in_master].sort_values("hot60_per_day", ascending=False)
    t["rank"] = np.arange(1, len(t) + 1)
    t.reset_index().to_csv(RES / "station_elderly_2025_typed.csv", index=False, encoding="utf-8-sig")
    S["n_full_in_master_with60"] = int(len(t))
    fac = t[t.type5 == "생활시설형"].copy()
    fac["rank_fac"] = np.arange(1, len(fac) + 1)
    fac.reset_index().to_csv(RES / "station_elderly_facility_2025.csv", index=False, encoding="utf-8-sig")
    top30 = t.head(30)
    S["elderly_top30"] = {"sum_hot60": float(top30.hot60_per_day.sum()), "share_of_all60_pct": float(100 * top30.hot60_per_day.sum() / t.hot60_per_day.sum()),
                          "types": top30.type5.value_counts().to_dict(), "gu": top30.gu.value_counts().to_dict(), "ratio_median": float(top30.ratio60.median()),
                          "top5": top30.head(5)[["name", "gu", "hot60_per_day", "ratio60", "type5"]].reset_index().to_dict("records")}
    S["facility_top"] = {"n_facility_stations": int(len(fac)), "sum_hot60_top20": float(fac.head(20).hot60_per_day.sum()),
                         "top5": fac.head(5)[["name", "gu", "hot60_per_day", "ratio60"]].reset_index().to_dict("records")}
    S["n_stations_ge10_60"] = int((t.hot60_per_day >= 10).sum())
    S["n_stations_ge5_60"] = int((t.hot60_per_day >= 5).sum())
    # ---------------- 민감도: 비교 평일 기간 한정, 폭염·비교 평일 모두 7/21~8/11 한정, 10대 제외
    def ratio_for(sub_h, sub_r, days_h, days_r, filt=None):
        hh = sub_h[sub_h.date.isin(days_h)]
        rr = sub_r[sub_r.date.isin(days_r)]
        if filt is not None:
            hh, rr = hh[filt(hh)], rr[filt(rr)]
        return float((hh.rent.sum() / len(days_h)) / (rr.rent.sum() / len(days_r)))

    ref_late = [d for d in ref_days if d >= "2025-07-21"]
    hot_mid = [d for d in hot_days if "2025-07-21" <= d <= "2025-08-11"]
    ref_mid = [d for d in ref_days if "2025-07-21" <= d <= "2025-08-11"]
    S["sensitivity"] = {
        "ref_late_days": ref_late, "hot_mid_days": hot_mid, "ref_mid_days": ref_mid,
        "base": {"60+": float(S["profile"]["60+"]["ratio_hot_ref"]), "20-50대": float(S["profile"]["20-50대"]["ratio_hot_ref"]),
                 "all": ratio_for(H, R, hot_days, ref_days), "all_excl_10대": ratio_for(H, R, hot_days, ref_days, lambda d: d.age != "~10대")},
        "ref_late": {"60+": ratio_for(H, R, hot_days, ref_late, lambda d: d.agegrp == "60+"), "20-50대": ratio_for(H, R, hot_days, ref_late, lambda d: d.agegrp == "20-50대"),
                     "all": ratio_for(H, R, hot_days, ref_late), "all_excl_10대": ratio_for(H, R, hot_days, ref_late, lambda d: d.age != "~10대")},
        "mid_window": {"60+": ratio_for(H, R, hot_mid, ref_mid, lambda d: d.agegrp == "60+"), "20-50대": ratio_for(H, R, hot_mid, ref_mid, lambda d: d.agegrp == "20-50대"),
                       "all": ratio_for(H, R, hot_mid, ref_mid)},
    }
    # 33℃ 경계 민감도: 폭염 평일 = 최고기온 33℃ 이상 평일(35℃ 이상 + 33~35℃), 비교 평일은 그대로
    h33 = pd.concat([H, MID], ignore_index=True)
    n33 = nh + len(mid_days)
    e60, e60b = h33[h33.agegrp == "60+"], H[H.agegrp == "60+"]
    r60 = R[R.agegrp == "60+"].rent.sum() / nr
    S["sensitivity"]["thr33"] = {
        "mid_days": mid_days, "n_hot33": int(n33),
        "ratio60": float((e60.rent.sum() / n33) / r60),
        "ratio2050": float((h33[h33.agegrp == "20-50대"].rent.sum() / n33) / (R[R.agegrp == "20-50대"].rent.sum() / nr)),
        "ratio_all": float((h33.rent.sum() / n33) / (R.rent.sum() / nr)),
        "rent60_per_day": float(e60.rent.sum() / n33),
        "day_ph60_per_day": float(e60[e60.hour.between(10, 19)].mins.sum() / 60 / n33),
        "min_per_trip60": float(e60.mins.sum() / e60.rent.sum()),
        "base_day_ph60_per_day": float(e60b[e60b.hour.between(10, 19)].mins.sum() / 60 / nh),
        "base_rent60_per_day": float(e60b.rent.sum() / nh)}
    # 10대 7시 비율(방학 효과 참고)
    t7h = H[(H.age == "~10대") & (H.hour == 7)].rent.sum() / nh
    t7r = R[(R.age == "~10대") & (R.hour == 7)].rent.sum() / nr
    S["sensitivity"]["teen_7h_ratio"] = float(t7h / t7r)
    # 날짜별 범위: 폭염 평일 각 날의 (해당 시간 건수) ÷ (비교 평일 평균)
    rng = {}
    for lab, hours in [("06-07", (6, 7)), ("12-16", (12, 13, 14, 15, 16)), ("12-14", (12, 13, 14)), ("20", (20,))]:
        rmean = R[(R.agegrp == "60+") & (R.hour.isin(hours))].rent.sum() / nr
        vals = [H[(H.agegrp == "60+") & (H.hour.isin(hours)) & (H.date == d)].rent.sum() / rmean for d in hot_days]
        rng[lab] = {"min": float(min(vals)), "max": float(max(vals))}
    S["daily_ratio_range_60+"] = rng
    (RES / "elderly_summary.json").write_text(json.dumps(S, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print("sensitivity", json.dumps(S["sensitivity"], ensure_ascii=False))
    print("daily ranges", json.dumps(rng, ensure_ascii=False))
    print(prof[["ref_rent_per_day", "hot_rent_per_day", "ratio_hot_ref", "ref_seasonal_pass_pct", "ref_km_per_trip", "ref_min_per_trip", "ref_kmh", "ref_male_pct", "ref_sex_unknown_pct"]].round(2).to_string())
    print("all ref:", {k: round(v, 2) for k, v in S["profile_all_ref"].items()})
    print("peaks", json.dumps(S["peaks"], ensure_ascii=False))
    print("hour_ratio_summary", json.dumps(S["hour_ratio_summary"], ensure_ascii=False))
    print("type comp ref", json.dumps(S["type_composition_ref"], ensure_ascii=False))
    print("type comp hot", json.dumps(S["type_composition_hot"], ensure_ascii=False))
    print("master type counts", S["type_counts_master"], "full", S["n_full_operation"])
    print("elderly top30", json.dumps(S["elderly_top30"], ensure_ascii=False)[:600])
    print("facility", json.dumps(S["facility_top"], ensure_ascii=False)[:600])
    return 0


if __name__ == "__main__":
    sys.exit(main())
