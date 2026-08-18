from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

from config import CHARS, UNITS_PER_EM, ASCENDER, DESCENDER
from modules.glyph import image_to_glyph, glyph_advance_width


def build_font(
    glyph_dir="data/glyphs",
    output_path="output/MyHandwriting.ttf",
    family_name="MyHandwriting",
    style_name="Regular",
):
    glyph_order = [".notdef"]
    glyphs = {".notdef": TTGlyphPen(None).glyph()}
    metrics = {".notdef": (UNITS_PER_EM, 0)}
    cmap = {}

    files = sorted(Path(glyph_dir).glob("*.png"))

    used = 0
    for file in files:
        idx = int(file.stem)  # segment.py가 "000.png", "001.png" ... 형식으로 저장

        if idx >= len(CHARS):
            # 문자셋(CHARS)에 정의되지 않은 칸은 건너뛴다.
            continue

        char = CHARS[idx]
        glyph_name = f"glyph{idx:03}"

        glyph = image_to_glyph(file)
        if glyph is None:
            continue

        glyph_order.append(glyph_name)
        glyphs[glyph_name] = glyph

        advance, lsb = glyph_advance_width(file)
        metrics[glyph_name] = (advance, lsb)

        cmap[ord(char)] = glyph_name
        used += 1

    if used == 0:
        raise RuntimeError(
            "생성된 글리프가 없습니다. data/glyphs 폴더에 분리된 글자 PNG가 "
            "있는지, config.py의 CHARS 설정이 맞는지 확인하세요."
        )

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

    print(f"{used}개 글자로 '{output_path}' 생성 완료")
    return output_path
