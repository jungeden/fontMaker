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
from modules.hangul import (
    build_component_list as build_hangul_components,
    decompose_code,
    ZONE_LAYOUTS,
    VOWEL_GROUP,
)
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

def _zone_to_rect(x, y, cell, zone_shape, pad_ratio=0.12):
    """
    자모 하나가 차지하는 zone(0~1000 정사각형 기준 x0,y0,x1,y1)을,
    실제 칸(cell) 안에서 그 zone이 있어야 할 절대 위치/크기로 변환한다.

    중요: 이 함수 하나로 안내 상자(_draw_guide_box)와 예시 워터마크
    (_draw_hangul_watermark)를 둘 다 계산해야, 두 가지가 항상 정확히
    같은 위치를 가리킨다. (이전 버전은 워터마크를 폰트가 자체적으로
    조합한 위치에 그리고, 안내 상자는 우리 zone 좌표로 따로 그려서
    서로 안 맞는 문제가 있었다)
    """
    x0, y0, x1, y1 = zone_shape
    pad = cell * pad_ratio
    avail = cell - 2 * pad
    scale = avail / 1000

    bx = x + pad + x0 * scale
    by = (y - cell) + pad + y0 * scale
    bw = (x1 - x0) * scale
    bh = (y1 - y0) * scale
    return bx, by, bw, bh


def _draw_jamo_in_zone(c, x, y, cell, zone_shape, ch, gray=GUIDE_GRAY):
    """zone 위치/크기에 맞춰 자모 하나를 연한 회색으로 그린다."""
    bx, by, bw, bh = _zone_to_rect(x, y, cell, zone_shape)
    fs = min(bw, bh) * 0.92

    c.setFont(KOREAN_FONT, fs)
    c.setFillGray(gray)
    c.drawCentredString(bx + bw / 2, by + bh * 0.12, ch)
    c.setFillGray(0)


def _draw_hangul_watermark(c, x, y, cell, comp):
    """
    실제 예시 음절("가", "곽" 등)을 우리 zone 좌표계 그대로 초성/중성/(종성)
    각각의 위치에 나눠 그린다. _draw_guide_box와 정확히 같은 zone 좌표를
    쓰기 때문에, 점선/실선 안내 상자가 항상 워터마크의 해당 부분과
    정확히 겹친다 - 즉 "점선 박스 안 = 워터마크에서 내가 써야 할 자모가
    있는 자리"가 항상 성립한다.
    """
    cho, jung, jong = decompose_code(ord(comp["example"]))
    group = VOWEL_GROUP[jung]
    has_batchim = jong is not None
    layout = ZONE_LAYOUTS[(has_batchim, group)]

    _draw_jamo_in_zone(c, x, y, cell, layout["cho"], cho)
    _draw_jamo_in_zone(c, x, y, cell, layout["jung"], jung)
    if has_batchim:
        _draw_jamo_in_zone(c, x, y, cell, layout["jong"], jong)


def _draw_guide_box(c, x, y, cell, zone_shape):
    """
    이 칸에서 실제로 손글씨를 써야 할 영역(=워터마크에서 해당 자모가
    있는 자리와 정확히 같은 자리)에 안내 상자를 그린다. 이 상자 밖으로
    나가면 조합했을 때 옆 자모와 겹칠 수 있으니, 상자 = 실제 쓰기
    한계선이라고 생각하면 된다.
    """
    bx, by, bw, bh = _zone_to_rect(x, y, cell, zone_shape)

    c.setStrokeGray(GUIDE_GRAY)
    c.setLineWidth(0.8)
    c.setDash(2, 2)
    c.rect(bx, by, bw, bh)
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
                     "연한 회색은 전부 자동으로 지워집니다. 점선/실선 상자 = 워터마크에서 "
                     "내가 써야 할 자모가 있는 자리와 정확히 같은 위치입니다. 그 안에만 쓰세요.")

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
