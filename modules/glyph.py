import cv2
import numpy as np

from fontTools.pens.ttGlyphPen import TTGlyphPen

from config import UNITS_PER_EM, GLYPH_SIZE, CURVE_SMOOTHING
from modules.vectorize import find_contours_with_holes, simplify, fix_winding


def _scale_flip(pt, upm=UNITS_PER_EM, image_size=GLYPH_SIZE):
    """
    이미지 픽셀 좌표(0~800, y가 아래로 증가) -> 폰트 유닛 좌표(0~1000, y가 위로 증가).
    guide.md에서 설명한 scale_point() + (upm - y) 변환을 한 번에 처리한다.
    """
    x, y = pt
    x = x * upm / image_size
    y = y * upm / image_size
    return (x, upm - y)


def _midpoint(a, b):
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def _draw_contour(pen, pts, smooth=CURVE_SMOOTHING):
    """
    한 개의 닫힌 윤곽선을 pen에 그린다.

    smooth=True 이면 다각형의 각 꼭짓점을 2차 베지어의 제어점으로 쓰고,
    변의 중점을 on-curve 점으로 사용해 부드러운 곡선을 만든다.
    (원래 코드는 lineTo만 사용해서 손글씨 곡선이 전부 각진 다각형으로
    나왔던 문제 - guide.md에서 지적된 'Bezier Curve 미지원' 문제 - 를 해결)
    """
    pts = [tuple(p) for p in pts]
    if len(pts) < 3:
        return

    if smooth:
        n = len(pts)
        start = _midpoint(pts[-1], pts[0])
        pen.moveTo(start)
        for i in range(n):
            control = pts[i]
            end = _midpoint(pts[i], pts[(i + 1) % n])
            pen.qCurveTo(control, end)
        pen.closePath()
    else:
        pen.moveTo(pts[0])
        for p in pts[1:]:
            pen.lineTo(p)
        pen.closePath()


def image_to_glyph(path, smooth=CURVE_SMOOTHING):
    """
    글자 PNG 한 장을 fontTools TTGlyph 객체로 변환한다.

    - RETR_TREE 기반으로 안쪽 구멍(ㅇ,ㅎ,ㅁ,ㅂ 등)을 지원한다.
    - 각 contour의 winding(방향)을 TrueType 규칙에 맞게 보정한다.
    - 기본적으로 2차 베지어 곡선으로 부드럽게 그린다.
    """
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None

    contours, hierarchy = find_contours_with_holes(img)

    pen = TTGlyphPen(None)

    if len(contours) == 0:
        return pen.glyph()

    for i, contour in enumerate(contours):
        simplified = simplify(contour)
        pts = simplified.squeeze()

        if pts.ndim != 2 or len(pts) < 3:
            continue

        is_hole = hierarchy[i][3] != -1  # parent가 있으면 구멍(내부 윤곽선)

        font_pts = np.array([_scale_flip(p) for p in pts])
        font_pts = fix_winding(font_pts, is_hole)

        _draw_contour(pen, font_pts, smooth=smooth)

    return pen.glyph()


def glyph_advance_width(path, upm=UNITS_PER_EM, image_size=GLYPH_SIZE,
                         side_bearing=60):
    """
    글자마다 실제 폭에 맞는 advance width(다음 글자까지의 이동 거리)를 계산한다.
    (원래 코드는 모든 글자에 고정값 1000을 써서 넓은 글자/좁은 글자 상관없이
    같은 간격이 되던 문제 - guide.md의 'Advance Width 자동 계산' 항목 - 를 해결)

    반환값: (advance_width, left_side_bearing)
    """
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return upm, side_bearing

    inv = 255 - img
    pts = cv2.findNonZero(inv)
    if pts is None:
        return upm, side_bearing

    _, _, w, _ = cv2.boundingRect(pts)
    glyph_width = w * upm / image_size

    advance = int(round(glyph_width + side_bearing * 2))
    return advance, side_bearing
