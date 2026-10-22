# -*- coding: utf-8 -*-
"""
00_download.py — 서울 열린데이터광장 파일 내려받기 (재현용; 이미 받은 파일은 건너뜀)

- OA-15245 「서울시 공공자전거 따릉이 이용정보(시간대별)」 월별 CSV: 2024-06~09, 2025-06~09, 2026-06
- OA-13252 「서울시 공공자전거 따릉이 대여소 정보」 최신 XLSX(26.6월 기준)
- 두 데이터 모두 공공누리 1유형(출처표시), 로그인·키 없이 내려받는 공개 파일이다.
- 페이지의 파일 목록 행(<tr>)에서 파일명과 downloadFile('seq')의 seq 를 읽고, 페이지의 자바스크립트가 보내는 것과 같은
  POST(https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?&useCache=false, 폼 필드 infId·infSeq·seq)로 받는다.
  파일당 1회 요청이며 목록 조회 외의 자동 탐색은 하지 않는다.
- 받은 파일은 data_raw/따릉이/ 에 서버가 준 파일명 그대로 두고 수정하지 않는다. _download_log.json 에 URL·일시·바이트·sha256.

실행: python -P -E -X utf8 code/00_download.py [--list] [--months 202406,202407,...]
"""
import argparse
import hashlib
import json
import re
import sys
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data_raw" / "따릉이"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) traffic-contest-2026-cand6/1.0"}
PAGE = "https://data.seoul.go.kr/dataList/{inf}/F/{seq}/datasetView.do"
DL = "https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?&useCache=false"
MONTHS = ["202406", "202407", "202408", "202409", "202506", "202507", "202508", "202509", "202606"]


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


def list_files(inf_id: str, inf_seq: str = "1") -> list[tuple[str, str]]:
    """데이터셋 페이지의 파일 목록 → [(파일명, seq)]"""
    r = requests.get(PAGE.format(inf=inf_id, seq=inf_seq), headers=UA, timeout=60)
    r.raise_for_status()
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", r.text, flags=re.S):
        m = re.search(r"downloadFile\('(\d+)'\)", tr)
        if not m:
            continue
        cells = [" ".join(re.sub(r"<[^>]+>", " ", c).split()) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
        names = [c for c in cells if re.search(r"\.(?:csv|xlsx|zip|xls)$", c, flags=re.I)]
        if names:
            out.append((names[0], m.group(1)))
    return out


def download(inf_id: str, inf_seq: str, seq: str, name: str) -> Path:
    out = RAW / name
    if out.exists():
        print(f"  건너뜀(이미 있음): {name} ({out.stat().st_size:,} B)")
        return out
    RAW.mkdir(parents=True, exist_ok=True)
    t0 = datetime.now()
    with requests.post(DL, data={"infId": inf_id, "infSeq": inf_seq, "seq": seq}, headers=UA, timeout=600, stream=True) as r:
        r.raise_for_status()
        cd = r.headers.get("Content-Disposition", "")
        m = re.search(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)", cd)
        if m:
            server_name = urllib.parse.unquote(m.group(1)).strip()
            out = RAW / server_name
        tmp = out.with_suffix(out.suffix + ".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
        tmp.rename(out)
    log_download({"source": f"서울 열린데이터광장 {inf_id}", "page": PAGE.format(inf=inf_id, seq=inf_seq), "url": DL,
                  "form": {"infId": inf_id, "infSeq": inf_seq, "seq": seq}, "file": out.name, "bytes": out.stat().st_size,
                  "sha256": sha256(out), "downloaded_at": t0.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"  저장: {out.name} ({out.stat().st_size:,} B)")
    time.sleep(1.0)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="파일 목록만 출력")
    ap.add_argument("--months", default=",".join(MONTHS))
    a = ap.parse_args()
    months = [m.strip() for m in a.months.split(",") if m.strip()]
    print("[열린데이터광장] OA-15245 이용정보(시간대별) 목록")
    files = list_files("OA-15245")
    print(f"  목록 {len(files)}개")
    want = [(n, s) for n, s in files if any(f"_{m}" in n for m in months)]
    for n, s in want:
        print(f"  {n}  seq={s}")
    print("[열린데이터광장] OA-13252 대여소 정보 목록")
    files2 = list_files("OA-13252")
    stn = [(n, s) for n, s in files2 if n.lower().endswith(".xlsx")]
    if stn:
        print(f"  최신: {stn[0][0]}  seq={stn[0][1]}")
    if a.list:
        return 0
    for n, s in want:
        download("OA-15245", "1", s, n)
    if stn:
        download("OA-13252", "1", stn[0][1], stn[0][0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
