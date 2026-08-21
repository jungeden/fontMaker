"""
라틴 문자 쌍 사이의 자동 커닝(kerning) 계산 + GPOS kern 피처 적용.

커닝이란 특정 두 글자를 나란히 놓았을 때 생기는 시각적인 간격 차이를
보정하는 것이다. 예를 들어 활자에서 "AV"를 그냥 이어붙이면 사이에
불필요하게 큰 틈이 생기는데, 커닝으로 이 틈을 좁혀서 다른 글자 쌍과
비슷한 간격으로 보이게 만든다.

손글씨는 활자처럼 규격화되어 있지 않아서 완벽한 커닝표를 손으로 만들기는
어렵지만, 각 글자의 실제 잉크 윤곽선(왼쪽 끝/오른쪽 끝 프로파일)을
계산해서 너무 붙거나 너무 뜬 쌍만 자동으로 보정해준다.

(한글 음절은 전부 같은 폭의 정사각형 칸에 들어가는 전각 문자라서
커닝을 적용하지 않는다 - 이게 표준적인 한글 조판 방식이다)
"""

from fontTools.pens.recordingPen import RecordingPen
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

from config import KERNING_MAX_RATIO, KERNING_MAX_ABS

RASTER_ROWS = 40          # 프로파일 샘플링 해상도 (세로 방향)
MIN_KERN_UNITS = 15       # 이보다 작은 보정은 무시 (피처 용량 절약, 육안으로도 티 안 남)
DEFAULT_TARGET_GAP = 100  # 글자 사이에 이상적으로 남기고 싶은 여백 (폰트 유닛)


def _contours_of(glyph, glyf):
    pen = RecordingPen()
    glyph.draw(pen, glyf)
    contours, cur = [], []
    for cmd, pts in pen.value:
        if cmd == "moveTo":
            cur = [pts[0]]
        elif cmd in ("qCurveTo", "lineTo"):
            cur.extend(pts)
        elif cmd == "closePath":
            if len(cur) >= 2:
                contours.append(cur)
            cur = []
    return contours


def _profile(contours, ascender, descender, rows=RASTER_ROWS):
    """
    각 행(row, 세로 위치)마다 잉크의 왼쪽 끝(min x)과 오른쪽 끝(max x)을
    계산한다 (수평선을 그어서 윤곽선과 만나는 지점을 찾는 scanline 교차법).
    잉크가 없는 행은 None.
    """
    left = [None] * rows
    right = [None] * rows
    if not contours:
        return left, right

    step = (ascender - descender) / rows

    for row in range(rows):
        y = ascender - (row + 0.5) * step
        xs = []
        for c in contours:
            n = len(c)
            for i in range(n):
                x1, y1 = c[i]
                x2, y2 = c[(i + 1) % n]
                if y1 == y2:
                    continue
                if min(y1, y2) <= y < max(y1, y2):
                    t = (y - y1) / (y2 - y1)
                    xs.append(x1 + t * (x2 - x1))
        if xs:
            left[row] = min(xs)
            right[row] = max(xs)

    return left, right


def build_kern_feature(font, latin_cmap, target_gap=DEFAULT_TARGET_GAP):
    """
    font: fontTools TTFont (glyf, hmtx, hhea, cmap 등이 이미 설정된 상태)
    latin_cmap: {codepoint: glyph_name} (라틴/숫자/특수문자만)

    라틴 글자들의 모든 순서쌍에 대해 커닝 값을 계산하고, 유의미한 보정이
    필요한 쌍만 GPOS kern 피처로 추가한다. 반환값: 추가된 커닝 쌍 개수.
    """
    if not latin_cmap:
        return 0

    glyf = font["glyf"]
    hmtx = font["hmtx"]
    ascender = font["hhea"].ascent
    descender = font["hhea"].descent

    names = sorted(set(latin_cmap.values()))

    profiles = {}
    for name in names:
        if name not in glyf:
            continue
        contours = _contours_of(glyf[name], glyf)
        profiles[name] = _profile(contours, ascender, descender)

    lines = []
    for nameL in names:
        if nameL not in profiles or nameL not in hmtx.metrics:
            continue
        advanceL = hmtx[nameL][0]
        _, rightL = profiles[nameL]
        if all(v is None for v in rightL):
            continue

        for nameR in names:
            if nameL == nameR or nameR not in profiles:
                continue
            leftR, _ = profiles[nameR]
            if all(v is None for v in leftR):
                continue

            gaps = [
                (lR + advanceL) - rL
                for rL, lR in zip(rightL, leftR)
                if rL is not None and lR is not None
            ]
            if not gaps:
                continue

            kern = target_gap - min(gaps)
            limit = max(advanceL * KERNING_MAX_RATIO, KERNING_MAX_ABS)
            kern = max(-limit, min(limit, kern))
            kern = round(kern)

            if abs(kern) >= MIN_KERN_UNITS:
                lines.append(f"    pos {nameL} {nameR} {kern};")

    if not lines:
        return 0

    fea = "feature kern {\n" + "\n".join(lines) + "\n} kern;\n"
    addOpenTypeFeaturesFromString(font, fea)
    return len(lines)
