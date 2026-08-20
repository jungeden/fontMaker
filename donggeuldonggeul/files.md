
# /fontMaker

### app.py

~~~py
"""
손글씨 TTF 폰트 생성기 - 메인 실행 스크립트
(한글 11,172자 자동 조합 + 영문/숫자/특수문자 지원)

사용법:
    python app.py template
        -> 손글씨 작성용 원고지 PDF 생성 (output/template.pdf, 여러 페이지 + 범례)
           한글 컴포넌트 183개(초성 6종/중성 2종/종성 1종) +
           영문 대소문자/숫자/특수문자 94개, 총 277개 컴포넌트 정보는
           data/manifest.json 에 저장된다.
           인쇄 후 손글씨로 채워서, 페이지 순서대로 스캔/촬영한 뒤
           data/scans/page1.jpg, page2.jpg ... 로 저장한다.

    python app.py build
        -> data/scans 안의 모든 page*.jpg 를 순서대로 전처리 -> 컴포넌트 분할
           -> 한글 11,172자(가능한 만큼) 자동 조합 + 영문/숫자/특수문자
           -> 폰트(.ttf) 생성까지 한 번에 실행
           결과물: output/MyHandwriting.ttf
           (컴포넌트를 일부만 채워도, 그 컴포넌트로 만들 수 있는 글자만 생성된다)
"""

import re
import sys
from pathlib import Path

import cv2

from modules.template import create_template, create_grid_overlay
from modules.preprocess import preprocess
from modules.segment import segment
from modules.fontbuild import build_font


def ensure_dirs():
    for folder in ["data/scans", "data/glyphs", "output"]:
        Path(folder).mkdir(parents=True, exist_ok=True)


def step_template():
    ensure_dirs()
    _components, n_pages = create_template()
    create_grid_overlay(n_pages)
    print("output/template.pdf 생성 완료. 인쇄 후 손글씨로 채워서 스캔하세요.")
    print("스캔 파일은 data/scans/page1.jpg, page2.jpg ... 순서로 저장하세요.")
    print("(참고: 연한 회색 안내선/글자는 전처리 시 자동으로 지워지므로 보통은 "
          "그대로 스캔해서 올리면 됩니다. output/grid_overlay_page*.png 는 직접 "
          "합성하고 싶을 때만 쓰는 보조 파일입니다.)")


def _find_scan_pages(scan_dir="data/scans"):
    files = list(Path(scan_dir).glob("page*.jpg")) + list(Path(scan_dir).glob("page*.png"))

    def page_num(p):
        m = re.search(r"(\d+)", p.stem)
        return int(m.group(1)) if m else 0

    return sorted(files, key=page_num)


def step_build():
    ensure_dirs()

    pages = _find_scan_pages()

    if not pages:
        print("스캔 이미지가 없습니다 (data/scans/page1.jpg, page2.jpg ...).")
        print("먼저 'python app.py template' 로 원고지를 만들고, 손글씨를 채운 뒤")
        print("페이지 순서대로 스캔/촬영한 이미지를 data/scans 에 저장하세요.")
        return

    print(f"[1/3] 이미지 전처리 중... ({len(pages)}페이지)")
    images = []
    for p in pages:
        img = preprocess(str(p))
        cv2.imwrite(f"output/clean_{p.stem}.png", img)
        images.append(img)

    print("[2/3] 컴포넌트 분할 중...")
    segment(images)

    print("[3/3] 11,172자 자동 조합 + 폰트 생성 중...")
    build_font()

    print("완료! output/MyHandwriting.ttf 를 설치해서 확인해보세요.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"

    if cmd == "template":
        step_template()
    elif cmd == "build":
        step_build()
    else:
        print("알 수 없는 명령입니다. 'template' 또는 'build'를 사용하세요.")

~~~

### config.py

~~~py
# config.py
# 프로젝트 전역 설정값. 모든 모듈이 여기서 값을 가져다 쓴다.
# (Readme.md의 template.py CHARS 50자 목록과 guide.md의 config.py CHARS 14자 목록이
#  서로 달랐던 문제를 여기서 하나로 통일한다.)

# ────────────────────────────────
# 템플릿(스캔용 원고지) 설정
# ────────────────────────────────
PAGE_MARGIN = 20   # mm, 페이지 좌/상단 여백
ROWS = 10
COLS = 10
CELL_SIZE = 18     # mm, 칸 한 변의 길이

# ────────────────────────────────
# 폰트 설정
# ────────────────────────────────
UNITS_PER_EM = 1000
ASCENDER = 800
DESCENDER = -200
ADVANCE_WIDTH = 1000
FONT_SIZE = 16

# ────────────────────────────────
# 글리프 이미지 처리 설정
# ────────────────────────────────
GLYPH_SIZE = 800        # 정규화된 글자 이미지 캔버스 크기 (px, 정사각형)
TARGET_HEIGHT = 700     # 글자 높이를 이 값(px)에 맞춰 확대/축소
BASELINE_MARGIN = 40    # 캔버스 하단 ~ baseline 사이 여백 (px)

# ────────────────────────────────
# 윤곽선 단순화 / 곡선화 설정
# ────────────────────────────────
APPROX_EPSILON = 2      # cv2.approxPolyDP 근사 정밀도 (작을수록 원본에 가까움)
CURVE_SMOOTHING = True  # True: 2차 베지어로 부드럽게, False: 직선(폴리곤) 그대로

# ────────────────────────────────
# 사용 문자셋
# ────────────────────────────────
# (이전 버전: 여기 50자 CHARS 목록을 직접 손글씨로 받아 그대로 폰트에 넣었음)
#
# 지금은 11,172자 전체를 자동 조합하는 방식으로 바뀌어서, 손글씨로 받아야 할
# 최소 단위(초성 6종/중성 2종/종성 1종, 총 183개)는 modules/hangul.py 의
# build_component_list() 가 관리한다. 여기서는 더 이상 문자 목록을 직접
# 정의하지 않는다.

# ────────────────────────────────
# 가이드(안내선) 자동 제거 설정
# ────────────────────────────────
# 템플릿의 점선/실선 안내상자, 번호, 예시 글자, baseline 안내선 등은 전부
# "글자가 아니라 안내용"이므로 아주 연한 회색으로 인쇄한다. 스캔 후 전처리
# 단계에서 이 밝기보다 밝은 픽셀은 전부 흰색(배경)으로 지워버리기 때문에,
# 사용자가 직접 가이드를 지우지 않아도 자동으로 사라진다.
#
# GUIDE_GRAY: ReportLab 회색 값 (0=검정, 1=흰색). 안내선을 인쇄할 때 쓴다.
# GUIDE_STRIP_THRESHOLD: 0~255 픽셀값. 전처리 시 이 값보다 밝은 픽셀은
#   전부 흰색으로 지운다. GUIDE_GRAY로 인쇄된 안내선(약 255*GUIDE_GRAY)보다
#   확실히 낮아야 안내선이 지워진다. 실제 손글씨(검은 펜/연필)는 이보다
#   훨씬 어두우므로 영향받지 않는다.
GUIDE_GRAY = 0.85              # 인쇄용 (약 픽셀값 217)
GUIDE_STRIP_THRESHOLD = 195    # 전처리용 (이보다 밝으면 흰색 처리)

# ────────────────────────────────
# 획 굵기(두께) 자동 보정 설정
# ────────────────────────────────
# 사람마다, 그리고 같은 사람이라도 글자를 크게/작게 쓸 때마다 실제 펜/연필
# 굵기와 무관하게 "디지털 이미지 안에서" 획이 차지하는 두께가 달라진다.
# 게다가 한글은 개별 자모를 목표 높이(TARGET_HEIGHT)로 강제로 확대/축소
# 하기 때문에, 작게 쓴 자모일수록 확대되면서 획도 더 두꺼워진다. 이대로
# 두면 자모/문자마다 획 굵기가 들쭉날쭉해 보인다.
#
# 이를 보정하기 위해, 분할·정규화가 끝난 각 글자 이미지에서 실제 획 굵기를
# 추정(잉크 면적/둘레 비율)한 뒤, 목표 굵기(TARGET_STROKE_PX)에 맞춰
# 팽창(dilate)/침식(erode) 처리를 한다. GLYPH_SIZE=800px 캔버스 기준.
#
# 굵기 추정치는 완벽하지 않다 (특히 ㄲ,ㄸ처럼 여러 획이 겹치거나 꺾이는
# 복잡한 모양에서 실제보다 두껍게 추정되기 쉽다). 추정치를 과신해서 한
# 번에 크게 깎으면 받침 등 얇은 부분이 통째로 사라질 수 있으므로, 아래
# 안전장치들로 "한 번에 너무 많이 깎지 않고, 여러 번에 걸쳐 조금씩,
# 잉크가 일정 비율 이상 사라지면 즉시 멈춘다."
STROKE_NORMALIZE = True
TARGET_STROKE_PX = 34           # 목표 굵기
STROKE_MAX_KERNEL_RADIUS = 4   # 한 번의 보정에서 깎거나 붙일 수 있는 최대 반지름(px)
STROKE_MIN_AREA_RATIO = 0.8     # 침식 후 최소 유지되어야 하는 잉크 면적 비율 (이하로 떨어지면 그 단계는 취소)
STROKE_MAX_ITERATIONS = 10      # 목표 굵기에 다가가기 위해 반복 보정하는 최대 횟수

~~~

### preview.py

~~~py
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

    draw.text((2, 20 + 2), "보정 전", font=label_font, fill=0)
    draw.text((2, 20 + tile_size + 2), "보정 후", font=label_font, fill=0)

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
    for label, ttf in [("힌팅 적용", ttf_hinted), ("힌팅 없음", ttf_unhinted)]:
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
~~~

### README.md

~~~md
# 손글씨 TTF 폰트 생성기

내 손글씨로 완성형 한글 11,172자(가~힣) + 조합되지 않은 단독 자모(ㄱ, ㅏ 등) + 영문 대소문자
+ 숫자 + 특수문자/기호까지 담은 TTF 폰트를 만드는 도구. 커닝(kerning)과 힌팅(hinting)까지
자동으로 적용된다.

11,172자를 전부 손으로 쓰는 대신, **모양이 실제로 달라지는 최소 단위(183개)만** 손글씨로
받고, 나머지는 초성/중성/종성 조합 공식으로 자동 조립한다. 영문/숫자/특수문자(129개)는
한글과 달리 조합되지 않으므로 한 칸에 한 글자씩 그대로 받는다.

총 **183(한글 컴포넌트) + 129(영문/숫자/특수문자) = 312칸**만 손글씨로 채우면 된다.

**전체 빌드 없이 빠르게 미리보기하려면 `preview.py`를 쓰면 된다** (아래 "빠른 미리보기"
섹션 참고). ZONE_LAYOUTS나 KIND_SCALE 등을 조정할 때마다 11,172자 전체를 다시 빌드할
필요 없이 1~5초 안에 결과를 확인할 수 있다.

## 왜 183개인가 (한글)

- **초성(19개) × 6가지 = 114개** — 받침 유무(2) × 뒤에 오는 모음의 방향(세로형/가로형/복합형,
  3)에 따라 초성의 폭과 위치가 달라진다. (예: "가"의 ㄱ과 "곡"의 ㄱ은 모양이 다르다)
- **중성(21개) × 2가지 = 42개** — 받침 유무에 따라 모음의 세로 길이가 달라진다.
- **종성/받침(27개) × 1가지 = 27개** — 받침은 항상 글자 하단의 같은 자리에만 오므로
  형태 변화가 없다.

114 + 42 + 27 = **183개**만 쓰면, 유니코드 조합 공식
`코드 = 0xAC00 + (초성인덱스×21 + 중성인덱스)×28 + 종성인덱스` 으로 11,172자를 전부 조합할 수 있다.

### 손글씨(컴포넌트)와 배치 좌표(zone)는 분리되어 있다

"어떤 손글씨를 쓸지"는 위처럼 큰 방향(세로형/가로형/복합형) 3종류만 받지만, "그걸 어디에
배치할지"는 그보다 더 세밀하게 9종류로 나눠서 조정할 수 있다. 같은 세로모음이라도 ㅏ 뒤에
오는 초성과 ㅓ 뒤에 오는 초성은 위치가 아주 살짝 다를 수 있기 때문에, 배치 좌표만 아래처럼
세분화해뒀다 (손글씨를 더 받을 필요는 없음 — 같은 손글씨를 재사용하되 위치/크기만 미세하게
다르게 조정 가능).

| 세부그룹 | 모음 | 세부그룹 | 모음 | 세부그룹 | 모음 |
|---|---|---|---|---|---|
| V1 (ㅏ계열) | ㅏㅑㅐㅒ | H1 (ㅗ계열) | ㅗㅛ | C1 (ㅘ계열) | ㅘㅚㅙ |
| V2 (ㅓ계열) | ㅓㅕㅔㅖ | H2 (ㅜ계열) | ㅜㅠ | C2 (ㅝ계열) | ㅝㅟㅞ |
| V3 (ㅣ계열) | ㅣ | H3 (ㅡ계열) | ㅡ | C3 (ㅢ계열) | ㅢ |

`modules/hangul.py`의 `ZONE_LAYOUTS`가 이 9개 세부그룹 × 받침유무(2) = 18개 좌표 세트를
갖고 있다. 예를 들어 **"거"(V2)에서만 받침 위치가 어색하다**면, 아래처럼 그 세부그룹만
직접 덮어쓰면 된다 (다른 세부그룹/다른 코드는 전혀 건드릴 필요 없음):

```python
# modules/hangul.py 아무 곳에나 (ZONE_LAYOUTS 정의 이후) 추가
ZONE_LAYOUTS[(True, "V2")] = {
    "cho":  (100, 560, 400, 1000),
    "jung": (400, 510, 1000, 1000),
    "jong": (100,  40, 900, 390),
}
```

또는 이미 있는 `_BASE_ZONE_LAYOUTS`(V/H/C 3그룹 기준값)를 고치면 그 그룹에 속한 세부그룹
3개(예: V → V1,V2,V3)가 한꺼번에 바뀐다. "전체적으로 이 방향의 글자들이 다 이상하다"면
`_BASE_ZONE_LAYOUTS`를, "이 방향 중에서도 특정 모음 하나만 이상하다"면 위처럼
`ZONE_LAYOUTS[(batchim, "V1")]` 개별 항목을 고치면 된다.

## 단독 자모 (ㄱ, ㅏ 등)

183개 컴포넌트 중 51개(초성 19 + 종성전용 겹받침 11 + 중성 21)는, 완성형 음절이 아니라
낱자 하나만 입력했을 때도(예: 한글 자음/모음 입력, 사전 표기 등) 폰트가 적용되도록 별도
글리프로 자동 생성된다. 추가로 손글씨를 받을 필요는 없다 — 이미 조합에 쓰인 컴포넌트
(초성은 "받침없음 + 세로모음", 중성은 "받침없음", 종성전용 겹받침은 종성 컴포넌트를 그대로)
를 재활용한다.

기본값은 **그 자모가 실제 음절 조합에 쓰일 때와 똑같은 크기**로 나온다 (예: 단독 ㄱ =
"가"에서 ㄱ이 차지하는 만큼의 크기). 위치만 조합 시의 한쪽으로 치우친 자리 대신 전체
박스 정중앙으로 옮겨서 표시한다.

**단독 자음 크기를 직접 지정하고 싶다면** `modules/hangul.py`의 `STANDALONE_HEIGHT_OVERRIDE`를
쓰면 된다:

```python
# modules/hangul.py
STANDALONE_HEIGHT_OVERRIDE = {
    "cho": 350,   # 단독 초성(ㄱ,ㄴ,ㄷ...) 표시 높이를 350(폰트 유닛)으로 고정
    "jung": None, # 모음은 그대로(자동, 조합 시와 동일한 크기) 유지
    "jong": None,
}
```

숫자를 넣으면 그 종류(초성/중성/종성)의 단독 표시가 항상 그 높이로 고정되고, `None`으로
두면 기존처럼 "실제 조합 시 크기"를 자동으로 재사용한다.

## 영문/숫자/특수문자 (129개)

출력 가능한 기본 ASCII 문자 전체(`!` ~ `~`, 94자)에 더해, 모바일 키보드 기호 화면 등에서
자주 쓰는 문자 35개(말줄임표 …, 스마트 따옴표 " " ' ', 대시 — –, 낫표 「」『』【】, 별/하트/
동그라미 등 기호 ★☆♥♡○●□■◇◆△▲, 화살표 →←↑↓, 통화/저작권 기호 ₩©®™)를 추가로
지원한다. 공백은 글자 모양이 없으므로 폭 값만 자동으로 채워진다.

### 한글과 크기/굵기를 맞추는 자동 보정

- **크기**: 한글 자모는 `segment.py`에서 자모마다 목표 높이로 강제 확대/축소되지만, 라틴
  문자는 g/y/p 같은 내림선 글자의 baseline 정보를 지키기 위해 그런 보정을 하지 않는다.
  그대로 두면 사용자가 쓴 크기 그대로 들어가서 한글 옆에 있을 때 상대적으로 작아 보이는
  문제가 있었다. → 대문자 A~Z의 실제 손글씨 높이(중앙값)를 측정해서, 라틴 문자 전체에
  (개별 문자마다 다르게 적용하면 서로 비율이 깨지므로 반드시 전체에 동일하게) 배율 하나를
  곱해서 한글과 비슷한 시각적 무게감이 나도록 자동 보정한다 (`modules/latin.py`의
  `TARGET_CAP_HEIGHT`, 기본값 780 — 여전히 작아 보이면 이 값을 더 올리면 된다).
- **굵기**: 벡터 도형을 확대/축소하면 획 굵기도 같이 확대/축소되기 때문에, 자모/문자마다
  확대 비율이 다르면 최종 굵기도 들쭉날쭉해진다. → 분할·정규화가 끝난 각 글자 이미지에서
  실제 획 굵기를 추정(잉크 면적 대비 둘레 길이 비율)한 뒤, 목표 굵기에 맞춰 팽창(dilate)/
  침식(erode) 처리로 보정한다 (`modules/segment.py`의 `normalize_stroke_width`,
  `config.py`의 `TARGET_STROKE_PX`).

  굵기 추정치는 완벽하지 않다 — 특히 ㄲ,ㄸ,ㄶ처럼 여러 획이 겹치거나 꺾이는 부분이 많은
  복잡한 모양은 실제보다 두껍게 추정되기 쉬운데, 이 추정치를 과신해서 한 번에 크게
  깎아버리면 받침처럼 얇은 부분이 통째로 사라지는 문제가 있었다. 그래서 지금은 한 번에
  깎는 양을 제한하고(`STROKE_MAX_KERNEL_RADIUS`), 여러 번에 걸쳐 조금씩 목표에
  다가가며(`STROKE_MAX_ITERATIONS`), 침식으로 잉크가 일정 비율 이상
  사라지면(`STROKE_MIN_AREA_RATIO`) 그 단계를 즉시 취소하고 직전 상태를 유지한다. 그래도
  여전히 너무 얇게 나온다면 `config.py`의 `TARGET_STROKE_PX`를 올리면 된다.

## 원고지 가이드는 자동으로 지워진다

원고지 각 칸의 점선 상자, 번호, 예시 글자, baseline 안내선은 모두 **아주 연한 회색**으로
인쇄된다. 종이에서 보기엔 충분히 진하지만, 전처리 단계(`preprocess.py`)에서 이 밝기보다
밝은 픽셀은 전부 흰 배경으로 자동 처리하기 때문에 스캔한 뒤 사람이 직접 지울 필요가 없다.
실제 손글씨(검은 펜/연필)는 훨씬 어두우므로 영향받지 않는다. 칸을 나누는 검정 실선 테두리만
남아서 `segment.py`가 칸을 나누는 기준으로 쓴다.

한글 칸에는 예시 음절 전체("가", "곽" 등)가 큰 워터마크로 깔려 있어서, 내가 쓰는 자모가
전체 글자 안에서 어느 크기/위치에 있어야 하는지 보면서 쓸 수 있다. 점선 상자 = 실제 쓰기
한계선이라고 생각하면 된다 (상자를 벗어나면 조합했을 때 옆 자모와 겹칠 수 있음).

라틴 문자 칸은 **실선 상자 = 실제 사용 가능한 전체 높이**(위쪽 끝 = ascender, 아래쪽 끝 =
descender)다. 이 상자를 벗어나면 글자가 잘린다. 상자 안의 굵은 가로선이 baseline이고,
대부분의 글자는 이 선 위에 앉지만 g, y, p, q, j 는 이 선 아래(상자 하단까지)로 내려가면 된다.

(만약 그래도 가이드가 스캔 상태에 따라 완전히 지워지지 않는다면, `python app.py template`
실행 시 함께 만들어지는 `output/grid_overlay_page*.png`(격자선만 있는 투명 배경 PNG)를 이용해
직접 손으로 편집한 손글씨 이미지에 격자를 합성해서 올려도 된다.)

## 사용법

```bash
pip install -r requirements.txt

# 1) 원고지 PDF 생성 (312칸, 여러 페이지 + 범례 페이지 포함)
python app.py template
# -> output/template.pdf, output/grid_overlay_page*.png, data/manifest.json 생성됨

# 2) 인쇄해서 손글씨로 채운 뒤, 페이지 순서대로 스캔/촬영
#    data/scans/page1.jpg, data/scans/page2.jpg ... 로 저장

# 3) 전처리 -> 컴포넌트 분할 -> 한글 11,172자 자동 조합 + 단독 자모 + 영문/숫자/특수문자
#    -> 크기/굵기 자동 보정 -> 커닝 -> 힌팅 -> TTF 생성
python app.py build
# -> output/MyHandwriting.ttf
```

컴포넌트를 일부만 채워도, 그 컴포넌트로 조합/생성 가능한 글자만 생성된다(나머지는 자동 제외).

## 빠른 미리보기 (전체 빌드 없이)

`ZONE_LAYOUTS`, `KIND_SCALE`, `COMPONENT_SCALE`, `COMPONENT_OFFSET`,
`STANDALONE_HEIGHT_OVERRIDE`, `TARGET_STROKE_PX`, `TARGET_CAP_HEIGHT` 같은 값을 조금씩
바꿔가며 확인하고 싶을 때, 매번 `python app.py build`로 11,172자 전체를 다시 만들면 너무
느리다 (수십 초). `preview.py`는 **지정한 대표 글자 몇 개만** 담은 작은 미리보기 폰트를
1~5초 안에 만들어서 바로 이미지로 보여준다.

```bash
python preview.py hangul     # 한글 대표 음절 미리보기 (9개 모음 세부그룹 +
                              #   받침 유무 + 자음별 크기 + 겹받침, 한 장의 이미지로)
python preview.py latin      # 영문/숫자/특수문자 미리보기
python preview.py kerning    # 커닝 적용 전/후 비교
python preview.py stroke     # 획 굵기 보정 전/후 비교 (실제 컴포넌트 PNG 기준)
python preview.py hinting    # 힌팅 적용 전/후 비교 (작은 크기로 렌더링)
python preview.py all        # 위 다섯 가지를 전부 실행
```

결과 이미지는 `output/preview_*.png`로 저장된다. 내부적으로 최종 빌드
(`modules/fontbuild.py`)와 **완전히 같은 함수**(`compose_syllable_glyph`,
`build_latin_glyphs`, `build_kern_feature`, `assemble_fontbuilder`)를 그대로 재사용하기
때문에, 여기서 본 결과와 `python app.py build`의 최종 완성본은 항상 일치한다 — 한글만
11,172자 전체가 아니라 지정한 샘플 글자만 넣어서 빠른 것뿐이다.

미리보기에 어떤 글자를 넣을지는 `preview.py` 맨 위쪽의 `HANGUL_PREVIEW_ROWS`,
`DEFAULT_LATIN_SAMPLE`을 고쳐서 자유롭게 바꿀 수 있다. 이 도구는 `data/glyphs`에 이미
분할된 컴포넌트 PNG가 있어야 동작한다 (즉 `python app.py build`를 최소 한 번 실행해서
스캔 → 분할 단계를 거친 뒤 쓸 수 있다). 그 이후로는 손글씨를 다시 스캔하지 않는 한
`preview.py`만으로 빠르게 튜닝을 반복하고, 만족스러우면 마지막에 한 번만
`python app.py build`로 전체 폰트를 완성하면 된다.

## 구조 (모듈별 상세 설명)

```
fontMaker
├── data
│   ├── scans/            # 스캔한 원고지 사진 (page1.jpg, page2.jpg ...)
│   ├── glyphs/            # 분할된 컴포넌트 PNG (000.png ~ 311.png)
│   └── manifest.json      # 312개 컴포넌트 정의 (template.py가 생성, segment/compose/latin이 사용)
├── modules/                # 아래에 파일별로 상세 설명
├── output/                 # template.pdf, grid_overlay_page*.png, MyHandwriting.ttf, preview_*.png
├── app.py                  # 전체 파이프라인 실행 (template / build)
├── preview.py              # 빠른 미리보기 도구 (위 섹션 참고)
├── config.py                # 전역 설정값
└── requirements.txt
```

아래는 `modules/` 안 각 파일이 어떤 일을 하고, 어떤 함수들이 있는지에 대한 설명이다.
더 자세한 구현 설명은 각 파일 안의 주석에 있다 — 여기서는 "이 파일이 왜 있고, 어떤
함수를 호출하면 무슨 일이 일어나는지" 정도의 지도 역할만 한다.

### `hangul.py` — 한글 자모 데이터 + 조합 좌표 + 자모별 보정 테이블

한글 조합의 "설계도"에 해당하는 모든 상수/테이블이 모여 있는 파일. 실제 이미지 처리나
폰트 생성 코드는 없고, 순수하게 데이터와 좌표 계산만 담당한다.

- `CHO_LIST`, `JUNG_LIST`, `JONG_LIST`: 초성 19개/중성 21개/종성 27개의 유니코드 순서 목록.
- `VOWEL_GROUP`: 중성 21개 각각이 어느 세부그룹(V1~C3, 9종류)에 속하는지 매핑.
- `SUBGROUPS`, `GROUP_MACRO`: 세부그룹(V1 등)과 상위 그룹(V 등) 사이를 서로 변환하는 표.
  (컴포넌트는 상위 그룹 기준 3종류만 있고, 배치 좌표는 세부그룹 9종류로 나뉘기 때문에
  이 둘을 서로 변환할 일이 자주 있다)
- `ZONE_LAYOUTS`: (받침유무, 세부그룹) → 초성/중성/종성이 차지할 사각형 좌표. 이 프로젝트에서
  가장 자주 조정하게 될 테이블.
- `KIND_SCALE`, `COMPONENT_SCALE`, `COMPONENT_OFFSET`, `get_component_scale()`,
  `get_component_offset()`: 자모별 미세 크기/위치 보정. "특정 자모만 더 세밀하게 보정하고
  싶다면" 섹션 참고.
- `STANDALONE_HEIGHT_OVERRIDE`: 단독 자모(ㄱ, ㅏ 등) 표시 크기를 직접 지정하고 싶을 때 쓰는 표.
- `component_id(kind, jamo, batchim, group)`: 컴포넌트를 식별하는 문자열 id를 만든다
  (예: `"cho_ㄱ_N_V"`). `data/glyphs/000.png` 같은 실제 파일과 이 id를 연결하는
  `data/manifest.json`이 `template.py`에 의해 만들어진다.
- `compose_char(cho, jung, jong)`: 초/중/종성 자모로 실제 완성형 한글 한 글자를 조합한다
  (예: `compose_char("ㄱ","ㅏ")` → `"가"`). 원고지에 예시를 표시할 때, 미리보기 도구에서
  샘플을 만들 때 등 여러 곳에서 쓰인다.
- `decompose_code(code)`: 완성형 한글 코드포인트를 (초성, 중성, 종성)으로 분해한다.
  `compose_char`의 반대 방향. `compose.py`가 11,172자를 하나씩 돌면서 이 함수로 분해한 뒤
  조합한다.
- `build_component_list()`: 손글씨로 받아야 할 183개 컴포넌트 전체 목록을 만든다. 이 목록의
  순서가 곧 원고지 칸 순서 = `data/glyphs` 안 PNG 파일 인덱스 순서가 된다.
  `template.py`가 원고지를 그릴 때, `segment.py`가 칸을 나눌 때 이 함수를 쓴다.
- `build_standalone_jamo_list()`: 단독 자모 51개 각각에 대해 (유니코드 코드포인트, 대표
  컴포넌트 id)를 만든다. `compose.py`의 `build_standalone_glyphs()`가 이 목록을 써서
  실제 글리프를 만든다.

### `latin.py` — 영문/숫자/특수문자 컴포넌트 + 개별 글리프 생성

한글과 달리 라틴 문자는 서로 조합되지 않으므로, 이 파일은 "PNG 한 장 = 글리프 하나"를
직접 만드는 역할을 한다.

- `ASCII_CHARS`, `EXTRA_CHARS`, `LATIN_CHARS`: 지원하는 문자 목록(94 + 35 = 129자).
- `BASELINE_RATIO`: 라틴 문자 칸에서 baseline이 칸 높이의 몇 %에 위치하는지
  (`config.py`의 ASCENDER/DESCENDER로부터 계산됨). `template.py`가 원고지에 baseline
  안내선을 그릴 때, 이 파일이 이미지→폰트좌표 변환을 할 때 똑같이 쓴다 — 두 곳이 어긋나면
  안 되므로 반드시 이 상수 하나를 공유한다.
- `build_component_list()`: 129개 컴포넌트 목록 (한글의 `build_component_list`와 대응).
- `image_to_contours_latin(path)`: PNG 한 장을 (다각형 점 목록, 구멍여부) 튜플 리스트로
  변환한다. 한글용 `glyph.py`의 `image_to_contours`와 비슷하지만, baseline 위치를 살리는
  좌표 변환(`_scale_flip_latin`)을 쓴다는 점이 다르다.
- `_calc_global_scale(raw_glyphs)`: 대문자 A~Z의 실제 높이 중앙값을 측정해서, 그 값이
  `TARGET_CAP_HEIGHT`에 오도록 하는 배율 하나를 계산한다. "한글과 크기를 맞추는 자동 보정"
  섹션 참고.
- `build_latin_glyphs(glyph_dir, manifest)`: 위 함수들을 이용해 129개 전체의 최종 TTGlyph +
  advance width를 만든다. `fontbuild.py`와 `preview.py`가 이 함수를 호출한다.

### `template.py` — 원고지 PDF 생성

- `_zone_to_rect(x, y, cell, zone_shape)`: (칸의 위치, zone 좌표) → 실제 PDF 위의 사각형
  좌표로 변환하는 핵심 함수. 안내 상자(점선/실선)와 한글 워터마크가 **반드시 같은 함수**를
  써야 위치가 정확히 일치하므로, 이 함수 하나로 통일했다.
- `_draw_hangul_watermark`, `_draw_guide_box`, `_draw_latin_guide`, `_draw_cell`: 칸 하나를
  그리는 세부 함수들.
- `create_template(filename, manifest_path)`: 전체 원고지 PDF + 범례 페이지를 만들고,
  `data/manifest.json`을 저장한다. `app.py`의 `template` 명령이 이 함수를 호출한다.
- `create_grid_overlay(n_pages, ...)`: 격자선만 있는 투명 배경 PNG를 페이지별로 만든다
  (가이드 자동 제거가 잘 안 될 때 수동으로 합성하기 위한 보조 파일).

### `preprocess.py` — 스캔 이미지 보정

- `detect_page(image)`, `four_point_transform(image, pts)`: 사진 속에서 원고지 용지의
  네 꼭짓점을 찾아 반듯하게 펴는(기울기 보정) 역할.
- `preprocess(path)`: 위 보정 + 노이즈 제거 + 연한 회색 가이드 자동 제거
  (`GUIDE_STRIP_THRESHOLD`) + 흑백 이진화까지 한 번에 처리한다. `app.py`가 스캔 페이지마다
  이 함수를 호출한다.

### `segment.py` — 원고지 칸 → 컴포넌트 PNG 분할

- `_inset(cell)`: 칸 테두리(격자선)가 잉크로 오인식되지 않도록 가장자리를 살짝 잘라낸다.
- `has_content(cell)`: 칸이 비어있는지 확인 (빈 칸 자동 스킵용).
- `crop_content(cell)`, `normalize_glyph(glyph)`: **한글용**. 실제 잉크만 잘라내고, 목표
  높이로 맞춘 뒤 baseline에 정렬해서 정사각형 캔버스에 배치한다.
- `normalize_latin_cell(cell)`: **라틴용**. `normalize_glyph`와 달리 baseline 위치 정보를
  지키기 위해 내용 기준으로 재정렬하지 않고, 칸을 있는 그대로 정사각형으로 리사이즈만 한다.
- `_estimate_stroke_width(ink_mask)`, `normalize_stroke_width(img)`: 획 굵기 자동 보정
  (위 "한글과 크기/굵기를 맞추는 자동 보정" 섹션 참고). 두 정규화 함수 모두 마지막에 이
  보정을 거친다.
- `segment(images, output_dir, manifest_path)`: 페이지 이미지들을 받아서 칸을 나누고,
  컴포넌트 종류(한글/라틴)에 따라 위 정규화 함수들을 적용한 뒤 `data/glyphs/{idx}.png`로
  저장한다. `app.py`의 `build` 명령이 이 함수를 호출한다.

### `vectorize.py` — PNG → 윤곽선 검출

- `find_contours_with_holes(img)`: `cv2.RETR_TREE`로 바깥 윤곽선과 안쪽 구멍(ㅇ,ㅎ,ㅁ,ㅂ의
  속 빈 부분)을 모두 찾는다. 일반적인 `RETR_EXTERNAL`을 쓰면 ㅇ이 속이 꽉 찬 원이 되어버린다.
- `simplify(contour)`: 점 개수를 줄여 다각형을 단순화한다 (베지어 곡선화 전 전처리).
- `signed_area(pts)`, `fix_winding(pts, is_hole)`: TrueType 규칙(바깥 윤곽선=시계방향,
  구멍=반시계방향)에 맞게 점의 순서를 보정한다. 이걸 안 하면 구멍이 안 뚫리거나 글자
  전체가 사라질 수 있다.
- `convert_folder(...)`: (선택 기능) `data/glyphs`의 PNG들을 SVG로 변환하는 디버깅용 함수.

### `glyph.py` — 윤곽선 → 폰트 좌표계 변환 + 곡선화 (한글용)

- `_scale_flip(pt)`: 이미지 픽셀 좌표(0~800, y 아래로 증가) → 폰트 유닛 좌표(0~1000, y
  위로 증가) 변환.
- `image_to_contours(path)`: PNG 한 장을 (font-space 점 목록, 구멍여부) 튜플 리스트로
  변환한다. `vectorize.py`의 함수들 + 위 좌표 변환을 합친 것. `compose.py`가 컴포넌트를
  로드할 때 이 함수를 쓴다.
- `draw_contour(pen, pts)`: 점 목록을 2차 베지어 곡선으로 부드럽게 그린다 (각 변의 중점을
  on-curve 점으로 써서 각진 다각형이 아니라 곡선처럼 보이게 한다).
- `image_to_glyph(path)`: 위 두 함수를 합쳐 PNG → TTGlyph를 바로 만든다 (개별 컴포넌트
  미리보기/디버깅용).

### `compose.py` — 183개 컴포넌트로 11,172자 + 단독 자모 조합

이 프로젝트의 핵심 로직이 있는 파일. 자세한 설계 배경은 파일 맨 위 docstring 참고.

- `load_component_contours(glyph_dir, manifest_path)`: `data/glyphs`의 PNG들을 읽어서
  `{컴포넌트id: {"contours":[...], "bbox":(...)}}` 캐시를 만든다. bbox를 미리 계산해두는
  이유는 11,172자를 조합할 때마다 다시 계산하면 느리기 때문.
- `build_calibration(cache)`: 같은 문맥(예: "받침없음+세로모음" 초성 19개)에 속한
  컴포넌트들의 실제 손글씨 높이 중앙값을 계산한다. 이 값이 그 문맥 전체가 공유하는 "기준
  크기"가 된다 (크기가 안정적으로 나오는 핵심 메커니즘).
- `_fit_contours(entry, zone, kind, jamo, calibration_height)`: 컴포넌트 하나를 zone
  안에 비율 유지 + 중앙 정렬로 배치한다. 배율은 이 컴포넌트 자신의 크기가 아니라
  `calibration_height`(문맥 공통 기준)로 계산하므로, 같은 문맥 안에서는 항상 같은 배율이
  나와서 크기가 안정적이다. `KIND_SCALE`/`COMPONENT_SCALE`/`COMPONENT_OFFSET`도 여기서
  곱해진다.
- `compose_syllable_glyph(cache, calibration, cho, jung, jong)`: 초/중/종성 자모 하나로
  완성형 음절 하나의 TTGlyph를 만든다. `preview.py`가 샘플 글자 몇 개만 빠르게 만들 때도
  이 함수를 직접 호출한다.
- `compose_from_cache(cache, calibration)`, `compose_all(...)`: 가(0xAC00)~힣(0xD7A3)
  11,172자 전체를 조합한다. `compose_from_cache`는 캐시/calibration을 미리 계산해서
  넘길 때, `compose_all`은 파일 경로만 주고 한 번에 실행할 때 쓴다.
- `build_standalone_glyphs(cache, calibration)`: 단독 자모 51개의 글리프를 만든다
  ("단독 자모" 섹션 참고).

### `kerning.py` — 라틴 문자 쌍 자동 커닝

- `_contours_of(glyph, glyf)`: 컴파일된 TTGlyph에서 윤곽선 점 목록을 다시 꺼낸다.
- `_profile(contours, ascender, descender)`: 글자를 위아래로 잘게 나눠서, 각 높이에서
  잉크의 왼쪽 끝/오른쪽 끝 x좌표를 계산한다 (커닝 계산의 기초 자료).
- `build_kern_feature(font, latin_cmap, target_gap)`: 라틴 129자의 모든 쌍에 대해 두
  글자를 나란히 놓았을 때의 간격을 위 프로파일로 계산하고, 이상적인 간격(target_gap)과
  차이가 크면 GPOS `kern` 피처로 보정값을 추가한다. `fontbuild.py`와 `preview.py`(kerning
  모드)가 이 함수를 호출한다.

### `fontbuild.py` — 최종 .ttf 조립

- `assemble_fontbuilder(hangul_glyphs, ..., latin_metrics, family_name, style_name)`:
  글리프/cmap/지표를 모아 `fontTools.fontBuilder.FontBuilder`를 조립하는 공용 로직.
  `build_font()`(전체 완성 빌드)와 `preview.py`(대표 글자만 넣는 빠른 미리보기)가 이
  함수를 공유한다 — 그래서 미리보기 결과와 최종 완성본이 항상 일치한다.
- `_apply_hinting(unhinted_path, output_path)`: 시스템에 `ttfautohint`가 설치되어 있으면
  자동으로 힌팅을 적용한다 (없으면 힌팅 없이 저장 + 설치 안내).
- `build_font(...)`: 위 함수들을 전부 연결해서 `data/glyphs` → 최종 `output/MyHandwriting.ttf`
  까지 만드는 최상위 함수. `app.py`의 `build` 명령이 이 함수를 호출한다.

### `app.py` — 전체 파이프라인 실행 (CLI 진입점)

- `step_template()`: `template.py`로 원고지 PDF + 격자 오버레이를 만든다 (`template` 명령).
- `_find_scan_pages(scan_dir)`: `data/scans` 안의 `page1.jpg, page2.jpg ...`를 순서대로 찾는다.
- `step_build()`: 스캔 페이지들을 `preprocess.py`로 보정 → `segment.py`로 분할 →
  `fontbuild.py`로 최종 폰트 생성까지 전체 파이프라인을 실행한다 (`build` 명령).

### `preview.py` — 빠른 미리보기 도구

"빠른 미리보기" 섹션 참고.

## Kerning(커닝)과 Hinting(힌팅)이란?

**커닝**: 특정 두 글자를 나란히 놓았을 때 생기는 시각적인 간격 차이를 보정하는 것.
예를 들어 활자에서 "AV"를 그냥 이어붙이면 사이에 불필요하게 큰 틈이 생기는데, 커닝으로
이 틈을 좁혀서 다른 글자 쌍과 비슷한 간격으로 보이게 만든다. 이 프로젝트는 라틴 문자
129개의 모든 쌍(약 1만 6천 쌍)에 대해 실제 손글씨 윤곽선을 분석해서, 너무 붙거나 너무 뜬
쌍만 자동으로 보정하는 커닝을 적용한다 (`modules/kerning.py`). 한글 음절/단독 자모는 전부
같은 폭의 정사각형 칸에 들어가는 전각 문자라서 커닝을 적용하지 않는다 (표준적인 한글
조판 방식).

**힌팅**: 작은 크기(특히 저해상도 화면)에서 글자 획이 흐릿하거나 삐뚤어지지 않게, 폰트
안에 "이 크기에서는 이 획을 픽셀 격자에 맞춰 그려라"라는 지시를 추가하는 작업. 이 지시는
폰트 전용 바이트코드 언어로 작성해야 해서 직접 구현하기는 매우 복잡하지만, 널리 쓰이는
오픈소스 자동 힌팅 도구인 **ttfautohint**가 시스템에 설치되어 있으면 빌드 마지막 단계에서
자동으로 적용된다 (없으면 힌팅 없이 저장하고 설치 방법을 안내한다).

```bash
# ttfautohint 설치 (선택 사항 - 없어도 폰트는 정상적으로 만들어진다)
brew install ttfautohint          # macOS
sudo apt install ttfautohint      # Linux
# Windows: https://freetype.org/ttfautohint/#download
```

## 한계

- 초성 6종류 분류는 실제 정식 폰트 제작사가 쓰는 세밀한 분류(보통 더 많은 변형)보다는
  단순화된 버전이다. 배치 좌표는 9개 세부그룹으로 조정 가능하지만, 손글씨 자체는 3종류만
  받으므로 예를 들어 "ㅏ" 뒤 초성과 "ㅓ" 뒤 초성이 형태 자체는 완전히 같다.
- 컴포넌트는 문맥별 공유 배율을 쓰므로 같은 문맥 안에서는 크기가 안정적이지만, 자모 자체의
  자연스러운 형태 차이(예: ㄱ은 작고 ㅁ은 큼)까지 완전히 균일하게 만들지는 않는다 (의도적 —
  손글씨의 자연스러운 상대적 크기감을 존중한다). 그래도 유독 튀는 자모는 `COMPONENT_SCALE`로
  수동 보정할 수 있다.
- 획 굵기 자동 보정은 잉크 면적/둘레 비율 기반의 근사치라 완벽하게 균일하지는 않다.
  안전장치(단계적 보정 + 면적 가드)로 받침 등이 통째로 사라지는 것은 방지하지만, 그래도
  이상하다면 `config.py`의 `TARGET_STROKE_PX`나 `STROKE_MAX_KERNEL_RADIUS`를 조정하면 된다.
- 라틴 문자의 baseline 정렬은 스캔이 원고지 인쇄 비율과 잘 맞아떨어진다고 가정한다. 스캔이
  심하게 기울어지거나 왜곡되면 g/y/p 같은 글자의 baseline이 살짝 어긋날 수 있다.
- 진짜 폰트 제작사 수준의 정교한 곡선 피팅(최소자승 베지어 피팅)은 구현하지 않았다
  (2차 베지어 근사만 사용).
- `preview.py`의 힌팅 비교는 화면 배율/이미지 뷰어에 따라 차이가 잘 안 보일 수 있다 —
  이미지를 픽셀 100%로 확대해서 보는 것을 권장한다.

~~~

### requirements.txt

~~~txt

fonttools
opencv-python
numpy
Pillow
reportlab
svgpathtools
scipy


~~~

# /fontMaker/modules

### compose.py

~~~py
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

~~~

### fontbuild.py

~~~py
import shutil
import subprocess
import json
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

from config import UNITS_PER_EM, ASCENDER, DESCENDER, ADVANCE_WIDTH
from modules.compose import (
    load_component_contours,
    build_calibration,
    compose_from_cache,
    build_standalone_glyphs,
)
from modules.latin import build_latin_glyphs
from modules.kerning import build_kern_feature


def _apply_hinting(unhinted_path, output_path):
    """
    ttfautohint(https://freetype.org/ttfautohint/)가 시스템에 설치되어 있으면
    자동으로 힌팅을 적용한다. 없으면 힌팅 없이 그대로 저장하고 설치 방법을
    안내한다.

    힌팅이 뭔지: 작은 크기(특히 저해상도 화면)에서 글자 획이 흐릿하거나
    삐뚤어지지 않게, 폰트 안에 "이 크기에서는 이 획을 픽셀 격자에 맞춰
    그려라"라는 지시(명령어)를 추가하는 작업이다. 직접 이 명령어를 손으로
    작성하는 건 매우 복잡하므로(폰트 전용 바이트코드 언어), 널리 쓰이는
    오픈소스 자동 힌팅 도구인 ttfautohint를 그대로 활용한다.
    """
    ttfautohint = shutil.which("ttfautohint")

    if not ttfautohint:
        shutil.move(unhinted_path, output_path)
        print("참고: ttfautohint가 설치되어 있지 않아 힌팅 없이 저장했습니다. "
              "힌팅을 적용하려면 ttfautohint를 설치한 뒤 다시 빌드하세요 "
              "(Mac: brew install ttfautohint / "
              "Linux: sudo apt install ttfautohint / "
              "Windows: https://freetype.org/ttfautohint/#download 에서 설치).")
        return False

    try:
        subprocess.run(
            [ttfautohint, unhinted_path, output_path],
            check=True, capture_output=True, text=True,
        )
        Path(unhinted_path).unlink(missing_ok=True)
        print("ttfautohint로 자동 힌팅을 적용했습니다.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"참고: ttfautohint 실행에 실패해서 힌팅 없이 저장합니다. ({e.stderr[:200]})")
        shutil.move(unhinted_path, output_path)
        return False


def assemble_fontbuilder(
    hangul_glyphs, hangul_cmap,
    standalone_glyphs, standalone_cmap,
    latin_glyphs, latin_cmap, latin_metrics,
    family_name="MyHandwriting", style_name="Regular",
):
    """
    글리프/cmap/지표를 모아 FontBuilder를 조립하는 공용 로직.

    build_font()(전체 11,172자 완성 빌드)와 preview.py(대표 글자 몇 개만
    넣는 빠른 미리보기 빌드)가 이 함수를 공유한다 - 그래서 미리보기에서
    본 결과가 최종 완성본과 항상 일치한다.
    """
    glyph_order = [".notdef"]
    glyphs = {".notdef": TTGlyphPen(None).glyph()}
    metrics = {".notdef": (UNITS_PER_EM, 0)}
    cmap = {}

    # 한글 음절 + 단독 자모는 전부 정사각형(전각) 글자이므로 advance width를
    # 고정값으로 준다.
    for gname, glyph in hangul_glyphs.items():
        glyph_order.append(gname)
        glyphs[gname] = glyph
        metrics[gname] = (ADVANCE_WIDTH, 0)
    cmap.update(hangul_cmap)

    for gname, glyph in standalone_glyphs.items():
        glyph_order.append(gname)
        glyphs[gname] = glyph
        metrics[gname] = (ADVANCE_WIDTH, 0)
    cmap.update(standalone_cmap)

    # 라틴/숫자/특수문자는 글자마다 실제 폭에 맞는 advance width를 쓴다.
    for gname, glyph in latin_glyphs.items():
        glyph_order.append(gname)
        glyphs[gname] = glyph
        metrics[gname] = latin_metrics[gname]
    cmap.update(latin_cmap)

    fb = FontBuilder(UNITS_PER_EM, isTTF=True)

    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=ASCENDER, descent=DESCENDER)

    fb.setupOS2(
        sTypoAscender=ASCENDER,
        sTypoDescender=DESCENDER,
        usWinAscent=ASCENDER,
        usWinDescent=abs(DESCENDER),
    )

    fb.setupNameTable({
        "familyName": family_name,
        "styleName": style_name,
        "fullName": f"{family_name} {style_name}",
        "psName": f"{family_name}-{style_name}".replace(" ", ""),
    })

    fb.setupPost()
    fb.setupMaxp()

    return fb


def build_font(
    glyph_dir="data/glyphs",
    manifest_path="data/manifest.json",
    output_path="output/MyHandwriting.ttf",
    family_name="MyHandwriting", #폰트 이름
    style_name="Regular",
    apply_kerning=True,
    apply_hinting=True,
):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))

    cache, missing = load_component_contours(glyph_dir, manifest_path)
    if missing:
        print(f"참고: {len(missing)}개 컴포넌트가 아직 없어서 관련 음절/자모는 제외됩니다.")

    # 같은 문맥(예: 받침없음+세로모음 초성 19개)에 속한 컴포넌트들이 공통
    # 배율을 공유하도록, 문맥별 기준 높이를 한 번만 계산해서 재사용한다.
    calibration = build_calibration(cache)

    hangul_glyphs, hangul_cmap, hangul_built, hangul_skipped = compose_from_cache(cache, calibration)
    standalone_glyphs, standalone_cmap, standalone_built = build_standalone_glyphs(cache, calibration)
    latin_glyphs, latin_cmap, latin_metrics, latin_built = build_latin_glyphs(
        glyph_dir, manifest
    )

    if hangul_built == 0 and latin_built == 0 and standalone_built == 0:
        raise RuntimeError(
            "조합/생성된 글자가 하나도 없습니다. data/glyphs 에 컴포넌트 PNG가 "
            "있는지, data/manifest.json이 있는지 확인하세요."
        )

    fb = assemble_fontbuilder(
        hangul_glyphs, hangul_cmap,
        standalone_glyphs, standalone_cmap,
        latin_glyphs, latin_cmap, latin_metrics,
        family_name, style_name,
    )

    kern_pairs = 0
    if apply_kerning:
        kern_pairs = build_kern_feature(fb.font, latin_cmap)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if apply_hinting:
        unhinted_path = str(output_path) + ".unhinted.ttf"
        fb.save(unhinted_path)
        _apply_hinting(unhinted_path, output_path)
    else:
        fb.save(output_path)

    print(f"한글 {hangul_built}자 (미완성 컴포넌트로 {hangul_skipped}자 제외) + "
          f"단독 자모 {standalone_built}개 + "
          f"영문/숫자/특수문자 {latin_built}자, 총 {hangul_built + standalone_built + latin_built}자, "
          f"커닝 {kern_pairs}쌍 적용, '{output_path}' 생성 완료")
    return output_path

~~~

### glyph.py

~~~py
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

~~~

### hangul.py

~~~py
"""
한글 조합형 폰트를 위한 자모 데이터 + 배치 좌표 테이블.

핵심 아이디어
-------------
11,172자를 전부 손글씨로 받는 대신, "모양이 실제로 달라지는" 최소 단위만
손글씨로 받고 나머지는 좌표 기반으로 자동 조합한다.

- 초성(19개): 받침 유무(2) x 뒤에 오는 모음의 방향(3: 세로/가로/복합) 에 따라
  글자의 폭/위치가 크게 달라지므로 6가지 형태를 모두 받는다.  19 x 6 = 114
- 중성(21개): 받침 유무(2)에 따라 세로 길이가 달라지므로 2가지 형태를 받는다.
  21 x 2 = 42
- 종성/받침(27개): 항상 글자 하단의 같은 자리에만 오므로 형태 변화가 없다.
  1가지만 받는다.  27 x 1 = 27

합계 114 + 42 + 27 = 183개만 손글씨로 받으면, 11,172자 전체를 조합할 수 있다.

손글씨(컴포넌트)와 배치 좌표(zone)는 분리되어 있다
----------------------------------------------------
"어떤 손글씨를 쓸지"는 위처럼 큰 방향(V/H/C) 3종류만 받지만, "그걸 어디에
배치할지"는 그보다 더 세밀하게 조정할 수 있다. 같은 세로모음(V)이라도
ㅏ 뒤에 오는 초성과 ㅓ 뒤에 오는 초성은 위치가 아주 살짝 다를 수 있기
때문에, 배치 좌표만 9개 세부 그룹(V1/V2/V3, H1/H2/H3, C1/C2/C3)으로
나눠서 독립적으로 조정할 수 있게 했다. 즉:

- 손글씨(컴포넌트) 종류: V, H, C (3종류만 손으로 씀)
- 배치 좌표(zone) 종류: V1, V2, V3, H1, H2, H3, C1, C2, C3 (9종류, 좌표만 세밀 조정)

예를 들어 초성 ㄱ을 "세로모음(V)" 한 번만 쓰면, "가"(V1)와 "거"(V2)를 조합할
때 같은 ㄱ 손글씨를 재사용하되, 정확히 어느 위치/크기로 놓을지는
ZONE_LAYOUTS[(False,"V1")]와 ZONE_LAYOUTS[(False,"V2")]를 따로 조정해서
미세하게 다르게 만들 수 있다.

모음 세부 그룹 (9개, 배치 좌표 전용)
------------------------------------
- V1 (ㅏ계열): ㅏ ㅑ ㅐ ㅒ
- V2 (ㅓ계열): ㅓ ㅕ ㅔ ㅖ
- V3 (ㅣ계열): ㅣ
- H1 (ㅗ계열): ㅗ ㅛ
- H2 (ㅜ계열): ㅜ ㅠ
- H3 (ㅡ계열): ㅡ
- C1 (ㅘ계열): ㅘ ㅚ ㅙ
- C2 (ㅝ계열): ㅝ ㅟ ㅞ
- C3 (ㅢ계열): ㅢ
"""

# 유니코드 한글 자모 순서 (KS X 1001 / 완성형 인덱스 순서와 동일)
CHO_LIST = list("ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ")            # 19
JUNG_LIST = list("ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ")        # 21
JONG_LIST = list("ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ")  # 27 (받침 없음은 별도 처리)

assert len(CHO_LIST) == 19
assert len(JUNG_LIST) == 21
assert len(JONG_LIST) == 27

# 중성을 9개 "세부" 그룹으로 분류 (배치 좌표 전용, 손글씨 종류와는 무관)
VOWEL_GROUP = {
    "ㅏ": "V1", "ㅑ": "V1", "ㅐ": "V1", "ㅒ": "V1",
    "ㅓ": "V2", "ㅕ": "V2", "ㅔ": "V2", "ㅖ": "V2",
    "ㅣ": "V3",
    "ㅗ": "H1", "ㅛ": "H1",
    "ㅜ": "H2", "ㅠ": "H2",
    "ㅡ": "H3",
    "ㅘ": "C1", "ㅚ": "C1", "ㅙ": "C1",
    "ㅝ": "C2", "ㅟ": "C2", "ㅞ": "C2",
    "ㅢ": "C3",
}
assert set(VOWEL_GROUP) == set(JUNG_LIST)

# 세부 그룹 -> 상위(손글씨) 그룹 매핑 및 상위 그룹 -> 세부 그룹 목록
SUBGROUPS = {
    "V": ["V1", "V2", "V3"],
    "H": ["H1", "H2", "H3"],
    "C": ["C1", "C2", "C3"],
}
ALL_SUBGROUPS = [g for subs in SUBGROUPS.values() for g in subs]  # 9개

GROUP_MACRO = {sub: macro for macro, subs in SUBGROUPS.items() for sub in subs}

MACRO_LABEL = {"V": "세로모음", "H": "가로모음", "C": "복합모음"}
GROUP_LABEL = {
    "V1": "세로모음(ㅏ계열)", "V2": "세로모음(ㅓ계열)", "V3": "세로모음(ㅣ계열)",
    "H1": "가로모음(ㅗ계열)", "H2": "가로모음(ㅜ계열)", "H3": "가로모음(ㅡ계열)",
    "C1": "복합모음(ㅘ계열)", "C2": "복합모음(ㅝ계열)", "C3": "복합모음(ㅢ계열)",
}

# ────────────────────────────────────────────────────────────
# 조합 좌표(zone) 테이블
# UPM 1000x1000 정사각형 안에서, (받침유무, 모음 세부그룹) 조합마다
# 초성/중성/종성이 차지할 사각형 영역(x0,y0,x1,y1)을 정의한다.
# y=0이 베이스라인, y=1000이 글자 상단이다.
#
# 상위 그룹(V/H/C) 하나에 대해 좌표를 정의해두면, 그 안의 세부 그룹
# (예: V -> V1/V2/V3) 3개가 전부 같은 값으로 시작한다. 처음에는 같은
# 값이라도, 세부 그룹별로 ZONE_LAYOUTS[(batchim, "V1")] 처럼 따로 접근해서
# 독립적으로 조정할 수 있다 (예: V1과 V2만 미세하게 다르게 만들기).
# ────────────────────────────────────────────────────────────
_BASE_ZONE_LAYOUTS = {
    # 받침 없음 + 세로모음 (가, 나, 비...) : 좌우 배치
    (False, "V"): {
        "cho":  (100, 100, 450, 900),
        "jung": (400, 100, 900, 900),
        "jong": None,
    },
    # 받침 없음 + 가로모음 (고, 누, 드...) : 상하 배치
    (False, "H"): {
        "cho":  (200, 550, 800, 900),
        "jung": (100,   0, 900, 480),
        "jong": None,
    },
    # 받침 없음 + 복합모음 (과, 궈, 희...) : 초성은 좌상단, 모음이 아래+오른쪽 감쌈
    (False, "C"): {
        "cho":  (100, 550, 750, 900),
        "jung": (0,     0, 1000, 600),
        "jong": None,
    },
    # 받침 있음 + 세로모음 (각, 닫, 빛...)
    (True, "V"): {
        "cho":  (100, 550, 400, 1000),
        "jung": (400, 500, 1000, 1000),
        "jong": (100,  50, 900, 400),
    },
    # 받침 있음 + 가로모음 (곡, 녹, 숙...)
    (True, "H"): {
        "cho":  (0,   650, 1000, 1000),
        "jung": (100, 370, 900, 670),
        "jong": (150,   0, 1000, 350),
    },
    # 받침 있음 + 복합모음 (곽, 궐, 휙...)
    (True, "C"): {
        "cho":  (200, 700, 560, 1000),
        "jung": (200, 360, 800, 850),
        "jong": (200,   0, 900, 360),
    },
}

# 위 3그룹(V/H/C) 좌표를 9개 세부 그룹으로 그대로 복제해서 시작한다.
# (나중에 ZONE_LAYOUTS[(batchim, "V1")] 처럼 개별적으로 덮어써서 세밀 조정 가능)
ZONE_LAYOUTS = {}
for (_batchim, _macro), _layout in _BASE_ZONE_LAYOUTS.items():
    for _sub in SUBGROUPS[_macro]:
        ZONE_LAYOUTS[(_batchim, _sub)] = dict(_layout)


# ────────────────────────────────────────────────────────────
# 자모별 미세 보정 테이블 (선택 사항, 기본값은 "보정 없음")
#
# compose.py는 기본적으로 각 자모의 실제 손글씨 크기(bounding box)를
# 원본 비율 그대로 유지한 채(찌그러지지 않게) zone 안에 맞추고 중앙
# 정렬한다. 이것만으로도 대부분 자연스럽지만, 손글씨 특성상 어떤 자모는
# 상대적으로 작아 보이거나(예: ㄱ, ㅣ) 커 보일 수 있다(예: ㅁ, ㅇ). 그럴
# 때 아래 표의 숫자만 조정하면 해당 자모만 살짝 키우거나/줄이거나
# 위치를 옮길 수 있다 (다른 코드는 안 건드려도 됨).
#
# COMPONENT_SCALE/COMPONENT_OFFSET의 키는 (kind, jamo) 튜플이다.
# 예: ("cho","ㅇ")과 ("jong","ㅇ")은 서로 다른 손글씨 조각(초성 ㅇ vs
# 받침 ㅇ)이므로 따로따로 보정할 수 있다.
# ────────────────────────────────────────────────────────────

# 초성/중성/종성 유형별 기본 배율 (전체적인 균형 조절용)
KIND_SCALE = {
    "cho": 1.0,
    "jung": 1.0,
    "jong": 1.0,
}

# 특정 (종류, 자모)별 배율 보정. 실제로 폰트를 뽑아보고 특정 자모가
# 너무 작거나 커 보이면 여기에 추가하면 된다. 예:
#   COMPONENT_SCALE = {("cho", "ㅇ"): 1.08, ("jong", "ㄹ"): 0.95}
COMPONENT_SCALE = {}

# 특정 (종류, 자모)별 위치 보정 (dx, dy), 폰트 유닛(UPM=1000) 기준. 예:
#   COMPONENT_OFFSET = {("cho", "ㅊ"): (0, -15)}
COMPONENT_OFFSET = {}


def get_component_scale(kind, jamo):
    return COMPONENT_SCALE.get((kind, jamo), 1.0)


def get_component_offset(kind, jamo):
    return COMPONENT_OFFSET.get((kind, jamo), (0, 0))


# ────────────────────────────────────────────────────────────
# 단독 자모("ㄱ", "ㅏ" 등 조합되지 않은 낱자) 표시 크기 조정
#
# 기본값(None)일 때는 그 자모가 "실제 음절 조합에 쓰일 때 차지하는 높이"를
# 그대로 재사용한다 (예: 단독 ㄱ = "가"에서 ㄱ이 차지하는 만큼의 크기).
# 숫자를 넣으면(폰트 유닛, UPM=1000 기준) 해당 종류(초성/중성/종성)의
# 단독 표시 높이가 항상 그 값으로 고정된다.
#
# 예: 단독으로 쓴 초성(ㄱ,ㄴ,ㄷ...)이 너무 크게 느껴지고, 조합 글자 속
# 자음의 평균적인 크기(예: 350) 정도가 더 자연스럽다면 아래처럼 바꾸면 된다.
#   STANDALONE_HEIGHT_OVERRIDE["cho"] = 350
# 중성(모음)은 그대로 두고 싶으면 "jung"은 None으로 유지하면 된다.
# ────────────────────────────────────────────────────────────
STANDALONE_HEIGHT_OVERRIDE = {
    "cho": None,
    "jung": None,
    "jong": None,
}


def component_id(kind, jamo, batchim=None, group=None):
    """
    컴포넌트(손글씨 조각)를 유일하게 식별하는 문자열 id를 만든다.
    cho의 group은 항상 상위 그룹(V/H/C)이어야 한다 - 손글씨는 3종류만
    받기 때문. 세부 그룹(V1 등)은 zone 좌표를 찾을 때만 쓴다.
    """
    if kind == "cho":
        b = "B" if batchim else "N"
        return f"cho_{jamo}_{b}_{group}"
    if kind == "jung":
        b = "B" if batchim else "N"
        return f"jung_{jamo}_{b}"
    if kind == "jong":
        return f"jong_{jamo}"
    raise ValueError(kind)


def compose_char(cho, jung, jong=None):
    """초/중/종성 자모로부터 실제 완성형 한글 한 글자를 조합한다 (예시 표시용)."""
    ci = CHO_LIST.index(cho)
    vi = JUNG_LIST.index(jung)
    ji = (JONG_LIST.index(jong) + 1) if jong else 0
    code = 0xAC00 + (ci * 21 + vi) * 28 + ji
    return chr(code)


def decompose_code(code):
    """완성형 한글 코드포인트(0xAC00~0xD7A3) -> (초성, 중성, 종성 or None)."""
    s_index = code - 0xAC00
    ci = s_index // (21 * 28)
    vi = (s_index % (21 * 28)) // 28
    ji = s_index % 28

    cho = CHO_LIST[ci]
    jung = JUNG_LIST[vi]
    jong = JONG_LIST[ji - 1] if ji > 0 else None
    return cho, jung, jong


def _example_for_cho(cho, batchim, macro):
    # 이 상위 그룹(macro)에 속하는 세부 그룹 중 아무 모음이나 하나로 예시를 만든다.
    jung = next(v for v, g in VOWEL_GROUP.items() if GROUP_MACRO[g] == macro)
    jong = JONG_LIST[0] if batchim else None
    return compose_char(cho, jung, jong)


def _example_for_jung(jung, batchim):
    jong = JONG_LIST[0] if batchim else None
    return compose_char("ㄱ", jung, jong)


def _example_for_jong(jong):
    return compose_char("ㄱ", "ㅏ", jong)


def build_component_list():
    """
    손글씨로 받아야 할 183개 컴포넌트 목록을 순서대로 만든다.
    이 순서가 곧 템플릿 칸 순서 = data/glyphs 안 PNG 인덱스 순서가 된다.
    """
    components = []

    for cho in CHO_LIST:
        for batchim in (False, True):
            for macro in ("V", "H", "C"):
                # 이 컴포넌트가 실제로 쓰일 대표 예시(및 zone) 선택: 해당
                # 상위 그룹의 첫 번째 세부 그룹을 기준으로 안내 상자를 그린다.
                # (watermark/guide box는 이 예시 하나로 표시되지만, 실제
                # 조합 시에는 각 세부 그룹의 정확한 zone이 개별 적용된다)
                example = _example_for_cho(cho, batchim, macro)
                example_cho, example_jung, example_jong = decompose_code(ord(example))
                fine_group = VOWEL_GROUP[example_jung]

                components.append({
                    "id": component_id("cho", cho, batchim, macro),
                    "kind": "cho",
                    "jamo": cho,
                    "batchim": batchim,
                    "group": macro,
                    "label": f"초성 {cho} · {'받침있음' if batchim else '받침없음'} · {MACRO_LABEL[macro]}",
                    "example": example,
                    "zone_shape": ZONE_LAYOUTS[(batchim, fine_group)]["cho"],
                })

    for jung in JUNG_LIST:
        for batchim in (False, True):
            fine_group = VOWEL_GROUP[jung]
            components.append({
                "id": component_id("jung", jung, batchim),
                "kind": "jung",
                "jamo": jung,
                "batchim": batchim,
                "group": None,
                "label": f"중성 {jung} · {'받침있음' if batchim else '받침없음'}",
                "example": _example_for_jung(jung, batchim),
                "zone_shape": ZONE_LAYOUTS[(batchim, fine_group)]["jung"],
            })

    for jong in JONG_LIST:
        components.append({
            "id": component_id("jong", jong),
            "kind": "jong",
            "jamo": jong,
            "batchim": True,
            "group": None,
            "label": f"종성(받침) {jong}",
            "example": _example_for_jong(jong),
            "zone_shape": (0, 0, 1000, 280),  # 임의의 받침 zone 하나 기준 (안내용)
        })

    return components


# ────────────────────────────────────────────────────────────
# 단독 자모(조합되지 않은 낱자) 지원
#
# "ㄱ", "ㅏ" 처럼 완성형 음절이 아니라 낱자 하나만 입력해도 폰트가
# 적용되도록, 각 자모마다 대표로 쓸 컴포넌트를 하나씩 지정한다.
# - 초성 목록에 있는 자모(ㄱ,ㄴ,ㄷ... 19개)는 "받침없음 + 세로모음(V)"
#   초성 컴포넌트를 대표로 쓴다 (가장 기본적인/친숙한 형태).
# - 중성(모음, 21개)은 "받침없음" 중성 컴포넌트를 대표로 쓴다.
# - 종성에만 있는 겹받침(ㄳ,ㄵ,ㄶ,ㄺ,ㄻ,ㄼ,ㄽ,ㄾ,ㄿ,ㅀ,ㅄ)은 종성
#   컴포넌트를 그대로 쓴다 (이 자모들은 초성으로 쓰이지 않기 때문).
# ────────────────────────────────────────────────────────────
STANDALONE_REPRESENTATIVE_GROUP = "V"


def build_standalone_jamo_list():
    """
    단독 자모 51개(초성 19 + 종성전용 겹받침 11 + 중성 21) 각각에 대해
    (유니코드 코드포인트, 대표 컴포넌트 id)를 반환한다.
    """
    entries = []
    seen = set()

    for cho in CHO_LIST:
        comp_id = component_id("cho", cho, False, STANDALONE_REPRESENTATIVE_GROUP)
        entries.append((ord(cho), comp_id))
        seen.add(cho)

    for jong in JONG_LIST:
        if jong in seen:
            continue  # 이미 초성으로 등록됨 (같은 코드포인트)
        comp_id = component_id("jong", jong)
        entries.append((ord(jong), comp_id))
        seen.add(jong)

    for jung in JUNG_LIST:
        comp_id = component_id("jung", jung, False)
        entries.append((ord(jung), comp_id))

    return entries

~~~

### kerning.py

~~~py
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

RASTER_ROWS = 40          # 프로파일 샘플링 해상도 (세로 방향)
MIN_KERN_UNITS = 15       # 이보다 작은 보정은 무시 (피처 용량 절약, 육안으로도 티 안 남)
MAX_KERN_RATIO = 0.35     # advance width 대비 최대 보정 비율 (너무 큰 보정 방지)
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
            limit = advanceL * MAX_KERN_RATIO
            kern = max(-limit, min(limit, kern))
            kern = round(kern)

            if abs(kern) >= MIN_KERN_UNITS:
                lines.append(f"    pos {nameL} {nameR} {kern};")

    if not lines:
        return 0

    fea = "feature kern {\n" + "\n".join(lines) + "\n} kern;\n"
    addOpenTypeFeaturesFromString(font, fea)
    return len(lines)

~~~

### latin.py

~~~py
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
TARGET_CAP_HEIGHT = 780

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

~~~

### preprocess.py

~~~py
import cv2
import numpy as np

from config import GUIDE_STRIP_THRESHOLD


def order_points(pts):
    pts = np.array(pts, dtype="float32")

    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)

    return np.array([
        pts[np.argmin(s)],      # 좌상
        pts[np.argmin(diff)],   # 우상
        pts[np.argmax(s)],      # 우하
        pts[np.argmax(diff)],   # 좌하
    ], dtype="float32")


def four_point_transform(image, pts):
    rect = order_points(pts)
    tl, tr, br, bl = rect

    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxWidth = int(max(widthA, widthB))

    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxHeight = int(max(heightA, heightB))

    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1],
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)

    return cv2.warpPerspective(image, M, (maxWidth, maxHeight))


def detect_page(image):
    """용지(문서) 외곽 4개 꼭짓점을 찾는다. 못 찾으면 None."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edge = cv2.Canny(blur, 75, 200)

    # 경계선이 끊어져 있으면 4각형 검출이 잘 안 되므로 살짝 팽창시켜 연결한다.
    edge = cv2.dilate(edge, np.ones((3, 3), np.uint8), iterations=1)

    contours, _ = cv2.findContours(
        edge, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
    )
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    image_area = image.shape[0] * image.shape[1]

    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        # 문서 검출이 너무 작은 잡음 컨투어를 잡지 않도록 최소 면적 제한을 둔다.
        if len(approx) == 4 and cv2.contourArea(approx) > image_area * 0.2:
            return approx.reshape(4, 2)

    return None


def preprocess(path):
    image = cv2.imread(path)

    if image is None:
        raise FileNotFoundError(f"이미지를 열 수 없습니다: {path}")

    pts = detect_page(image)

    if pts is not None:
        image = four_point_transform(image, pts)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 스캔/사진 촬영 시 생기는 잡음 제거
    gray = cv2.medianBlur(gray, 3)

    # 템플릿에 연한 회색으로 인쇄된 안내선/번호/예시 글자를 자동으로 지운다.
    # (GUIDE_STRIP_THRESHOLD보다 밝은 픽셀은 전부 흰색 배경으로 처리.
    #  실제 손글씨 잉크는 이보다 훨씬 어두우므로 영향받지 않는다)
    gray = gray.copy()
    gray[gray > GUIDE_STRIP_THRESHOLD] = 255

    bw = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        10,
    )

    return bw

~~~

### segment.py

~~~py
import json
import os
from pathlib import Path

import cv2
import numpy as np

from config import (
    ROWS, COLS, GLYPH_SIZE, TARGET_HEIGHT, BASELINE_MARGIN,
    STROKE_NORMALIZE, TARGET_STROKE_PX,
    STROKE_MAX_KERNEL_RADIUS, STROKE_MIN_AREA_RATIO, STROKE_MAX_ITERATIONS,
)

CELLS_PER_PAGE = ROWS * COLS


def _inset(cell, margin_ratio=0.12):
    """
    칸의 테두리 선(원고지 격자선) 자체가 글자로 오인식되는 것을 막기 위해
    칸 가장자리를 안쪽으로 살짝 잘라낸다.
    """
    h, w = cell.shape
    my = int(h * margin_ratio)
    mx = int(w * margin_ratio)
    if h - 2 * my <= 0 or w - 2 * mx <= 0:
        return cell
    return cell[my:h - my, mx:w - mx]


def has_content(cell, min_pixels=15):
    """칸 안에 글자가 실제로 쓰여 있는지 확인 (빈 칸 자동 스킵용)."""
    inner = _inset(cell)
    inv = 255 - inner
    return cv2.countNonZero(inv) > min_pixels


def crop_content(cell):
    """칸 안에서 실제 잉크 영역만 바운딩 박스로 잘라낸다."""
    inner = _inset(cell)
    inv = 255 - inner
    pts = cv2.findNonZero(inv)

    if pts is None:
        return None

    x, y, w, h = cv2.boundingRect(pts)
    return inner[y:y + h, x:x + w]


def _estimate_stroke_width(ink_mask):
    """
    전체 잉크 영역과 둘레 길이로 평균 획 굵기를 추정한다.

    가늘고 긴 직사각형이라고 가정하면 area ≈ width * length,
    perimeter ≈ 2 * length 이므로 width ≈ 2 * area / perimeter 로 근사할
    수 있다 (스켈레톤 추출 없이 빠르게 계산 가능한 표준적인 근사법).
    """
    contours, _ = cv2.findContours(ink_mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    area = cv2.countNonZero(ink_mask)
    perimeter = sum(cv2.arcLength(c, True) for c in contours)
    if perimeter <= 0:
        return 0
    return 2 * area / perimeter


def normalize_stroke_width(
    img,
    target_width=TARGET_STROKE_PX,
    max_kernel_radius=STROKE_MAX_KERNEL_RADIUS,
    min_area_ratio=STROKE_MIN_AREA_RATIO,
    max_iterations=STROKE_MAX_ITERATIONS,
):
    """
    모든 글자의 획 굵기가 서로 비슷해지도록 팽창(dilate)/침식(erode)으로
    보정한다.

    왜 필요한가: 벡터 도형을 확대/축소하면 획 굵기도 같이 확대/축소된다.
    한글은 자모마다 목표 높이(TARGET_HEIGHT)에 맞춰 강제로 확대/축소되고,
    라틴 문자는 사용자가 쓴 크기 그대로 들어가기 때문에, 아무 보정 없이는
    자모/문자마다 최종 획 굵기가 들쭉날쭉해진다.

    안전하게 보정하는 이유: 굵기 추정치(면적/둘레 비율)는 완벽하지 않다.
    특히 ㄲ,ㄸ처럼 여러 획이 겹치거나 꺾이는 부분이 많은 복잡한 모양은
    실제보다 두껍게 추정되기 쉬운데, 이 추정치를 과신해서 한 번에 크게
    깎아버리면 받침처럼 얇은 부분이 통째로 사라질 수 있다. 그래서
    - 한 번에 깎거나 붙이는 양을 max_kernel_radius로 제한하고,
    - 여러 번에 걸쳐 조금씩(다시 측정하면서) 목표에 다가가고,
    - 침식으로 잉크 면적이 min_area_ratio 밑으로 떨어지면 그 단계는
      즉시 취소한다(그 이전 상태를 그대로 유지).
    """
    if not STROKE_NORMALIZE:
        return img

    original_area = cv2.countNonZero(255 - img)
    if original_area == 0:
        return img

    current = img

    for _ in range(max_iterations):
        inv = 255 - current
        current_width = _estimate_stroke_width(inv)
        if current_width <= 1:
            break

        delta = (target_width - current_width) / 2  # 반지름 기준 보정량
        k = min(int(round(abs(delta))), max_kernel_radius)
        if k < 1:
            break

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k * 2 + 1, k * 2 + 1))

        if delta > 0:
            candidate = cv2.dilate(inv, kernel)
        else:
            candidate = cv2.erode(inv, kernel)
            if cv2.countNonZero(candidate) / original_area < min_area_ratio:
                break  # 더 깎으면 위험하니 여기서 멈추고 직전 상태를 유지

        current = 255 - candidate

    return current


def normalize_glyph(
    glyph,
    canvas_size=GLYPH_SIZE,
    target_height=TARGET_HEIGHT,
    baseline_margin=BASELINE_MARGIN,
):
    """
    비율을 유지한 채 글자 높이를 target_height 로 맞추고, 모든 글자의 밑변이
    같은 baseline 위에 놓이도록 정렬한 뒤 canvas_size 정사각형에 배치한다.
    """
    h, w = glyph.shape
    if h == 0 or w == 0:
        return None

    scale = target_height / h
    new_w = max(1, round(w * scale))
    new_h = max(1, round(h * scale))

    max_w = canvas_size - 2
    if new_w > max_w:
        scale *= max_w / new_w
        new_w = max(1, round(w * scale))
        new_h = max(1, round(h * scale))

    resized = cv2.resize(glyph, (new_w, new_h), interpolation=cv2.INTER_AREA)

    canvas = np.full((canvas_size, canvas_size), 255, dtype=np.uint8)

    x_offset = (canvas_size - new_w) // 2
    y_offset = canvas_size - baseline_margin - new_h

    x_offset = max(0, min(x_offset, canvas_size - new_w))
    y_offset = max(0, min(y_offset, canvas_size - new_h))

    canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

    return normalize_stroke_width(canvas)


def _extract_cell(image, r, col):
    h, w = image.shape
    cell_w = w // COLS
    cell_h = h // ROWS
    x = col * cell_w
    y = r * cell_h
    return image[y:y + cell_h, x:x + cell_w]


def normalize_latin_cell(cell, canvas_size=GLYPH_SIZE, margin_ratio=0.12):
    """
    라틴 문자(영문/숫자/특수문자)용 정규화.

    한글용 normalize_glyph()와 달리 '내용 기준으로 잘라서 baseline에 재정렬'
    하지 않는다. g,y,p 같은 내림선 글자의 baseline 위치 정보를 유지해야
    하기 때문에, 칸에서 테두리만 제거(inset)한 뒤 있는 그대로 정사각형
    캔버스로 리사이즈한다. (baseline의 실제 위치는 modules/latin.py의
    BASELINE_RATIO 와, 이 칸에 인쇄된 안내선이 서로 맞아떨어진다고 가정한다)

    전체적인 크기(대문자 기준 높이) 보정은 여기서 하지 않고
    modules/latin.py의 build_latin_glyphs()에서 폰트 좌표계로 변환한 뒤
    한 번에 처리한다 (모든 라틴 글자에 같은 배율을 적용해야 서로 비율이
    안 흐트러지기 때문).
    """
    inner = _inset(cell, margin_ratio=margin_ratio)
    if inner.shape[0] == 0 or inner.shape[1] == 0:
        return None
    resized = cv2.resize(inner, (canvas_size, canvas_size), interpolation=cv2.INTER_AREA)
    return normalize_stroke_width(resized)


def segment(images, output_dir="data/glyphs", manifest_path="data/manifest.json"):
    """
    images: 전처리된(이진화된) 페이지 이미지 리스트. 1페이지짜리 스캔이면
            images=[img] 처럼 리스트로 넘기면 된다. (기존 단일 이미지 인자와의
            호환을 위해 images가 단일 ndarray로 오면 자동으로 리스트로 감싼다.)
    """
    if isinstance(images, np.ndarray):
        images = [images]

    os.makedirs(output_dir, exist_ok=True)

    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    total = len(manifest)

    idx = 0
    saved = 0

    for page_no, image in enumerate(images):
        for r in range(ROWS):
            for c in range(COLS):
                if idx >= total:
                    break

                cell = _extract_cell(image, r, c)

                if not has_content(cell):
                    idx += 1
                    continue

                kind = manifest[idx]["kind"]

                if kind == "latin":
                    glyph = normalize_latin_cell(cell)
                else:
                    glyph = crop_content(cell)
                    if glyph is not None:
                        glyph = normalize_glyph(glyph)

                if glyph is None:
                    idx += 1
                    continue

                cv2.imwrite(f"{output_dir}/{idx:03}.png", glyph)
                saved += 1
                idx += 1

            if idx >= total:
                break

        if idx >= total:
            break

    print(f"{saved}개의 컴포넌트 저장 완료 (총 {total}개 중, {len(images)}페이지 처리)")
    if saved < total:
        missing = total - saved
        print(f"주의: {missing}개 칸이 비어 있거나 인식되지 않았습니다. "
              f"해당 칸은 합성 시 자동으로 제외됩니다 (범례로 어떤 칸인지 확인하세요).")

~~~

### template.py

~~~py
import json
import math
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from PIL import Image, ImageDraw

from config import ROWS, COLS, CELL_SIZE, PAGE_MARGIN, GUIDE_GRAY
from modules.hangul import (
    build_component_list as build_hangul_components,
    decompose_code,
    ZONE_LAYOUTS,
    VOWEL_GROUP,
)
from modules.latin import build_component_list as build_latin_components, BASELINE_RATIO

# ReportLab 내장 CJK 폰트 (별도 폰트 파일 없이 한글을 그릴 수 있다)
KOREAN_FONT = "HYSMyeongJo-Medium"
pdfmetrics.registerFont(UnicodeCIDFont(KOREAN_FONT))

CELL = CELL_SIZE * mm
LEFT = PAGE_MARGIN * mm
TOP = PAGE_MARGIN * mm

CELLS_PER_PAGE = ROWS * COLS


# ────────────────────────────────────────────────────────────
# 가이드(안내선) 관련 요소는 전부 연한 회색(GUIDE_GRAY)으로 그린다.
# 종이에서 눈으로 보기엔 충분히 진하지만, 전처리 단계에서 자동으로
# 지워질 만큼은 연하다 (config.GUIDE_STRIP_THRESHOLD 참고).
# 칸을 나누는 실제 테두리(격자선)만 검정으로 남겨서 segment.py가
# 칸을 나눌 때 기준으로 쓸 수 있게 한다.
# ────────────────────────────────────────────────────────────

def _zone_to_rect(x, y, cell, zone_shape, pad_ratio=0.12):
    """
    자모 하나가 차지하는 zone(0~1000 정사각형 기준 x0,y0,x1,y1)을,
    실제 칸(cell) 안에서 그 zone이 있어야 할 절대 위치/크기로 변환한다.

    중요: 이 함수 하나로 안내 상자(_draw_guide_box)와 예시 워터마크
    (_draw_hangul_watermark)를 둘 다 계산해야, 두 가지가 항상 정확히
    같은 위치를 가리킨다. (이전 버전은 워터마크를 폰트가 자체적으로
    조합한 위치에 그리고, 안내 상자는 우리 zone 좌표로 따로 그려서
    서로 안 맞는 문제가 있었다)
    """
    x0, y0, x1, y1 = zone_shape
    pad = cell * pad_ratio
    avail = cell - 2 * pad
    scale = avail / 1000

    bx = x + pad + x0 * scale
    by = (y - cell) + pad + y0 * scale
    bw = (x1 - x0) * scale
    bh = (y1 - y0) * scale
    return bx, by, bw, bh


def _draw_jamo_in_zone(c, x, y, cell, zone_shape, ch, gray=GUIDE_GRAY):
    """zone 위치/크기에 맞춰 자모 하나를 연한 회색으로 그린다."""
    bx, by, bw, bh = _zone_to_rect(x, y, cell, zone_shape)
    fs = min(bw, bh) * 0.92

    c.setFont(KOREAN_FONT, fs)
    c.setFillGray(gray)
    c.drawCentredString(bx + bw / 2, by + bh * 0.12, ch)
    c.setFillGray(0)


def _draw_hangul_watermark(c, x, y, cell, comp):
    """
    실제 예시 음절("가", "곽" 등)을 우리 zone 좌표계 그대로 초성/중성/(종성)
    각각의 위치에 나눠 그린다. _draw_guide_box와 정확히 같은 zone 좌표를
    쓰기 때문에, 점선/실선 안내 상자가 항상 워터마크의 해당 부분과
    정확히 겹친다 - 즉 "점선 박스 안 = 워터마크에서 내가 써야 할 자모가
    있는 자리"가 항상 성립한다.
    """
    cho, jung, jong = decompose_code(ord(comp["example"]))
    group = VOWEL_GROUP[jung]
    has_batchim = jong is not None
    layout = ZONE_LAYOUTS[(has_batchim, group)]

    _draw_jamo_in_zone(c, x, y, cell, layout["cho"], cho)
    _draw_jamo_in_zone(c, x, y, cell, layout["jung"], jung)
    if has_batchim:
        _draw_jamo_in_zone(c, x, y, cell, layout["jong"], jong)


def _draw_guide_box(c, x, y, cell, zone_shape):
    """
    이 칸에서 실제로 손글씨를 써야 할 영역(=워터마크에서 해당 자모가
    있는 자리와 정확히 같은 자리)에 안내 상자를 그린다. 이 상자 밖으로
    나가면 조합했을 때 옆 자모와 겹칠 수 있으니, 상자 = 실제 쓰기
    한계선이라고 생각하면 된다.
    """
    bx, by, bw, bh = _zone_to_rect(x, y, cell, zone_shape)

    c.setStrokeGray(GUIDE_GRAY)
    c.setLineWidth(0.8)
    c.setDash(2, 2)
    c.rect(bx, by, bw, bh)
    c.setDash()
    c.setStrokeGray(0)


def _draw_latin_guide(c, x, y, cell):
    """
    라틴 문자용 안내.

    실선 상자 = 실제로 쓸 수 있는 전체 높이(위쪽 끝=ascender, 아래쪽
    끝=descender). 이 상자를 벗어나면 글자가 잘린다.
    상자 안의 굵은 가로선 = baseline. 대부분의 글자는 이 선 위에 앉고,
    g, y, p, q, j 처럼 아래로 내려가는 글자만 이 선 아래 (상자 하단까지)
    내려가면 된다.
    """
    pad = cell * 0.12
    left = x + pad
    right = x + cell - pad
    top = y - pad
    bottom = y - cell + pad
    height_inner = top - bottom

    c.setStrokeGray(GUIDE_GRAY)

    # 실선 상자 = ascender ~ descender 전체 한계선
    c.setLineWidth(0.7)
    c.rect(left, bottom, right - left, height_inner)

    # baseline 안내선
    baseline_y = top - BASELINE_RATIO * height_inner
    c.setLineWidth(1.0)
    c.line(left, baseline_y, right, baseline_y)

    c.setStrokeGray(0)


def _draw_cell(c, x, y, cell, idx, comp):
    if comp["kind"] == "latin":
        _draw_latin_guide(c, x, y, cell)
    else:
        _draw_hangul_watermark(c, x, y, cell, comp)

    # 칸 테두리(격자선)는 검정 실선으로 유지 - segment.py가 칸을 나누는 기준.
    c.setStrokeGray(0)
    c.setLineWidth(0.8)
    c.rect(x, y - cell, cell, cell)

    if comp["kind"] != "latin":
        _draw_guide_box(c, x, y, cell, comp["zone_shape"])

    # 좌상단: 인덱스 번호 (연한 회색 - 안내용, 자동으로 지워짐)
    c.setFont("Helvetica", 6)
    c.setFillGray(GUIDE_GRAY)
    c.drawString(x + 1.5, y - 7, f"{idx:03}")

    # 라틴 칸은 우하단에 어떤 글자인지 작게 표시 (한글은 위 워터마크로 대체)
    if comp["kind"] == "latin":
        c.setFont(KOREAN_FONT, 7)
        c.drawRightString(x + cell - 2, y - cell + 2, comp["example"])

    c.setFillGray(0)


def create_template(filename="output/template.pdf", manifest_path="data/manifest.json"):
    components = build_hangul_components() + build_latin_components()

    Path(manifest_path).parent.mkdir(parents=True, exist_ok=True)
    Path(manifest_path).write_text(
        json.dumps(components, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    n_pages = math.ceil(len(components) / CELLS_PER_PAGE)

    idx = 0
    for page in range(n_pages):
        c.setFont(KOREAN_FONT, 9)
        c.drawString(LEFT, height - TOP + 5 * mm,
                     f"손글씨 폰트 원고지  ({page + 1}/{n_pages} 페이지, "
                     f"{idx}~{min(idx + CELLS_PER_PAGE, len(components)) - 1}번)")
        c.setFont(KOREAN_FONT, 7)
        c.drawString(LEFT, height - TOP + 1.5 * mm,
                     "연한 회색은 전부 자동으로 지워집니다. 점선/실선 상자 = 워터마크에서 "
                     "내가 써야 할 자모가 있는 자리와 정확히 같은 위치입니다. 그 안에만 쓰세요.")

        for r in range(ROWS):
            for col in range(COLS):
                x = LEFT + col * CELL
                y = height - TOP - r * CELL

                if idx < len(components):
                    _draw_cell(c, x, y, CELL, idx, components[idx])
                else:
                    # 마지막 페이지에서 칸이 남으면 빈 테두리만 그린다.
                    # (페이지마다 항상 ROWS x COLS 격자 전체를 인쇄해야
                    #  스캔한 사진에서 칸을 나눌 때 격자가 일정하게 유지된다)
                    c.setStrokeGray(0)
                    c.setLineWidth(0.8)
                    c.rect(x, y - CELL, CELL, CELL)

                idx += 1

        c.showPage()

    # ── 범례 페이지: 인덱스 -> 자모/설명/예시 전체 목록 ──
    line_h = 4.2 * mm
    lines_per_page = int((height - 2 * TOP) / line_h)

    for start in range(0, len(components), lines_per_page):
        c.setFont(KOREAN_FONT, 10)
        c.drawString(LEFT, height - TOP, "범례 (칸 번호 -> 어떤 자모를 써야 하는지)")

        yy = height - TOP - 8 * mm
        for i in range(start, min(start + lines_per_page, len(components))):
            comp = components[i]
            c.setFont(KOREAN_FONT, 8)
            c.drawString(
                LEFT, yy,
                f"{i:03}  {comp['label']}   (예시: {comp['example']})"
            )
            yy -= line_h

        c.showPage()

    c.save()
    print(f"{filename} 생성 완료 ({n_pages}장 원고지 + 범례). "
          f"컴포넌트 목록은 {manifest_path} 에 저장됨.")
    return components, n_pages


def create_grid_overlay(n_pages, output_dir="output", dpi=300):
    """
    (선택 기능) 격자선(칸 테두리)만 있는 투명 배경 PNG를 페이지별로 만든다.

    가이드 자동 제거 기능으로 보통은 필요 없지만, 직접 스캔 이미지에서
    가이드를 수동으로 지운 뒤 이 격자와 합성해서 쓰고 싶은 경우를 위한
    보조 파일이다. template.py가 실제 PDF에 그리는 격자와 동일한 비율로
    그려진다 (A4, PAGE_MARGIN/CELL_SIZE 기준).
    """
    from reportlab.lib.pagesizes import A4 as _A4
    width_pt, height_pt = _A4
    px_per_pt = dpi / 72

    W = int(width_pt * px_per_pt)
    H = int(height_pt * px_per_pt)
    left = LEFT * px_per_pt
    top = TOP * px_per_pt
    cell = CELL * px_per_pt

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    paths = []

    for page in range(n_pages):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        for r in range(ROWS):
            for col in range(COLS):
                x = left + col * cell
                y = top + r * cell
                draw.rectangle(
                    [x, y, x + cell, y + cell],
                    outline=(0, 0, 0, 255), width=2
                )

        path = f"{output_dir}/grid_overlay_page{page + 1}.png"
        img.save(path)
        paths.append(path)

    print(f"격자 전용 투명 PNG {len(paths)}장 생성 완료: {', '.join(paths)}")
    return paths

~~~

### vectorize.py

~~~py
import cv2
import numpy as np
from pathlib import Path

from config import APPROX_EPSILON


def find_contours_with_holes(img):
    """
    바깥 윤곽선뿐 아니라 안쪽 구멍(ㅇ,ㅎ,ㅁ,ㅂ 등의 속이 빈 부분)까지 찾는다.

    기존 코드는 cv2.RETR_EXTERNAL 을 사용했는데, 이 모드는 가장 바깥
    윤곽선만 반환하기 때문에 "ㅇ"이 속이 꽉 찬 "●"으로 만들어지는
    문제가 있었다. RETR_TREE + hierarchy 를 사용해야 안쪽 구멍을
    별도 contour로 받아올 수 있다.

    반환값:
        contours  : contour 리스트
        hierarchy : 각 contour의 [next, prev, first_child, parent] (N,4) 배열
                    hierarchy[i][3] != -1 이면 i번째 contour는 "구멍"이다.
    """
    binary = 255 - img  # 흰색=배경 -> 0, 검은색(글자)=255 로 반전

    contours, hierarchy = cv2.findContours(
        binary,
        cv2.RETR_TREE,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    if hierarchy is None:
        return [], np.zeros((0, 4), dtype=int)

    return contours, hierarchy[0]  # cv2가 (1, N, 4) 형태로 주므로 [0]


def simplify(contour, epsilon=APPROX_EPSILON):
    """점 개수를 줄여 다각형을 단순화한다 (곡선화 이전 전처리)."""
    return cv2.approxPolyDP(contour, epsilon, True)


def signed_area(pts):
    """Shoelace 공식. y축이 위로 향하는(y-up) 좌표계 기준 부호 있는 면적."""
    pts = np.asarray(pts, dtype=np.float64)
    x = pts[:, 0]
    y = pts[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)


def fix_winding(pts, is_hole):
    """
    TrueType(glyf) 규칙:
      - 바깥 윤곽선은 시계방향(CW)  -> signed_area < 0
      - 안쪽 구멍(hole)은 반시계방향(CCW) -> signed_area > 0
    이 규칙과 반대로 감겨 있으면 점 순서를 뒤집어 바로잡는다.
    이 처리를 안 하면 구멍이 안 뚫리거나, 반대로 바깥 윤곽선이
    구멍 취급되어 글자가 통째로 사라질 수 있다.
    """
    pts = np.asarray(pts, dtype=np.float64)
    area = signed_area(pts)

    should_be_positive = is_hole

    if should_be_positive and area < 0:
        pts = pts[::-1]
    elif not should_be_positive and area > 0:
        pts = pts[::-1]

    return pts


# ── 아래는 디버그/미리보기용 SVG 출력 (폰트 생성 파이프라인 필수 요소는 아님) ──

def contours_to_svg_path(contours, hierarchy):
    """holes를 포함한 여러 contour를 하나의 SVG path data로 합친다 (fill-rule=evenodd 사용)."""
    path = ""

    for contour in contours:
        pts = contour.squeeze()
        if pts.ndim != 2 or len(pts) < 2:
            continue

        path += "M " + " ".join(f"{x},{y}" for x, y in pts) + " Z "

    return path.strip()


def save_svg(path_data, filename, size=800):
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
<path d="{path_data}" fill="black" fill-rule="evenodd"/>
</svg>
'''
    with open(filename, "w") as f:
        f.write(svg)


def convert_folder(glyph_dir="data/glyphs", svg_dir="data/svg"):
    """data/glyphs 의 모든 PNG를 미리보기용 SVG로 변환한다 (디버깅용)."""
    Path(svg_dir).mkdir(parents=True, exist_ok=True)

    count = 0
    for file in sorted(Path(glyph_dir).glob("*.png")):
        img = cv2.imread(str(file), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue

        contours, hierarchy = find_contours_with_holes(img)
        if len(contours) == 0:
            continue

        simplified = [simplify(c) for c in contours]
        path = contours_to_svg_path(simplified, hierarchy)

        save_svg(path, f"{svg_dir}/{file.stem}.svg")
        count += 1

    print(f"SVG {count}개 생성 완료")

~~~

# /fontMaker/data

### manifest.json

~~~json
[
  {
    "id": "cho_ㄱ_N_V",
    "kind": "cho",
    "jamo": "ㄱ",
    "batchim": false,
    "group": "V",
    "label": "초성 ㄱ · 받침없음 · 세로모음",
    "example": "가",
    "zone_shape": [
      100,
      100,
      450,
      900
    ]
  },
  {
    "id": "cho_ㄱ_N_H",
    "kind": "cho",
    "jamo": "ㄱ",
    "batchim": false,
    "group": "H",
    "label": "초성 ㄱ · 받침없음 · 가로모음",
    "example": "고",
    "zone_shape": [
      200,
      550,
      800,
      900
    ]
  },
  {
    "id": "cho_ㄱ_N_C",
    "kind": "cho",
    "jamo": "ㄱ",
    "batchim": false,
    "group": "C",
    "label": "초성 ㄱ · 받침없음 · 복합모음",
    "example": "과",
    "zone_shape": [
      100,
      550,
      750,
      900
    ]
  },
  {
    "id": "cho_ㄱ_B_V",
    "kind": "cho",
    "jamo": "ㄱ",
    "batchim": true,
    "group": "V",
    "label": "초성 ㄱ · 받침있음 · 세로모음",
    "example": "각",
    "zone_shape": [
      100,
      550,
      400,
      1000
    ]
  },
  {
    "id": "cho_ㄱ_B_H",
    "kind": "cho",
    "jamo": "ㄱ",
    "batchim": true,
    "group": "H",
    "label": "초성 ㄱ · 받침있음 · 가로모음",
    "example": "곡",
    "zone_shape": [
      0,
      650,
      1000,
      1000
    ]
  },
  {
    "id": "cho_ㄱ_B_C",
    "kind": "cho",
    "jamo": "ㄱ",
    "batchim": true,
    "group": "C",
    "label": "초성 ㄱ · 받침있음 · 복합모음",
    "example": "곽",
    "zone_shape": [
      200,
      700,
      560,
      1000
    ]
  },
  {
    "id": "cho_ㄲ_N_V",
    "kind": "cho",
    "jamo": "ㄲ",
    "batchim": false,
    "group": "V",
    "label": "초성 ㄲ · 받침없음 · 세로모음",
    "example": "까",
    "zone_shape": [
      100,
      100,
      450,
      900
    ]
  },
  {
    "id": "cho_ㄲ_N_H",
    "kind": "cho",
    "jamo": "ㄲ",
    "batchim": false,
    "group": "H",
    "label": "초성 ㄲ · 받침없음 · 가로모음",
    "example": "꼬",
    "zone_shape": [
      200,
      550,
      800,
      900
    ]
  },
  {
    "id": "cho_ㄲ_N_C",
    "kind": "cho",
    "jamo": "ㄲ",
    "batchim": false,
    "group": "C",
    "label": "초성 ㄲ · 받침없음 · 복합모음",
    "example": "꽈",
    "zone_shape": [
      100,
      550,
      750,
      900
    ]
  },
  {
    "id": "cho_ㄲ_B_V",
    "kind": "cho",
    "jamo": "ㄲ",
    "batchim": true,
    "group": "V",
    "label": "초성 ㄲ · 받침있음 · 세로모음",
    "example": "깍",
    "zone_shape": [
      100,
      550,
      400,
      1000
    ]
  },
  {
    "id": "cho_ㄲ_B_H",
    "kind": "cho",
    "jamo": "ㄲ",
    "batchim": true,
    "group": "H",
    "label": "초성 ㄲ · 받침있음 · 가로모음",
    "example": "꼭",
    "zone_shape": [
      0,
      650,
      1000,
      1000
    ]
  },
  {
    "id": "cho_ㄲ_B_C",
    "kind": "cho",
    "jamo": "ㄲ",
    "batchim": true,
    "group": "C",
    "label": "초성 ㄲ · 받침있음 · 복합모음",
    "example": "꽉",
    "zone_shape": [
      200,
      700,
      560,
      1000
    ]
  },
  {
    "id": "cho_ㄴ_N_V",
    "kind": "cho",
    "jamo": "ㄴ",
    "batchim": false,
    "group": "V",
    "label": "초성 ㄴ · 받침없음 · 세로모음",
    "example": "나",
    "zone_shape": [
      100,
      100,
      450,
      900
    ]
  },
  {
    "id": "cho_ㄴ_N_H",
    "kind": "cho",
    "jamo": "ㄴ",
    "batchim": false,
    "group": "H",
    "label": "초성 ㄴ · 받침없음 · 가로모음",
    "example": "노",
    "zone_shape": [
      200,
      550,
      800,
      900
    ]
  },
  {
    "id": "cho_ㄴ_N_C",
    "kind": "cho",
    "jamo": "ㄴ",
    "batchim": false,
    "group": "C",
    "label": "초성 ㄴ · 받침없음 · 복합모음",
    "example": "놔",
    "zone_shape": [
      100,
      550,
      750,
      900
    ]
  },
  {
    "id": "cho_ㄴ_B_V",
    "kind": "cho",
    "jamo": "ㄴ",
    "batchim": true,
    "group": "V",
    "label": "초성 ㄴ · 받침있음 · 세로모음",
    "example": "낙",
    "zone_shape": [
      100,
      550,
      400,
      1000
    ]
  },
  {
    "id": "cho_ㄴ_B_H",
    "kind": "cho",
    "jamo": "ㄴ",
    "batchim": true,
    "group": "H",
    "label": "초성 ㄴ · 받침있음 · 가로모음",
    "example": "녹",
    "zone_shape": [
      0,
      650,
      1000,
      1000
    ]
  },
  {
    "id": "cho_ㄴ_B_C",
    "kind": "cho",
    "jamo": "ㄴ",
    "batchim": true,
    "group": "C",
    "label": "초성 ㄴ · 받침있음 · 복합모음",
    "example": "놕",
    "zone_shape": [
      200,
      700,
      560,
      1000
    ]
  },
  {
    "id": "cho_ㄷ_N_V",
    "kind": "cho",
    "jamo": "ㄷ",
    "batchim": false,
    "group": "V",
    "label": "초성 ㄷ · 받침없음 · 세로모음",
    "example": "다",
    "zone_shape": [
      100,
      100,
      450,
      900
    ]
  },
  {
    "id": "cho_ㄷ_N_H",
    "kind": "cho",
    "jamo": "ㄷ",
    "batchim": false,
    "group": "H",
    "label": "초성 ㄷ · 받침없음 · 가로모음",
    "example": "도",
    "zone_shape": [
      200,
      550,
      800,
      900
    ]
  },
  {
    "id": "cho_ㄷ_N_C",
    "kind": "cho",
    "jamo": "ㄷ",
    "batchim": false,
    "group": "C",
    "label": "초성 ㄷ · 받침없음 · 복합모음",
    "example": "돠",
    "zone_shape": [
      100,
      550,
      750,
      900
    ]
  },
  {
    "id": "cho_ㄷ_B_V",
    "kind": "cho",
    "jamo": "ㄷ",
    "batchim": true,
    "group": "V",
    "label": "초성 ㄷ · 받침있음 · 세로모음",
    "example": "닥",
    "zone_shape": [
      100,
      550,
      400,
      1000
    ]
  },
  {
    "id": "cho_ㄷ_B_H",
    "kind": "cho",
    "jamo": "ㄷ",
    "batchim": true,
    "group": "H",
    "label": "초성 ㄷ · 받침있음 · 가로모음",
    "example": "독",
    "zone_shape": [
      0,
      650,
      1000,
      1000
    ]
  },
  {
    "id": "cho_ㄷ_B_C",
    "kind": "cho",
    "jamo": "ㄷ",
    "batchim": true,
    "group": "C",
    "label": "초성 ㄷ · 받침있음 · 복합모음",
    "example": "돡",
    "zone_shape": [
      200,
      700,
      560,
      1000
    ]
  },
  {
    "id": "cho_ㄸ_N_V",
    "kind": "cho",
    "jamo": "ㄸ",
    "batchim": false,
    "group": "V",
    "label": "초성 ㄸ · 받침없음 · 세로모음",
    "example": "따",
    "zone_shape": [
      100,
      100,
      450,
      900
    ]
  },
  {
    "id": "cho_ㄸ_N_H",
    "kind": "cho",
    "jamo": "ㄸ",
    "batchim": false,
    "group": "H",
    "label": "초성 ㄸ · 받침없음 · 가로모음",
    "example": "또",
    "zone_shape": [
      200,
      550,
      800,
      900
    ]
  },
  {
    "id": "cho_ㄸ_N_C",
    "kind": "cho",
    "jamo": "ㄸ",
    "batchim": false,
    "group": "C",
    "label": "초성 ㄸ · 받침없음 · 복합모음",
    "example": "똬",
    "zone_shape": [
      100,
      550,
      750,
      900
    ]
  },
  {
    "id": "cho_ㄸ_B_V",
    "kind": "cho",
    "jamo": "ㄸ",
    "batchim": true,
    "group": "V",
    "label": "초성 ㄸ · 받침있음 · 세로모음",
    "example": "딱",
    "zone_shape": [
      100,
      550,
      400,
      1000
    ]
  },
  {
    "id": "cho_ㄸ_B_H",
    "kind": "cho",
    "jamo": "ㄸ",
    "batchim": true,
    "group": "H",
    "label": "초성 ㄸ · 받침있음 · 가로모음",
    "example": "똑",
    "zone_shape": [
      0,
      650,
      1000,
      1000
    ]
  },
  {
    "id": "cho_ㄸ_B_C",
    "kind": "cho",
    "jamo": "ㄸ",
    "batchim": true,
    "group": "C",
    "label": "초성 ㄸ · 받침있음 · 복합모음",
    "example": "똭",
    "zone_shape": [
      200,
      700,
      560,
      1000
    ]
  },
  {
    "id": "cho_ㄹ_N_V",
    "kind": "cho",
    "jamo": "ㄹ",
    "batchim": false,
    "group": "V",
    "label": "초성 ㄹ · 받침없음 · 세로모음",
    "example": "라",
    "zone_shape": [
      100,
      100,
      450,
      900
    ]
  },
  {
    "id": "cho_ㄹ_N_H",
    "kind": "cho",
    "jamo": "ㄹ",
    "batchim": false,
    "group": "H",
    "label": "초성 ㄹ · 받침없음 · 가로모음",
    "example": "로",
    "zone_shape": [
      200,
      550,
      800,
      900
    ]
  },
  {
    "id": "cho_ㄹ_N_C",
    "kind": "cho",
    "jamo": "ㄹ",
    "batchim": false,
    "group": "C",
    "label": "초성 ㄹ · 받침없음 · 복합모음",
    "example": "롸",
    "zone_shape": [
      100,
      550,
      750,
      900
    ]
  },
  {
    "id": "cho_ㄹ_B_V",
    "kind": "cho",
    "jamo": "ㄹ",
    "batchim": true,
    "group": "V",
    "label": "초성 ㄹ · 받침있음 · 세로모음",
    "example": "락",
    "zone_shape": [
      100,
      550,
      400,
      1000
    ]
  },
  {
    "id": "cho_ㄹ_B_H",
    "kind": "cho",
    "jamo": "ㄹ",
    "batchim": true,
    "group": "H",
    "label": "초성 ㄹ · 받침있음 · 가로모음",
    "example": "록",
    "zone_shape": [
      0,
      650,
      1000,
      1000
    ]
  },
  {
    "id": "cho_ㄹ_B_C",
    "kind": "cho",
    "jamo": "ㄹ",
    "batchim": true,
    "group": "C",
    "label": "초성 ㄹ · 받침있음 · 복합모음",
    "example": "롹",
    "zone_shape": [
      200,
      700,
      560,
      1000
    ]
  },
  {
    "id": "cho_ㅁ_N_V",
    "kind": "cho",
    "jamo": "ㅁ",
    "batchim": false,
    "group": "V",
    "label": "초성 ㅁ · 받침없음 · 세로모음",
    "example": "마",
    "zone_shape": [
      100,
      100,
      450,
      900
    ]
  },
  {
    "id": "cho_ㅁ_N_H",
    "kind": "cho",
    "jamo": "ㅁ",
    "batchim": false,
    "group": "H",
    "label": "초성 ㅁ · 받침없음 · 가로모음",
    "example": "모",
    "zone_shape": [
      200,
      550,
      800,
      900
    ]
  },
  {
    "id": "cho_ㅁ_N_C",
    "kind": "cho",
    "jamo": "ㅁ",
    "batchim": false,
    "group": "C",
    "label": "초성 ㅁ · 받침없음 · 복합모음",
    "example": "뫄",
    "zone_shape": [
      100,
      550,
      750,
      900
    ]
  },
  {
    "id": "cho_ㅁ_B_V",
    "kind": "cho",
    "jamo": "ㅁ",
    "batchim": true,
    "group": "V",
    "label": "초성 ㅁ · 받침있음 · 세로모음",
    "example": "막",
    "zone_shape": [
      100,
      550,
      400,
      1000
    ]
  },
  {
    "id": "cho_ㅁ_B_H",
    "kind": "cho",
    "jamo": "ㅁ",
    "batchim": true,
    "group": "H",
    "label": "초성 ㅁ · 받침있음 · 가로모음",
    "example": "목",
    "zone_shape": [
      0,
      650,
      1000,
      1000
    ]
  },
  {
    "id": "cho_ㅁ_B_C",
    "kind": "cho",
    "jamo": "ㅁ",
    "batchim": true,
    "group": "C",
    "label": "초성 ㅁ · 받침있음 · 복합모음",
    "example": "뫅",
    "zone_shape": [
      200,
      700,
      560,
      1000
    ]
  },
  {
    "id": "cho_ㅂ_N_V",
    "kind": "cho",
    "jamo": "ㅂ",
    "batchim": false,
    "group": "V",
    "label": "초성 ㅂ · 받침없음 · 세로모음",
    "example": "바",
    "zone_shape": [
      100,
      100,
      450,
      900
    ]
  },
  {
    "id": "cho_ㅂ_N_H",
    "kind": "cho",
    "jamo": "ㅂ",
    "batchim": false,
    "group": "H",
    "label": "초성 ㅂ · 받침없음 · 가로모음",
    "example": "보",
    "zone_shape": [
      200,
      550,
      800,
      900
    ]
  },
  {
    "id": "cho_ㅂ_N_C",
    "kind": "cho",
    "jamo": "ㅂ",
    "batchim": false,
    "group": "C",
    "label": "초성 ㅂ · 받침없음 · 복합모음",
    "example": "봐",
    "zone_shape": [
      100,
      550,
      750,
      900
    ]
  },
  {
    "id": "cho_ㅂ_B_V",
    "kind": "cho",
    "jamo": "ㅂ",
    "batchim": true,
    "group": "V",
    "label": "초성 ㅂ · 받침있음 · 세로모음",
    "example": "박",
    "zone_shape": [
      100,
      550,
      400,
      1000
    ]
  },
  {
    "id": "cho_ㅂ_B_H",
    "kind": "cho",
    "jamo": "ㅂ",
    "batchim": true,
    "group": "H",
    "label": "초성 ㅂ · 받침있음 · 가로모음",
    "example": "복",
    "zone_shape": [
      0,
      650,
      1000,
      1000
    ]
  },
  {
    "id": "cho_ㅂ_B_C",
    "kind": "cho",
    "jamo": "ㅂ",
    "batchim": true,
    "group": "C",
    "label": "초성 ㅂ · 받침있음 · 복합모음",
    "example": "봑",
    "zone_shape": [
      200,
      700,
      560,
      1000
    ]
  },
  {
    "id": "cho_ㅃ_N_V",
    "kind": "cho",
    "jamo": "ㅃ",
    "batchim": false,
    "group": "V",
    "label": "초성 ㅃ · 받침없음 · 세로모음",
    "example": "빠",
    "zone_shape": [
      100,
      100,
      450,
      900
    ]
  },
  {
    "id": "cho_ㅃ_N_H",
    "kind": "cho",
    "jamo": "ㅃ",
    "batchim": false,
    "group": "H",
    "label": "초성 ㅃ · 받침없음 · 가로모음",
    "example": "뽀",
    "zone_shape": [
      200,
      550,
      800,
      900
    ]
  },
  {
    "id": "cho_ㅃ_N_C",
    "kind": "cho",
    "jamo": "ㅃ",
    "batchim": false,
    "group": "C",
    "label": "초성 ㅃ · 받침없음 · 복합모음",
    "example": "뽜",
    "zone_shape": [
      100,
      550,
      750,
      900
    ]
  },
  {
    "id": "cho_ㅃ_B_V",
    "kind": "cho",
    "jamo": "ㅃ",
    "batchim": true,
    "group": "V",
    "label": "초성 ㅃ · 받침있음 · 세로모음",
    "example": "빡",
    "zone_shape": [
      100,
      550,
      400,
      1000
    ]
  },
  {
    "id": "cho_ㅃ_B_H",
    "kind": "cho",
    "jamo": "ㅃ",
    "batchim": true,
    "group": "H",
    "label": "초성 ㅃ · 받침있음 · 가로모음",
    "example": "뽁",
    "zone_shape": [
      0,
      650,
      1000,
      1000
    ]
  },
  {
    "id": "cho_ㅃ_B_C",
    "kind": "cho",
    "jamo": "ㅃ",
    "batchim": true,
    "group": "C",
    "label": "초성 ㅃ · 받침있음 · 복합모음",
    "example": "뽝",
    "zone_shape": [
      200,
      700,
      560,
      1000
    ]
  },
  {
    "id": "cho_ㅅ_N_V",
    "kind": "cho",
    "jamo": "ㅅ",
    "batchim": false,
    "group": "V",
    "label": "초성 ㅅ · 받침없음 · 세로모음",
    "example": "사",
    "zone_shape": [
      100,
      100,
      450,
      900
    ]
  },
  {
    "id": "cho_ㅅ_N_H",
    "kind": "cho",
    "jamo": "ㅅ",
    "batchim": false,
    "group": "H",
    "label": "초성 ㅅ · 받침없음 · 가로모음",
    "example": "소",
    "zone_shape": [
      200,
      550,
      800,
      900
    ]
  },
  {
    "id": "cho_ㅅ_N_C",
    "kind": "cho",
    "jamo": "ㅅ",
    "batchim": false,
    "group": "C",
    "label": "초성 ㅅ · 받침없음 · 복합모음",
    "example": "솨",
    "zone_shape": [
      100,
      550,
      750,
      900
    ]
  },
  {
    "id": "cho_ㅅ_B_V",
    "kind": "cho",
    "jamo": "ㅅ",
    "batchim": true,
    "group": "V",
    "label": "초성 ㅅ · 받침있음 · 세로모음",
    "example": "삭",
    "zone_shape": [
      100,
      550,
      400,
      1000
    ]
  },
  {
    "id": "cho_ㅅ_B_H",
    "kind": "cho",
    "jamo": "ㅅ",
    "batchim": true,
    "group": "H",
    "label": "초성 ㅅ · 받침있음 · 가로모음",
    "example": "속",
    "zone_shape": [
      0,
      650,
      1000,
      1000
    ]
  },
  {
    "id": "cho_ㅅ_B_C",
    "kind": "cho",
    "jamo": "ㅅ",
    "batchim": true,
    "group": "C",
    "label": "초성 ㅅ · 받침있음 · 복합모음",
    "example": "솩",
    "zone_shape": [
      200,
      700,
      560,
      1000
    ]
  },
  {
    "id": "cho_ㅆ_N_V",
    "kind": "cho",
    "jamo": "ㅆ",
    "batchim": false,
    "group": "V",
    "label": "초성 ㅆ · 받침없음 · 세로모음",
    "example": "싸",
    "zone_shape": [
      100,
      100,
      450,
      900
    ]
  },
  {
    "id": "cho_ㅆ_N_H",
    "kind": "cho",
    "jamo": "ㅆ",
    "batchim": false,
    "group": "H",
    "label": "초성 ㅆ · 받침없음 · 가로모음",
    "example": "쏘",
    "zone_shape": [
      200,
      550,
      800,
      900
    ]
  },
  {
    "id": "cho_ㅆ_N_C",
    "kind": "cho",
    "jamo": "ㅆ",
    "batchim": false,
    "group": "C",
    "label": "초성 ㅆ · 받침없음 · 복합모음",
    "example": "쏴",
    "zone_shape": [
      100,
      550,
      750,
      900
    ]
  },
  {
    "id": "cho_ㅆ_B_V",
    "kind": "cho",
    "jamo": "ㅆ",
    "batchim": true,
    "group": "V",
    "label": "초성 ㅆ · 받침있음 · 세로모음",
    "example": "싹",
    "zone_shape": [
      100,
      550,
      400,
      1000
    ]
  },
  {
    "id": "cho_ㅆ_B_H",
    "kind": "cho",
    "jamo": "ㅆ",
    "batchim": true,
    "group": "H",
    "label": "초성 ㅆ · 받침있음 · 가로모음",
    "example": "쏙",
    "zone_shape": [
      0,
      650,
      1000,
      1000
    ]
  },
  {
    "id": "cho_ㅆ_B_C",
    "kind": "cho",
    "jamo": "ㅆ",
    "batchim": true,
    "group": "C",
    "label": "초성 ㅆ · 받침있음 · 복합모음",
    "example": "쏵",
    "zone_shape": [
      200,
      700,
      560,
      1000
    ]
  },
  {
    "id": "cho_ㅇ_N_V",
    "kind": "cho",
    "jamo": "ㅇ",
    "batchim": false,
    "group": "V",
    "label": "초성 ㅇ · 받침없음 · 세로모음",
    "example": "아",
    "zone_shape": [
      100,
      100,
      450,
      900
    ]
  },
  {
    "id": "cho_ㅇ_N_H",
    "kind": "cho",
    "jamo": "ㅇ",
    "batchim": false,
    "group": "H",
    "label": "초성 ㅇ · 받침없음 · 가로모음",
    "example": "오",
    "zone_shape": [
      200,
      550,
      800,
      900
    ]
  },
  {
    "id": "cho_ㅇ_N_C",
    "kind": "cho",
    "jamo": "ㅇ",
    "batchim": false,
    "group": "C",
    "label": "초성 ㅇ · 받침없음 · 복합모음",
    "example": "와",
    "zone_shape": [
      100,
      550,
      750,
      900
    ]
  },
  {
    "id": "cho_ㅇ_B_V",
    "kind": "cho",
    "jamo": "ㅇ",
    "batchim": true,
    "group": "V",
    "label": "초성 ㅇ · 받침있음 · 세로모음",
    "example": "악",
    "zone_shape": [
      100,
      550,
      400,
      1000
    ]
  },
  {
    "id": "cho_ㅇ_B_H",
    "kind": "cho",
    "jamo": "ㅇ",
    "batchim": true,
    "group": "H",
    "label": "초성 ㅇ · 받침있음 · 가로모음",
    "example": "옥",
    "zone_shape": [
      0,
      650,
      1000,
      1000
    ]
  },
  {
    "id": "cho_ㅇ_B_C",
    "kind": "cho",
    "jamo": "ㅇ",
    "batchim": true,
    "group": "C",
    "label": "초성 ㅇ · 받침있음 · 복합모음",
    "example": "왁",
    "zone_shape": [
      200,
      700,
      560,
      1000
    ]
  },
  {
    "id": "cho_ㅈ_N_V",
    "kind": "cho",
    "jamo": "ㅈ",
    "batchim": false,
    "group": "V",
    "label": "초성 ㅈ · 받침없음 · 세로모음",
    "example": "자",
    "zone_shape": [
      100,
      100,
      450,
      900
    ]
  },
  {
    "id": "cho_ㅈ_N_H",
    "kind": "cho",
    "jamo": "ㅈ",
    "batchim": false,
    "group": "H",
    "label": "초성 ㅈ · 받침없음 · 가로모음",
    "example": "조",
    "zone_shape": [
      200,
      550,
      800,
      900
    ]
  },
  {
    "id": "cho_ㅈ_N_C",
    "kind": "cho",
    "jamo": "ㅈ",
    "batchim": false,
    "group": "C",
    "label": "초성 ㅈ · 받침없음 · 복합모음",
    "example": "좌",
    "zone_shape": [
      100,
      550,
      750,
      900
    ]
  },
  {
    "id": "cho_ㅈ_B_V",
    "kind": "cho",
    "jamo": "ㅈ",
    "batchim": true,
    "group": "V",
    "label": "초성 ㅈ · 받침있음 · 세로모음",
    "example": "작",
    "zone_shape": [
      100,
      550,
      400,
      1000
    ]
  },
  {
    "id": "cho_ㅈ_B_H",
    "kind": "cho",
    "jamo": "ㅈ",
    "batchim": true,
    "group": "H",
    "label": "초성 ㅈ · 받침있음 · 가로모음",
    "example": "족",
    "zone_shape": [
      0,
      650,
      1000,
      1000
    ]
  },
  {
    "id": "cho_ㅈ_B_C",
    "kind": "cho",
    "jamo": "ㅈ",
    "batchim": true,
    "group": "C",
    "label": "초성 ㅈ · 받침있음 · 복합모음",
    "example": "좍",
    "zone_shape": [
      200,
      700,
      560,
      1000
    ]
  },
  {
    "id": "cho_ㅉ_N_V",
    "kind": "cho",
    "jamo": "ㅉ",
    "batchim": false,
    "group": "V",
    "label": "초성 ㅉ · 받침없음 · 세로모음",
    "example": "짜",
    "zone_shape": [
      100,
      100,
      450,
      900
    ]
  },
  {
    "id": "cho_ㅉ_N_H",
    "kind": "cho",
    "jamo": "ㅉ",
    "batchim": false,
    "group": "H",
    "label": "초성 ㅉ · 받침없음 · 가로모음",
    "example": "쪼",
    "zone_shape": [
      200,
      550,
      800,
      900
    ]
  },
  {
    "id": "cho_ㅉ_N_C",
    "kind": "cho",
    "jamo": "ㅉ",
    "batchim": false,
    "group": "C",
    "label": "초성 ㅉ · 받침없음 · 복합모음",
    "example": "쫘",
    "zone_shape": [
      100,
      550,
      750,
      900
    ]
  },
  {
    "id": "cho_ㅉ_B_V",
    "kind": "cho",
    "jamo": "ㅉ",
    "batchim": true,
    "group": "V",
    "label": "초성 ㅉ · 받침있음 · 세로모음",
    "example": "짝",
    "zone_shape": [
      100,
      550,
      400,
      1000
    ]
  },
  {
    "id": "cho_ㅉ_B_H",
    "kind": "cho",
    "jamo": "ㅉ",
    "batchim": true,
    "group": "H",
    "label": "초성 ㅉ · 받침있음 · 가로모음",
    "example": "쪽",
    "zone_shape": [
      0,
      650,
      1000,
      1000
    ]
  },
  {
    "id": "cho_ㅉ_B_C",
    "kind": "cho",
    "jamo": "ㅉ",
    "batchim": true,
    "group": "C",
    "label": "초성 ㅉ · 받침있음 · 복합모음",
    "example": "쫙",
    "zone_shape": [
      200,
      700,
      560,
      1000
    ]
  },
  {
    "id": "cho_ㅊ_N_V",
    "kind": "cho",
    "jamo": "ㅊ",
    "batchim": false,
    "group": "V",
    "label": "초성 ㅊ · 받침없음 · 세로모음",
    "example": "차",
    "zone_shape": [
      100,
      100,
      450,
      900
    ]
  },
  {
    "id": "cho_ㅊ_N_H",
    "kind": "cho",
    "jamo": "ㅊ",
    "batchim": false,
    "group": "H",
    "label": "초성 ㅊ · 받침없음 · 가로모음",
    "example": "초",
    "zone_shape": [
      200,
      550,
      800,
      900
    ]
  },
  {
    "id": "cho_ㅊ_N_C",
    "kind": "cho",
    "jamo": "ㅊ",
    "batchim": false,
    "group": "C",
    "label": "초성 ㅊ · 받침없음 · 복합모음",
    "example": "촤",
    "zone_shape": [
      100,
      550,
      750,
      900
    ]
  },
  {
    "id": "cho_ㅊ_B_V",
    "kind": "cho",
    "jamo": "ㅊ",
    "batchim": true,
    "group": "V",
    "label": "초성 ㅊ · 받침있음 · 세로모음",
    "example": "착",
    "zone_shape": [
      100,
      550,
      400,
      1000
    ]
  },
  {
    "id": "cho_ㅊ_B_H",
    "kind": "cho",
    "jamo": "ㅊ",
    "batchim": true,
    "group": "H",
    "label": "초성 ㅊ · 받침있음 · 가로모음",
    "example": "촉",
    "zone_shape": [
      0,
      650,
      1000,
      1000
    ]
  },
  {
    "id": "cho_ㅊ_B_C",
    "kind": "cho",
    "jamo": "ㅊ",
    "batchim": true,
    "group": "C",
    "label": "초성 ㅊ · 받침있음 · 복합모음",
    "example": "촥",
    "zone_shape": [
      200,
      700,
      560,
      1000
    ]
  },
  {
    "id": "cho_ㅋ_N_V",
    "kind": "cho",
    "jamo": "ㅋ",
    "batchim": false,
    "group": "V",
    "label": "초성 ㅋ · 받침없음 · 세로모음",
    "example": "카",
    "zone_shape": [
      100,
      100,
      450,
      900
    ]
  },
  {
    "id": "cho_ㅋ_N_H",
    "kind": "cho",
    "jamo": "ㅋ",
    "batchim": false,
    "group": "H",
    "label": "초성 ㅋ · 받침없음 · 가로모음",
    "example": "코",
    "zone_shape": [
      200,
      550,
      800,
      900
    ]
  },
  {
    "id": "cho_ㅋ_N_C",
    "kind": "cho",
    "jamo": "ㅋ",
    "batchim": false,
    "group": "C",
    "label": "초성 ㅋ · 받침없음 · 복합모음",
    "example": "콰",
    "zone_shape": [
      100,
      550,
      750,
      900
    ]
  },
  {
    "id": "cho_ㅋ_B_V",
    "kind": "cho",
    "jamo": "ㅋ",
    "batchim": true,
    "group": "V",
    "label": "초성 ㅋ · 받침있음 · 세로모음",
    "example": "칵",
    "zone_shape": [
      100,
      550,
      400,
      1000
    ]
  },
  {
    "id": "cho_ㅋ_B_H",
    "kind": "cho",
    "jamo": "ㅋ",
    "batchim": true,
    "group": "H",
    "label": "초성 ㅋ · 받침있음 · 가로모음",
    "example": "콕",
    "zone_shape": [
      0,
      650,
      1000,
      1000
    ]
  },
  {
    "id": "cho_ㅋ_B_C",
    "kind": "cho",
    "jamo": "ㅋ",
    "batchim": true,
    "group": "C",
    "label": "초성 ㅋ · 받침있음 · 복합모음",
    "example": "콱",
    "zone_shape": [
      200,
      700,
      560,
      1000
    ]
  },
  {
    "id": "cho_ㅌ_N_V",
    "kind": "cho",
    "jamo": "ㅌ",
    "batchim": false,
    "group": "V",
    "label": "초성 ㅌ · 받침없음 · 세로모음",
    "example": "타",
    "zone_shape": [
      100,
      100,
      450,
      900
    ]
  },
  {
    "id": "cho_ㅌ_N_H",
    "kind": "cho",
    "jamo": "ㅌ",
    "batchim": false,
    "group": "H",
    "label": "초성 ㅌ · 받침없음 · 가로모음",
    "example": "토",
    "zone_shape": [
      200,
      550,
      800,
      900
    ]
  },
  {
    "id": "cho_ㅌ_N_C",
    "kind": "cho",
    "jamo": "ㅌ",
    "batchim": false,
    "group": "C",
    "label": "초성 ㅌ · 받침없음 · 복합모음",
    "example": "톼",
    "zone_shape": [
      100,
      550,
      750,
      900
    ]
  },
  {
    "id": "cho_ㅌ_B_V",
    "kind": "cho",
    "jamo": "ㅌ",
    "batchim": true,
    "group": "V",
    "label": "초성 ㅌ · 받침있음 · 세로모음",
    "example": "탁",
    "zone_shape": [
      100,
      550,
      400,
      1000
    ]
  },
  {
    "id": "cho_ㅌ_B_H",
    "kind": "cho",
    "jamo": "ㅌ",
    "batchim": true,
    "group": "H",
    "label": "초성 ㅌ · 받침있음 · 가로모음",
    "example": "톡",
    "zone_shape": [
      0,
      650,
      1000,
      1000
    ]
  },
  {
    "id": "cho_ㅌ_B_C",
    "kind": "cho",
    "jamo": "ㅌ",
    "batchim": true,
    "group": "C",
    "label": "초성 ㅌ · 받침있음 · 복합모음",
    "example": "톽",
    "zone_shape": [
      200,
      700,
      560,
      1000
    ]
  },
  {
    "id": "cho_ㅍ_N_V",
    "kind": "cho",
    "jamo": "ㅍ",
    "batchim": false,
    "group": "V",
    "label": "초성 ㅍ · 받침없음 · 세로모음",
    "example": "파",
    "zone_shape": [
      100,
      100,
      450,
      900
    ]
  },
  {
    "id": "cho_ㅍ_N_H",
    "kind": "cho",
    "jamo": "ㅍ",
    "batchim": false,
    "group": "H",
    "label": "초성 ㅍ · 받침없음 · 가로모음",
    "example": "포",
    "zone_shape": [
      200,
      550,
      800,
      900
    ]
  },
  {
    "id": "cho_ㅍ_N_C",
    "kind": "cho",
    "jamo": "ㅍ",
    "batchim": false,
    "group": "C",
    "label": "초성 ㅍ · 받침없음 · 복합모음",
    "example": "퐈",
    "zone_shape": [
      100,
      550,
      750,
      900
    ]
  },
  {
    "id": "cho_ㅍ_B_V",
    "kind": "cho",
    "jamo": "ㅍ",
    "batchim": true,
    "group": "V",
    "label": "초성 ㅍ · 받침있음 · 세로모음",
    "example": "팍",
    "zone_shape": [
      100,
      550,
      400,
      1000
    ]
  },
  {
    "id": "cho_ㅍ_B_H",
    "kind": "cho",
    "jamo": "ㅍ",
    "batchim": true,
    "group": "H",
    "label": "초성 ㅍ · 받침있음 · 가로모음",
    "example": "폭",
    "zone_shape": [
      0,
      650,
      1000,
      1000
    ]
  },
  {
    "id": "cho_ㅍ_B_C",
    "kind": "cho",
    "jamo": "ㅍ",
    "batchim": true,
    "group": "C",
    "label": "초성 ㅍ · 받침있음 · 복합모음",
    "example": "퐉",
    "zone_shape": [
      200,
      700,
      560,
      1000
    ]
  },
  {
    "id": "cho_ㅎ_N_V",
    "kind": "cho",
    "jamo": "ㅎ",
    "batchim": false,
    "group": "V",
    "label": "초성 ㅎ · 받침없음 · 세로모음",
    "example": "하",
    "zone_shape": [
      100,
      100,
      450,
      900
    ]
  },
  {
    "id": "cho_ㅎ_N_H",
    "kind": "cho",
    "jamo": "ㅎ",
    "batchim": false,
    "group": "H",
    "label": "초성 ㅎ · 받침없음 · 가로모음",
    "example": "호",
    "zone_shape": [
      200,
      550,
      800,
      900
    ]
  },
  {
    "id": "cho_ㅎ_N_C",
    "kind": "cho",
    "jamo": "ㅎ",
    "batchim": false,
    "group": "C",
    "label": "초성 ㅎ · 받침없음 · 복합모음",
    "example": "화",
    "zone_shape": [
      100,
      550,
      750,
      900
    ]
  },
  {
    "id": "cho_ㅎ_B_V",
    "kind": "cho",
    "jamo": "ㅎ",
    "batchim": true,
    "group": "V",
    "label": "초성 ㅎ · 받침있음 · 세로모음",
    "example": "학",
    "zone_shape": [
      100,
      550,
      400,
      1000
    ]
  },
  {
    "id": "cho_ㅎ_B_H",
    "kind": "cho",
    "jamo": "ㅎ",
    "batchim": true,
    "group": "H",
    "label": "초성 ㅎ · 받침있음 · 가로모음",
    "example": "혹",
    "zone_shape": [
      0,
      650,
      1000,
      1000
    ]
  },
  {
    "id": "cho_ㅎ_B_C",
    "kind": "cho",
    "jamo": "ㅎ",
    "batchim": true,
    "group": "C",
    "label": "초성 ㅎ · 받침있음 · 복합모음",
    "example": "확",
    "zone_shape": [
      200,
      700,
      560,
      1000
    ]
  },
  {
    "id": "jung_ㅏ_N",
    "kind": "jung",
    "jamo": "ㅏ",
    "batchim": false,
    "group": null,
    "label": "중성 ㅏ · 받침없음",
    "example": "가",
    "zone_shape": [
      400,
      100,
      900,
      900
    ]
  },
  {
    "id": "jung_ㅏ_B",
    "kind": "jung",
    "jamo": "ㅏ",
    "batchim": true,
    "group": null,
    "label": "중성 ㅏ · 받침있음",
    "example": "각",
    "zone_shape": [
      400,
      500,
      1000,
      1000
    ]
  },
  {
    "id": "jung_ㅐ_N",
    "kind": "jung",
    "jamo": "ㅐ",
    "batchim": false,
    "group": null,
    "label": "중성 ㅐ · 받침없음",
    "example": "개",
    "zone_shape": [
      400,
      100,
      900,
      900
    ]
  },
  {
    "id": "jung_ㅐ_B",
    "kind": "jung",
    "jamo": "ㅐ",
    "batchim": true,
    "group": null,
    "label": "중성 ㅐ · 받침있음",
    "example": "객",
    "zone_shape": [
      400,
      500,
      1000,
      1000
    ]
  },
  {
    "id": "jung_ㅑ_N",
    "kind": "jung",
    "jamo": "ㅑ",
    "batchim": false,
    "group": null,
    "label": "중성 ㅑ · 받침없음",
    "example": "갸",
    "zone_shape": [
      400,
      100,
      900,
      900
    ]
  },
  {
    "id": "jung_ㅑ_B",
    "kind": "jung",
    "jamo": "ㅑ",
    "batchim": true,
    "group": null,
    "label": "중성 ㅑ · 받침있음",
    "example": "갹",
    "zone_shape": [
      400,
      500,
      1000,
      1000
    ]
  },
  {
    "id": "jung_ㅒ_N",
    "kind": "jung",
    "jamo": "ㅒ",
    "batchim": false,
    "group": null,
    "label": "중성 ㅒ · 받침없음",
    "example": "걔",
    "zone_shape": [
      400,
      100,
      900,
      900
    ]
  },
  {
    "id": "jung_ㅒ_B",
    "kind": "jung",
    "jamo": "ㅒ",
    "batchim": true,
    "group": null,
    "label": "중성 ㅒ · 받침있음",
    "example": "걕",
    "zone_shape": [
      400,
      500,
      1000,
      1000
    ]
  },
  {
    "id": "jung_ㅓ_N",
    "kind": "jung",
    "jamo": "ㅓ",
    "batchim": false,
    "group": null,
    "label": "중성 ㅓ · 받침없음",
    "example": "거",
    "zone_shape": [
      400,
      100,
      900,
      900
    ]
  },
  {
    "id": "jung_ㅓ_B",
    "kind": "jung",
    "jamo": "ㅓ",
    "batchim": true,
    "group": null,
    "label": "중성 ㅓ · 받침있음",
    "example": "걱",
    "zone_shape": [
      400,
      500,
      1000,
      1000
    ]
  },
  {
    "id": "jung_ㅔ_N",
    "kind": "jung",
    "jamo": "ㅔ",
    "batchim": false,
    "group": null,
    "label": "중성 ㅔ · 받침없음",
    "example": "게",
    "zone_shape": [
      400,
      100,
      900,
      900
    ]
  },
  {
    "id": "jung_ㅔ_B",
    "kind": "jung",
    "jamo": "ㅔ",
    "batchim": true,
    "group": null,
    "label": "중성 ㅔ · 받침있음",
    "example": "겍",
    "zone_shape": [
      400,
      500,
      1000,
      1000
    ]
  },
  {
    "id": "jung_ㅕ_N",
    "kind": "jung",
    "jamo": "ㅕ",
    "batchim": false,
    "group": null,
    "label": "중성 ㅕ · 받침없음",
    "example": "겨",
    "zone_shape": [
      400,
      100,
      900,
      900
    ]
  },
  {
    "id": "jung_ㅕ_B",
    "kind": "jung",
    "jamo": "ㅕ",
    "batchim": true,
    "group": null,
    "label": "중성 ㅕ · 받침있음",
    "example": "격",
    "zone_shape": [
      400,
      500,
      1000,
      1000
    ]
  },
  {
    "id": "jung_ㅖ_N",
    "kind": "jung",
    "jamo": "ㅖ",
    "batchim": false,
    "group": null,
    "label": "중성 ㅖ · 받침없음",
    "example": "계",
    "zone_shape": [
      400,
      100,
      900,
      900
    ]
  },
  {
    "id": "jung_ㅖ_B",
    "kind": "jung",
    "jamo": "ㅖ",
    "batchim": true,
    "group": null,
    "label": "중성 ㅖ · 받침있음",
    "example": "곅",
    "zone_shape": [
      400,
      500,
      1000,
      1000
    ]
  },
  {
    "id": "jung_ㅗ_N",
    "kind": "jung",
    "jamo": "ㅗ",
    "batchim": false,
    "group": null,
    "label": "중성 ㅗ · 받침없음",
    "example": "고",
    "zone_shape": [
      100,
      0,
      900,
      480
    ]
  },
  {
    "id": "jung_ㅗ_B",
    "kind": "jung",
    "jamo": "ㅗ",
    "batchim": true,
    "group": null,
    "label": "중성 ㅗ · 받침있음",
    "example": "곡",
    "zone_shape": [
      100,
      370,
      900,
      670
    ]
  },
  {
    "id": "jung_ㅘ_N",
    "kind": "jung",
    "jamo": "ㅘ",
    "batchim": false,
    "group": null,
    "label": "중성 ㅘ · 받침없음",
    "example": "과",
    "zone_shape": [
      0,
      0,
      1000,
      600
    ]
  },
  {
    "id": "jung_ㅘ_B",
    "kind": "jung",
    "jamo": "ㅘ",
    "batchim": true,
    "group": null,
    "label": "중성 ㅘ · 받침있음",
    "example": "곽",
    "zone_shape": [
      200,
      360,
      800,
      850
    ]
  },
  {
    "id": "jung_ㅙ_N",
    "kind": "jung",
    "jamo": "ㅙ",
    "batchim": false,
    "group": null,
    "label": "중성 ㅙ · 받침없음",
    "example": "괘",
    "zone_shape": [
      0,
      0,
      1000,
      600
    ]
  },
  {
    "id": "jung_ㅙ_B",
    "kind": "jung",
    "jamo": "ㅙ",
    "batchim": true,
    "group": null,
    "label": "중성 ㅙ · 받침있음",
    "example": "괙",
    "zone_shape": [
      200,
      360,
      800,
      850
    ]
  },
  {
    "id": "jung_ㅚ_N",
    "kind": "jung",
    "jamo": "ㅚ",
    "batchim": false,
    "group": null,
    "label": "중성 ㅚ · 받침없음",
    "example": "괴",
    "zone_shape": [
      0,
      0,
      1000,
      600
    ]
  },
  {
    "id": "jung_ㅚ_B",
    "kind": "jung",
    "jamo": "ㅚ",
    "batchim": true,
    "group": null,
    "label": "중성 ㅚ · 받침있음",
    "example": "괵",
    "zone_shape": [
      200,
      360,
      800,
      850
    ]
  },
  {
    "id": "jung_ㅛ_N",
    "kind": "jung",
    "jamo": "ㅛ",
    "batchim": false,
    "group": null,
    "label": "중성 ㅛ · 받침없음",
    "example": "교",
    "zone_shape": [
      100,
      0,
      900,
      480
    ]
  },
  {
    "id": "jung_ㅛ_B",
    "kind": "jung",
    "jamo": "ㅛ",
    "batchim": true,
    "group": null,
    "label": "중성 ㅛ · 받침있음",
    "example": "굑",
    "zone_shape": [
      100,
      370,
      900,
      670
    ]
  },
  {
    "id": "jung_ㅜ_N",
    "kind": "jung",
    "jamo": "ㅜ",
    "batchim": false,
    "group": null,
    "label": "중성 ㅜ · 받침없음",
    "example": "구",
    "zone_shape": [
      100,
      0,
      900,
      480
    ]
  },
  {
    "id": "jung_ㅜ_B",
    "kind": "jung",
    "jamo": "ㅜ",
    "batchim": true,
    "group": null,
    "label": "중성 ㅜ · 받침있음",
    "example": "국",
    "zone_shape": [
      100,
      370,
      900,
      670
    ]
  },
  {
    "id": "jung_ㅝ_N",
    "kind": "jung",
    "jamo": "ㅝ",
    "batchim": false,
    "group": null,
    "label": "중성 ㅝ · 받침없음",
    "example": "궈",
    "zone_shape": [
      0,
      0,
      1000,
      600
    ]
  },
  {
    "id": "jung_ㅝ_B",
    "kind": "jung",
    "jamo": "ㅝ",
    "batchim": true,
    "group": null,
    "label": "중성 ㅝ · 받침있음",
    "example": "궉",
    "zone_shape": [
      200,
      360,
      800,
      850
    ]
  },
  {
    "id": "jung_ㅞ_N",
    "kind": "jung",
    "jamo": "ㅞ",
    "batchim": false,
    "group": null,
    "label": "중성 ㅞ · 받침없음",
    "example": "궤",
    "zone_shape": [
      0,
      0,
      1000,
      600
    ]
  },
  {
    "id": "jung_ㅞ_B",
    "kind": "jung",
    "jamo": "ㅞ",
    "batchim": true,
    "group": null,
    "label": "중성 ㅞ · 받침있음",
    "example": "궥",
    "zone_shape": [
      200,
      360,
      800,
      850
    ]
  },
  {
    "id": "jung_ㅟ_N",
    "kind": "jung",
    "jamo": "ㅟ",
    "batchim": false,
    "group": null,
    "label": "중성 ㅟ · 받침없음",
    "example": "귀",
    "zone_shape": [
      0,
      0,
      1000,
      600
    ]
  },
  {
    "id": "jung_ㅟ_B",
    "kind": "jung",
    "jamo": "ㅟ",
    "batchim": true,
    "group": null,
    "label": "중성 ㅟ · 받침있음",
    "example": "귁",
    "zone_shape": [
      200,
      360,
      800,
      850
    ]
  },
  {
    "id": "jung_ㅠ_N",
    "kind": "jung",
    "jamo": "ㅠ",
    "batchim": false,
    "group": null,
    "label": "중성 ㅠ · 받침없음",
    "example": "규",
    "zone_shape": [
      100,
      0,
      900,
      480
    ]
  },
  {
    "id": "jung_ㅠ_B",
    "kind": "jung",
    "jamo": "ㅠ",
    "batchim": true,
    "group": null,
    "label": "중성 ㅠ · 받침있음",
    "example": "귝",
    "zone_shape": [
      100,
      370,
      900,
      670
    ]
  },
  {
    "id": "jung_ㅡ_N",
    "kind": "jung",
    "jamo": "ㅡ",
    "batchim": false,
    "group": null,
    "label": "중성 ㅡ · 받침없음",
    "example": "그",
    "zone_shape": [
      100,
      0,
      900,
      480
    ]
  },
  {
    "id": "jung_ㅡ_B",
    "kind": "jung",
    "jamo": "ㅡ",
    "batchim": true,
    "group": null,
    "label": "중성 ㅡ · 받침있음",
    "example": "극",
    "zone_shape": [
      100,
      370,
      900,
      670
    ]
  },
  {
    "id": "jung_ㅢ_N",
    "kind": "jung",
    "jamo": "ㅢ",
    "batchim": false,
    "group": null,
    "label": "중성 ㅢ · 받침없음",
    "example": "긔",
    "zone_shape": [
      0,
      0,
      1000,
      600
    ]
  },
  {
    "id": "jung_ㅢ_B",
    "kind": "jung",
    "jamo": "ㅢ",
    "batchim": true,
    "group": null,
    "label": "중성 ㅢ · 받침있음",
    "example": "긕",
    "zone_shape": [
      200,
      360,
      800,
      850
    ]
  },
  {
    "id": "jung_ㅣ_N",
    "kind": "jung",
    "jamo": "ㅣ",
    "batchim": false,
    "group": null,
    "label": "중성 ㅣ · 받침없음",
    "example": "기",
    "zone_shape": [
      400,
      100,
      900,
      900
    ]
  },
  {
    "id": "jung_ㅣ_B",
    "kind": "jung",
    "jamo": "ㅣ",
    "batchim": true,
    "group": null,
    "label": "중성 ㅣ · 받침있음",
    "example": "긱",
    "zone_shape": [
      400,
      500,
      1000,
      1000
    ]
  },
  {
    "id": "jong_ㄱ",
    "kind": "jong",
    "jamo": "ㄱ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㄱ",
    "example": "각",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㄲ",
    "kind": "jong",
    "jamo": "ㄲ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㄲ",
    "example": "갂",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㄳ",
    "kind": "jong",
    "jamo": "ㄳ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㄳ",
    "example": "갃",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㄴ",
    "kind": "jong",
    "jamo": "ㄴ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㄴ",
    "example": "간",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㄵ",
    "kind": "jong",
    "jamo": "ㄵ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㄵ",
    "example": "갅",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㄶ",
    "kind": "jong",
    "jamo": "ㄶ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㄶ",
    "example": "갆",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㄷ",
    "kind": "jong",
    "jamo": "ㄷ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㄷ",
    "example": "갇",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㄹ",
    "kind": "jong",
    "jamo": "ㄹ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㄹ",
    "example": "갈",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㄺ",
    "kind": "jong",
    "jamo": "ㄺ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㄺ",
    "example": "갉",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㄻ",
    "kind": "jong",
    "jamo": "ㄻ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㄻ",
    "example": "갊",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㄼ",
    "kind": "jong",
    "jamo": "ㄼ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㄼ",
    "example": "갋",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㄽ",
    "kind": "jong",
    "jamo": "ㄽ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㄽ",
    "example": "갌",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㄾ",
    "kind": "jong",
    "jamo": "ㄾ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㄾ",
    "example": "갍",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㄿ",
    "kind": "jong",
    "jamo": "ㄿ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㄿ",
    "example": "갎",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㅀ",
    "kind": "jong",
    "jamo": "ㅀ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㅀ",
    "example": "갏",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㅁ",
    "kind": "jong",
    "jamo": "ㅁ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㅁ",
    "example": "감",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㅂ",
    "kind": "jong",
    "jamo": "ㅂ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㅂ",
    "example": "갑",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㅄ",
    "kind": "jong",
    "jamo": "ㅄ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㅄ",
    "example": "값",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㅅ",
    "kind": "jong",
    "jamo": "ㅅ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㅅ",
    "example": "갓",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㅆ",
    "kind": "jong",
    "jamo": "ㅆ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㅆ",
    "example": "갔",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㅇ",
    "kind": "jong",
    "jamo": "ㅇ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㅇ",
    "example": "강",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㅈ",
    "kind": "jong",
    "jamo": "ㅈ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㅈ",
    "example": "갖",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㅊ",
    "kind": "jong",
    "jamo": "ㅊ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㅊ",
    "example": "갗",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㅋ",
    "kind": "jong",
    "jamo": "ㅋ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㅋ",
    "example": "갘",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㅌ",
    "kind": "jong",
    "jamo": "ㅌ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㅌ",
    "example": "같",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㅍ",
    "kind": "jong",
    "jamo": "ㅍ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㅍ",
    "example": "갚",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "jong_ㅎ",
    "kind": "jong",
    "jamo": "ㅎ",
    "batchim": true,
    "group": null,
    "label": "종성(받침) ㅎ",
    "example": "갛",
    "zone_shape": [
      0,
      0,
      1000,
      280
    ]
  },
  {
    "id": "latin_0021",
    "kind": "latin",
    "jamo": "!",
    "batchim": null,
    "group": null,
    "label": "문자 '!' (U+0021)",
    "example": "!",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0022",
    "kind": "latin",
    "jamo": "\"",
    "batchim": null,
    "group": null,
    "label": "문자 '\"' (U+0022)",
    "example": "\"",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0023",
    "kind": "latin",
    "jamo": "#",
    "batchim": null,
    "group": null,
    "label": "문자 '#' (U+0023)",
    "example": "#",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0024",
    "kind": "latin",
    "jamo": "$",
    "batchim": null,
    "group": null,
    "label": "문자 '$' (U+0024)",
    "example": "$",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0025",
    "kind": "latin",
    "jamo": "%",
    "batchim": null,
    "group": null,
    "label": "문자 '%' (U+0025)",
    "example": "%",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0026",
    "kind": "latin",
    "jamo": "&",
    "batchim": null,
    "group": null,
    "label": "문자 '&' (U+0026)",
    "example": "&",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0027",
    "kind": "latin",
    "jamo": "'",
    "batchim": null,
    "group": null,
    "label": "문자 ''' (U+0027)",
    "example": "'",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0028",
    "kind": "latin",
    "jamo": "(",
    "batchim": null,
    "group": null,
    "label": "문자 '(' (U+0028)",
    "example": "(",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0029",
    "kind": "latin",
    "jamo": ")",
    "batchim": null,
    "group": null,
    "label": "문자 ')' (U+0029)",
    "example": ")",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_002A",
    "kind": "latin",
    "jamo": "*",
    "batchim": null,
    "group": null,
    "label": "문자 '*' (U+002A)",
    "example": "*",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_002B",
    "kind": "latin",
    "jamo": "+",
    "batchim": null,
    "group": null,
    "label": "문자 '+' (U+002B)",
    "example": "+",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_002C",
    "kind": "latin",
    "jamo": ",",
    "batchim": null,
    "group": null,
    "label": "문자 ',' (U+002C)",
    "example": ",",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_002D",
    "kind": "latin",
    "jamo": "-",
    "batchim": null,
    "group": null,
    "label": "문자 '-' (U+002D)",
    "example": "-",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_002E",
    "kind": "latin",
    "jamo": ".",
    "batchim": null,
    "group": null,
    "label": "문자 '.' (U+002E)",
    "example": ".",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_002F",
    "kind": "latin",
    "jamo": "/",
    "batchim": null,
    "group": null,
    "label": "문자 '/' (U+002F)",
    "example": "/",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0030",
    "kind": "latin",
    "jamo": "0",
    "batchim": null,
    "group": null,
    "label": "문자 '0' (U+0030)",
    "example": "0",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0031",
    "kind": "latin",
    "jamo": "1",
    "batchim": null,
    "group": null,
    "label": "문자 '1' (U+0031)",
    "example": "1",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0032",
    "kind": "latin",
    "jamo": "2",
    "batchim": null,
    "group": null,
    "label": "문자 '2' (U+0032)",
    "example": "2",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0033",
    "kind": "latin",
    "jamo": "3",
    "batchim": null,
    "group": null,
    "label": "문자 '3' (U+0033)",
    "example": "3",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0034",
    "kind": "latin",
    "jamo": "4",
    "batchim": null,
    "group": null,
    "label": "문자 '4' (U+0034)",
    "example": "4",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0035",
    "kind": "latin",
    "jamo": "5",
    "batchim": null,
    "group": null,
    "label": "문자 '5' (U+0035)",
    "example": "5",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0036",
    "kind": "latin",
    "jamo": "6",
    "batchim": null,
    "group": null,
    "label": "문자 '6' (U+0036)",
    "example": "6",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0037",
    "kind": "latin",
    "jamo": "7",
    "batchim": null,
    "group": null,
    "label": "문자 '7' (U+0037)",
    "example": "7",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0038",
    "kind": "latin",
    "jamo": "8",
    "batchim": null,
    "group": null,
    "label": "문자 '8' (U+0038)",
    "example": "8",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0039",
    "kind": "latin",
    "jamo": "9",
    "batchim": null,
    "group": null,
    "label": "문자 '9' (U+0039)",
    "example": "9",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_003A",
    "kind": "latin",
    "jamo": ":",
    "batchim": null,
    "group": null,
    "label": "문자 ':' (U+003A)",
    "example": ":",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_003B",
    "kind": "latin",
    "jamo": ";",
    "batchim": null,
    "group": null,
    "label": "문자 ';' (U+003B)",
    "example": ";",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_003C",
    "kind": "latin",
    "jamo": "<",
    "batchim": null,
    "group": null,
    "label": "문자 '<' (U+003C)",
    "example": "<",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_003D",
    "kind": "latin",
    "jamo": "=",
    "batchim": null,
    "group": null,
    "label": "문자 '=' (U+003D)",
    "example": "=",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_003E",
    "kind": "latin",
    "jamo": ">",
    "batchim": null,
    "group": null,
    "label": "문자 '>' (U+003E)",
    "example": ">",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_003F",
    "kind": "latin",
    "jamo": "?",
    "batchim": null,
    "group": null,
    "label": "문자 '?' (U+003F)",
    "example": "?",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0040",
    "kind": "latin",
    "jamo": "@",
    "batchim": null,
    "group": null,
    "label": "문자 '@' (U+0040)",
    "example": "@",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0041",
    "kind": "latin",
    "jamo": "A",
    "batchim": null,
    "group": null,
    "label": "문자 'A' (U+0041)",
    "example": "A",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0042",
    "kind": "latin",
    "jamo": "B",
    "batchim": null,
    "group": null,
    "label": "문자 'B' (U+0042)",
    "example": "B",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0043",
    "kind": "latin",
    "jamo": "C",
    "batchim": null,
    "group": null,
    "label": "문자 'C' (U+0043)",
    "example": "C",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0044",
    "kind": "latin",
    "jamo": "D",
    "batchim": null,
    "group": null,
    "label": "문자 'D' (U+0044)",
    "example": "D",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0045",
    "kind": "latin",
    "jamo": "E",
    "batchim": null,
    "group": null,
    "label": "문자 'E' (U+0045)",
    "example": "E",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0046",
    "kind": "latin",
    "jamo": "F",
    "batchim": null,
    "group": null,
    "label": "문자 'F' (U+0046)",
    "example": "F",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0047",
    "kind": "latin",
    "jamo": "G",
    "batchim": null,
    "group": null,
    "label": "문자 'G' (U+0047)",
    "example": "G",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0048",
    "kind": "latin",
    "jamo": "H",
    "batchim": null,
    "group": null,
    "label": "문자 'H' (U+0048)",
    "example": "H",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0049",
    "kind": "latin",
    "jamo": "I",
    "batchim": null,
    "group": null,
    "label": "문자 'I' (U+0049)",
    "example": "I",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_004A",
    "kind": "latin",
    "jamo": "J",
    "batchim": null,
    "group": null,
    "label": "문자 'J' (U+004A)",
    "example": "J",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_004B",
    "kind": "latin",
    "jamo": "K",
    "batchim": null,
    "group": null,
    "label": "문자 'K' (U+004B)",
    "example": "K",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_004C",
    "kind": "latin",
    "jamo": "L",
    "batchim": null,
    "group": null,
    "label": "문자 'L' (U+004C)",
    "example": "L",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_004D",
    "kind": "latin",
    "jamo": "M",
    "batchim": null,
    "group": null,
    "label": "문자 'M' (U+004D)",
    "example": "M",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_004E",
    "kind": "latin",
    "jamo": "N",
    "batchim": null,
    "group": null,
    "label": "문자 'N' (U+004E)",
    "example": "N",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_004F",
    "kind": "latin",
    "jamo": "O",
    "batchim": null,
    "group": null,
    "label": "문자 'O' (U+004F)",
    "example": "O",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0050",
    "kind": "latin",
    "jamo": "P",
    "batchim": null,
    "group": null,
    "label": "문자 'P' (U+0050)",
    "example": "P",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0051",
    "kind": "latin",
    "jamo": "Q",
    "batchim": null,
    "group": null,
    "label": "문자 'Q' (U+0051)",
    "example": "Q",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0052",
    "kind": "latin",
    "jamo": "R",
    "batchim": null,
    "group": null,
    "label": "문자 'R' (U+0052)",
    "example": "R",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0053",
    "kind": "latin",
    "jamo": "S",
    "batchim": null,
    "group": null,
    "label": "문자 'S' (U+0053)",
    "example": "S",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0054",
    "kind": "latin",
    "jamo": "T",
    "batchim": null,
    "group": null,
    "label": "문자 'T' (U+0054)",
    "example": "T",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0055",
    "kind": "latin",
    "jamo": "U",
    "batchim": null,
    "group": null,
    "label": "문자 'U' (U+0055)",
    "example": "U",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0056",
    "kind": "latin",
    "jamo": "V",
    "batchim": null,
    "group": null,
    "label": "문자 'V' (U+0056)",
    "example": "V",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0057",
    "kind": "latin",
    "jamo": "W",
    "batchim": null,
    "group": null,
    "label": "문자 'W' (U+0057)",
    "example": "W",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0058",
    "kind": "latin",
    "jamo": "X",
    "batchim": null,
    "group": null,
    "label": "문자 'X' (U+0058)",
    "example": "X",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0059",
    "kind": "latin",
    "jamo": "Y",
    "batchim": null,
    "group": null,
    "label": "문자 'Y' (U+0059)",
    "example": "Y",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_005A",
    "kind": "latin",
    "jamo": "Z",
    "batchim": null,
    "group": null,
    "label": "문자 'Z' (U+005A)",
    "example": "Z",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_005B",
    "kind": "latin",
    "jamo": "[",
    "batchim": null,
    "group": null,
    "label": "문자 '[' (U+005B)",
    "example": "[",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_005C",
    "kind": "latin",
    "jamo": "\\",
    "batchim": null,
    "group": null,
    "label": "문자 '\\' (U+005C)",
    "example": "\\",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_005D",
    "kind": "latin",
    "jamo": "]",
    "batchim": null,
    "group": null,
    "label": "문자 ']' (U+005D)",
    "example": "]",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_005E",
    "kind": "latin",
    "jamo": "^",
    "batchim": null,
    "group": null,
    "label": "문자 '^' (U+005E)",
    "example": "^",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_005F",
    "kind": "latin",
    "jamo": "_",
    "batchim": null,
    "group": null,
    "label": "문자 '_' (U+005F)",
    "example": "_",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0060",
    "kind": "latin",
    "jamo": "`",
    "batchim": null,
    "group": null,
    "label": "문자 '`' (U+0060)",
    "example": "`",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0061",
    "kind": "latin",
    "jamo": "a",
    "batchim": null,
    "group": null,
    "label": "문자 'a' (U+0061)",
    "example": "a",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0062",
    "kind": "latin",
    "jamo": "b",
    "batchim": null,
    "group": null,
    "label": "문자 'b' (U+0062)",
    "example": "b",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0063",
    "kind": "latin",
    "jamo": "c",
    "batchim": null,
    "group": null,
    "label": "문자 'c' (U+0063)",
    "example": "c",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0064",
    "kind": "latin",
    "jamo": "d",
    "batchim": null,
    "group": null,
    "label": "문자 'd' (U+0064)",
    "example": "d",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0065",
    "kind": "latin",
    "jamo": "e",
    "batchim": null,
    "group": null,
    "label": "문자 'e' (U+0065)",
    "example": "e",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0066",
    "kind": "latin",
    "jamo": "f",
    "batchim": null,
    "group": null,
    "label": "문자 'f' (U+0066)",
    "example": "f",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0067",
    "kind": "latin",
    "jamo": "g",
    "batchim": null,
    "group": null,
    "label": "문자 'g' (U+0067)",
    "example": "g",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0068",
    "kind": "latin",
    "jamo": "h",
    "batchim": null,
    "group": null,
    "label": "문자 'h' (U+0068)",
    "example": "h",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0069",
    "kind": "latin",
    "jamo": "i",
    "batchim": null,
    "group": null,
    "label": "문자 'i' (U+0069)",
    "example": "i",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_006A",
    "kind": "latin",
    "jamo": "j",
    "batchim": null,
    "group": null,
    "label": "문자 'j' (U+006A)",
    "example": "j",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_006B",
    "kind": "latin",
    "jamo": "k",
    "batchim": null,
    "group": null,
    "label": "문자 'k' (U+006B)",
    "example": "k",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_006C",
    "kind": "latin",
    "jamo": "l",
    "batchim": null,
    "group": null,
    "label": "문자 'l' (U+006C)",
    "example": "l",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_006D",
    "kind": "latin",
    "jamo": "m",
    "batchim": null,
    "group": null,
    "label": "문자 'm' (U+006D)",
    "example": "m",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_006E",
    "kind": "latin",
    "jamo": "n",
    "batchim": null,
    "group": null,
    "label": "문자 'n' (U+006E)",
    "example": "n",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_006F",
    "kind": "latin",
    "jamo": "o",
    "batchim": null,
    "group": null,
    "label": "문자 'o' (U+006F)",
    "example": "o",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0070",
    "kind": "latin",
    "jamo": "p",
    "batchim": null,
    "group": null,
    "label": "문자 'p' (U+0070)",
    "example": "p",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0071",
    "kind": "latin",
    "jamo": "q",
    "batchim": null,
    "group": null,
    "label": "문자 'q' (U+0071)",
    "example": "q",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0072",
    "kind": "latin",
    "jamo": "r",
    "batchim": null,
    "group": null,
    "label": "문자 'r' (U+0072)",
    "example": "r",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0073",
    "kind": "latin",
    "jamo": "s",
    "batchim": null,
    "group": null,
    "label": "문자 's' (U+0073)",
    "example": "s",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0074",
    "kind": "latin",
    "jamo": "t",
    "batchim": null,
    "group": null,
    "label": "문자 't' (U+0074)",
    "example": "t",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0075",
    "kind": "latin",
    "jamo": "u",
    "batchim": null,
    "group": null,
    "label": "문자 'u' (U+0075)",
    "example": "u",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0076",
    "kind": "latin",
    "jamo": "v",
    "batchim": null,
    "group": null,
    "label": "문자 'v' (U+0076)",
    "example": "v",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0077",
    "kind": "latin",
    "jamo": "w",
    "batchim": null,
    "group": null,
    "label": "문자 'w' (U+0077)",
    "example": "w",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0078",
    "kind": "latin",
    "jamo": "x",
    "batchim": null,
    "group": null,
    "label": "문자 'x' (U+0078)",
    "example": "x",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_0079",
    "kind": "latin",
    "jamo": "y",
    "batchim": null,
    "group": null,
    "label": "문자 'y' (U+0079)",
    "example": "y",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_007A",
    "kind": "latin",
    "jamo": "z",
    "batchim": null,
    "group": null,
    "label": "문자 'z' (U+007A)",
    "example": "z",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_007B",
    "kind": "latin",
    "jamo": "{",
    "batchim": null,
    "group": null,
    "label": "문자 '{' (U+007B)",
    "example": "{",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_007C",
    "kind": "latin",
    "jamo": "|",
    "batchim": null,
    "group": null,
    "label": "문자 '|' (U+007C)",
    "example": "|",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_007D",
    "kind": "latin",
    "jamo": "}",
    "batchim": null,
    "group": null,
    "label": "문자 '}' (U+007D)",
    "example": "}",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_007E",
    "kind": "latin",
    "jamo": "~",
    "batchim": null,
    "group": null,
    "label": "문자 '~' (U+007E)",
    "example": "~",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_2026",
    "kind": "latin",
    "jamo": "…",
    "batchim": null,
    "group": null,
    "label": "문자 '…' (U+2026)",
    "example": "…",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_2014",
    "kind": "latin",
    "jamo": "—",
    "batchim": null,
    "group": null,
    "label": "문자 '—' (U+2014)",
    "example": "—",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_2013",
    "kind": "latin",
    "jamo": "–",
    "batchim": null,
    "group": null,
    "label": "문자 '–' (U+2013)",
    "example": "–",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_00B7",
    "kind": "latin",
    "jamo": "·",
    "batchim": null,
    "group": null,
    "label": "문자 '·' (U+00B7)",
    "example": "·",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_201C",
    "kind": "latin",
    "jamo": "“",
    "batchim": null,
    "group": null,
    "label": "문자 '“' (U+201C)",
    "example": "“",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_201D",
    "kind": "latin",
    "jamo": "”",
    "batchim": null,
    "group": null,
    "label": "문자 '”' (U+201D)",
    "example": "”",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_2018",
    "kind": "latin",
    "jamo": "‘",
    "batchim": null,
    "group": null,
    "label": "문자 '‘' (U+2018)",
    "example": "‘",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_2019",
    "kind": "latin",
    "jamo": "’",
    "batchim": null,
    "group": null,
    "label": "문자 '’' (U+2019)",
    "example": "’",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_300C",
    "kind": "latin",
    "jamo": "「",
    "batchim": null,
    "group": null,
    "label": "문자 '「' (U+300C)",
    "example": "「",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_300D",
    "kind": "latin",
    "jamo": "」",
    "batchim": null,
    "group": null,
    "label": "문자 '」' (U+300D)",
    "example": "」",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_300E",
    "kind": "latin",
    "jamo": "『",
    "batchim": null,
    "group": null,
    "label": "문자 '『' (U+300E)",
    "example": "『",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_300F",
    "kind": "latin",
    "jamo": "』",
    "batchim": null,
    "group": null,
    "label": "문자 '』' (U+300F)",
    "example": "』",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_3010",
    "kind": "latin",
    "jamo": "【",
    "batchim": null,
    "group": null,
    "label": "문자 '【' (U+3010)",
    "example": "【",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_3011",
    "kind": "latin",
    "jamo": "】",
    "batchim": null,
    "group": null,
    "label": "문자 '】' (U+3011)",
    "example": "】",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_2605",
    "kind": "latin",
    "jamo": "★",
    "batchim": null,
    "group": null,
    "label": "문자 '★' (U+2605)",
    "example": "★",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_2606",
    "kind": "latin",
    "jamo": "☆",
    "batchim": null,
    "group": null,
    "label": "문자 '☆' (U+2606)",
    "example": "☆",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_2665",
    "kind": "latin",
    "jamo": "♥",
    "batchim": null,
    "group": null,
    "label": "문자 '♥' (U+2665)",
    "example": "♥",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_2661",
    "kind": "latin",
    "jamo": "♡",
    "batchim": null,
    "group": null,
    "label": "문자 '♡' (U+2661)",
    "example": "♡",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_25CB",
    "kind": "latin",
    "jamo": "○",
    "batchim": null,
    "group": null,
    "label": "문자 '○' (U+25CB)",
    "example": "○",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_25CF",
    "kind": "latin",
    "jamo": "●",
    "batchim": null,
    "group": null,
    "label": "문자 '●' (U+25CF)",
    "example": "●",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_25A1",
    "kind": "latin",
    "jamo": "□",
    "batchim": null,
    "group": null,
    "label": "문자 '□' (U+25A1)",
    "example": "□",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_25A0",
    "kind": "latin",
    "jamo": "■",
    "batchim": null,
    "group": null,
    "label": "문자 '■' (U+25A0)",
    "example": "■",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_25C7",
    "kind": "latin",
    "jamo": "◇",
    "batchim": null,
    "group": null,
    "label": "문자 '◇' (U+25C7)",
    "example": "◇",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_25C6",
    "kind": "latin",
    "jamo": "◆",
    "batchim": null,
    "group": null,
    "label": "문자 '◆' (U+25C6)",
    "example": "◆",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_25B3",
    "kind": "latin",
    "jamo": "△",
    "batchim": null,
    "group": null,
    "label": "문자 '△' (U+25B3)",
    "example": "△",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_25B2",
    "kind": "latin",
    "jamo": "▲",
    "batchim": null,
    "group": null,
    "label": "문자 '▲' (U+25B2)",
    "example": "▲",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_203B",
    "kind": "latin",
    "jamo": "※",
    "batchim": null,
    "group": null,
    "label": "문자 '※' (U+203B)",
    "example": "※",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_2192",
    "kind": "latin",
    "jamo": "→",
    "batchim": null,
    "group": null,
    "label": "문자 '→' (U+2192)",
    "example": "→",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_2190",
    "kind": "latin",
    "jamo": "←",
    "batchim": null,
    "group": null,
    "label": "문자 '←' (U+2190)",
    "example": "←",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_2191",
    "kind": "latin",
    "jamo": "↑",
    "batchim": null,
    "group": null,
    "label": "문자 '↑' (U+2191)",
    "example": "↑",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_2193",
    "kind": "latin",
    "jamo": "↓",
    "batchim": null,
    "group": null,
    "label": "문자 '↓' (U+2193)",
    "example": "↓",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_20A9",
    "kind": "latin",
    "jamo": "₩",
    "batchim": null,
    "group": null,
    "label": "문자 '₩' (U+20A9)",
    "example": "₩",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_00A9",
    "kind": "latin",
    "jamo": "©",
    "batchim": null,
    "group": null,
    "label": "문자 '©' (U+00A9)",
    "example": "©",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_00AE",
    "kind": "latin",
    "jamo": "®",
    "batchim": null,
    "group": null,
    "label": "문자 '®' (U+00AE)",
    "example": "®",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  },
  {
    "id": "latin_2122",
    "kind": "latin",
    "jamo": "™",
    "batchim": null,
    "group": null,
    "label": "문자 '™' (U+2122)",
    "example": "™",
    "zone_shape": [
      0,
      0,
      1000,
      1000
    ]
  }
]
~~~
