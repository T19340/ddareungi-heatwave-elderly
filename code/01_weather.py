# -*- coding: utf-8 -*-
"""
01_weather.py — 기상 자료 수집 (서울 108 지점)

(1) 기상청 ASOS 일자료(공공데이터포털 오픈API 15059093): data_raw/기상/asos_seoul108_daily_2024_2026.csv
    - 인증키는 환경변수 DATA_GO_KR_KEY 또는 ..\\..\\.secrets\\DATA_GO_KR_KEY.txt 에서만 읽고, 코드·로그·출력에 적지 않는다.
    - 파일이 이미 있으면 건너뛴다(--force 로 다시 받음).
(2) 기상청 기상자료개방포털 > 기후통계분석 > 기상현상일수 > 폭염일수(일최고기온 33℃ 이상), 지점 서울(108), 1973~올해:
    로그인 없이 화면 조회 폼이 돌려주는 HTML 표를 data_raw/기상/heatwave_chart_stn108_*.html 로 저장(파싱은 10_clean.py).
(3) 받은 파일의 URL·일시·바이트·sha256 을 data_raw/기상/_download_log.json 에 남긴다.

실행: python -P -E -X utf8 code/01_weather.py [--force] [--skip-asos] [--skip-heatwave]
"""
import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data_raw" / "기상"
RAW.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) traffic-contest-2026-cand6/1.0"}
STN, STN_NAME = "108", "서울"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def log_download(record: dict) -> None:
    p = RAW / "_download_log.json"
    log = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    log.append(record)
    p.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")


def read_key() -> str | None:
    """인증키: 환경변수 → 프로젝트 루트 .secrets 파일. 값은 절대 출력하지 않는다."""
    k = os.environ.get("DATA_GO_KR_KEY", "").strip()
    if k:
        return k
    f = ROOT.parent / ".secrets" / "DATA_GO_KR_KEY.txt"
    if f.exists():
        k = f.read_text(encoding="utf-8").strip()
        return k or None
    return None


def download_asos_daily(force: bool) -> None:
    out = RAW / "asos_seoul108_daily_2024_2026.csv"
    if out.exists() and not force:
        print(f"  건너뜀(이미 있음): {out.name} ({out.stat().st_size:,} B)")
        return
    key = read_key()
    if not key:
        print("  [막힘] 인증키 없음: 환경변수 DATA_GO_KR_KEY 또는 .secrets/DATA_GO_KR_KEY.txt (공공데이터포털 15059093 활용신청, 자동승인)")
        return
    url = "http://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"
    cols = ["stnId", "stnNm", "tm", "avgTa", "minTa", "maxTa", "sumRn", "avgRhm", "sumSsHr", "avgWs"]
    rows = []
    today = datetime.now().strftime("%Y%m%d")
    windows = [("20240601", "20240930"), ("20250601", "20250930"), ("20260601", min("20261031", today))]
    for start, end in windows:
        page = 1
        while True:
            params = {"serviceKey": key, "pageNo": page, "numOfRows": 999, "dataType": "JSON", "dataCd": "ASOS",
                      "dateCd": "DAY", "startDt": start, "endDt": end, "stnIds": STN}
            r = requests.get(url, params=params, headers=UA, timeout=120)
            r.raise_for_status()
            js = r.json()
            body = js["response"]["body"]
            items = body.get("items", {}).get("item", []) if body.get("items") else []
            for it in items:
                rows.append([it.get(c, "") for c in cols])
            total = int(body.get("totalCount", 0))
            if page * 999 >= total or not items:
                break
            page += 1
            time.sleep(0.3)
        time.sleep(0.3)
    import csv
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    log_download({"source": "기상청 지상(종관, ASOS) 일자료 조회서비스(공공데이터포털 15059093)", "url": url,
                  "params": "stnIds=108, dateCd=DAY, 2024-06-01~2024-09-30, 2025-06-01~2025-09-30, 2026-06-01~조회일 (인증키 생략)",
                  "file": out.name, "rows": len(rows), "bytes": out.stat().st_size, "sha256": sha256(out),
                  "downloaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    print(f"  저장: {out.name} ({len(rows)}행)")


def download_kma_heatwave(force: bool, start_year: int = 1973, end_year: int | None = None) -> Path | None:
    """기상자료개방포털 폭염일수 화면 조회(POST). ④ 과제에서 대전(133)으로 성공한 요청과 같은 폼 필드."""
    end_year = end_year or datetime.now().year
    existing = sorted(RAW.glob(f"heatwave_chart_stn{STN}_*.html"))
    if existing and not force:
        print(f"  건너뜀(이미 있음): {existing[-1].name}")
        return existing[-1]
    url = "https://data.kma.go.kr/climate/heatWave/selectHeatWaveChart.do"
    s = requests.Session()
    s.get(url, headers=UA, timeout=60)
    data = {"pgmNo": "106", "menuNo": "549", "serviceSe": "F00101", "selectType": "1", "mddlClssCd": "SFC01",
            "maxTa": "33.0", "schType": "2", "schStnId": STN, "txtStnNm": STN_NAME,
            "startYear": str(start_year), "endYear": str(end_year), "firstLoading": "N"}
    t0 = datetime.now()
    r = s.post(url, data=data, headers=dict(UA, Referer=url), timeout=120)
    r.raise_for_status()
    if "연합계" not in r.text:
        print("  [실패] 응답에 폭염일수 표가 없음(화면 구조 변경 가능). 저장하지 않음.")
        return None
    out = RAW / f"heatwave_chart_stn{STN}_{start_year}-{end_year}_{t0:%Y%m%d}.html"
    out.write_text(r.text, encoding="utf-8")
    log_download({"source": "기상청 기상자료개방포털 기후통계분석 > 기상현상일수 > 폭염일수(지점 서울 108)", "url": url,
                  "post_data": data, "file": out.name, "bytes": out.stat().st_size, "sha256": sha256(out),
                  "downloaded_at": t0.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"  저장: {out.name} ({out.stat().st_size:,} B)")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--skip-asos", action="store_true")
    ap.add_argument("--skip-heatwave", action="store_true")
    a = ap.parse_args()
    if not a.skip_asos:
        print("[기상청] ASOS 일자료 서울(108)")
        try:
            download_asos_daily(a.force)
        except Exception as e:  # 키·네트워크 오류는 메시지만(키 값은 포함되지 않음)
            print(f"  [실패] {type(e).__name__}")
    if not a.skip_heatwave:
        print("[기상청] 폭염일수 서울(108) 1973~")
        try:
            download_kma_heatwave(a.force)
        except Exception as e:
            print(f"  [실패] {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
