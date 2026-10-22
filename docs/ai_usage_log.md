# ai_usage_log.md — 후보 ⑥ 「따릉이는 폭염에 멈추지 않는다」 AI 작업 범위 (보고서 4절 작성용)

작성 2026-10-21 (하위 작업자 Claude Code, 모델 Claude Fable 5.1; 검토 A·B 1·2차 반영 수정의 일부는 Claude Opus 5.5). 검토자 A·B의 전수 검토(2회)도 별도의 AI 작업자가 했다. 상위 기록은 `../AI_활용_기록.md`.

## AI(이 작업자)가 한 일
1. **수집 코드**: `code/00_download.py`(열린데이터광장 파일 목록 파싱·POST 다운로드, 받은 파일은 건너뜀), `code/01_weather.py`(ASOS 일자료 API — 인증키는 환경변수/.secrets에서만, 폭염일수 화면 조회 POST). 따릉이 월 파일·대여소 정보·ASOS CSV 자체는 메인 작업자가 받아 둔 것을 썼고, 폭염일수 표(서울 108)는 이 작업자가 받았다.
2. **정리·집계**: `code/10_clean.py` — 월 9개 파일(3.4 GB)을 읽어 집계 3종(일×시간×연령×이용권, 일×대여소, 일 총량×기상×달력)과 대여소 마스터·폭염일수 CSV 생성. 메인 작업자의 예비 집계(`data_proc/prelim/`)와 합계 전수 대조(행·합계 모두 일치, 공휴일 3일·기온 구간 경계 7일만 다름).
3. **모형**: `code/20_model.py` — 식 (1) 로그 선형 회귀(HAC 표준오차), 시간대·연령·이용권·연도 하위 모형, 강건성 12사양, 스플라인, 2026-06 표본 외 예측, 반사실(보조).
4. **대여소·노출**: `code/21_station.py`(같은 해 안 대여소 유지 비율), `code/22_exposure.py`(폭염일 구성), `code/23_exposure_gap.py`(연령군×시간대 노출 명시간, 시간별 비율 곡선, 자치구, 통근 거점·고령 다수 대여소, 유형 추정), `code/24_elderly.py`(연령대별 이용 성격 표: 정기권 비율·회당 거리·시간·속도·성별, 시간별 비중·비율 곡선, 5유형 구성, 생활시설형 상위) — 메인 작업자의 `explore/` 탐색 결과를 읽기만 하고 원자료에서 다시 계산.
5. **검증**: `code/40_verify.py` — csv·html.parser·openpyxl·numpy.lstsq 로 165개 수치를 다시 계산(원자료 136·집계 파일 26·결과 파일 3, `results/verification.md`, 불일치 0). 유형 분류는 규칙을 정할 때 본 45곳을 이름·좌표로(`results/type_manual_check.csv`, 43곳 일치), 그 밖에서 무작위로 뽑은 100곳을 이름·주소로 대조(`results/type_random_check.csv`, 77곳 일치; seed 2026).
6. **그림**: `code/30_figures.py` — 본문 6장 + 부록 2장(Pretendard, 강조색 진청 1개 + 회색).
7. **보고서**: `code/50_build_report.py` + `report/template.html` — 논문 양식 HTML, 수치는 결과 파일에서 자동 삽입, Chrome headless PDF, 70dpi 쪽 이미지. `code/60_readability_check.py` — 문장 길이·숫자 밀도·금지어·줄표·캡션·고아 제목·쪽수·요약 일치·참고문헌 감사.
8. **문서**: `data_raw/SOURCES.md`, `STATUS.md`, `SPEC.md` 결정 기록, `repo/`(README·requirements·.gitignore·code·results·figures·docs).

## AI에 입력한 것
- 프로젝트 폴더 안의 지침 문서(BRIEF.md, SPEC.md, 논문양식·시인성·논증구조·전수검증 지침, 기준 요약문)와 공개 데이터 파일, 웹 공개 페이지(열린데이터광장·UCI·법령정보센터·기상청)만. 개인정보·비공개 자료 없음. 인증키 값은 읽기만 하고 어디에도 출력하지 않음.
