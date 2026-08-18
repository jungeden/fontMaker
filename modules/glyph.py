from fontTools.pens.ttGlyphPen import TTGlyphPen

pen = TTGlyphPen(None)
pen.moveTo((100,100))
# pen.moveTo((x,1000-y))
pen.lineTo((200,100))
pen.qCurveTo(

    (150,50),

    (200,100)

)
pen.closePath()
glyph = pen.glyph()

from fontTools.pens.ttGlyphPen import TTGlyphPen

def contour_to_glyph(contour):

    pen = TTGlyphPen(None)

    pts = contour.squeeze()

    if len(pts) < 2:
        return None

    x,y = pts[0]

    pen.moveTo((x,-y))

    for p in pts[1:]:

        x,y = p

        pen.lineTo((x,-y))

    pen.closePath()

    return pen.glyph()


