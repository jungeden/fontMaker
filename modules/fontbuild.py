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


def build_font(
    glyph_dir="data/glyphs",
    manifest_path="data/manifest.json",
    output_path="output/MyHandwriting.ttf",
    family_name="MyHandwriting",
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
