# 따릉이는 폭염에 멈추지 않는다 — 서울 공공자전거 3,600만 건으로 본 고령 이용자의 생활 이동과 폭염 노출

「데이터로 바꾸는 우리의 이동 — AI와 함께하는 교통문제 해결을 위한 데이터 분석 공모전」(숲과나눔 풀씨행동연구소·한겨레, 2026) 출품작의 분석 코드입니다.
대표자: 김현수 · 저장소 https://github.com/T19340/ddareungi-heatwave-elderly

제출 보고서와 이 저장소가 다른 곳 세 가지(대여소 공간 유형 등)는 맨 아래 [정오표](#정오표)에 정리했습니다. 주요 결과와 정책 제안의 방향은 그대로입니다.

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
│   ├─ 25_type_random_sample.py 유형 규칙 검증용 무작위 100곳을 다시 뽑아 type_random_check.csv의 표본과 같은지 확인
│   ├─ 30_figures.py         그림 1~6과 부록 그림 B·C의 화면용 판 (figures/: fig1~6, figA_type, figB_top_map)
│   ├─ 31_figures_print.py   같은 그림을 보고서에 들어갈 실제 크기·300dpi로 다시 그림 (figures_print/, 제출 보고서에 넣은 판)
│   ├─ 32_figA_station_map.py 부록 그림 A(대여소별 유지 비율 지도)를 같은 방식으로 그림 (figures_print/figA_station_map.png)
│   ├─ 40_verify.py          핵심 수치 독립 재계산 → results/verification.md
│   ├─ 50_build_report.py    HTML 판 보고서(+PDF) 생성 (report/template.html + 공통 CSS, 수치 자동 삽입, nb 자동 감싸기)
│   ├─ 60_readability_check.py 시인성·논증 구조 점검표 + 참고문헌 감사
│   └─ 90_make_repo.py       이 저장소 폴더 조립
├─ report/template.html      보고서 뼈대(머리글·강조색·그림 크기 슬롯)
├─ 공통_논문양식/            paper.css + fonts/(Noto Serif KR·Pretendard, OFL 라이선스 동봉)
├─ data_raw/SOURCES.md       데이터 출처·라이선스·기준시점·한계 (원본 파일은 저장소에 없음)
├─ results/                  모형 계수·강건성·대여소·자치구·노출 표(CSV/JSON), 검증표, 점검표, 유형 대조표(type_manual_check.csv·type_random_check.csv), 참가자 대조 기록(participant_check.md)
├─ figures/                  그림 PNG (30번이 만든 화면용 판)
└─ docs/                     AI에 준 작업 지시문(BRIEF.md 발췌본, SPEC.md 원문)과 AI 활용 기록
```
스크립트는 자기 위치 기준 상대경로(`Path(__file__).parents[1]`)만 쓰므로 저장소를 어디에 받아도 됩니다. 실행하면 저장소 안에 `data_raw/`(원본), `data_proc/`(집계), `results/`, `figures/`, `figures_print/`, `report/`가 만들어집니다. 공통 CSS는 저장소 안 `공통_논문양식/`을 쓰려면 `50_build_report.py --css ../공통_논문양식/paper.css`.

## 제출 보고서와 이 저장소의 대응
제출 보고서 「김현수_분석보고서.pdf」는 Word 문서로 따로 조판한 판입니다. `50_build_report.py`가 만드는 HTML 판과는 문장·표 이름·쪽 구성이 다르고, 검증표(`results/verification.md`)의 표·그림 이름은 HTML 판을 따릅니다(대응은 [정오표](#정오표) 3). 보고서에 넣은 그림 파일은 아래와 같습니다. 제출 당시와 같은 입력 파일로 31·32번을 다시 실행하면 9장 모두 바이트 단위로 같은 파일이 나옵니다.

| 제출 보고서 | 파일(`figures_print/`, 300dpi) | 코드 |
|---|---|---|
| 그림 1~6 | `fig1_flow.png`, `fig2_heat_effects.png`, `fig3_profile.png`, `fig4_adjust.png`, `fig5_who.png`, `fig6_where.png` | `31_figures_print.py` |
| 부록 그림 A | `figA_station_map.png` | `32_figA_station_map.py` |
| 부록 그림 B | `figA_type.png` | `31_figures_print.py` |
| 부록 그림 C | `figB_top_map.png` | `31_figures_print.py` |

`figures/`에는 같은 그림의 화면용 판(`30_figures.py`, 200dpi)이 있습니다.

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
python -P -E -X utf8 code/25_type_random_sample.py # 종료코드 0 = 유형 검증 표본이 type_random_check.csv와 같음
python -P -E -X utf8 code/30_figures.py            # figures/ (화면용)
python -P -E -X utf8 code/31_figures_print.py      # figures_print/ (제출 보고서에 넣은 판)
python -P -E -X utf8 code/32_figA_station_map.py   # figures_print/figA_station_map.png (부록 그림 A)
python -P -E -X utf8 code/40_verify.py             # 종료코드 0 = 검증표 165개 수치가 모두 일치 (약 1분)
python -P -E -X utf8 code/50_build_report.py --css ../공통_논문양식/paper.css --pdf   # HTML 판 보고서 report/보고서.html·pdf (Chrome headless)
python -P -E -X utf8 code/60_readability_check.py
# 50에 --team·--lead·--url 을 주면 머리글 자리표시자를 채운 판을 따로 만듦(report/<팀명>_분석보고서.pdf). 제출 보고서는 Word로 따로 조판한 판
```
`-P -E -X utf8`은 스크립트 폴더를 import 경로에 넣지 않고, 환경변수를 무시하며(인증키는 코드가 `os.environ`에서 직접 읽으므로 영향 없음), 입출력을 UTF-8로 고정하는 옵션입니다. 각 단계의 산출물: 10 → `data_proc/`(집계 3종·대여소 마스터·폭염일수 CSV·`clean_summary.json`), 20~24 → `results/`(CSV·JSON), 30 → `figures/`, 31·32 → `figures_print/`, 40 → `results/verification.md`, 50 → `report/보고서.html`·`보고서.pdf`·`pages/`, 60 → `report/readability_check.md`·`results/reference_audit.md`.

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
- `40_verify.py`는 원자료를 csv 모듈로 다시 읽거나(136개) 집계 파일을 다른 코드로 다시 계산해(26개) 165개 수치를 대조합니다(모형 예측값·개별 유형 판정 표를 그대로 읽어 센 3개 포함). 입력 구분은 표의 '입력' 열에 있습니다. 종료코드가 0이 아니면 `results/verification.md`의 '불일치' 행을 확인하세요.
- `60_readability_check.py`는 `report/보고서.pdf`가 있어야 하므로 50을 `--pdf`로 먼저 실행합니다. 요약 문단 일치 검사는 저장소 상위 폴더의 `기준_요약문.md`가 있을 때만 수행되고, 없으면 '기준 파일 없음'으로 표시됩니다.
- 대여소 유형(역세권·주거·생활시설·공원·강변·기타)은 대여소 이름의 낱말로 추정한 것이며 보고서에서도 '추정'으로만 씁니다.
- 한글 글꼴: 30·31번 그림은 저장소의 `공통_논문양식/fonts/Pretendard-*.otf`를 등록해 씁니다(없으면 Malgun Gothic). 32번(부록 그림 A)은 Malgun Gothic을 씁니다.

## 라이선스·출처 표기
- 데이터: 서울 열린데이터광장 두 건은 공공누리 제1유형(출처표시; 상업적 이용·변경 가능), 기상청 ASOS 일자료는 공공데이터포털 등록 조건(공공누리, 출처 표시), 폭염일수 표는 기상자료개방포털 이용 조건(출처 표시). 결과물에는 "서울특별시 열린데이터광장, 서울시 공공자전거 따릉이 이용정보(시간대별)·대여소 정보", "기상청 ASOS 일자료 조회서비스(공공데이터포털)", "기상청 기상자료개방포털 폭염일수"로 출처를 표기했습니다. 자세한 라이선스·컬럼·한계는 `data_raw/SOURCES.md`.
- 선행 자료로 인용만 한 것: UCI Machine Learning Repository 「Seoul Bike Sharing Demand」(CC BY 4.0, DOI 10.24432/C5F62R; 분석 데이터로 쓰지 않음), 「관공서의 공휴일에 관한 규정」(국가법령정보센터; 공휴일 정의).
- 글꼴: Noto Serif KR(OFL)·Pretendard(OFL), `공통_논문양식/fonts/`에 라이선스 전문 동봉. 그림·보고서 외 용도로 재배포할 때도 OFL 조건을 따릅니다.
- 분석에 AI(Claude Code, Anthropic; 모델 Claude Fable 5.1, 검토 반영 일부는 Claude Opus 5.5)를 사용했습니다. 범위와 검증은 `docs/ai_usage_log.md`. AI가 작성·실행한 재계산표는 `results/verification.md`에 있습니다.

## 정오표
제출 보고서 「김현수_분석보고서.pdf」에서 아래 세 가지를 바로잡습니다. 폭염 효과 추정, 고령 이용자의 이용 유지와 노출 시간, 자치구 분포 등 주요 결과와 정책 제안의 방향은 바뀌지 않습니다. 쪽 번호는 보고서에 인쇄된 번호입니다.

### 1. 대여소 공간 유형 (5.5절 6쪽, 6.3절 7쪽, 주 7 9쪽, 부록 표 A·B 10~11쪽, 부록 그림 B 설명 12쪽)
이 위치에 적힌 유형 수치는 2026년 10월 21일 검토에서 분류 규칙을 고치기 전의 값입니다. 보고서의 그림(그림 3(b)·6(b), 부록 그림 B·C)과 이 저장소는 고친 규칙을 따르며, 고친 규칙으로 계산한 값은 다음과 같습니다.

- 규칙(앞 규칙 우선): 주거형 → 공원·강변형 → 역세권형 → 생활시설형 → 기타. 체육·스포츠·수련관·세무서·마트 등은 생활시설형, 유원지와 하천 이름(청계천·안양천 등)은 공원·강변형으로 분류합니다. 전체 낱말 목록은 `code/24_elderly.py`의 `classify5`에 있습니다.
- 유형별 대여소 수(2026년 6월 기준 2,789곳): 역세권형 583, 주거형 465, 생활시설형 474, 공원·강변형 196, 기타 1,071곳.
- 비교 평일 대여의 유형별 구성비(같은 순서): 고령 이용자 27.4·16.7·15.0·7.8·33.0%, 청장년층 27.5·15.4·14.5·7.4·35.1%. 두 집단의 구성이 비슷하다는 해석은 같습니다.
- 유형별 유지 비율 중앙값은 4분류가 아니라 5개 유형 기준으로 공원·강변형 0.881(n=123), 생활시설형 0.886(n=257), 기타 0.892(n=627), 역세권형 0.900(n=410), 주거형 0.909(n=270)입니다. 공원·강변형이 가장 낮고 주거형이 가장 높으며 두 유형의 차이가 유의하다는 결과(맨-휘트니 U 검정 p<0.001)는 같습니다. 부록 그림 B 설명의 '4개 유형'은 '5개 유형'입니다.
- 고령 이용 상위 30곳의 유형은 역세권형 15, 생활시설형 5, 기타 4, 주거형 4, 공원·강변형 2곳입니다. 5.5절의 '과반인 16개소'는 '절반인 15개소'입니다.
- 부록 표 A의 '공간 유형(추정)' 칸에서 10·22·24·30위는 생활시설형, 13·15위는 공원·강변형, 28위는 주거형입니다(전체는 `results/station_elderly_2025_typed.csv`의 `type5` 열).
- 생활시설형 상위 20곳(부록 표 B, 6.3절의 우선 정비 대상)은 `results/station_elderly_facility_2025.csv`의 상위 20곳입니다.
  - 새로 들어가는 곳: 강서구민올림픽체육센터, 강동세무서, 청소년수련관 후문, KBS 스포츠월드, 세이브마트, 제2구민체육센타 앞, 중계 롯데마트
  - 빠지는 곳: 노원정보도서관, 구일고등학교 정문, 가락1동주민센터, 상봉시장앞 교차로 한성빌딩 앞, 공항초등학교건너편, 노원구청, 강서구청
  - 이에 따라 5.5절에서 이용량이 가장 높다고 쓴 '강서구립등빛도서관', '신창시장', '송파구청'은 '강서구립등빛도서관', '강서구민올림픽체육센터', '강동세무서'입니다(신창시장 7위, 송파구청 8위).
- 5.2절(5쪽)의 '역세권형이 27%로 가장 높고'는 '기타를 뺀 네 유형 가운데 역세권형이 27%로 가장 높고'입니다. 27%는 고친 규칙의 값이고, 그림 3(b)의 기타(33%)는 어느 유형에도 들지 않은 나머지라 비교에서 뺍니다.

### 2. 강건성 서술 (주 3, 8쪽)
- '2026년 6월 표본 포함(n=274)'은 n=273입니다.
- '총 13가지 모형 설정(Specification)에서 35℃ 이상 효과는 -19.9% ~ -2.5%(기상 미통제 시) 범위로 일관되게 확인되었다'는 '일조·습도를 통제한 11가지 설정에서 35℃ 이상 효과는 -19.9% ~ -13.6%이다'입니다. 13가지 가운데 나머지 둘은 기준 구간을 30~33℃로 바꾼 설정(-22.0%, 30~33℃ 대비)과 일조·습도를 통제하지 않은 설정(-2.5%)입니다. 부록 표 D의 값은 그대로입니다.

### 3. 검증 서술 (4절, 3쪽)
- '본문에 인용된 핵심 결과 수치 72개 전체를 기존 분석 파이프라인과 독립된 별도의 검증 코드로 원시 데이터에서 재산출하여'는 '분석 수치 165개를 기존 분석 파이프라인과 독립된 별도의 검증 코드(`code/40_verify.py`)로 다시 계산하여'입니다. 165개 가운데 136개는 원시 데이터에서, 26개는 집계 파일에서 다시 계산했고, 3개는 결과 파일의 값을 그대로 읽어 셌습니다. 불일치는 0개입니다(`results/verification.md`).
- 검증표의 표·그림 이름은 HTML 판 보고서 기준입니다. 표 1·2와 그림 1~6은 제출 보고서와 같고, 나머지는 표 A → 부록 표 C, 표 B → 부록 표 A, 표 C → 부록 표 B, 표 D → 그림 6(a)와 `results/gu_exposure_2025.csv`, 표 E → 부록 표 D, 부록 그림 A → 부록 그림 B, 부록 그림 B → 부록 그림 C로 대응합니다.
