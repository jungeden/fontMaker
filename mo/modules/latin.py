"""
영문 대소문자 / 숫자 / 특수문자용 컴포넌트.

한글 자모와 달리 이 문자들은 서로 조합되지 않는다. 템플릿 한 칸에 문자
하나씩 받아서 그대로 하나의 글리프로 만든다.

다만 한글(정사각형, baseline=0에서 위로만 그려짐)과 달리 라틴 문자는
g, y, p, q, j 처럼 baseline 아래로 내려가는 글자(descender)가 있기 때문에,
글자를 칸 안에서 "내용 기준으로 다시 잘라 baseline에 맞추는" 방식(한글에
쓰는 방식)을 쓰면 안 된다. 대신 템플릿에 baseline 안내선을 인쇄해두고,
칸을 안내선 위치 그대로(내용 기준 재정렬 없이) 잘라서 그 위치 정보를
유지한다. (segment.py의 normalize_latin_cell 참고)
"""

from pathlib import Path

import cv2
import numpy as np

from fontTools.pens.ttGlyphPen import TTGlyphPen

from config import UNITS_PER_EM, GLYPH_SIZE, ASCENDER, DESCENDER
from modules.vectorize import find_contours_with_holes, simplify, fix_winding
from modules.glyph import draw_contour

# 출력 가능한 기본 ASCII 문자 전체: 숫자, 영문 대소문자, 대부분의 특수문자/기호.
# (공백은 그려지는 모양이 없으므로 별도 처리)
ASCII_CHARS = [chr(c) for c in range(0x21, 0x7F)]  # '!' ~ '~', 94자

# ASCII에는 없지만 모바일 키보드 기호 화면 등에서 자주 쓰는 추가 문자.
EXTRA_CHARS = [
    # 말줄임표, 대시류
    "…", "—", "–", "·",
    # 스마트 따옴표
    "\u201c", "\u201d", "\u2018", "\u2019",  # “ ” ‘ ’
    # 한국어/일본어 인용부호(낫표)
    "「", "」", "『", "』", "【", "】",
    # 자주 쓰는 기호/장식 문자
    "★", "☆", "♥", "♡", "○", "●", "□", "■", "◇", "◆", "△", "▲",
    "※", "→", "←", "↑", "↓",
    # 통화/저작권 기호
    "₩", "©", "®", "™",
]

LATIN_CHARS = ASCII_CHARS + EXTRA_CHARS  # 총 94 + 33 = 127자

# baseline이 칸(정확히는 칸에서 여백을 뺀 안쪽 영역) 위에서부터 몇 % 위치에
# 있는지. ASCENDER:DESCENDER = 800:200 이므로 위에서 80% 지점이 baseline이다.
# (config.py의 ASCENDER/DESCENDER와 항상 같은 비율을 쓰도록 계산해서, 폰트
#  전체 지표와 템플릿 안내선이 어긋나지 않게 한다)
BASELINE_RATIO = ASCENDER / (ASCENDER - DESCENDER)  # 기본값: 0.8

# 대문자 기준 목표 높이 (폰트 유닛, UPM=1000 기준). 한글 음절이 보통
# 800~900 유닛 정도 높이로 그려지므로, 라틴 대문자도 비슷한 시각적
# 무게감을 갖도록 이 값을 목표로 전체 배율을 자동으로 맞춘다.
TARGET_CAP_HEIGHT = 750

# 배율 보정이 너무 과하게 걸리지 않도록 하는 안전 범위.
MIN_AUTO_SCALE = 0.5
MAX_AUTO_SCALE = 2.5

SIDE_BEARING = 60
SPACE_ADVANCE = UNITS_PER_EM // 3


def component_id(ch):
    return f"latin_{ord(ch):04X}"


def build_component_list():
    """손글씨로 받아야 할 라틴/숫자/특수문자 컴포넌트 목록."""
    components = []
    for ch in LATIN_CHARS:
        components.append({
            "id": component_id(ch),
            "kind": "latin",
            "jamo": ch,
            "batchim": None,
            "group": None,
            "label": f"문자 '{ch}' (U+{ord(ch):04X})",
            "example": ch,
            "zone_shape": (0, 0, 1000, 1000),  # 사용 안 함 (라틴은 baseline 안내선을 따로 그림)
        })
    return components


def _scale_flip_latin(pt, upm=UNITS_PER_EM, image_size=GLYPH_SIZE):
    """
    이미지 픽셀 좌표 -> 폰트 유닛 좌표.
    한글용 _scale_flip과 달리, 이미지 최상단이 ASCENDER, 최하단이 DESCENDER가
    되도록 매핑해서 baseline(=0)의 실제 위치가 살아있게 한다.
    """
    x, y = pt
    fx = x * upm / image_size
    fy = ASCENDER - (y / image_size) * (ASCENDER - DESCENDER)
    return (fx, fy)


def image_to_contours_latin(path):
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

        is_hole = hierarchy[i][3] != -1
        font_pts = np.array([_scale_flip_latin(p) for p in pts])
        font_pts = fix_winding(font_pts, is_hole)
        result.append((font_pts.tolist(), is_hole))

    return result


def _calc_global_scale(raw_glyphs):
    """
    대문자 A~Z의 실제 손글씨 높이(중앙값)를 측정해서, 그 높이가
    TARGET_CAP_HEIGHT에 오도록 하는 전체 배율을 계산한다.

    한글은 segment.py에서 자모마다 목표 높이로 강제 확대/축소하지만,
    라틴 문자는 baseline 정보를 지키기 위해 그런 보정을 하지 않아서
    사용자가 쓴 크기 그대로 들어간다. 그 결과 한글 옆에 놓았을 때
    상대적으로 작아 보이는 문제가 있었는데, 여기서 대문자 높이를
    기준으로 전체적으로 한 번에 배율을 맞춰서 해결한다. (개별 문자마다
    다른 배율을 적용하면 문자 간 상대적 크기 비율이 깨지므로, 반드시
    모든 라틴/기호 문자에 "같은" 배율 하나만 적용해야 한다)
    """
    cap_heights = []
    for code in range(ord('A'), ord('Z') + 1):
        gname = f"latin{code:04X}"
        entry = raw_glyphs.get(gname)
        if not entry:
            continue
        ys = [y for pts, _ in entry["contours"] for _, y in pts]
        if ys:
            cap_heights.append(max(ys))

    if not cap_heights:
        return 1.0, 0

    cap_heights.sort()
    median_cap = cap_heights[len(cap_heights) // 2]

    if median_cap <= 0:
        return 1.0, len(cap_heights)

    scale = TARGET_CAP_HEIGHT / median_cap
    scale = max(MIN_AUTO_SCALE, min(MAX_AUTO_SCALE, scale))
    return scale, len(cap_heights)


def build_latin_glyphs(glyph_dir, manifest):
    """
    manifest(전체 컴포넌트 목록, data/manifest.json)를 순회하면서
    kind == "latin" 인 항목만 글리프로 만든다.
    (인덱스는 manifest 안에서의 절대 위치를 그대로 쓰므로, 한글 컴포넌트와
    섞여 있어도 파일명({idx:03}.png)이 어긋나지 않는다)
    """
    glyph_dir = Path(glyph_dir)

    # 1차: 모든 라틴/기호 컴포넌트의 원본 윤곽선을 먼저 읽어온다.
    raw = {}
    for i, comp in enumerate(manifest):
        if comp["kind"] != "latin":
            continue

        png = glyph_dir / f"{i:03}.png"
        if not png.exists():
            continue

        contours = image_to_contours_latin(png)
        if not contours:
            continue

        ch = comp["jamo"]
        gname = f"latin{ord(ch):04X}"
        raw[gname] = {"contours": contours, "char": ch}

    # 2차: 대문자 높이를 기준으로 전체 배율을 한 번 계산해서 모두에게 적용.
    global_scale, n_samples = _calc_global_scale(raw)
    if n_samples:
        print(f"라틴 문자 크기 보정: 대문자 {n_samples}개 기준 배율 {global_scale:.2f}배 적용")

    glyphs = {"space": TTGlyphPen(None).glyph()}
    metrics = {"space": (SPACE_ADVANCE, 0)}
    cmap = {0x20: "space"}

    built = 0
    for gname, entry in raw.items():
        pen = TTGlyphPen(None)
        xs = []
        for pts, _is_hole in entry["contours"]:
            scaled = [(x * global_scale, y * global_scale) for x, y in pts]
            xs.extend(x for x, _ in scaled)
            draw_contour(pen, scaled)

        glyphs[gname] = pen.glyph()

        glyph_w = (max(xs) - min(xs)) if xs else 0
        advance = int(round(glyph_w + SIDE_BEARING * 2))
        metrics[gname] = (advance, SIDE_BEARING)

        cmap[ord(entry["char"])] = gname
        built += 1

    return glyphs, cmap, metrics, built
