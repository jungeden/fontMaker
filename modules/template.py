from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4

# 예제 문자
CHARS = [
    "가","나","다","라","마","바","사","아","자","차",
    "카","타","파","하","거","너","더","러","머","버",
    "서","어","저","처","커","터","퍼","허","고","노",
    "도","로","모","보","소","오","조","초","코","토",
    "포","호","구","누","두","루","무","부","수","우",
]

ROWS = 10
COLS = 10

CELL = 18 * mm

LEFT = 15 * mm
TOP = 20 * mm

def create_template(filename="output/template.pdf"):

    c = canvas.Canvas(filename, pagesize=A4)

    width, height = A4

    idx = 0

    for r in range(ROWS):

        for col in range(COLS):

            x = LEFT + col * CELL
            y = height - TOP - r * CELL

            c.rect(x, y - CELL, CELL, CELL)

            if idx < len(CHARS):

                c.setFont("Helvetica", 10)

                c.drawCentredString(
                    x + CELL/2,
                    y - CELL + 5,
                    CHARS[idx]
                )

            idx += 1

    c.save()