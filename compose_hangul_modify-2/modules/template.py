import json
import math
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from PIL import Image, ImageDraw

from config import ROWS, COLS, CELL_SIZE, PAGE_MARGIN, GUIDE_GRAY
from modules.hangul import build_component_list as build_hangul_components
from modules.latin import build_component_list as build_latin_components, BASELINE_RATIO

# ReportLab 내장 CJK 폰트 (별도 폰트 파일 없이 한글을 그릴 수 있다)
KOREAN_FONT = "HYSMyeongJo-Medium"
pdfmetrics.registerFont(UnicodeCIDFont(KOREAN_FONT))

CELL = CELL_SIZE * mm
LEFT = PAGE_MARGIN * mm
TOP = PAGE_MARGIN * mm

CELLS_PER_PAGE = ROWS * COLS


# ────────────────────────────────────────────────────────────
# 가이드(안내선) 관련 요소는 전부 연한 회색(GUIDE_GRAY)으로 그린다.
# 종이에서 눈으로 보기엔 충분히 진하지만, 전처리 단계에서 자동으로
# 지워질 만큼은 연하다 (config.GUIDE_STRIP_THRESHOLD 참고).
# 칸을 나누는 실제 테두리(격자선)만 검정으로 남겨서 segment.py가
# 칸을 나눌 때 기준으로 쓸 수 있게 한다.
# ────────────────────────────────────────────────────────────

def _draw_hangul_watermark(c, x, y, cell, comp):
    """
    칸 뒤에 실제 예시 음절 전체("가", "곽" 등)를 크게 연한 회색으로 깔아서,
    사용자가 자기가 쓰는 자모가 전체 글자 안에서 어느 크기/위치에 있어야
    하는지 한눈에 보면서 쓸 수 있게 한다. 이 워터마크 자체는 스캔 후
    자동으로 지워지므로, 실제로 추출되는 것은 안내상자 안에 사용자가 쓴
    잉크뿐이다.
    """
    c.setFont(KOREAN_FONT, cell * 0.72)
    c.setFillGray(GUIDE_GRAY)
    c.drawCentredString(x + cell / 2, y - cell * 0.80, comp["example"])
    c.setFillGray(0)


def _draw_guide_box(c, x, y, cell, zone_shape):
    """
    칸 안에 실제 조합 시 이 자모가 차지할 영역과 같은 '가로:세로 비율'의
    안내 상자를 그린다. 세로모음용 초성은 좁고 길게, 가로모음용 초성은
    넓고 납작하게 그려지므로, 상자 모양만 보고도 글자를 어떤 비율로
    써야 하는지 감을 잡을 수 있다. 이 상자 밖으로 나가면 조합했을 때
    옆 자모와 겹칠 수 있으니, 상자 = 실제 쓰기 한계선이라고 생각하면 된다.
    """
    x0, y0, x1, y1 = zone_shape
    ratio_w = (x1 - x0) / 1000
    ratio_h = (y1 - y0) / 1000

    pad = cell * 0.12
    avail = cell - 2 * pad

    box_w = avail * ratio_w
    box_h = avail * ratio_h

    scale = min(avail / box_w if box_w else 1, avail / box_h if box_h else 1)
    box_w *= scale
    box_h *= scale

    bx = x + (cell - box_w) / 2
    by = y - cell + (cell - box_h) / 2

    c.setStrokeGray(GUIDE_GRAY)
    c.setLineWidth(0.8)
    c.setDash(2, 2)
    c.rect(bx, by, box_w, box_h)
    c.setDash()
    c.setStrokeGray(0)


def _draw_latin_guide(c, x, y, cell):
    """
    라틴 문자용 안내.

    실선 상자 = 실제로 쓸 수 있는 전체 높이(위쪽 끝=ascender, 아래쪽
    끝=descender). 이 상자를 벗어나면 글자가 잘린다.
    상자 안의 굵은 가로선 = baseline. 대부분의 글자는 이 선 위에 앉고,
    g, y, p, q, j 처럼 아래로 내려가는 글자만 이 선 아래 (상자 하단까지)
    내려가면 된다.
    """
    pad = cell * 0.12
    left = x + pad
    right = x + cell - pad
    top = y - pad
    bottom = y - cell + pad
    height_inner = top - bottom

    c.setStrokeGray(GUIDE_GRAY)

    # 실선 상자 = ascender ~ descender 전체 한계선
    c.setLineWidth(0.7)
    c.rect(left, bottom, right - left, height_inner)

    # baseline 안내선
    baseline_y = top - BASELINE_RATIO * height_inner
    c.setLineWidth(1.0)
    c.line(left, baseline_y, right, baseline_y)

    c.setStrokeGray(0)


def _draw_cell(c, x, y, cell, idx, comp):
    if comp["kind"] == "latin":
        _draw_latin_guide(c, x, y, cell)
    else:
        _draw_hangul_watermark(c, x, y, cell, comp)

    # 칸 테두리(격자선)는 검정 실선으로 유지 - segment.py가 칸을 나누는 기준.
    c.setStrokeGray(0)
    c.setLineWidth(0.8)
    c.rect(x, y - cell, cell, cell)

    if comp["kind"] != "latin":
        _draw_guide_box(c, x, y, cell, comp["zone_shape"])

    # 좌상단: 인덱스 번호 (연한 회색 - 안내용, 자동으로 지워짐)
    c.setFont("Helvetica", 6)
    c.setFillGray(GUIDE_GRAY)
    c.drawString(x + 1.5, y - 7, f"{idx:03}")

    # 라틴 칸은 우하단에 어떤 글자인지 작게 표시 (한글은 위 워터마크로 대체)
    if comp["kind"] == "latin":
        c.setFont(KOREAN_FONT, 7)
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
        c.setFont(KOREAN_FONT, 7)
        c.drawString(LEFT, height - TOP + 1.5 * mm,
                     "연한 회색 안내선/글자는 자동으로 지워집니다. 검정 테두리 안, "
                     "회색 점선/실선 상자 안에만 또렷하게 쓰세요.")

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
                    c.setStrokeGray(0)
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
    return components, n_pages


def create_grid_overlay(n_pages, output_dir="output", dpi=300):
    """
    (선택 기능) 격자선(칸 테두리)만 있는 투명 배경 PNG를 페이지별로 만든다.

    가이드 자동 제거 기능으로 보통은 필요 없지만, 직접 스캔 이미지에서
    가이드를 수동으로 지운 뒤 이 격자와 합성해서 쓰고 싶은 경우를 위한
    보조 파일이다. template.py가 실제 PDF에 그리는 격자와 동일한 비율로
    그려진다 (A4, PAGE_MARGIN/CELL_SIZE 기준).
    """
    from reportlab.lib.pagesizes import A4 as _A4
    width_pt, height_pt = _A4
    px_per_pt = dpi / 72

    W = int(width_pt * px_per_pt)
    H = int(height_pt * px_per_pt)
    left = LEFT * px_per_pt
    top = TOP * px_per_pt
    cell = CELL * px_per_pt

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    paths = []

    for page in range(n_pages):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        for r in range(ROWS):
            for col in range(COLS):
                x = left + col * cell
                y = top + r * cell
                draw.rectangle(
                    [x, y, x + cell, y + cell],
                    outline=(0, 0, 0, 255), width=2
                )

        path = f"{output_dir}/grid_overlay_page{page + 1}.png"
        img.save(path)
        paths.append(path)

    print(f"격자 전용 투명 PNG {len(paths)}장 생성 완료: {', '.join(paths)}")
    return paths
