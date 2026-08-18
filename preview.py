"""
빠른 미리보기 도구.

ZONE_LAYOUTS, KIND_SCALE, COMPONENT_SCALE, COMPONENT_OFFSET,
STANDALONE_HEIGHT_OVERRIDE (modules/hangul.py), TARGET_CAP_HEIGHT
(modules/latin.py), TARGET_STROKE_PX (config.py) 등을 조정한 뒤, 전체
11,172자를 다시 빌드하지 않고도 대표 글자 몇 개만 빠르게 만들어서 바로
확인할 수 있다.

내부적으로 실제 최종 빌드(modules/fontbuild.py)와 완전히 같은 함수들
(compose_syllable_glyph, build_latin_glyphs, build_kern_feature,
assemble_fontbuilder)을 그대로 재사용한다 - 그래서 여기서 보이는 결과와
`python app.py build`의 최종 완성본은 항상 일치한다. 다만 한글은 11,172자
전체가 아니라 지정한 샘플 글자만 넣으므로 훨씬 빠르다 (보통 1~5초).

사용법:
    python preview.py hangul     # 한글 대표 음절 미리보기 (9개 모음 세부그룹 +
                                  #   받침 유무 + 여러 자음 비교, 한 장의 이미지로)
    python preview.py latin      # 영문/숫자/특수문자 미리보기
    python preview.py kerning    # 커닝 적용 전/후 비교
    python preview.py stroke     # 획 굵기 보정 전/후 비교 (실제 컴포넌트 PNG 기준)
    python preview.py hinting    # 힌팅 적용 전/후 비교 (작은 크기로 렌더링)
    python preview.py all        # 위 다섯 가지를 전부 실행

결과 이미지는 output/preview_*.png 로 저장된다. data/glyphs 에 이미 분할된
컴포넌트 PNG가 있어야 한다 (즉, `python app.py build`를 최소 한 번은
실행해서 스캔 -> 분할 단계를 거친 뒤 사용하는 도구다. 이후로는 손글씨를
다시 스캔하지 않는 한 이 도구만으로 빠르게 튜닝을 반복할 수 있다).
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from modules.compose import (
    load_component_contours,
    build_calibration,
    compose_syllable_glyph,
    build_standalone_glyphs,
)
from modules.hangul import decompose_code
from modules.latin import build_latin_glyphs
from modules.kerning import build_kern_feature
from modules.fontbuild import assemble_fontbuilder, _apply_hinting
from modules.segment import normalize_stroke_width

OUTPUT_DIR = "output"

# ────────────────────────────────────────────────────────────
# 미리보기에 쓸 대표 한글 샘플. 자유롭게 바꿔도 된다 - 여기 있는 글자만
# 조합해서 작은 미리보기 폰트를 만들기 때문에, 확인하고 싶은 글자를
# 직접 추가/삭제하면 된다.
#
# 아래 구성:
#   1행: 받침없음, 자음 ㄱ 고정 - 모음 9개 세부그룹(V1~C3)을 한 눈에 비교
#   2행: 받침있음, 자음 ㄱ 고정 - 위와 동일하되 받침 붙었을 때
#   3행: 받침없음, 모음 ㅏ 고정 - 자음별 크기가 서로 비슷한지 비교
#   4행: 겹받침/복잡한 받침 예시
# ────────────────────────────────────────────────────────────
def _make_hangul_preview_rows():
    """
    손으로 음절을 입력하면 오타가 나기 쉬우므로, modules/hangul.py의 실제
    데이터(ALL_SUBGROUPS, VOWEL_GROUP, JONG_LIST)로부터 예시 음절을 계산해서
    만든다. 자유롭게 이 함수를 수정해서 원하는 예시를 추가/삭제해도 된다.
    """
    from modules.hangul import compose_char, ALL_SUBGROUPS, VOWEL_GROUP, JONG_LIST, CHO_LIST

    rep_vowel = {}
    for v, g in VOWEL_GROUP.items():
        rep_vowel.setdefault(g, v)  # 세부그룹(V1~C3)마다 대표 모음 하나

    row1 = "".join(compose_char("ㄱ", rep_vowel[g]) for g in ALL_SUBGROUPS)
    row2 = "".join(compose_char("ㄱ", rep_vowel[g], "ㄱ") for g in ALL_SUBGROUPS)
    row3 = "".join(
        compose_char(c, "ㅏ")
        for c in ["ㄱ", "ㄲ", "ㄴ", "ㄷ", "ㄸ", "ㄹ", "ㅁ", "ㅂ", "ㅃ",
                  "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅉ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"]
    )
    row4 = "".join(
        compose_char("ㄱ", "ㅏ", j) for j in JONG_LIST if j not in CHO_LIST
    )  # 초성에는 없는(=겹받침 전용) 자모만

    return [
        ("No batchim, cho=ㄱ, 9 vowel groups", row1),
        ("Batchim, cho=ㄱ, 9 vowel groups", row2),
        ("Consonant size compare (vowel=ㅏ)", row3),
        ("Complex batchim (cho=ㄱ, vowel=ㅏ)", row4),
    ]


HANGUL_PREVIEW_ROWS = _make_hangul_preview_rows()

DEFAULT_LATIN_SAMPLE = "ABCDEFGHIJKLMabcdefghijklm0123456789!?.,\"'—…★☆♥→"


def _collect_sample_chars(rows):
    chars = set()
    for _label, text in rows:
        chars.update(text)
    return chars


def build_preview_font(
    hangul_sample_rows=HANGUL_PREVIEW_ROWS,
    latin_sample=DEFAULT_LATIN_SAMPLE,
    glyph_dir="data/glyphs",
    manifest_path="data/manifest.json",
    output_path=f"{OUTPUT_DIR}/preview.ttf",
    apply_kerning=True,
    apply_hinting=False,
):
    """
    지정한 샘플 문자만 담은 작은 미리보기 폰트를 만든다. 전체 11,172자를
    조합하는 compose_from_cache() 대신, 필요한 글자만 compose_syllable_glyph()
    로 하나씩 만들기 때문에 훨씬 빠르다.
    """
    manifest = __import__("json").loads(Path(manifest_path).read_text(encoding="utf-8"))

    cache, missing = load_component_contours(glyph_dir, manifest_path)
    calibration = build_calibration(cache)

    hangul_chars = _collect_sample_chars(hangul_sample_rows) if hangul_sample_rows else set()

    hangul_glyphs = {}
    hangul_cmap = {}
    for ch in hangul_chars:
        code = ord(ch)
        if not (0xAC00 <= code <= 0xD7A3):
            continue  # 완성형 한글이 아니면(자모 낱자 등) 스킵
        cho, jung, jong = decompose_code(code)
        glyph = compose_syllable_glyph(cache, calibration, cho, jung, jong)
        if glyph is None:
            continue
        gname = f"uni{code:04X}"
        hangul_glyphs[gname] = glyph
        hangul_cmap[code] = gname

    standalone_glyphs, standalone_cmap, _n = build_standalone_glyphs(cache, calibration)

    latin_glyphs_all, latin_cmap_all, latin_metrics_all, _n2 = build_latin_glyphs(glyph_dir, manifest)

    # latin_sample에 있는 문자만 추려서 미리보기 폰트에 넣는다 (전체 129자를
    # 다 넣어도 빠르긴 하지만, 요청한 샘플만 넣는 편이 의도가 명확하다).
    wanted_codes = {ord(c) for c in latin_sample} | {0x20}
    latin_glyphs = {}
    latin_cmap = {}
    latin_metrics = {}
    for code, gname in latin_cmap_all.items():
        if code in wanted_codes:
            latin_glyphs[gname] = latin_glyphs_all[gname]
            latin_cmap[code] = gname
            latin_metrics[gname] = latin_metrics_all[gname]

    fb = assemble_fontbuilder(
        hangul_glyphs, hangul_cmap,
        standalone_glyphs, standalone_cmap,
        latin_glyphs, latin_cmap, latin_metrics,
        family_name="Preview", style_name="Regular",
    )

    if apply_kerning:
        build_kern_feature(fb.font, latin_cmap)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if apply_hinting:
        unhinted = str(output_path) + ".unhinted.ttf"
        fb.save(unhinted)
        _apply_hinting(unhinted, output_path)
    else:
        fb.save(output_path)

    return output_path


def _render_lines(ttf_path, lines, font_size=90, pad=20, line_gap=14, label_width=340):
    """
    (라벨, 텍스트) 쌍의 목록을 세로로 쌓아서 하나의 이미지로 그린다.
    라벨은 작은 글씨로 왼쪽에, 텍스트는 미리보기 폰트로 렌더링한다.
    """
    label_font = ImageFont.load_default()
    text_font = ImageFont.truetype(ttf_path, font_size)

    dummy = Image.new("L", (10, 10))
    d = ImageDraw.Draw(dummy)

    row_heights = []
    row_widths = []
    for _label, text in lines:
        bbox = d.textbbox((0, 0), text, font=text_font)
        row_widths.append(bbox[2] - bbox[0])
        row_heights.append(bbox[3] - bbox[1])

    W = label_width + max(row_widths, default=0) + pad * 2
    H = sum(max(h, font_size) + line_gap for h in row_heights) + pad * 2

    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    y = pad
    for (label, text), h in zip(lines, row_heights):
        row_h = max(h, font_size)
        draw.text((pad, y + row_h // 2 - 6), label, font=label_font, fill=(120, 120, 120))
        draw.text((label_width, y), text, font=text_font, fill=(0, 0, 0))
        y += row_h + line_gap

    return img


def preview_hangul():
    print("한글 미리보기 폰트 생성 중...")
    ttf = build_preview_font(hangul_sample_rows=HANGUL_PREVIEW_ROWS, latin_sample="", apply_hinting=False)
    img = _render_lines(ttf, HANGUL_PREVIEW_ROWS, font_size=90)
    out = f"{OUTPUT_DIR}/preview_hangul.png"
    img.save(out)
    print(f"저장됨: {out}")


def preview_latin():
    print("영문/숫자/특수문자 미리보기 폰트 생성 중...")
    lines = [
        ("Uppercase", "ABCDEFGHIJKLM"),
        ("Lowercase", "abcdefghijklmnop"),
        ("Digits", "0123456789"),
        ("Punctuation", "!?.,:;\"'—…"),
        ("Symbols", "★☆♥♡○●□■◇◆→←"),
        ("Mixed", "Hello 가나다 123 Ab"),
    ]
    sample = "".join(t for _l, t in lines)
    ttf = build_preview_font(hangul_sample_rows=[("혼합", "가나다")], latin_sample=sample, apply_hinting=False)
    img = _render_lines(ttf, lines, font_size=90)
    out = f"{OUTPUT_DIR}/preview_latin.png"
    img.save(out)
    print(f"저장됨: {out}")


def preview_kerning():
    print("커닝 적용 전/후 비교 폰트 생성 중...")
    sample = "AVAWATToVoWoAWAY.,\"'FAILWORKTYPE"
    ttf_with = build_preview_font(hangul_sample_rows=[], latin_sample=sample,
                                    apply_kerning=True, apply_hinting=False,
                                    output_path=f"{OUTPUT_DIR}/preview_kern_on.ttf")
    ttf_without = build_preview_font(hangul_sample_rows=[], latin_sample=sample,
                                       apply_kerning=False, apply_hinting=False,
                                       output_path=f"{OUTPUT_DIR}/preview_kern_off.ttf")

    lines_on = [("Kerning ON", sample)]
    lines_off = [("Kerning OFF", sample)]
    img_on = _render_lines(ttf_with, lines_on, font_size=80)
    img_off = _render_lines(ttf_without, lines_off, font_size=80)

    W = max(img_on.width, img_off.width)
    H = img_on.height + img_off.height
    combined = Image.new("RGB", (W, H), "white")
    combined.paste(img_off, (0, 0))
    combined.paste(img_on, (0, img_off.height))

    out = f"{OUTPUT_DIR}/preview_kerning.png"
    combined.save(out)
    print(f"저장됨: {out} (위: 커닝 없음, 아래: 커닝 적용)")


def preview_stroke(sample_ids=None, glyph_dir="data/glyphs", manifest_path="data/manifest.json"):
    """
    실제 분할된 컴포넌트 PNG 몇 개를 골라서, 획 굵기 보정 전/후를 나란히
    보여준다 (config.py의 TARGET_STROKE_PX 등을 바로 반영해서 다시 실행하면 됨).
    """
    import json as _json
    import cv2
    import numpy as np

    print("획 굵기 보정 전/후 비교 중...")

    manifest = _json.loads(Path(manifest_path).read_text(encoding="utf-8"))

    if sample_ids is None:
        # 대표로 몇 개만 고른다: 단순한 자모 + 복잡한(꺾이는/겹치는) 자모
        wanted = ["cho_ㄱ_N_V", "cho_ㅁ_N_V", "jong_ㅁ", "jong_ㄶ", "cho_ㅇ_N_V"]
        sample_ids = [i for i, c in enumerate(manifest) if c["id"] in wanted]

    tiles = []
    labels = []
    for idx in sample_ids:
        png = Path(glyph_dir) / f"{idx:03}.png"
        if not png.exists():
            continue
        img = cv2.imread(str(png), cv2.IMREAD_GRAYSCALE)
        corrected = normalize_stroke_width(img)
        tiles.append((img, corrected))
        labels.append(manifest[idx]["id"])

    if not tiles:
        print("비교할 컴포넌트를 찾지 못했습니다 (data/glyphs 확인 필요).")
        return

    tile_size = 200
    cols = len(tiles)
    img_out = Image.new("L", (tile_size * cols, tile_size * 2 + 30), 255)
    draw = ImageDraw.Draw(img_out)
    label_font = ImageFont.load_default()

    for i, (before, after) in enumerate(tiles):
        b = Image.fromarray(before).resize((tile_size, tile_size))
        a = Image.fromarray(after).resize((tile_size, tile_size))
        img_out.paste(b, (i * tile_size, 20))
        img_out.paste(a, (i * tile_size, 20 + tile_size))
        draw.text((i * tile_size + 4, 2), labels[i], font=label_font, fill=0)

    draw.text((2, 20 + 2), "before", font=label_font, fill=0)
    draw.text((2, 20 + tile_size + 2), "after", font=label_font, fill=0)

    out = f"{OUTPUT_DIR}/preview_stroke.png"
    img_out.convert("RGB").save(out)
    print(f"저장됨: {out} (위: 보정 전, 아래: 보정 후)")


def preview_hinting():
    print("힌팅 적용 전/후 비교 폰트 생성 중 (작은 크기로 렌더링)...")
    sample = "Hello 가나다 123"

    ttf_hinted = build_preview_font(
        hangul_sample_rows=[("", "가나다")], latin_sample=sample,
        apply_hinting=True, output_path=f"{OUTPUT_DIR}/preview_hint_on.ttf",
    )
    ttf_unhinted = build_preview_font(
        hangul_sample_rows=[("", "가나다")], latin_sample=sample,
        apply_hinting=False, output_path=f"{OUTPUT_DIR}/preview_hint_off.ttf",
    )

    sizes = [12, 16, 24, 40]
    pad = 10
    row_h = 60
    W = 500
    img = Image.new("RGB", (W, row_h * len(sizes) * 2 + 40), "white")
    draw = ImageDraw.Draw(img)
    label_font = ImageFont.load_default()

    y = 10
    for label, ttf in [("hinting on", ttf_hinted), ("hintinh off", ttf_unhinted)]:
        draw.text((pad, y), f"--- {label} ---", font=label_font, fill=(150, 0, 0))
        y += 16
        for size in sizes:
            font = ImageFont.truetype(ttf, size)
            draw.text((pad, y), f"{size}px: {sample}", font=font, fill=(0, 0, 0))
            y += row_h // len(sizes) + size // 2 + 6

    out = f"{OUTPUT_DIR}/preview_hinting.png"
    img.save(out)
    print(f"저장됨: {out}")
    print("참고: 화면 배율/뷰어에 따라 차이가 잘 안 보일 수 있습니다. "
          "이미지 파일을 실제 픽셀 100%로 확대해서 보는 것을 권장합니다.")


MODES = {
    "hangul": preview_hangul,
    "latin": preview_latin,
    "kerning": preview_kerning,
    "stroke": preview_stroke,
    "hinting": preview_hinting,
}


if __name__ == "__main__":
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode == "all":
        for fn in MODES.values():
            fn()
    elif mode in MODES:
        MODES[mode]()
    else:
        print(f"알 수 없는 모드: {mode}")
        print(f"사용 가능: {', '.join(MODES)}, all")