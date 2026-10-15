"""Windows 맑은 고딕 기반 한글 PDF: 보고서/두 그림/기준일 포함."""
from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer

BASE = Path(__file__).resolve().parents[1]
REPORTS = BASE / "reports"


def select_korean_font() -> str:
    candidates = [
        Path("C:/Windows/Fonts/malgun.ttf"),
        Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    ]
    for font in candidates:
        if font.is_file():
            try:
                pdfmetrics.registerFont(TTFont("ReportKorean", str(font)))
                return "ReportKorean"
            except Exception:
                continue
    raise RuntimeError("PDF용 한글 TTF 글꼴을 찾지 못했습니다. Windows 맑은 고딕 확인 필요.")


def scaled_image(path: Path, max_width: float = 480, max_height: float = 270) -> Image:
    original_width, original_height = ImageReader(str(path)).getSize()
    scale = min(max_width / original_width, max_height / original_height)
    return Image(str(path), width=original_width * scale, height=original_height * scale)


def main() -> None:
    font = select_korean_font()
    source = REPORTS / "llm_summary.md"
    charts = [REPORTS / "naver_trend.png", REPORTS / "tourism_stay_top10.png",
              REPORTS / "tourism_consumption_top10.png"]
    required = [source, *charts]
    missing = [str(p) for p in required if not p.exists() or p.stat().st_size == 0]
    if missing:
        raise FileNotFoundError("PDF 필수 입력 파일 없음/비어 있음: " + ", ".join(missing))
    styles = getSampleStyleSheet()
    for name in ("Title", "Heading1", "Heading2", "BodyText"):
        styles[name].fontName = font
    output = REPORTS / f"tourism_trend_report_{date.today().isoformat()}.pdf"
    doc = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=55, leftMargin=55)
    story = [
        Paragraph("관광 트렌드 자동 분석 보고서", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"생성일: {date.today().isoformat()}", styles["BodyText"]),
        Spacer(1, 10),
        Paragraph("데이터 해석의 한계: NAVER 검색 ratio는 실제 검색 건수가 아닌 상대지수이며, "
                  "관광공사 강도 지표는 지역·기준월별 지수입니다. 두 자료는 단위·지역·기간이 달라 "
                  "직접 비교하거나 인과를 단정할 수 없습니다. 최신 월은 집계 중인 부분 월일 수 있습니다.",
                  styles["BodyText"]),
        Spacer(1, 12),
    ]
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            story.append(Spacer(1, 5))
        else:
            story.append(Paragraph(escape(line).replace("  ", "&nbsp; "),
                                   styles["BodyText"]))
    for figure in charts:
        story.append(Spacer(1, 14))
        story.append(scaled_image(figure))
    doc.build(story)
    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError("PDF 파일 생성 확인 실패")
    print("[PASS] PDF:", output)
    print("[REVIEW REQUIRED] PDF 한글/그래프/인과 해석을 눈으로 확인하세요.")


if __name__ == "__main__":
    main()
