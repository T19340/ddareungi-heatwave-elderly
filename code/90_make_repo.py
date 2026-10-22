# -*- coding: utf-8 -*-
"""
90_make_repo.py — 공개 저장소용 폴더 repo/ 조립 (원본 데이터 제외)

repo/
  README.md(원본 ../repo_README.md), requirements.txt, .gitignore
  code/            00~60 스크립트 + 이 스크립트
  report/template.html
  공통_논문양식/   paper.css + fonts/ (OFL·Pretendard 라이선스 동봉)
  data_raw/SOURCES.md
  results/         CSV·JSON·verification.md·reference_audit.md·readability_check.md
  figures/         PNG
  docs/            BRIEF.md 발췌본, SPEC.md 원문, 기준_요약문 ⑤, ai_usage_log.md
실행: python -P -E -X utf8 code/90_make_repo.py
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / "repo"
PROJ = ROOT.parent
if REPO.exists():
    shutil.rmtree(REPO)
for d in ["code", "report", "data_raw", "results", "figures", "docs", "공통_논문양식/fonts"]:
    (REPO / d).mkdir(parents=True, exist_ok=True)
for f in sorted((ROOT / "code").glob("*.py")):
    shutil.copy2(f, REPO / "code" / f.name)
shutil.copy2(ROOT / "report" / "template.html", REPO / "report" / "template.html")
shutil.copy2(ROOT / "report" / "readability_check.md", REPO / "results" / "readability_check.md")
if (ROOT / "results" / "participant_check.md").exists():
    shutil.copy2(ROOT / "results" / "participant_check.md", REPO / "results" / "participant_check.md")
shutil.copy2(PROJ / "공통_논문양식" / "paper.css", REPO / "공통_논문양식" / "paper.css")
for f in (PROJ / "공통_논문양식" / "fonts").iterdir():
    shutil.copy2(f, REPO / "공통_논문양식" / "fonts" / f.name)
shutil.copy2(ROOT / "data_raw" / "SOURCES.md", REPO / "data_raw" / "SOURCES.md")
for f in sorted((ROOT / "results").iterdir()):
    if f.suffix in (".csv", ".json", ".md", ".txt") and not f.name.startswith("_"):
        shutil.copy2(f, REPO / "results" / f.name)
for f in sorted((ROOT / "figures").glob("*.png")):
    shutil.copy2(f, REPO / "figures" / f.name)
shutil.copy2(ROOT / "SPEC.md", REPO / "docs" / "SPEC.md")
shutil.copy2(ROOT / "ai_usage_log.md", REPO / "docs" / "ai_usage_log.md")
brief = (PROJ / "BRIEF.md").read_text(encoding="utf-8")
brief_ex = brief.split("## 5. 환경 메모")[0]
brief_ex = re.sub(r"yaerumjung@koreashe\.org", "(이메일 생략)", brief_ex)
(REPO / "docs" / "BRIEF.md").write_text("# BRIEF.md (발췌본: 대회 사실·양식·규정·공통 작업 규칙)\n\n" + brief_ex, encoding="utf-8")
base = (PROJ / "기준_요약문.md").read_text(encoding="utf-8")
m = re.search(r"## ⑤.*", base, flags=re.S)
(REPO / "docs" / "기준_요약문_⑤.md").write_text("# 기준 요약문 ⑤ (보고서 요약·절 구성의 뼈대)\n\n" + (m.group(0) if m else ""), encoding="utf-8")
(REPO / "requirements.txt").write_text("""# 2026-10-21 실행 환경 (Python 3.14.2, Windows 11). 실제 import 한 패키지만.
pandas==3.0.1
numpy==2.4.2
scipy==1.17.1
statsmodels==0.14.6
matplotlib==3.10.8
openpyxl==3.1.5
requests==2.32.5
PyMuPDF==1.27.2.3
""", encoding="utf-8")
(REPO / ".gitignore").write_text("""# 원본 데이터는 저장소에 넣지 않는다 (code/00_download.py, 01_weather.py 로 다시 받는다)
data_raw/*
!data_raw/SOURCES.md
data_proc/
explore/
# 보고서 산출물(PDF·쪽 이미지)은 제출본으로 따로 관리
report/*.pdf
report/*.html
report/pages/
# 파이썬
__pycache__/
*.pyc
# 키·환경
.env
.secrets/
*.key
# 임시
*.tmp
~$*
""", encoding="utf-8")
shutil.copy2(ROOT / "repo_README.md", REPO / "README.md")  # README 원본은 프로젝트 폴더의 repo_README.md
n_files = sum(1 for _ in REPO.rglob("*") if _.is_file())
big = [str(f.relative_to(REPO)) for f in REPO.rglob("*") if f.is_file() and f.stat().st_size > 50 * 1024 * 1024]
print(f"repo/ 조립: 파일 {n_files}개; 50MB 초과: {big or '없음'}")
sys.exit(0)
