"""
183개 컴포넌트를 로드해서 11,172자 전체 완성형 한글을 좌표 기반으로 자동 조합.

핵심 수정 사항 (이전 버전의 버그):
이전 버전은 컴포넌트를 "항상 1000x1000 전체를 꽉 채운 그림"이라고 가정하고,
x축/y축을 각각 zone의 가로/세로 비율에 맞춰 따로 늘렸다(sx, sy를 각각 계산).
이러면 실제 손글씨가 원래 비율과 다르게 가로나 세로로 찌그러진다.

지금은 각 컴포넌트의 실제 잉크 바운딩 박스(bounding box)를 구해서, 그
비율을 유지한 채(letterbox 방식) zone 안에 맞추고 중앙 정렬한다. 그래서
글자가 절대 찌그러지지 않는다. 자모마다 자연스러운 크기가 달라서
(예: ㄱ은 작고 ㅁ은 큼) 여전히 상대적으로 작거나 커 보일 수 있는데, 이건
modules/hangul.py의 KIND_SCALE / COMPONENT_SCALE / COMPONENT_OFFSET
표로 미세 조정할 수 있다.
"""

import json
from pathlib import Path

from fontTools.pens.ttGlyphPen import TTGlyphPen

from modules.glyph import image_to_contours, draw_contour
from modules.hangul import (
    VOWEL_GROUP,
    ZONE_LAYOUTS,
    KIND_SCALE,
    component_id,
    decompose_code,
    get_component_scale,
    get_component_offset,
    build_standalone_jamo_list,
)

HANGUL_START = 0xAC00
HANGUL_END = 0xD7A3  # inclusive

# zone 좌표(modules/hangul.py의 ZONE_LAYOUTS) 자체에 이미 적당한 여백이
# 포함되어 있으므로, 여기서는 아주 작은 안전 여백만 추가로 둔다.
ZONE_INNER_PADDING = 0.0

# 단독 자모("ㄱ", "ㅏ" 등 조합되지 않은 낱자)를 표시할 사각형 영역
# (1000x1000 기준). 합성 음절과 비슷한 시각적 무게감을 갖도록 여백을 둔다.
STANDALONE_BOX = (80, 20, 920, 920)


def _contours_bbox(contours):
    """윤곽선 전체의 실제 잉크 바운딩 박스 (x0, y0, x1, y1). 빈 경우 None."""
    xs = [x for pts, _ in contours for x, _ in pts]
    ys = [y for pts, _ in contours for _, y in pts]
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def load_component_contours(glyph_dir="data/glyphs", manifest_path="data/manifest.json"):
    """
    manifest.json(템플릿 생성 시 저장된 183개 컴포넌트 순서)과
    data/glyphs 안의 인덱스별 PNG를 읽어서, id -> {contours, bbox} 캐시를 만든다.

    bbox를 여기서 컴포넌트당 한 번만 계산해두는 이유: 11,172자를 조합할 때마다
    같은 컴포넌트의 bbox를 매번 다시 계산하면 183개 bbox 계산이 11,172번
    반복되어 느려진다. 여기서 미리 계산해두면 183번만 계산하면 된다.
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
        bbox = _contours_bbox(contours) if contours else None

        if contours and bbox:
            cache[comp["id"]] = {"contours": contours, "bbox": bbox}
        else:
            missing.append(comp["id"])

    return cache, missing


def _fit_contours(entry, zone, kind, jamo):
    """
    entry: {"contours": [...], "bbox": (gx0,gy0,gx1,gy1)} - 컴포넌트 원본 윤곽선.
    zone: 이 컴포넌트가 들어갈 사각형 (x0,y0,x1,y1).

    원본 비율을 유지한 채(letterbox) zone 안에 맞추고 중앙 정렬한다.
    KIND_SCALE / 자모별 보정값(COMPONENT_SCALE, COMPONENT_OFFSET)을 곱/더한다.
    """
    contours = entry["contours"]
    gx0, gy0, gx1, gy1 = entry["bbox"]
    glyph_w = gx1 - gx0
    glyph_h = gy1 - gy0

    if glyph_w <= 0 or glyph_h <= 0:
        return []

    zx0, zy0, zx1, zy1 = zone
    pad_x = (zx1 - zx0) * ZONE_INNER_PADDING
    pad_y = (zy1 - zy0) * ZONE_INNER_PADDING
    zx0, zy0, zx1, zy1 = zx0 + pad_x, zy0 + pad_y, zx1 - pad_x, zy1 - pad_y
    zone_w = zx1 - zx0
    zone_h = zy1 - zy0

    # 원본 비율을 유지하며 zone 안에 가득 차도록 배율 계산 (letterbox 방식,
    # 가로/세로 중 더 제약이 되는 쪽에 맞춤 -> 절대 찌그러지지 않음)
    base_scale = min(zone_w / glyph_w, zone_h / glyph_h)
    scale = base_scale * KIND_SCALE.get(kind, 1.0) * get_component_scale(kind, jamo)

    draw_w = glyph_w * scale
    draw_h = glyph_h * scale

    # zone 중앙 정렬
    center_x = zx0 + (zone_w - draw_w) / 2
    center_y = zy0 + (zone_h - draw_h) / 2

    dx, dy = get_component_offset(kind, jamo)

    final_x = center_x - gx0 * scale + dx
    final_y = center_y - gy0 * scale + dy

    out = []
    for pts, is_hole in contours:
        new_pts = [(x * scale + final_x, y * scale + final_y) for x, y in pts]
        out.append((new_pts, is_hole))
    return out


def compose_syllable_glyph(cache, cho, jung, jong=None):
    """초/중/종성 자모 하나로 완성형 음절 하나의 TTGlyph를 조합한다."""
    group = VOWEL_GROUP[jung]
    has_batchim = jong is not None
    layout = ZONE_LAYOUTS[(has_batchim, group)]

    cho_entry = cache.get(component_id("cho", cho, has_batchim, group))
    jung_entry = cache.get(component_id("jung", jung, has_batchim))

    if cho_entry is None or jung_entry is None:
        return None  # 아직 손글씨로 채워지지 않은 컴포넌트

    all_contours = []
    all_contours += _fit_contours(cho_entry, layout["cho"], "cho", cho)
    all_contours += _fit_contours(jung_entry, layout["jung"], "jung", jung)

    if has_batchim:
        jong_entry = cache.get(component_id("jong", jong))
        if jong_entry is None:
            return None
        all_contours += _fit_contours(jong_entry, layout["jong"], "jong", jong)

    pen = TTGlyphPen(None)
    for pts, _is_hole in all_contours:
        draw_contour(pen, pts)

    return pen.glyph()


def compose_from_cache(cache):
    """
    이미 로드된 컴포넌트 캐시(load_component_contours의 결과)로부터
    가(0xAC00) ~ 힣(0xD7A3) 완성형 한글 11,172자를 전부 조합한다.
    아직 손글씨가 채워지지 않은 컴포넌트가 필요한 음절은 건너뛴다
    (부분적으로만 손글씨를 채워도 그 범위 내에서 폰트를 만들어볼 수 있다).

    반환값: (glyphs: {glyph_name: TTGlyph}, cmap: {codepoint: glyph_name},
             built_count, skipped_count)
    """
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


def compose_all(glyph_dir="data/glyphs", manifest_path="data/manifest.json"):
    """
    load_component_contours() + compose_from_cache()를 한 번에 실행하는
    편의 함수 (단독으로 한글 조합 결과만 필요할 때 사용).
    """
    cache, missing = load_component_contours(glyph_dir, manifest_path)

    if missing:
        print(f"참고: {len(missing)}개 컴포넌트가 아직 없어서 관련 음절은 제외됩니다.")

    return compose_from_cache(cache)


def build_standalone_glyphs(cache):
    """
    조합되지 않은 단독 자모("ㄱ", "ㅏ" 등)를 그 자체로 입력했을 때도 폰트가
    적용되도록, 51개 자모 각각에 대해 대표 컴포넌트를 STANDALONE_BOX
    안에 비율 유지 + 중앙 정렬로 배치한 글리프를 만든다.

    반환값: (glyphs: {glyph_name: TTGlyph}, cmap: {codepoint: glyph_name}, built_count)
    """
    glyphs = {}
    cmap = {}
    built = 0

    for codepoint, comp_id in build_standalone_jamo_list():
        entry = cache.get(comp_id)
        if entry is None:
            continue

        contours = _fit_contours(entry, STANDALONE_BOX, "standalone", comp_id)

        pen = TTGlyphPen(None)
        for pts, _is_hole in contours:
            draw_contour(pen, pts)

        gname = f"jamo{codepoint:04X}"
        glyphs[gname] = pen.glyph()
        cmap[codepoint] = gname
        built += 1

    return glyphs, cmap, built
