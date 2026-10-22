# 따릉이는 폭염에 멈추지 않는다 — 서울 공공자전거 3,600만 건으로 본 고령 이용자의 생활 이동과 폭염 노출

「데이터로 바꾸는 우리의 이동 — AI와 함께하는 교통문제 해결을 위한 데이터 분석 공모전」(숲과나눔 풀씨행동연구소·한겨레, 2026) 출품작의 분석 코드입니다.
팀: {{팀명}} · 대표 {{대표자}} · 저장소 https://github.com/T19340/ddareungi-heatwave-elderly

## 무엇을 하는 코드인가
서울 열린데이터광장의 **공공자전거 이용정보(시간대별)** 9개월(2024·2025년 6~9월, 2026년 6월, 3,600만 건)과 기상청 **ASOS 서울 일자료**, **서울 폭염일수** 표를 결합해,

1. 일 단위 로그 선형 회귀(기온·강수 구간 + 주말·공휴일·월·연도 + 일조·습도, Newey-West 표준오차)로 **폭염이 전체 이용을 얼마나 줄이는지**(35℃ 이상인 날 −18%, 비 20mm 초과 −44%)와 시간대·연령·이용권별 차이를 재고,
2. 2025년 7~8월 평일(무강수·비공휴일)의 **폭염일 8일 vs 기준일 10일** 비교로 **60대 이상 이용의 성격**(정기권 97%, 2.5km·25분·시속 5.9km, 아침·저녁 봉우리), **폭염일의 조정 방식**(아침 유지·낮 감소·저녁 회복), **남는 노출**(하루 6,453건·88% 유지·낮 1,439명시간), **노출이 몰리는 자치구·대여소**(강서·영등포·송파·노원, 역세권·생활시설형 대여소 상위 목록)를 계산합니다.

핵심 수치(2026-10-21 실행)는 `results/summary_stats.json`, `exposure_gap_summary.json`, `elderly_summary.json`에 있고, 165개 수치를 다른 코드로 다시 계산한 결과가 `results/verification.md`(불일치 0; 원자료 136개·집계 파일 26개·결과 파일을 그대로 읽어 센 항목 3개)입니다.

## 폴더 구조
```
repo/
├─ README.md, requirements.txt, .gitignore
├─ code/
│   ├─ 00_download.py        열린데이터광장 파일(이용정보 월별 9개, 대여소 정보) 내려받기 (받은 파일은 건너뜀)
│   ├─ 01_weather.py         기상청 ASOS 일자료(오픈API, 환경변수 DATA_GO_KR_KEY) + 서울 폭염일수 화면 조회
│   ├─ 10_clean.py           집계 3종 + 대여소 마스터 + 폭염일수 CSV (data_proc/)
│   ├─ 20_model.py           식 (1) 회귀, 하위 모형, 강건성, 스플라인, 2026-06 표본 외 예측 (results/)
│   ├─ 21_station.py         대여소별 유지 비율(같은 해 안), 자치구·유형
│   ├─ 22_exposure.py        폭염일 이용 구성
│   ├─ 23_exposure_gap.py    연령군×시간대 노출 명시간, 시간별 비율, 자치구, 통근·고령 대여소, 유형
│   ├─ 24_elderly.py         연령대별 이용 성격 표, 시간별 비중·비율 곡선, 5유형 구성, 생활시설형 상위
│   ├─ 30_figures.py         보고서 그림 6장 + 부록 2장 (figures/: fig1~6, figA_type, figB_top_map)
│   ├─ 31_figures_print.py   같은 그림을 보고서에 들어갈 실제 크기·300dpi로 다시 그림 (figures_print/)
│   ├─ 40_verify.py          핵심 수치 독립 재계산 → results/verification.md
│   ├─ 50_build_report.py    보고서 HTML(+PDF) 생성 (report/template.html + 공통 CSS, 수치 자동 삽입, nb 자동 감싸기)
│   ├─ 60_readability_check.py 시인성·논증 구조 점검표 + 참고문헌 감사
│   └─ 90_make_repo.py       이 저장소 폴더 조립
├─ report/template.html      보고서 뼈대(머리글·강조색·그림 크기 슬롯)
├─ 공통_논문양식/            paper.css + fonts/(Noto Serif KR·Pretendard, OFL 라이선스 동봉)
├─ data_raw/SOURCES.md       데이터 출처·라이선스·기준시점·한계 (원본 파일은 저장소에 없음)
├─ results/                  모형 계수·강건성·대여소·자치구·노출 표(CSV/JSON), 검증표, 점검표, 유형 수작업 대조표(type_manual_check.csv), 참가자 대조 기록 양식(participant_check.md)
├─ figures/                  그림 PNG
└─ docs/                     AI에 준 작업 지시문(BRIEF.md 발췌본, SPEC.md 원문, 기준 요약문 ⑤)과 AI 활용 기록
```
스크립트는 자기 위치 기준 상대경로(`Path(__file__).parents[1]`)만 쓰므로 저장소를 어디에 받아도 됩니다. 실행하면 저장소 안에 `data_raw/`(원본), `data_proc/`(집계), `results/`, `figures/`, `report/`가 만들어집니다. 공통 CSS는 저장소 안 `공통_논문양식/`을 쓰려면 `50_build_report.py --css ../공통_논문양식/paper.css`.

## 실행 요구 사양
- Windows 11, Python 3.14.2(다른 OS도 되지만 그림 글꼴 대체와 Chrome 경로를 맞춰야 함). 메모리 4 GB 이상(월 CSV 한 개 최대 460 MB를 pandas로 읽음), 디스크 4 GB 이상.
- `requirements.txt`의 패키지(pandas 3.0, numpy, scipy, statsmodels, matplotlib, openpyxl, requests, PyMuPDF). PyMuPDF는 60_readability_check.py의 PDF 점검과 50_build_report.py의 쪽 이미지 생성에 씁니다.
- PDF 렌더에는 Google Chrome이 필요합니다(기본 경로 `C:\Program Files\Google\Chrome\Application\chrome.exe`, 다른 경로는 `50_build_report.py --chrome <경로>`).

## 인증키 (기상청 ASOS 일자료 API에만 필요)
1. 공공데이터포털(data.go.kr) 로그인 → 「기상청_지상(종관, ASOS) 일자료 조회서비스」(https://www.data.go.kr/data/15059093/openapi.do) 활용신청(자동 승인) → 마이페이지의 일반 인증키(Decoding) 값.
2. 실행 전에 환경변수로 넣습니다. PowerShell: `$env:DATA_GO_KR_KEY = "<인증키>"`, cmd: `set DATA_GO_KR_KEY=<인증키>`. 환경변수가 없으면 코드는 저장소 상위 폴더의 `.secrets/DATA_GO_KR_KEY.txt`를 읽습니다(저장소에는 넣지 않음, `.gitignore`).
3. 키 값은 어떤 코드·로그·결과 파일에도 기록되지 않습니다(`01_weather.py`는 요청 매개변수를 로그에 남길 때 키를 생략). 열린데이터광장·기상자료개방포털 자료는 키 없이 받습니다.

## 실행 순서 (Windows, Python 3.14)
```
python -m pip install -r requirements.txt
$env:DATA_GO_KR_KEY = "<공공데이터포털 인증키>"     # PowerShell (cmd는 set DATA_GO_KR_KEY=...)
python -P -E -X utf8 code/00_download.py           # data_raw/따릉이/ 에 월 파일 9개(약 3.4 GB)와 대여소 XLSX; 이미 있는 파일은 건너뜀. --list 는 목록만, --months 202406,... 로 일부만
python -P -E -X utf8 code/01_weather.py            # data_raw/기상/ 에 ASOS 일자료 CSV와 폭염일수 화면 HTML; --force 로 다시 받음
python -P -E -X utf8 code/10_clean.py              # 약 1분
python -P -E -X utf8 code/20_model.py
python -P -E -X utf8 code/21_station.py
python -P -E -X utf8 code/22_exposure.py
python -P -E -X utf8 code/23_exposure_gap.py
python -P -E -X utf8 code/24_elderly.py
python -P -E -X utf8 code/30_figures.py
python -P -E -X utf8 code/40_verify.py             # 종료코드 0 = 보고서 수치와 전부 일치 (약 1분)
python -P -E -X utf8 code/50_build_report.py --css ../공통_논문양식/paper.css --pdf   # report/보고서.html·pdf (Chrome headless)
python -P -E -X utf8 code/60_readability_check.py
# 제출용: --team "팀명" --lead "대표자" --url "https://github.com/계정/저장소" 를 주면 자리표시자를 채운 report/팀명_분석보고서.pdf
```
`-P -E -X utf8`은 스크립트 폴더를 import 경로에 넣지 않고, 환경변수를 무시하며(인증키는 코드가 `os.environ`에서 직접 읽으므로 영향 없음), 입출력을 UTF-8로 고정하는 옵션입니다. 각 단계의 산출물: 10 → `data_proc/`(집계 3종·대여소 마스터·폭염일수 CSV·`clean_summary.json`), 20~24 → `results/`(CSV·JSON), 30 → `figures/`, 40 → `results/verification.md`, 50 → `report/보고서.html`·`보고서.pdf`·`pages/`, 60 → `report/readability_check.md`·`results/reference_audit.md`.

## 데이터 다운로드 절차와 기준시점
| 데이터 | 받는 방법 | 기준시점 | 보고서에 쓴 파일의 다운로드 일시 |
|---|---|---|---|
| 서울시 공공자전거 따릉이 이용정보(시간대별) OA-15245 (공공누리 제1유형, 서울특별시 자전거PM과) https://data.seoul.go.kr/dataList/OA-15245/F/1/datasetView.do | 00_download.py: 데이터셋 페이지의 파일 목록(`downloadFile(seq)`)을 읽어 페이지와 같은 POST 요청(`datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do`, 폼 infId·infSeq·seq)으로 월별 CSV 9개를 파일당 1회 내려받음. 로그인·키 없음 | 2024-06~09, 2025-06~09, 2026-06 (데이터 갱신 2026-07-15, 반기 갱신) | 2026-10-21 |
| 서울시 공공자전거 따릉이 대여소 정보 OA-13252 (공공누리 제1유형) https://data.seoul.go.kr/dataList/OA-13252/F/1/datasetView.do | 00_download.py: 같은 방식으로 최신 XLSX 1개 | 2026-06 기준 | 2026-10-21 |
| 기상청 ASOS 일자료 조회서비스(공공데이터포털 15059093, 지점 서울 108, 일 평균·최고·최저기온·강수량·평균습도·일조시간) | 01_weather.py: 오픈API(인증키), 2024-06-01~09-30 · 2025-06-01~09-30 · 2026-06-01~실행일 세 구간 | 2024-06-01~2026-10-19 (2026년 구간의 끝은 실행일에 따라 달라짐; 분석에는 2026-06-30까지만 씀) | 2026-10-21 |
| 기상청 폭염일수(기상자료개방포털 기후통계분석 > 기상현상일수 > 폭염일수, 지점 서울 108) https://data.kma.go.kr/climate/heatWave/selectHeatWaveChart.do | 01_weather.py: 화면 조회 폼과 같은 POST, 표 HTML 저장(로그인 없음) | 1973~2026 (2026년은 조회 시점까지 연중 미완) | 2026-10-21 |

받은 파일마다 `data_raw/<폴더>/_download_log.json`에 URL·요청 폼·일시·바이트·sha256이 남습니다. 자료의 열 이름·행수·알려진 한계는 `data_raw/SOURCES.md`.

## 재현 시 유의점
- 열린데이터광장 파일이 갱신되면 파일명·행수가 바뀔 수 있습니다(보고서 기준시점은 위 표). 2025-06 파일에는 '이용시간(분)' 열이 없습니다. 월 CSV는 cp949 인코딩이며 엑셀로 열어 다시 저장하지 마세요.
- ASOS 2025-09-13의 일조시간이 결측이라 주 모형은 243일로 적합됩니다(일조 0 대체 사양은 `results/model_robust.csv`). 받는 날짜에 따라 2026년 ASOS 행수는 달라지지만 분석 결과에는 영향이 없습니다(6월까지만 사용).
- 공휴일은 「관공서의 공휴일에 관한 규정」의 공휴일과 선거일(2025-06-03 임시공휴일, 2026-06-03)을 `10_clean.py`에 적어 두었습니다.
- `40_verify.py`는 원자료를 csv 모듈로 다시 읽거나(136개) 집계 파일을 다른 코드로 다시 계산해(26개) 165개 수치를 대조합니다(모형 예측값·수작업 유형 판정을 그대로 읽어 센 3개 포함). 입력 구분은 표의 '입력' 열에 있습니다. 종료코드가 0이 아니면 `results/verification.md`의 '불일치' 행을 확인하세요.
- `60_readability_check.py`는 `report/보고서.pdf`가 있어야 하므로 50을 `--pdf`로 먼저 실행합니다. 요약 문단 일치 검사는 저장소 상위 폴더의 `기준_요약문.md`가 있을 때만 수행되고, 없으면 '기준 파일 없음'으로 표시됩니다(`docs/기준_요약문_⑤.md`에 같은 문단이 있음).
- 대여소 유형(역세권·주거·생활시설·공원·강변·기타)은 대여소 이름의 낱말로 추정한 것이며 보고서에서도 '추정'으로만 씁니다.
- 한글 글꼴: 그림은 `공통_논문양식/fonts/Pretendard-*.otf`를 등록해 씁니다(없으면 Malgun Gothic).

## 라이선스·출처 표기
- 데이터: 서울 열린데이터광장 두 건은 공공누리 제1유형(출처표시; 상업적 이용·변경 가능), 기상청 ASOS 일자료는 공공데이터포털 등록 조건(공공누리, 출처 표시), 폭염일수 표는 기상자료개방포털 이용 조건(출처 표시). 결과물에는 "서울특별시 열린데이터광장, 서울시 공공자전거 따릉이 이용정보(시간대별)·대여소 정보", "기상청 ASOS 일자료 조회서비스(공공데이터포털)", "기상청 기상자료개방포털 폭염일수"로 출처를 표기했습니다. 자세한 라이선스·컬럼·한계는 `data_raw/SOURCES.md`.
- 선행 자료로 인용만 한 것: UCI Machine Learning Repository 「Seoul Bike Sharing Demand」(CC BY 4.0, DOI 10.24432/C5F62R; 분석 데이터로 쓰지 않음), 「관공서의 공휴일에 관한 규정」(국가법령정보센터; 공휴일 정의).
- 글꼴: Noto Serif KR(OFL)·Pretendard(OFL), `공통_논문양식/fonts/`에 라이선스 전문 동봉. 그림·보고서 외 용도로 재배포할 때도 OFL 조건을 따릅니다.
- 분석에 AI(Claude Code, Anthropic; 모델 Claude Fable 5.1, 검토 반영 일부는 Claude Opus 5.5)를 사용했습니다. 범위와 검증은 `docs/ai_usage_log.md`. AI가 작성·실행한 재계산표는 `results/verification.md`, 참가자(사람)가 원자료를 열어 직접 대조한 기록은 `results/participant_check.md`(제출 전 채움)입니다.
