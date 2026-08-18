from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

from config import CHARS, ROWS, COLS, CELL_SIZE, PAGE_MARGIN

# ── 중요한 버그 수정 ───────────────────────────────────────────
# 기존 코드는 c.setFont("Helvetica", 10) 을 사용했는데, Helvetica는
# 라틴 문자만 지원하는 표준 PDF 폰트라서 "가","나","다" 같은 한글은
# 아예 그려지지 않는다(빈 칸 또는 깨진 글자로 출력됨).
# ReportLab은 별도 폰트 파일을 넣지 않아도 쓸 수 있는 CJK용 내장
# CID 폰트(UnicodeCIDFont)를 제공하므로 이를 등록해서 사용한다.
KOREAN_FONT = "HYSMyeongJo-Medium"
pdfmetrics.registerFont(UnicodeCIDFont(KOREAN_FONT))
# ────────────────────────────────────────────────────────────

CELL = CELL_SIZE * mm
LEFT = PAGE_MARGIN * mm
TOP = PAGE_MARGIN * mm


def create_template(filename="output/template.pdf"):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    idx = 0

    for r in range(ROWS):
        for col in range(COLS):
            x = LEFT + col * CELL
            y = height - TOP - r * CELL

            c.rect(x, y - CELL, CELL, CELL)

            if idx < len(CHARS):
                # 칸 안에 연하게 참고용 글자를 인쇄 (사용자가 따라 쓰도록)
                c.setFont(KOREAN_FONT, 10)
                c.setFillGray(0.6)
                c.drawCentredString(x + CELL / 2, y - CELL + 5, CHARS[idx])
                c.setFillGray(0)

            idx += 1

    c.save()
