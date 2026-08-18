import json
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

from config import UNITS_PER_EM, ASCENDER, DESCENDER, ADVANCE_WIDTH
from modules.compose import compose_all
from modules.latin import build_latin_glyphs


def build_font(
    glyph_dir="data/glyphs",
    manifest_path="data/manifest.json",
    output_path="output/MyHandwriting.ttf",
    family_name="MyHandwriting",
    style_name="Regular",
):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))

    hangul_glyphs, hangul_cmap, hangul_built, hangul_skipped = compose_all(
        glyph_dir, manifest_path
    )
    latin_glyphs, latin_cmap, latin_metrics, latin_built = build_latin_glyphs(
        glyph_dir, manifest
    )

    if hangul_built == 0 and latin_built == 0:
        raise RuntimeError(
            "조합/생성된 글자가 하나도 없습니다. data/glyphs 에 컴포넌트 PNG가 "
            "있는지, data/manifest.json이 있는지 확인하세요."
        )

    glyph_order = [".notdef"]
    glyphs = {".notdef": TTGlyphPen(None).glyph()}
    metrics = {".notdef": (UNITS_PER_EM, 0)}
    cmap = {}

    # 한글 음절은 전부 정사각형(전각) 글자이므로 advance width를 고정값으로 준다.
    for gname, glyph in hangul_glyphs.items():
        glyph_order.append(gname)
        glyphs[gname] = glyph
        metrics[gname] = (ADVANCE_WIDTH, 0)
    cmap.update(hangul_cmap)

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

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fb.save(output_path)

    print(f"한글 {hangul_built}자 (미완성 컴포넌트로 {hangul_skipped}자 제외) + "
          f"영문/숫자/특수문자 {latin_built}자, 총 {hangul_built + latin_built}자 "
          f"'{output_path}' 생성 완료")
    return output_path
