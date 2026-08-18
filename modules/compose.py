"""
183개 컴포넌트를 로드해서 11,172자 전체 완성형 한글을 좌표 기반으로 자동 조합.

핵심 설계: "위치(zone)"와 "크기(scale)"를 분리한다
---------------------------------------------------
이전 버전은 각 컴포넌트를 "자기 zone에 맞춰 최대한 크게(letterbox)" 개별적으로
맞췄다. 문제는 손글씨가 자모마다 미세하게 비율이 다르기 때문에, "가로/세로 중
어느 쪽이 꽉 차는지"가 자모마다 문맥마다 흔들려서 최종 크기가 들쭉날쭉해지는
것이었다 (크기가 흔들리면, 벡터를 확대/축소할 때 획 굵기도 같이 흔들리므로
굵기도 같이 들쭉날쭉해진다). 예를 들어 "차"의 ㅊ과 "초"의 ㅊ처럼, 같은 자모라도
문맥(zone)이 다르면 크기가 안정적이지 않았다.

지금은 같은 문맥(예: "받침없음 + 세로모음" 초성 19개)에 속한 컴포넌트들이 실제
손글씨로 그려진 높이의 "중앙값"을 계산해서, 그 문맥에 속한 모든 컴포넌트가
"공통 배율 하나"를 공유하도록 바꿨다. zone의 크기는 "이 문맥은 대략 이 정도
크기여야 한다"는 목표치를 정할 뿐, 개별 컴포넌트의 배율을 direct로 흔들지
않는다. 그 결과:

- 같은 문맥 안에서는 항상 같은 배율을 쓰므로 (예: "가"의 ㄱ과 "차"의 ㅊ) 크기가
  안정적이다.
- 다른 문맥(V/H/C, 받침 유무)끼리는 의도한 대로 다른 크기를 가질 수 있다
  (zone 크기가 다르므로 - 이건 버그가 아니라 의도된 디자인이다).
- 손글�씨 굵기도 크기가 안정되면서 자연히 더 일관되게 나온다.
"""

import json
from pathlib import Path

from fontTools.pens.ttGlyphPen import TTGlyphPen

from modules.glyph import image_to_contours, draw_contour
from modules.hangul import (
    CHO_LIST,
    JUNG_LIST,
    JONG_LIST,
    VOWEL_GROUP,
    GROUP_MACRO,
    ZONE_LAYOUTS,
    KIND_SCALE,
    STANDALONE_HEIGHT_OVERRIDE,
    component_id,
    decompose_code,
    get_component_scale,
    get_component_offset,
    build_standalone_jamo_list,
)

HANGUL_START = 0xAC00
HANGUL_END = 0xD7A3  # inclusive

# 목표 높이 = zone 높이의 이 비율. 너무 꽉 채우면(1.0) 여백이 없어 보이고,
# 너무 작으면(<0.8) 헐거워 보인다.
FILL_RATIO = 0.90

# 특정 컴포넌트가 유독 커서(예: ㅁ처럼 넓은 자모) zone을 심하게 벗어나면
# 이 비율까지만 추가로 줄이는 안전장치. 공통 배율 자체는 건드리지 않고,
# 정말 넘칠 때만 그 컴포넌트 하나에 한해 최소한으로 개입한다.
MAX_OVERFLOW_RATIO = 1.0


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


def _median_height(cache, comp_ids):
    """주어진 컴포넌트 id 목록 중 실제로 존재하는 것들의 잉크 높이 중앙값."""
    heights = []
    for cid in comp_ids:
        entry = cache.get(cid)
        if entry is None:
            continue
        gx0, gy0, gx1, gy1 = entry["bbox"]
        h = gy1 - gy0
        if h > 0:
            heights.append(h)

    if not heights:
        return None

    heights.sort()
    return heights[len(heights) // 2]


def build_calibration(cache):
    """
    각 문맥(초성: 받침유무x상위그룹 6가지 / 중성: 받침유무 2가지 / 종성: 1가지)
    별로, 그 문맥에 속한 컴포넌트들의 실제 손글씨 높이 중앙값을 계산한다.

    반환값은 {(kind, batchim, macro_or_None): median_height} 형태의 딕셔너리.
    이 값이 나중에 _fit_contours()에서 "이 문맥은 대략 이만큼 크다"는 공통
    기준으로 쓰인다.
    """
    calibration = {}

    for batchim in (False, True):
        for macro in ("V", "H", "C"):
            ids = [component_id("cho", cho, batchim, macro) for cho in CHO_LIST]
            calibration[("cho", batchim, macro)] = _median_height(cache, ids)

    for batchim in (False, True):
        ids = [component_id("jung", jung, batchim) for jung in JUNG_LIST]
        calibration[("jung", batchim, None)] = _median_height(cache, ids)

    ids = [component_id("jong", jong) for jong in JONG_LIST]
    calibration[("jong", True, None)] = _median_height(cache, ids)

    return calibration


def _fit_contours(entry, zone, kind, jamo, calibration_height):
    """
    entry: {"contours": [...], "bbox": (gx0,gy0,gx1,gy1)} - 컴포넌트 원본 윤곽선.
    zone: 이 컴포넌트가 들어갈 사각형 (x0,y0,x1,y1).
    calibration_height: 같은 문맥에 속한 컴포넌트들이 공유하는 기준 높이
        (build_calibration()의 결과). 이 값이 있으면 모든 컴포넌트가 같은
        배율을 쓰게 되어 크기가 안정적이다. 없으면(예외 상황) 이 컴포넌트
        자신의 높이로 대체한다.

    비율을 유지한 채(찌그러지지 않게) zone 안에 중앙 정렬로 배치한다.
    KIND_SCALE / 자모별 보정값(COMPONENT_SCALE, COMPONENT_OFFSET)을 곱/더한다.
    """
    contours = entry["contours"]
    gx0, gy0, gx1, gy1 = entry["bbox"]
    glyph_w = gx1 - gx0
    glyph_h = gy1 - gy0

    if glyph_w <= 0 or glyph_h <= 0:
        return []

    zx0, zy0, zx1, zy1 = zone
    zone_w = zx1 - zx0
    zone_h = zy1 - zy0

    ref_height = calibration_height if calibration_height else glyph_h
    target_height = zone_h * FILL_RATIO

    # 문맥 공통 배율: 이 컴포넌트만의 bbox가 아니라, 같은 문맥의 대표 높이를
    # 기준으로 계산하므로 같은 문맥 안에서는 항상 같은 배율이 나온다.
    base_scale = target_height / ref_height
    scale = base_scale * KIND_SCALE.get(kind, 1.0) * get_component_scale(kind, jamo)

    draw_w = glyph_w * scale
    draw_h = glyph_h * scale

    # 안전장치: 이 특정 컴포넌트가 유독 커서 zone을 심하게 벗어나면 그
    # 컴포넌트에 한해서만 최소한으로 더 줄인다 (공통 배율 자체는 안 건드림).
    if draw_w > zone_w * MAX_OVERFLOW_RATIO:
        shrink = (zone_w * MAX_OVERFLOW_RATIO) / draw_w
        scale *= shrink
        draw_w *= shrink
        draw_h *= shrink
    if draw_h > zone_h * MAX_OVERFLOW_RATIO:
        shrink = (zone_h * MAX_OVERFLOW_RATIO) / draw_h
        scale *= shrink
        draw_w *= shrink
        draw_h *= shrink

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

    cho_cal = calibration.get(("cho", has_batchim, macro_group))
    jung_cal = calibration.get(("jung", has_batchim, None))

    all_contours = []
    all_contours += _fit_contours(cho_entry, layout["cho"], "cho", cho, cho_cal)
    all_contours += _fit_contours(jung_entry, layout["jung"], "jung", jung, jung_cal)

    if has_batchim:
        jong_entry = cache.get(component_id("jong", jong))
        if jong_entry is None:
            return None
        jong_cal = calibration.get(("jong", True, None))
        all_contours += _fit_contours(jong_entry, layout["jong"], "jong", jong, jong_cal)

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
            cal = calibration.get(("cho", False, "V"))
        elif comp_id.startswith("jung_"):
            kind = "jung"
            fine_group = VOWEL_GROUP.get(jamo_char, "V1")
            real_zone = ZONE_LAYOUTS[(False, fine_group)]["jung"]
            cal = calibration.get(("jung", False, None))
        else:
            kind = "jong"
            real_zone = ZONE_LAYOUTS[(True, "V1")]["jong"]
            cal = calibration.get(("jong", True, None))

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

        contours = _fit_contours(entry, virtual_zone, kind, jamo_char, cal)

        pen = TTGlyphPen(None)
        for pts, _is_hole in contours:
            draw_contour(pen, pts)

        gname = f"jamo{codepoint:04X}"
        glyphs[gname] = pen.glyph()
        cmap[codepoint] = gname
        built += 1

    return glyphs, cmap, built
