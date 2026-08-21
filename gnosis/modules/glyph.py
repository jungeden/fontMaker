import cv2
import numpy as np

from fontTools.pens.ttGlyphPen import TTGlyphPen

from config import UNITS_PER_EM, GLYPH_SIZE, CURVE_SMOOTHING
from modules.vectorize import find_contours_with_holes, simplify, fix_winding


def _scale_flip(pt, upm=UNITS_PER_EM, image_size=GLYPH_SIZE):
    """
    이미지 픽셀 좌표(0~800, y가 아래로 증가) -> 폰트 유닛 좌표(0~1000, y가 위로 증가).
    """
    x, y = pt
    x = x * upm / image_size
    y = y * upm / image_size
    return (x, upm - y)


def _midpoint(a, b):
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def image_to_contours(path):
    """
    글자 PNG 한 장을 (font-space 점 리스트, is_hole) 튜플들의 리스트로 변환한다.
    pen에 바로 그리지 않고 "폰트 좌표계로 변환된 윤곽선 데이터"만 반환하므로,
    이후 compose.py에서 이 데이터를 이동/확대해서 여러 글자를 조합하는 데 재사용할 수 있다.

    - RETR_TREE 기반으로 안쪽 구멍(ㅇ,ㅎ,ㅁ,ㅂ 등)을 지원한다.
    - 각 contour의 winding(방향)을 TrueType 규칙에 맞게 보정해서 반환한다.
    """
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None

    contours, hierarchy = find_contours_with_holes(img)
    if len(contours) == 0:
        return []

    result = []
    for i, contour in enumerate(contours):
        simplified = simplify(contour)
        pts = simplified.squeeze()

        if pts.ndim != 2 or len(pts) < 3:
            continue

        is_hole = hierarchy[i][3] != -1  # parent가 있으면 구멍(내부 윤곽선)

        font_pts = np.array([_scale_flip(p) for p in pts])
        font_pts = fix_winding(font_pts, is_hole)

        result.append((font_pts.tolist(), is_hole))

    return result


def draw_contour(pen, pts, smooth=CURVE_SMOOTHING):
    """
    폰트 좌표계로 변환된 점들을 pen에 그린다.

    smooth=True 이면 다각형의 각 꼭짓점을 2차 베지어의 제어점으로 쓰고,
    변의 중점을 on-curve 점으로 사용해 부드러운 곡선을 만든다.
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
    글자 PNG 한 장을 fontTools TTGlyph 객체로 바로 변환한다.
    (개별 컴포넌트 미리보기/디버깅용. 실제 11,172자 합성에는 compose.py가
    image_to_contours() + draw_contour()를 직접 사용한다.)
    """
    contours = image_to_contours(path)
    if not contours:
        return TTGlyphPen(None).glyph()

    pen = TTGlyphPen(None)
    for pts, _is_hole in contours:
        draw_contour(pen, pts, smooth=smooth)

    return pen.glyph()


def glyph_advance_width(path, upm=UNITS_PER_EM, image_size=GLYPH_SIZE,
                         side_bearing=60):
    """개별 컴포넌트(자모)만 단독 글자로 만들 때 쓰는 폭 계산 (디버깅/미리보기용)."""
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
