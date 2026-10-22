# -*- coding: utf-8 -*-
"""
60_readability_check.py — 시인성·논증구조 자체 점검표 (report/readability_check.md) + 참고문헌 감사 (results/reference_audit.md)

점검 항목(시인성_시각화_지침 D-3 + 지침_추가_논증구조 4절 + 전수_검증_프로토콜):
  60자 초과 문장 수(목표 0), 숫자 3개 이상 문장 수(목표 0), 단락별 문장 수(3~6)·글자 수(220~450), 쪽 끝 고아 제목 0,
  nb 감싸기 적용 수, 그림 수, 본문 쪽수(요약~6절), 금지 어휘(가설·틀렸·기각·실패·1위·전국 최다·덜 줄) 0, 줄표 0,
  1절 첫 단락 4문장 구조, 요약 = 기준_요약문.md ⑤ 문단(숫자 제외), 캡션 2문장 이내, 공고문 인용 0, 미인용·2차 출처 0,
  숫자 뒤 조사 받침 일치(전체 HTML; 0.83으로·0.88이다·0.66은, 2차 검토 N-11).
대상: 본문 <p>(표 캡션·주석·미주·참고문헌·도구 단락 제외). 숫자 세기 규칙: 날짜·범위·연도쌍·인용·그림/표 참조·통계량은 하나로 세거나 제외,
  연령 구간 이름(60대·20~50대·60~64세)과 절 참조(5.1절)는 숫자로 세지 않음(범주·위치 표시이지 읽어야 할 수치가 아님).

실행: python -P -E -X utf8 code/60_readability_check.py  (report/보고서.html·보고서.pdf 가 있어야 함)
"""
import html as htmlmod
import re
import sys
from datetime import datetime
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
REP = ROOT / "report"
H = (REP / "보고서.html").read_text(encoding="utf-8")
body = H.split("<body>", 1)[1]
main = body.split('<section class="appendix">', 1)[0]
main_no_notes = re.sub(r'<div class="notes">.*?</div>', "", main, flags=re.S)
main_no_notes = re.sub(r'<div class="refs">.*?</div>', "", main_no_notes, flags=re.S)


def strip_tags(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = htmlmod.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


paras = []
for m in re.finditer(r"<p(?:\s+class=\"([^\"]*)\")?[^>]*>(.*?)</p>", main_no_notes, flags=re.S):
    cls = m.group(1) or ""
    if any(c in cls for c in ("tcap", "tnote", "tools")):
        continue
    if "noindent" in cls and len(strip_tags(m.group(2))) < 12:
        continue
    txt = strip_tags(re.sub(r"<sup[^>]*>.*?</sup>", "", m.group(2)))
    if txt:
        paras.append((cls, txt))

sections = []
for m in re.finditer(r"<h2>(.*?)</h2>(.*?)(?=<h2>|<section class=\"appendix\">|$)", main_no_notes, flags=re.S):
    title = strip_tags(m.group(1))
    first_p = re.search(r"<p(?:\s+class=\"(?![^\"]*(?:tcap|tnote|tools))[^\"]*\")?[^>]*>(.*?)</p>", m.group(2), flags=re.S)
    sections.append((title, strip_tags(first_p.group(1)) if first_p else ""))


def sentences(t):
    t = re.sub(r"\(([^()]*)\)", lambda mm: "(" + mm.group(1).replace(". ", "。") + ")", t)
    parts = re.split(r"(?<=[.!?])\s+|(?<=다\.)(?=\S)", t)
    return [p.strip().replace("。", ". ") for p in parts if p.strip()]


def count_numbers(sent):
    s = sent
    s = re.sub(r"\[\d+\]", " ", s)
    s = re.sub(r"\d+(?:~\d+)?(?:대|세)", " ", s)      # 연령 구간 이름
    s = re.sub(r"\d(?:\.\d)?절", " ", s)               # 절 참조
    s = re.sub(r"(?:그림|표|식|주)\s?\(?[0-9A-Z]+\)?", " ", s)
    s = re.sub(r"\d{4}-\d{2}-\d{2}", " N ", s)
    s = re.sub(r"\d{4}[·~]\d{4}년", " N ", s)
    s = re.sub(r"\d{4}년\s?\d{1,2}월", " N ", s)
    s = re.sub(r"\d[\d,\.]*\s?[~–-]\s?\d[\d,\.]*", " N ", s)
    s = re.sub(r"[ρr]\s?=\s?[+\-−]?\d[\d\.]*", " N ", s)
    s = re.sub(r"p\s?[<=>]\s?[^\s)]+", " N ", s)
    s = re.sub(r"\d\s?×\s?\d", " N ", s)
    return len(re.findall(r"N|\d[\d,\.]*", s))


rows_long, rows_num, para_stats = [], [], []
for cls, txt in paras:
    ss = sentences(txt)
    para_stats.append((len(ss), len(txt), txt[:28]))
    for sen in ss:
        if len(sen) > 60:
            rows_long.append((len(sen), sen))
        k = count_numbers(sen)
        if k >= 3:
            rows_num.append((k, sen))

n_nb = len(re.findall(r'<span class="nb">', main))
n_fig = len(re.findall(r"<figure", main))
n_fig_app = len(re.findall(r"<figure", body)) - n_fig
FORB = ["가설", "틀렸", "기각", "실패", "1위", "전국 최다", "순위권", "덜 줄", "덜 준다", "다양한", "효과적으로", "시사하는 바", "할 필요가 있다", "에 있어서"]
forb = {w: len(re.findall(w, strip_tags(main))) for w in FORB}
forb_hit = {k: v for k, v in forb.items() if v}
sec1_first = next((fp for (t, fp) in sections if t.startswith("1.")), "")
sec1_n = len(sentences(sec1_first))
abs_html = re.search(r'<div class="abstract">(.*?)</div>', main, flags=re.S)
abs_txt = strip_tags(abs_html.group(1)).replace("요약", "", 1).strip() if abs_html else ""
ref_path = ROOT.parent / "기준_요약문.md"
ref_match = "기준 파일 없음"
if ref_path.exists():
    rt = ref_path.read_text(encoding="utf-8")
    m5 = re.search(r"## ⑤[^\n]*\n(.+?)\n", rt)
    if m5:
        norm = lambda s: re.sub(r"[\d,\.%\s]", "", s)
        ref_match = "일치(숫자 제외)" if norm(m5.group(1)) == norm(abs_txt) else "불일치"
        if ref_match == "불일치":
            a, b = norm(m5.group(1)), norm(abs_txt)
            i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
            ref_match += f" (첫 차이 {i}번째: 기준 '{a[max(0, i - 10):i + 15]}' vs 보고서 '{b[max(0, i - 10):i + 15]}')"

_no_refs = re.sub(r'<div class="refs">.*?</div>', "", main, flags=re.S)
dash_n = strip_tags(_no_refs).count("—")
caps_raw = re.findall(r"<figcaption>(.*?)</figcaption>", body, flags=re.S) + re.findall(r'<p class="tcap">(.*?)</p>', body, flags=re.S)
cap_bad = []
for c_ in caps_raw:
    ctext = re.sub(r"^(?:그림|표)\s?[0-9A-Z]+\.\s*", "", strip_tags(c_))
    if len(sentences(ctext)) > 2:
        cap_bad.append(ctext[:40])

# ---- 참고문헌 감사
refs_html = re.search(r'<div class="refs">(.*?)</div>', body, flags=re.S)
ref_items = re.findall(r'<li><span class="lab">(?:<span class="nb">)?\[(\d+)\](?:</span>)?</span>(.*?)</li>', refs_html.group(1), flags=re.S) if refs_html else []
main_wo_refs = re.sub(r'<div class="refs">.*?</div>', "", body, flags=re.S)
PRIMARY = ("data.seoul.go.kr", "data.go.kr", "data.kma.go.kr", "archive.ics.uci.edu", "law.go.kr", "mpm.go.kr", "weather.go.kr", "kma.go.kr", "seoul.go.kr", "index.go.kr", "kdca.go.kr", "doi.org/10.")
audit_rows, uncited, secondary = [], [], []
cited_nums = set(int(x) for x in re.findall(r"\[(\d+)\]", strip_tags(main_wo_refs)))
for num, txt_ in ref_items:
    desc = strip_tags(txt_)
    locs = []
    for sec_m in re.finditer(r"<h([23])>(.*?)</h\1>(.*?)(?=<h[23]>|<section class=\"appendix\">|$)", main_wo_refs, flags=re.S):
        head, content = strip_tags(sec_m.group(2)), sec_m.group(3)
        k = len(re.findall(r"\[" + num + r"\]", strip_tags(content)))
        if k:
            locs.append(f"{head[:18]}({k})")
    if not locs:
        uncited.append(num)
    if not any(d in desc for d in PRIMARY):
        secondary.append(num)
    audit_rows.append((num, desc[:80], ", ".join(locs) or "(없음)"))
missing = sorted(n_ for n_ in cited_nums if str(n_) not in {n for n, _ in ref_items})
notice_cites = len(re.findall(r"공고\s?\[\d+\]", strip_tags(main_wo_refs))) + int("koreashe.org" in strip_tags(body))
(ROOT / "results" / "reference_audit.md").write_text(
    "\n".join(["# results/reference_audit.md — 참고문헌 전수 점검 (" + datetime.now().strftime("%Y-%m-%d %H:%M") + ")", "",
               "| 번호 | 자료 | 인용 위치(절·표·그림·주, 횟수) |", "|---|---|---|"] +
              [f"| [{n_}] | {d} | {l} |" for n_, d, l in audit_rows] +
              ["", f"- 공모전 공고문 인용: {notice_cites} (목표 0)", f"- 미인용 항목: {uncited or '없음'}", f"- 본문에 있는데 목록에 없는 번호: {missing or '없음'}",
               f"- 1차 자료(열린데이터광장·공공데이터포털·기상청·법령정보센터·인사혁신처·UCI 저장소·e-나라지표·질병관리청 감시 통계·DOI가 있는 학술지 논문)가 아닌 출처: {secondary or '없음'}",
               "- 폭염일수는 기상청 기상자료개방포털 표 그대로, 이용 집계는 서울 열린데이터광장 파일 그대로 인용."]), encoding="utf-8")

# ---- 단위·조사 공백 / 물결 공백 / 년월일 붙임 (HTML 원문 기준) + 빈 표 셀
_all_txt = strip_tags(body)
UNIT = r"(?:km/h|km|mm|%|℃|분|시간|명시간|건|곳|일|년|월|번|회|배|개|대)"
sp_unit = re.findall(r"\d" + UNIT + r"\s+(?:를|을|는|은|이|가|로|의|에|도|와|과|만)(?=[\s\.,)]|$)", _all_txt)
sp_tilde = re.findall(r"\d~\s+\d|\d\s+~\s*\d", _all_txt)
sp_ymd = re.findall(r"\d{4}년\d|\d{1,2}월\d{1,2}일\d", _all_txt)
empty_td = len([m for m in re.findall(r"<td([^>]*)>\s*</td>", body) if "note" not in m])  # 표 D 비고 칸(class=note)은 비어도 됨
# 숫자 뒤 조사 받침: 숫자(+단위) 바로 뒤 조사가 읽기의 받침과 맞는지(영 일 삼 육 칠 팔은 받침, 이 사 오 구는 없음; 10·100·1000은 십·백·천)
_DJ = {"0": "x", "1": "l", "2": "", "3": "x", "4": "", "5": "", "6": "x", "7": "l", "8": "l", "9": ""}
_SYM = {"km/h": "", "km": "", "mm": "", "%": "", "℃": ""}


def _jong_tok(num, unit):
    if unit:
        if unit in _SYM:
            return _SYM[unit]
        k = (ord(unit[-1]) - 0xAC00) % 28
        return "" if k == 0 else ("l" if k == 8 else "x")
    digits = num.replace(",", "")
    if "." not in digits and digits.strip("0") and digits.endswith("0"):
        return "x"
    return _DJ[digits[-1]]


_BAD = {"": {"은", "이", "을", "과", "으로"}, "l": {"는", "가", "를", "와", "으로", "다", "고", "며", "나", "였다"},
        "x": {"는", "가", "를", "와", "로", "다", "고", "며", "나", "였다"}}
_UNITS = r"(명시간|시간|km/h|km|mm|%|℃|곳|일|건|분|번|명|배|개|년|월|시|세|대|회|종|점|행|쪽)?"
_PARTS = r"(으로|이었다|이다|이고|이며|이나|였다|은|는|이|가|을|를|과|와|로|다|고|며|나)(?![가-힣])"
_pp = re.compile(r"(\d[\d,]*(?:\.\d+)?)" + _UNITS + r"\]?" + _PARTS)       # 숫자(+단위) 바로 뒤, [8]은 처럼 대괄호 번호 포함
_pq = re.compile(r"\)" + _PARTS)                                            # 괄호 뒤 조사는 괄호 앞 말에 맞춘다: 아침(6~7시)을, 0.24(n=1,605)다
_tail = re.compile(r"(\d[\d,]*(?:\.\d+)?)" + _UNITS + r"\]?$")
particle_bad, particle_n = [], 0
for m_ in _pp.finditer(_all_txt):
    particle_n += 1
    if m_.group(3) in _BAD[_jong_tok(m_.group(1), m_.group(2))]:
        particle_bad.append(_all_txt[max(0, m_.start() - 14): m_.end() + 3])
for m_ in _pq.finditer(_all_txt):
    i_, depth_ = m_.start(), 0
    while i_ >= 0:
        depth_ += {")": 1, "(": -1}.get(_all_txt[i_], 0)
        if depth_ == 0:
            break
        i_ -= 1
    mt_ = _tail.search(_all_txt[max(0, i_ - 24):max(0, i_)])
    if i_ <= 0 or not mt_:
        continue          # 괄호 앞이 숫자가 아니면 이 검사의 대상이 아님
    particle_n += 1
    if m_.group(1) in _BAD[_jong_tok(mt_.group(1), mt_.group(2))]:
        particle_bad.append(_all_txt[max(0, i_ - 14): m_.end() + 3])

# ---- PDF: 쪽수·고아 제목
doc = fitz.open(REP / "보고서.pdf")
# ---- PDF 글자 간격: 숫자+단위 뒤 한글, 물결 앞뒤의 간격이 그 줄의 중앙값보다 0.15em 넘게 벌어진 곳 / 줄 끝에서 단위와 조사가 갈라진 곳
gap_unit, gap_tilde, split_lines = 0, 0, 0
_pat_u = re.compile(r"\d" + UNIT + r"(?=[가-힣])")
for pg in doc:
    for bl in pg.get_text("rawdict")["blocks"]:
        lines = bl.get("lines", [])
        for li, ln in enumerate(lines):
            chars = [ch for sp in ln["spans"] for ch in sp["chars"]]
            if len(chars) < 3:
                continue
            txt = "".join(ch["c"] for ch in chars)
            fs = ln["spans"][0]["size"]
            g = [chars[j + 1]["bbox"][0] - chars[j]["bbox"][2] for j in range(len(chars) - 1)]
            med = sorted(g)[len(g) // 2]
            for m_ in _pat_u.finditer(txt):
                j = m_.end() - 1
                if j < len(g) and g[j] - med > 0.15 * fs:
                    gap_unit += 1
            for m_ in re.finditer(r"\d~\d", txt):
                j = m_.start()
                if (g[j] - med > 0.15 * fs) or (g[j + 1] - med > 0.15 * fs):
                    gap_tilde += 1
            if li + 1 < len(lines) and re.search(r"\d" + UNIT + r"$", txt.rstrip()):
                nxt = "".join(ch["c"] for sp in lines[li + 1]["spans"] for ch in sp["chars"])
                if re.match(r"^(?:를|을|는|은|이|가|로|의|에|도|와|과|만)(?=[\s\.,)]|$)", nxt):
                    split_lines += 1
PH = doc[0].rect.height
body_pages, app_page = None, None
for i, pg in enumerate(doc):
    h = pg.search_for("분석도구 및 참고문헌")
    if h and body_pages is None:
        body_pages = i + h[0].y0 / PH
    if pg.search_for("표 A.") and app_page is None:
        app_page = i + 1
orphans = []
for i, pg in enumerate(doc):
    blocks = [b for b in pg.get_text("blocks") if b[6] == 0 and b[1] < PH * 0.92]
    if not blocks:
        continue
    last = max(blocks, key=lambda b: b[3])
    txt = last[4].strip()
    if re.match(r"^\d{1,2}\.(?:\d\s|\s)[가-힣A-Za-z①-⑨]", txt) and len(txt) < 80 and not txt.rstrip().endswith("."):
        orphans.append((i + 1, txt[:50]))

md = [f"# report/readability_check.md — 시인성·논증 구조 자체 점검 ({datetime.now():%Y-%m-%d %H:%M})", "",
      "| 항목 | 값 | 목표 | 판정 |", "|---|---|---|---|",
      f"| 60자 초과 문장 수(본문 단락) | {len(rows_long)} | 0 | {'통과' if not rows_long else '미달'} |",
      f"| 숫자 3개 이상 문장 수 | {len(rows_num)} | 0 | {'통과' if not rows_num else '미달'} |",
      f"| 본문 단락 수 / 문장 수 3~6 벗어난 단락 | {len(para_stats)} / {sum(1 for n, c, _ in para_stats if not 3 <= n <= 6)} | 0 | {'통과' if all(3 <= n <= 6 for n, c, _ in para_stats) else '확인'} |",
      f"| 글자 수 220~450 벗어난 단락 | {sum(1 for n, c, _ in para_stats if not 220 <= c <= 450)} | 0 | 참고(짧은 전환 단락 허용) |",
      f"| 쪽 끝 고아 제목 | {len(orphans)} | 0 | {'통과' if not orphans else '미달'} |",
      f"| nb 감싸기 적용 수(본문) | {n_nb} | — | — |",
      f"| 그림 수(본문 / 부록) | {n_fig} / {n_fig_app} | 6~9 / — | {'통과' if 6 <= n_fig <= 9 else '미달'} |",
      f"| 본문 쪽수(요약~6절) | {body_pages:.2f} | ≤6.0(목표 5.8) | {'통과' if body_pages and round(body_pages, 2) <= 6.0 else '미달'} |",
      f"| 전체 쪽수(부록 포함) | {len(doc)} | — | 부록 {app_page}쪽부터 |",
      f"| 금지 어휘 출현 | {forb_hit} | 모두 0 | {'통과' if not any(forb.values()) else '미달'} |",
      f"| 1절 첫 단락 문장 수(목적→왜 지금→빈칸→질문·산출물) | {sec1_n} | 4 | {'통과' if sec1_n == 4 else '미달'} |",
      f"| 요약 = 기준_요약문.md ⑤ 문단 | {ref_match} | 일치 | {'통과' if ref_match.startswith('일치') else '미달'} |",
      f"| 줄표(—) 출현(본문·캡션·미주, 참고문헌 제외) | {dash_n} | 0 | {'통과' if dash_n == 0 else '미달'} |",
      f"| 캡션 문장 수 2 초과 | {len(cap_bad)} | 0 | {'통과' if not cap_bad else '미달'} |",
      f"| 공고문 인용 | {notice_cites} | 0 | {'통과' if notice_cites == 0 else '미달'} |",
      f"| 미인용 참고문헌 / 목록에 없는 인용 번호 | {len(uncited)} / {len(missing)} | 0 / 0 | {'통과' if not uncited and not missing else '미달'} |",
      f"| 사실 문장의 2차 출처(뉴스·블로그·보도자료) | {len(secondary)} | 0 | {'통과' if not secondary else '미달'} |",
      f"| 요약 글자 수(공백 포함) | {len(abs_txt)} | 기준 문단 그대로 | 참고 |",
      f"| 단위·조사 공백(HTML 원문 '2.5km 를' 류) | {len(sp_unit)} | 0 | {'통과' if not sp_unit else '미달'} |",
      f"| 물결 공백(HTML 원문 '6~ 7시' 류) | {len(sp_tilde)} | 0 | {'통과' if not sp_tilde else '미달'} |",
      f"| 년·월·일 뒤 띄어쓰기 누락(HTML 원문 '2024년6일' 류) | {len(sp_ymd)} | 0 | {'통과' if not sp_ymd else '미달'} |",
      f"| PDF 글자 간격: 단위→한글 벌어짐(줄 중앙값+0.15em 초과) / 물결 앞뒤 벌어짐 | {gap_unit} / {gap_tilde} | 0 / 0 | {'통과' if gap_unit == 0 and gap_tilde == 0 else '미달'} |",
      f"| PDF 줄 끝에서 숫자+단위와 조사가 갈라진 줄 | {split_lines} | 0 | {'통과' if split_lines == 0 else '미달'} |",
      f"| 빈 표 셀(HTML, 표 D 비고 칸 제외) | {empty_td} | 0 | {'통과' if empty_td == 0 else '미달'} |",
      f"| 숫자 뒤 조사 받침 불일치('0.83로'·'0.88다' 류, 전체 HTML, 검사한 숫자+조사 {particle_n}곳) | {len(particle_bad)} | 0 | {'통과' if not particle_bad else '미달'} |",
      "", "## 각 절 첫 문장 (목적문인지 사람이 확인)", "", "| 절 | 첫 문장 |", "|---|---|"]
for t, fp in sections:
    md.append(f"| {t} | {sentences(fp)[0] if fp else '(없음)'} |")
md += ["", "## 1절 첫 단락 문장별", ""] + [f"{i + 1}. {s}" for i, s in enumerate(sentences(sec1_first))]
if rows_long:
    md += ["", "## 60자 초과 문장", ""] + [f"- ({L}자) {s}" for L, s in rows_long]
if rows_num:
    md += ["", "## 숫자 3개 이상 문장", ""] + [f"- ({k}개) {s}" for k, s in rows_num]
md += ["", "## 단락별 문장 수·글자 수", "", "| 문장 | 글자 | 첫 구절 |", "|---|---|---|"] + [f"| {n} | {c} | {t}… |" for n, c, t in para_stats]
if cap_bad:
    md += ["", "## 문장 수 2 초과 캡션", ""] + [f"- {c_}…" for c_ in cap_bad]
if particle_bad:
    md += ["", "## 숫자 뒤 조사 받침 불일치", ""] + [f"- …{t}…" for t in particle_bad]
if orphans:
    md += ["", "## 쪽 끝 고아 제목", ""] + [f"- {p}쪽: {t}" for p, t in orphans]
md += ["", "주: 문장 길이는 공백 포함 글자 수. 숫자 세기는 날짜·범위·연도쌍·통계량을 하나로, 인용·그림/표 참조·연령 구간 이름·절 참조는 제외. "
       "요약·캡션·표·미주·참고문헌은 문장 길이 검사에서 제외(미주에는 프롬프트 원문 인용이 있어 60자를 넘는다). 요약은 기준_요약문.md ⑤ 문단을 수치만 바꿔 그대로 쓴다. "
       "단위·조사·물결 공백은 HTML 원문과 PDF 글자 좌표(PyMuPDF rawdict)로 검사했다. PDF 텍스트 추출 도구는 글자 간격 휴리스틱으로 단어를 나누므로 추출 결과의 공백은 조판과 다를 수 있다."]
(REP / "readability_check.md").write_text("\n".join(md), encoding="utf-8")
print("\n".join(md[:22]))
sys.exit(0)
