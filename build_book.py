# 장별 Markdown 원고(chapters/)를 표지·목차·편 표지·본문이 있는 교재 PDF로 조립하는 스크립트
import os
import re
import subprocess
import time
from pathlib import Path

import markdown
import pypdfium2 as pdfium

HERE = Path(__file__).parent

# 인쇄에 쓸 브라우저. 환경 변수 BROWSER로 지정하거나 설치된 Edge/Chrome을 자동으로 찾는다.
BROWSER_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]
BROWSER = os.environ.get("BROWSER") or next((c for c in BROWSER_CANDIDATES if Path(c).exists()), BROWSER_CANDIDATES[0])
BOOK = "해외 플랜트 현장 실무 교재"
OUT = HERE / "해외플랜트_현장실무교재.pdf"

LIST_ITEM = re.compile(r"^\s*(?:[-*] |\d+\. )")


def fix_blocks(md_text: str) -> str:
    # python-markdown은 표와 목록 앞뒤에 빈 줄이 있어야 블록으로 인식한다.
    # 목록 항목 안에 들여쓴 표는 들여쓰기를 제거해 독립된 표로 만든다.
    out: list[str] = []
    for line in md_text.splitlines():
        prev = out[-1] if out else ""
        is_table = line.lstrip().startswith("|")
        prev_is_table = prev.lstrip().startswith("|")
        if is_table:
            line = line.lstrip()
            if prev.strip() and not prev_is_table:
                out.append("")
        elif prev_is_table and line.strip():
            out.append("")
        elif (LIST_ITEM.match(line) and not line.startswith(" ") and prev.strip()
              and not LIST_ITEM.match(prev) and not prev.startswith(" ")):
            out.append("")
        out.append(line)
    return "\n".join(out)


# (편 번호, 편 제목, [(장 번호, 장 제목, 영문 제목, 원고 파일)])
PARTS = [
    (1, "플랜트 프로젝트의 이해", [
        (1, "플랜트 산업의 구조와 주요 기기", "Structure of the Plant Industry and Major Equipment", "ch01"),
        (2, "프로젝트 조직과 직무", "Project Organization and Job Roles", "ch02"),
        (3, "공정 관리", "Schedule Management", "ch03"),
        (4, "물량, 생산성과 계약", "Quantity, Productivity and Contract", "ch04"),
    ]),
    (2, "코드·표준과 품질 관리", [
        (5, "코드와 표준", "Codes and Standards", "ch05"),
        (6, "품질 관리 체계와 문서", "Quality System and Documents", "ch06"),
        (7, "용접 절차와 자격", "Welding Procedure and Qualification", "ch07"),
    ]),
    (3, "재료", [
        (8, "금속 재료의 분류와 제조", "Classification and Manufacturing of Metals", "ch08"),
        (9, "스테인리스강의 종류와 표기", "Types and Designations of Stainless Steel", "ch09"),
        (10, "스테인리스강의 부식과 표면 처리", "Corrosion and Surface Treatment of Stainless Steel", "ch10"),
        (11, "저온 재질과 충격 인성", "Low-Temperature Materials and Impact Toughness", "ch11"),
        (12, "부식과 방식", "Corrosion and Corrosion Prevention", "ch12"),
        (13, "도장과 코팅", "Painting and Coating", "ch13"),
    ]),
    (4, "배관 설계와 자재", [
        (14, "배관의 크기와 스케줄", "Pipe Size and Schedule", "ch14"),
        (15, "배관 제작 방식, 도면 표기와 무게", "Pipe Manufacturing, Drawing Notation and Weight", "ch15"),
        (16, "배관 피팅", "Pipe Fittings", "ch16"),
        (17, "소켓 용접과 분기 접속", "Socket Weld and Branch Connections", "ch17"),
        (18, "플랜지와 가스켓", "Flanges and Gaskets", "ch18"),
        (19, "볼트와 체결 관리", "Bolting and Joint Assembly", "ch19"),
        (20, "밸브", "Valves", "ch20"),
        (21, "특수 배관", "Special Piping Systems", "ch21"),
    ]),
    (5, "용접", [
        (22, "용접의 기초 용어", "Fundamental Welding Terms", "ch22"),
        (23, "용접 전기와 아크", "Welding Electricity and Arc", "ch23"),
        (24, "TIG 용접", "TIG (GTAW) Welding", "ch24"),
        (25, "보호가스와 퍼징", "Shielding Gas and Purging", "ch25"),
        (26, "용접 결함", "Welding Defects", "ch26"),
        (27, "후열처리", "Post Weld Heat Treatment", "ch27"),
        (28, "자동화 용접과 신기술", "Automated Welding and New Technologies", "ch28"),
    ]),
    (6, "검사와 시험", [
        (29, "비파괴 검사 개요와 표면 검사", "NDT Overview and Surface Examination", "ch29"),
        (30, "방사선·초음파 검사", "Radiographic and Ultrasonic Testing", "ch30"),
        (31, "압력시험", "Pressure Test", "ch31"),
    ]),
    (7, "안전과 기초 지식", [
        (32, "현장 기초 지식", "Basic Knowledge for Site Work", "ch32"),
    ]),
    (8, "스마트 건설과 산업 동향", [
        (33, "건설 자동화와 로봇", "Construction Automation and Robotics", "ch33"),
        (34, "디지털 전환과 산업 동향", "Digital Transformation and Industry Trends", "ch34"),
    ]),
]

CSS = """
@page { size: A4; margin: 24mm 16mm 20mm 16mm; }
@page cover { margin: 0; }
@page part { margin: 0; }
@page toc { margin: 22mm 18mm 18mm 18mm;
  @bottom-center { content: counter(page); font-size: 9pt; color: #555; } }
%(named)s
body { font-family: 'Malgun Gothic', 'Segoe UI', sans-serif; font-size: 10pt; line-height: 1.6; color: #222; }
section { break-before: page; }
section.cover { page: cover; height: 295mm; background: #16324f; color: #fff; padding: 88mm 22mm 0; box-sizing: border-box; break-before: auto; }
section.cover .kicker { letter-spacing: 4px; font-size: 11pt; color: #9db8d3; }
section.cover h1 { font-size: 34pt; line-height: 1.25; margin: 10px 0 14px; border: none; color: #fff; }
section.cover .sub { font-size: 14pt; color: #d5e2ef; border-top: 2px solid #4f7ba3; padding-top: 12px; }
section.cover .en { margin-top: 90mm; font-size: 11pt; color: #9db8d3; }
section.toc { page: toc; }
section.toc h1 { font-size: 22pt; color: #16324f; border-bottom: 3px solid #16324f; padding-bottom: 6px; margin: 0 0 12px; }
.toc .part { font-size: 11.5pt; font-weight: bold; color: #fff; background: #2b5c8a; padding: 3px 10px; margin: 12px 0 4px; }
.toc .row { display: flex; align-items: baseline; font-size: 10pt; padding: 2px 6px; }
.toc .row .t { flex: 0 1 auto; }
.toc .row .dots { flex: 1 1 auto; border-bottom: 1px dotted #999; margin: 0 6px; transform: translateY(-3px); }
.toc .row .p { flex: 0 0 auto; color: #16324f; font-weight: bold; }
section.partpage { page: part; height: 295mm; padding: 100mm 24mm 0; box-sizing: border-box; background: #eef3f8; }
.partpage .pno { font-size: 14pt; letter-spacing: 4px; color: #2b5c8a; font-weight: bold; }
.partpage h1 { font-size: 30pt; color: #16324f; margin: 6px 0 18px; border: none; }
.partpage ul { list-style: none; padding: 0; margin: 0; border-top: 2px solid #16324f; }
.partpage li { padding: 6px 2px; border-bottom: 1px solid #c5d2df; font-size: 11.5pt; }
.opener { border-top: 6px solid #16324f; border-bottom: 1px solid #b8c4d0; padding: 14px 0 12px; margin-bottom: 14px; }
.opener .chno { font-size: 11pt; letter-spacing: 3px; color: #2b5c8a; font-weight: bold; }
.opener h1 { font-size: 23pt; margin: 4px 0 2px; color: #16324f; border: none; line-height: 1.3; }
.opener .en { font-size: 10.5pt; color: #6b7a8a; }
h2 { font-size: 13pt; margin: 18px 0 6px; padding: 3px 0 3px 8px; border-left: 5px solid #2b5c8a; background: #f0f4f8; color: #16324f; break-after: avoid; }
h3 { font-size: 11pt; margin: 12px 0 4px; color: #2b5c8a; break-after: avoid; }
p { margin: 5px 0; }
ul, ol { margin: 4px 0 6px; padding-left: 22px; }
li { margin: 3px 0; }
code { font-family: Consolas, 'Malgun Gothic', monospace; background: #eef2f6; padding: 0 4px; border-radius: 3px; font-size: 9.2pt; }
table { border-collapse: collapse; margin: 6px 0 10px; width: 100%%; font-size: 9.3pt; break-inside: avoid; }
th, td { border: 1px solid #c5ced8; padding: 4px 7px; vertical-align: top; text-align: left; }
th { background: #dfe8f1; color: #16324f; }
figure.fig { margin: 8px 0 12px; text-align: center; break-inside: avoid; }
figure.fig svg { width: 62%%; }
figcaption { font-size: 9pt; color: #555; margin-top: 3px; }
p:has(> strong:only-child) { break-after: avoid; }
.formula { border: 1.5px solid #2b5c8a; background: #f5f9fd; padding: 8px 12px; margin: 8px 0; text-align: center; font-size: 11pt; break-inside: avoid; }
.admonition { border-left: 5px solid #2b5c8a; background: #f0f5fa; padding: 6px 12px; margin: 8px 0 10px; break-inside: avoid; }
.admonition p { margin: 2px 0; }
.admonition-title { font-weight: bold; color: #16324f; margin-bottom: 2px !important; }
.admonition.tip { border-color: #2f8f5b; background: #eef8f1; }
.admonition.tip .admonition-title { color: #1d6b40; }
.admonition.warning { border-color: #d07a12; background: #fdf4e6; }
.admonition.warning .admonition-title { color: #a45c05; }
"""


def named_page_css() -> str:
    rules = []
    for _, _, chapters in PARTS:
        for no, title, _, _ in chapters:
            head = f"제{no}장  {title}"
            rules.append(
                f'@page ch{no} {{ size: A4; margin: 24mm 16mm 20mm 16mm;'
                f' @top-left {{ content: "{BOOK}"; font-size: 8.5pt; color: #6b7a8a; border-bottom: 0.6pt solid #b8c4d0; width: 50%; text-align: left; }}'
                f' @top-right {{ content: "{head}"; font-size: 8.5pt; color: #6b7a8a; border-bottom: 0.6pt solid #b8c4d0; width: 50%; text-align: right; }}'
                f' @bottom-center {{ content: counter(page); font-size: 9pt; color: #555; }} }}'
                f" section.ch{no} {{ page: ch{no}; }}"
            )
    return "\n".join(rules)


def render_chapter(no: int, title: str, english: str, fname: str) -> str | None:
    path = HERE / "chapters" / f"{fname}.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").replace("{N}", str(no))
    body = markdown.markdown(fix_blocks(text), extensions=["tables", "sane_lists", "admonition"])
    return (
        f'<section class="chapter ch{no}"><div class="opener"><div class="chno">제 {no} 장</div>'
        f"<h1>{title}</h1><div class=\"en\">{english}</div></div>{body}</section>"
    )


def build_html(pages: dict[int, int]) -> tuple[str, list[int]]:
    parts_html, toc_rows, built = [], [], []
    for pno, ptitle, chapters in PARTS:
        chapter_html = []
        for no, title, english, fname in chapters:
            html = render_chapter(no, title, english, fname)
            if html:
                chapter_html.append(html)
                built.append(no)
        if not chapter_html:
            continue
        listing = "".join(
            f"<li>제 {no} 장  {title}</li>" for no, title, _, f in chapters if (HERE / "chapters" / f"{f}.md").exists()
        )
        parts_html.append(
            f'<section class="partpage"><div class="pno">제 {pno} 편</div><h1>{ptitle}</h1><ul>{listing}</ul></section>'
        )
        parts_html += chapter_html
        toc_rows.append(f'<div class="part">제 {pno} 편  {ptitle}</div>')
        for no, title, _, f in chapters:
            if no in built:
                toc_rows.append(
                    f'<div class="row"><span class="t">제{no}장  {title}</span><span class="dots"></span>'
                    f'<span class="p">{pages.get(no, "")}</span></div>'
                )
    cover = (
        '<section class="cover"><div class="kicker">FIELD TRAINING MANUAL</div>'
        f"<h1>{BOOK}</h1><div class=\"sub\">배관 · 용접 · 재료 · 품질 · 검사</div>"
        '<div class="en">Overseas Plant Construction Site</div></section>'
    )
    toc = '<section class="toc"><h1>목 차</h1>' + "".join(toc_rows) + "</section>"
    css = CSS % {"named": named_page_css()}
    html = (
        f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>{css}</style></head><body>'
        + cover + toc + "".join(parts_html) + "</body></html>"
    )
    return html, built


def print_pdf(html: str) -> None:
    src = HERE / f"_book_{time.time_ns()}.html"  # 파일명이 같으면 브라우저 캐시가 재사용되므로 매번 다르게 한다
    src.write_text(html, encoding="utf-8")
    subprocess.run(
        [BROWSER, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={OUT}", src.as_uri()],
        check=True, timeout=600,
    )
    src.unlink()


def find_pages(built: list[int]) -> dict[int, int]:
    pdf = pdfium.PdfDocument(OUT.read_bytes())  # 파일 핸들을 잡아 두면 다음 인쇄가 덮어쓰지 못한다
    texts = [pdf[i].get_textpage().get_text_range() for i in range(len(pdf))]
    lookup = {no: (english, title) for _, _, chs in PARTS for no, title, english, _ in chs}
    pages: dict[int, int] = {}
    for no in built:
        english, _ = lookup[no]
        for i, t in enumerate(texts):
            if english in t:
                pages[no] = i + 1
                break
    return pages


def main() -> None:
    html, built = build_html({})
    print_pdf(html)
    pages = find_pages(built)
    html, _ = build_html(pages)
    print_pdf(html)
    pdf = pdfium.PdfDocument(OUT.read_bytes())
    print(f"생성: {OUT.name}, {len(pdf)}쪽, 장 {len(built)}개")


if __name__ == "__main__":
    main()
