import json
from pathlib import Path

from fontTools.pens.ttGlyphPen import TTGlyphPen

from config import UNITS_PER_EM
from modules.glyph import image_to_contours, draw_contour
from modules.hangul import (
    VOWEL_GROUP,
    ZONE_LAYOUTS,
    component_id,
    decompose_code,
)

HANGUL_START = 0xAC00
HANGUL_END = 0xD7A3  # inclusive


def load_component_contours(glyph_dir="data/glyphs", manifest_path="data/manifest.json"):
    """
    manifest.json(템플릿 생성 시 저장된 183개 컴포넌트 순서)과
    data/glyphs 안의 인덱스별 PNG를 읽어서, id -> contour 데이터 캐시를 만든다.
    """
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    glyph_dir = Path(glyph_dir)

    cache = {}
    missing = []

    for i, comp in enumerate(manifest):
        png = glyph_dir / f"{i:03}.png"
        if not png.exists():
            missing.append(comp["id"])
            continue

        contours = image_to_contours(png)
        if contours:
            cache[comp["id"]] = contours
        else:
            missing.append(comp["id"])

    return cache, missing

# 크기 불변
# def _transform_contours(contours, zone, upm=UNITS_PER_EM):

#     x0, y0, x1, y1 = zone

#     zone_w = x1 - x0
#     zone_h = y1 - y0

#     offset_x = x0 + (zone_w - upm) / 2
#     offset_y = y0 + (zone_h - upm) / 2

#     out=[]

#     for pts,is_hole in contours:
#         new_pts=[
#             (
#                 x + offset_x,
#                 y + offset_y,
#             )
#             for x,y in pts
#         ]
#         out.append((new_pts,is_hole))

#     return out

#크기 가변, 비율 유지
def _transform_contours(contours, zone, upm=UNITS_PER_EM):
    """
    원본 비율을 유지하면서 zone 안에 맞춘다.
    (letterbox 방식)
    """
    x0, y0, x1, y1 = zone

    zone_w = x1 - x0
    zone_h = y1 - y0

    # 하나의 배율만 사용
    scale = min(zone_w / upm, zone_h / upm)

    draw_w = upm * scale
    draw_h = upm * scale

    # 가운데 정렬
    offset_x = x0 + (zone_w - draw_w) / 2
    offset_y = y0 + (zone_h - draw_h) / 2

    out = []

    for pts, is_hole in contours:
        new_pts = [
            (
                x * scale + offset_x,
                y * scale + offset_y,
            )
            for x, y in pts
        ]
        out.append((new_pts, is_hole))

    return out

# 원래
# def _transform_contours(contours, zone, upm=UNITS_PER_EM):
#     """
#     컴포넌트가 그려진 1000x1000 기준 좌표를, 실제 음절 안에서 이 컴포넌트가
#     차지할 사각형(zone)으로 이동/확대(letterbox 없이 딱 맞춰 늘림)한다.
#     """
#     x0, y0, x1, y1 = zone
#     sx = (x1 - x0) / upm
#     sy = (y1 - y0) / upm

#     out = []
#     for pts, is_hole in contours:
#         new_pts = [(x * sx + x0, y * sy + y0) for x, y in pts]
#         out.append((new_pts, is_hole))
#     return out


def compose_syllable_glyph(cache, cho, jung, jong=None):
    """초/중/종성 자모 하나로 완성형 음절 하나의 TTGlyph를 조합한다."""
    group = VOWEL_GROUP[jung]
    has_batchim = jong is not None
    layout = ZONE_LAYOUTS[(has_batchim, group)]

    cho_contours = cache.get(component_id("cho", cho, has_batchim, group))
    jung_contours = cache.get(component_id("jung", jung, has_batchim))

    if cho_contours is None or jung_contours is None:
        return None  # 아직 손글씨로 채워지지 않은 컴포넌트

    all_contours = []
    all_contours += _transform_contours(cho_contours, layout["cho"])
    all_contours += _transform_contours(jung_contours, layout["jung"])

    if has_batchim:
        jong_contours = cache.get(component_id("jong", jong))
        if jong_contours is None:
            return None
        all_contours += _transform_contours(jong_contours, layout["jong"])

    pen = TTGlyphPen(None)
    for pts, _is_hole in all_contours:
        draw_contour(pen, pts)

    return pen.glyph()


def compose_all(glyph_dir="data/glyphs", manifest_path="data/manifest.json"):
    """
    가(0xAC00) ~ 힣(0xD7A3) 완성형 한글 11,172자를 전부 조합한다.
    아직 손글씨가 채워지지 않은 컴포넌트가 필요한 음절은 건너뛴다
    (부분적으로만 손글씨를 채워도 그 범위 내에서 폰트를 만들어볼 수 있다).

    반환값: (glyphs: {glyph_name: TTGlyph}, cmap: {codepoint: glyph_name},
             built_count, skipped_count)
    """
    cache, missing = load_component_contours(glyph_dir, manifest_path)

    if missing:
        print(f"참고: {len(missing)}개 컴포넌트가 아직 없어서 관련 음절은 제외됩니다.")

    glyphs = {}
    cmap = {}
    built = 0
    skipped = 0

    for code in range(HANGUL_START, HANGUL_END + 1):
        cho, jung, jong = decompose_code(code)

        glyph = compose_syllable_glyph(cache, cho, jung, jong)
        if glyph is None:
            skipped += 1
            continue

        gname = f"uni{code:04X}"
        glyphs[gname] = glyph
        cmap[code] = gname
        built += 1

    return glyphs, cmap, built, skipped
