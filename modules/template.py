import json
import math
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

from config import ROWS, COLS, CELL_SIZE, PAGE_MARGIN
from modules.hangul import build_component_list as build_hangul_components
from modules.latin import build_component_list as build_latin_components, BASELINE_RATIO

# ReportLab 내장 CJK 폰트 (별도 폰트 파일 없이 한글을 그릴 수 있다)
KOREAN_FONT = "HYSMyeongJo-Medium"
pdfmetrics.registerFont(UnicodeCIDFont(KOREAN_FONT))

CELL = CELL_SIZE * mm
LEFT = PAGE_MARGIN * mm
TOP = PAGE_MARGIN * mm

CELLS_PER_PAGE = ROWS * COLS


def _draw_guide_box(c, x, y, cell, zone_shape):
    """
    칸 안에 실제 조합 시 이 자모가 차지할 영역과 같은 '가로:세로 비율'의
    안내 상자를 그린다. 세로모음용 초성은 좁고 길게, 가로모음용 초성은
    넓고 납작하게 안내 상자가 그려지므로, 사용자가 상자 모양만 보고도
    글자를 어떤 비율로 써야 하는지 감을 잡을 수 있다.
    """
    x0, y0, x1, y1 = zone_shape
    ratio_w = (x1 - x0) / 1000
    ratio_h = (y1 - y0) / 1000

    pad = cell * 0.12
    avail = cell - 2 * pad

    box_w = avail * ratio_w
    box_h = avail * ratio_h

    # 비율 유지한 채 사용 가능한 영역 안에 맞춘다 (letterbox)
    scale = min(avail / box_w if box_w else 1, avail / box_h if box_h else 1)
    box_w *= scale
    box_h *= scale

    bx = x + (cell - box_w) / 2
    by = y - cell + (cell - box_h) / 2

    c.setLineWidth(0.4)
    c.setDash(2, 2)
    c.rect(bx, by, box_w, box_h)
    c.setDash()


def _draw_latin_guide(c, x, y, cell):
    """
    라틴 문자용 안내: g,y,p 같은 내림선 글자를 위해 baseline 위치를 선으로
    표시한다. segment.py는 이 칸을 '내용 기준으로 재정렬'하지 않고 그대로
    자르므로, 여기 그려진 baseline 비율이 실제 폰트의 baseline과 일치해야
    한다 (BASELINE_RATIO = ASCENDER/(ASCENDER-DESCENDER)).
    """
    pad = cell * 0.12
    left = x + pad
    right = x + cell - pad
    top = y - pad
    bottom = y - cell + pad
    height_inner = top - bottom

    c.setLineWidth(0.4)
    c.setDash(2, 2)
    c.rect(left, bottom, right - left, height_inner)
    c.setDash()

    baseline_y = top - BASELINE_RATIO * height_inner
    c.setLineWidth(0.6)
    c.line(left, baseline_y, right, baseline_y)


def _draw_cell(c, x, y, cell, idx, comp):
    c.setLineWidth(0.8)
    c.rect(x, y - cell, cell, cell)

    if comp["kind"] == "latin":
        _draw_latin_guide(c, x, y, cell)
    else:
        _draw_guide_box(c, x, y, cell, comp["zone_shape"])

    # 좌상단: 인덱스 번호 (segment.py / 범례와 대조용)
    c.setFont("Helvetica", 6)
    c.drawString(x + 1.5, y - 7, f"{idx:03}")

    # 우하단: 참고용 예시 (아주 작게, 회색)
    c.setFont(KOREAN_FONT, 7)
    c.setFillGray(0.55)
    c.drawRightString(x + cell - 2, y - cell + 2, comp["example"])
    c.setFillGray(0)


def create_template(filename="output/template.pdf", manifest_path="data/manifest.json"):
    components = build_hangul_components() + build_latin_components()

    Path(manifest_path).parent.mkdir(parents=True, exist_ok=True)
    Path(manifest_path).write_text(
        json.dumps(components, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    n_pages = math.ceil(len(components) / CELLS_PER_PAGE)

    idx = 0
    for page in range(n_pages):
        c.setFont(KOREAN_FONT, 9)
        c.drawString(LEFT, height - TOP + 5 * mm,
                     f"손글씨 폰트 원고지  ({page + 1}/{n_pages} 페이지, "
                     f"{idx}~{min(idx + CELLS_PER_PAGE, len(components)) - 1}번)")

        for r in range(ROWS):
            for col in range(COLS):
                x = LEFT + col * CELL
                y = height - TOP - r * CELL

                if idx < len(components):
                    _draw_cell(c, x, y, CELL, idx, components[idx])
                else:
                    # 마지막 페이지에서 칸이 남으면 빈 테두리만 그린다.
                    # (페이지마다 항상 ROWS x COLS 격자 전체를 인쇄해야
                    #  스캔한 사진에서 칸을 나눌 때 격자가 일정하게 유지된다)
                    c.setLineWidth(0.8)
                    c.rect(x, y - CELL, CELL, CELL)

                idx += 1

        c.showPage()

    # ── 범례 페이지: 인덱스 -> 자모/설명/예시 전체 목록 ──
    line_h = 4.2 * mm
    lines_per_page = int((height - 2 * TOP) / line_h)

    for start in range(0, len(components), lines_per_page):
        c.setFont(KOREAN_FONT, 10)
        c.drawString(LEFT, height - TOP, "범례 (칸 번호 -> 어떤 자모를 써야 하는지)")

        yy = height - TOP - 8 * mm
        for i in range(start, min(start + lines_per_page, len(components))):
            comp = components[i]
            c.setFont(KOREAN_FONT, 8)
            c.drawString(
                LEFT, yy,
                f"{i:03}  {comp['label']}   (예시: {comp['example']})"
            )
            yy -= line_h

        c.showPage()

    c.save()
    print(f"{filename} 생성 완료 ({n_pages}장 원고지 + 범례). "
          f"컴포넌트 목록은 {manifest_path} 에 저장됨.")
