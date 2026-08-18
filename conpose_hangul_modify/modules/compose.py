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
    KIND_SCALE,
    COMPONENT_SCALE,
    COMPONENT_OFFSET,
)

HANGUL_START = 0xAC00
HANGUL_END = 0xD7A3


def load_component_contours(glyph_dir="data/glyphs", manifest_path="data/manifest.json"):
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


def _get_contours_bbox(contours):
    """윤곽선 데이터에서 실제 글씨가 차지하는 최소/최대 좌표(Bounding Box)를 계산합니다."""
    if not contours:
        return 0, 0, 0, 0
    
    all_x = []
    all_y = []
    for pts, _ in contours:
        for x, y in pts:
            all_x.append(x)
            all_y.append(y)
            
    if not all_x:
        return 0, 0, 0, 0
        
    return min(all_x), min(all_y), max(all_x), max(all_y)


def _transform_contours(contours, zone, kind, jamo, upm=UNITS_PER_EM):
    """
    원본 비율을 완벽히 유지하면서, 자모의 실제 Bounding Box를 기반으로 
    해당 가이드 영역(zone)의 중앙에 맞추고 보정값을 적용합니다.
    """
    x0, y0, x1, y1 = zone
    zone_w = x1 - x0
    zone_h = y1 - y0

    # 1. 실제 손글씨 윤곽선의 크기(Bounding Box) 추출
    g_x0, g_y0, g_x1, g_y1 = _get_contours_bbox(contours)
    glyph_w = g_x1 - g_x0
    glyph_h = g_y1 - g_y0

    # 예외 처리: 유효한 윤곽선이 없다면 변환 없이 반환
    if glyph_w <= 0 or glyph_h <= 0:
        return contours

    # 2. 기본 배율 계산: 원본 비율을 유지하면서 가이드 영역(zone)에 가득 차도록 함 (Letterbox 방식)
    base_scale = min(zone_w / glyph_w, zone_h / glyph_h)

    # 3. hangul.py에 설정된 자모별/유형별 보정값 적용
    k_scale = KIND_SCALE.get(kind, 1.0)
    c_scale = COMPONENT_SCALE.get(jamo, 1.0)
    final_scale = base_scale * k_scale * c_scale

    # 4. 배율이 적용된 최종 크기 계산
    draw_w = glyph_w * final_scale
    draw_h = glyph_h * final_scale

    # 5. 가이드 영역(zone)의 한가운데로 오도록 정렬 위치 계산
    center_x = x0 + (zone_w - draw_w) / 2
    center_y = y0 + (zone_h - draw_h) / 2

    # 6. 자모별 미세 위치 오프셋 값 가져오기
    offset_x, offset_y = COMPONENT_OFFSET.get(jamo, (0, 0))

    # 7. 실제 좌표 이동값 계산 (글자 고유의 시작점 g_x0, g_y0를 0으로 영점 조절 후 center로 이동)
    final_x = center_x + offset_x - (g_x0 * final_scale)
    final_y = center_y + offset_y - (g_y0 * final_scale)

    out = []
    for pts, is_hole in contours:
        new_pts = [
            (x * final_scale + final_x, y * final_scale + final_y)
            for x, y in pts
        ]
        out.append((new_pts, is_hole))
        
    return out


def compose_syllable_glyph(cache, cho, jung, jong=None):
    """초/중/종성 자모 하나로 완성형 음절 하나의 TTGlyph를 조합합니다."""
    group = VOWEL_GROUP[jung]
    has_batchim = jong is not None
    layout = ZONE_LAYOUTS[(has_batchim, group)]

    cho_contours = cache.get(component_id("cho", cho, has_batchim, group))
    jung_contours = cache.get(component_id("jung", jung, has_batchim))

    if cho_contours is None or jung_contours is None:
        return None  # 컴포넌트 부족 시 스킵

    all_contours = []
    # _transform_contours에 자모 종류(kind)와 실제 자모 글자(jamo)를 함께 전달합니다.
    all_contours += _transform_contours(cho_contours, layout["cho"], "cho", cho)
    all_contours += _transform_contours(jung_contours, layout["jung"], "jung", jung)

    if has_batchim:
        jong_contours = cache.get(component_id("jong", jong))
        if jong_contours is None:
            return None
        all_contours += _transform_contours(jong_contours, layout["jong"], "jong", jong)

    pen = TTGlyphPen(None)
    for pts, _is_hole in all_contours:
        draw_contour(pen, pts)

    return pen.glyph()


def compose_all(glyph_dir="data/glyphs", manifest_path="data/manifest.json"):
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