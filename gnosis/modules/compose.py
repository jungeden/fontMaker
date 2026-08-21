"""
183개 컴포넌트를 로드해서 11,172자 전체 완성형 한글을 좌표 기반으로 자동 조합.

핵심 설계: 공통 원고지 칸(frame)과 조합 zone을 분리한다
--------------------------------------------------------
분할 단계는 잉크만 잘라내지 않고 모든 컴포넌트를 같은 칸 캔버스로 보존한다.
조합은 이 공통 frame을 zone에 한 번 배치하므로, 손글씨의 실제 크기·여백·칸 안
위치가 유지된다. 문맥별 중앙값 보정과 넘침 뒤 재축소는 쓰지 않는다. 필요한
수동 조정은 component id별 크기와 위치가 독립된 값으로 적용된다.
"""

import json
from pathlib import Path

from fontTools.pens.ttGlyphPen import TTGlyphPen

from config import HANGUL_FILL_RATIO, UNITS_PER_EM
from modules.glyph import image_to_contours, draw_contour
from modules.hangul import (
    CHO_LIST,
    JUNG_LIST,
    JONG_LIST,
    VOWEL_GROUP,
    GROUP_MACRO,
    ZONE_LAYOUTS,
    STANDALONE_HEIGHT_OVERRIDE,
    component_id,
    decompose_code,
    get_component_scale,
    get_component_offset,
    get_layout_component_scale,
    get_layout_component_offset,
    STANDALONE_JAMO_SCALE,
    STANDALONE_JAMO_OFFSET,
    build_standalone_jamo_list,
)

HANGUL_START = 0xAC00
HANGUL_END = 0xD7A3  # inclusive

# 모든 컴포넌트의 공통 frame은 zone 내부에서 이 비율만큼 채워진다.
FILL_RATIO = HANGUL_FILL_RATIO


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
            cache[comp["id"]] = {
                "contours": contours,
                "bbox": bbox,
                # PNG 전체가 같은 원고지 칸이다. bbox는 빈 칸 검증용일 뿐,
                # 조합 배율이나 기준점 계산에는 쓰지 않는다.
                "frame": (0, 0, UNITS_PER_EM, UNITS_PER_EM),
            }
        else:
            missing.append(comp["id"])

    return cache, missing


def build_calibration(cache):
    """
    이전 API 호환용 빈 설정값.

    문맥별 중앙값 크기 보정은 제거됐다. 조합 크기는 공통 frame과
    ZONE_LAYOUTS로 계산한다.
    """
    return {}


def _fit_contours(entry, zone, component, calibration_height=None,
                  scale_adjust=1.0, offset_adjust=(0, 0),
                  layout_scale=1.0, layout_offset=(0, 0)):
    """
    entry: {"contours": [...], "frame": (x0,y0,x1,y1)} - 컴포넌트 원본 윤곽선.
    zone: 이 컴포넌트가 들어갈 사각형 (x0,y0,x1,y1).
    calibration_height: 이전 API 호환용 인자. 사용하지 않는다.

    비율을 유지한 채(찌그러지지 않게) zone 안에 중앙 정렬로 배치한다.
    모든 컴포넌트가 공유하는 원고지 칸(frame)을 기준으로 한 번만 스케일한다.
    배치 그룹 조정과 개별 수동 조정은 서로 독립적으로 적용된다.
    """
    contours = entry["contours"]
    fx0, fy0, fx1, fy1 = entry["frame"]
    frame_w = fx1 - fx0
    frame_h = fy1 - fy0

    if frame_w <= 0 or frame_h <= 0:
        return []

    zx0, zy0, zx1, zy1 = zone
    zone_w = zx1 - zx0
    zone_h = zy1 - zy0

    base_scale = min(zone_w / frame_w, zone_h / frame_h) * FILL_RATIO
    scale = (base_scale * layout_scale * get_component_scale(component)
             * scale_adjust)

    # 원고지 칸 전체가 zone 중앙에 오도록 배치한다. 잉크만 중앙에 맞추지
    # 않으므로, 사용자가 쓴 실제 크기와 칸 안 여백/위치가 유지된다.
    frame_center_x = (fx0 + fx1) / 2
    frame_center_y = (fy0 + fy1) / 2
    zone_center_x = (zx0 + zx1) / 2
    zone_center_y = (zy0 + zy1) / 2
    dx, dy = get_component_offset(component)
    layout_dx, layout_dy = layout_offset
    extra_dx, extra_dy = offset_adjust

    final_x = zone_center_x - frame_center_x * scale + layout_dx + dx + extra_dx
    final_y = zone_center_y - frame_center_y * scale + layout_dy + dy + extra_dy

    out = []
    for pts, is_hole in contours:
        new_pts = [(x * scale + final_x, y * scale + final_y) for x, y in pts]
        out.append((new_pts, is_hole))
    return out


def compose_syllable_glyph(cache, calibration, cho, jung, jong=None):
    """초/중/종성 자모 하나로 완성형 음절 하나의 TTGlyph를 조합한다."""
    fine_group = VOWEL_GROUP[jung]        # 배치 좌표(zone)용 세부 그룹 (9종류)
    macro_group = GROUP_MACRO[fine_group]  # 손글씨(컴포넌트)용 상위 그룹 (3종류)
    has_batchim = jong is not None
    layout = ZONE_LAYOUTS[(has_batchim, fine_group)]

    cho_entry = cache.get(component_id("cho", cho, has_batchim, macro_group))
    jung_entry = cache.get(component_id("jung", jung, has_batchim))

    if cho_entry is None or jung_entry is None:
        return None  # 아직 손글씨로 채워지지 않은 컴포넌트

    cho_id = component_id("cho", cho, has_batchim, macro_group)
    jung_id = component_id("jung", jung, has_batchim)

    all_contours = []
    all_contours += _fit_contours(
        cho_entry, layout["cho"], cho_id,
        layout_scale=get_layout_component_scale("cho", has_batchim, fine_group),
        layout_offset=get_layout_component_offset("cho", has_batchim, fine_group),
    )
    all_contours += _fit_contours(
        jung_entry, layout["jung"], jung_id,
        layout_scale=get_layout_component_scale("jung", has_batchim, fine_group),
        layout_offset=get_layout_component_offset("jung", has_batchim, fine_group),
    )

    if has_batchim:
        jong_entry = cache.get(component_id("jong", jong))
        if jong_entry is None:
            return None
        jong_id = component_id("jong", jong)
        all_contours += _fit_contours(
            jong_entry, layout["jong"], jong_id,
            layout_scale=get_layout_component_scale("jong", True, None),
            layout_offset=get_layout_component_offset("jong", True, None),
        )

    pen = TTGlyphPen(None)
    for pts, _is_hole in all_contours:
        draw_contour(pen, pts)

    return pen.glyph()


def compose_from_cache(cache, calibration=None):
    """
    이미 로드된 컴포넌트 캐시(load_component_contours의 결과)로부터
    가(0xAC00) ~ 힣(0xD7A3) 완성형 한글 11,172자를 전부 조합한다.
    아직 손글씨가 채워지지 않은 컴포넌트가 필요한 음절은 건너뛴다
    (부분적으로만 손글씨를 채워도 그 범위 내에서 폰트를 만들어볼 수 있다).

    반환값: (glyphs: {glyph_name: TTGlyph}, cmap: {codepoint: glyph_name},
             built_count, skipped_count)
    """
    if calibration is None:
        calibration = build_calibration(cache)

    glyphs = {}
    cmap = {}
    built = 0
    skipped = 0

    for code in range(HANGUL_START, HANGUL_END + 1):
        cho, jung, jong = decompose_code(code)

        glyph = compose_syllable_glyph(cache, calibration, cho, jung, jong)
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


def build_standalone_glyphs(cache, calibration=None):
    """
    조합되지 않은 단독 자모("ㄱ", "ㅏ" 등)를 그 자체로 입력했을 때도 폰트가
    적용되도록, 51개 자모 각각에 대해 대표 컴포넌트로 글리프를 만든다.

    중요: 크기는 "1000x1000 전체를 채우는 큰 글자"가 아니라, 그 자모가
    실제 음절 조합에 쓰일 때와 똑같은 크기(같은 zone 높이, 같은 calibration)
    를 그대로 재사용한다. 다만 위치는 조합 시의 한쪽으로 치우친 자리가
    아니라, 1000x1000 전체 박스 안에서 좌우/상하 정중앙에 오도록 배치한다.
    (예: 초성 ㄱ 단독 표시 = "가"에서 ㄱ이 차지하는 만큼의 크기, 화면
    중앙에 위치)

    반환값: (glyphs: {glyph_name: TTGlyph}, cmap: {codepoint: glyph_name}, built_count)
    """
    if calibration is None:
        calibration = build_calibration(cache)

    glyphs = {}
    cmap = {}
    built = 0

    for codepoint, comp_id in build_standalone_jamo_list():
        entry = cache.get(comp_id)
        if entry is None:
            continue

        jamo_char = chr(codepoint)

        if comp_id.startswith("cho_"):
            kind = "cho"
            real_zone = ZONE_LAYOUTS[(False, "V1")]["cho"]
        elif comp_id.startswith("jung_"):
            kind = "jung"
            fine_group = VOWEL_GROUP.get(jamo_char, "V1")
            real_zone = ZONE_LAYOUTS[(False, fine_group)]["jung"]
        else:
            kind = "jong"
            real_zone = ZONE_LAYOUTS[(True, "V1")]["jong"]

        _, rz_y0, _, rz_y1 = real_zone
        real_h = rz_y1 - rz_y0

        # STANDALONE_HEIGHT_OVERRIDE에 값이 지정되어 있으면 그 값을 쓰고,
        # 없으면(None) 실제 조합 시 이 자모가 차지하는 높이를 그대로 쓴다.
        override_h = STANDALONE_HEIGHT_OVERRIDE.get(kind)
        target_h = override_h if override_h else real_h

        # 1000 폭 전체에서 좌우 중앙 + 상하 중앙에 오도록 가상 zone을 만든다
        # (조합 시의 한쪽으로 치우친 위치는 사용하지 않음).
        vy0 = (1000 - target_h) / 2
        virtual_zone = (0, vy0, 1000, vy0 + target_h)

        contours = _fit_contours(
            entry, virtual_zone, comp_id,
            scale_adjust=STANDALONE_JAMO_SCALE.get(jamo_char, 1.0),
            offset_adjust=STANDALONE_JAMO_OFFSET.get(jamo_char, (0, 0)),
        )

        pen = TTGlyphPen(None)
        for pts, _is_hole in contours:
            draw_contour(pen, pts)

        gname = f"jamo{codepoint:04X}"
        glyphs[gname] = pen.glyph()
        cmap[codepoint] = gname
        built += 1

    return glyphs, cmap, built
