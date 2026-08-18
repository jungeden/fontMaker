## ttf 파일 만들기

### 구조

~~~
fontMaker
├── data
⎪       ├── glyphs
⎪       ├── scans
⎪       └── svg
⎪ 
├── modules
⎪       ├── __pycache__
⎪       ⎪       ├── preprocess.cpython-311.pyc
⎪       ⎪       └── template.cpython-311.pyc
⎪       ├── fontbuild.py
⎪       ├── glyph.py
⎪       ├── preprocess.py
⎪       ├── segment.py
⎪       ├── template.py
⎪       └── vectorize.py
├── output
⎪       └── template.pdf
├── Readme.md
├── guide.md
├── app.py
├── config.py
└── requirments.txt
~~~

### preprocess.py

~~~python

import cv2
import numpy as np

def order_points(pts):
    pts = np.array(pts, dtype="float32")

    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)

    return np.array([
        pts[np.argmin(s)],      # 좌상
        pts[np.argmin(diff)],   # 우상
        pts[np.argmax(s)],      # 우하
        pts[np.argmax(diff)]    # 좌하
    ], dtype="float32")


def four_point_transform(image, pts):

    rect = order_points(pts)

    tl, tr, br, bl = rect

    widthA = np.linalg.norm(br-bl)
    widthB = np.linalg.norm(tr-tl)

    maxWidth = int(max(widthA, widthB))

    heightA = np.linalg.norm(tr-br)
    heightB = np.linalg.norm(tl-bl)

    maxHeight = int(max(heightA, heightB))

    dst = np.array([
        [0,0],
        [maxWidth-1,0],
        [maxWidth-1,maxHeight-1],
        [0,maxHeight-1]
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(rect,dst)

    return cv2.warpPerspective(image,M,(maxWidth,maxHeight))

# 문서 찾기
def detect_page(image):

    gray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)

    blur = cv2.GaussianBlur(gray,(5,5),0)

    edge = cv2.Canny(blur,75,200)

    contours,_ = cv2.findContours(
        edge,
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE
    )

    contours = sorted(contours,key=cv2.contourArea,reverse=True)

    for c in contours:

        peri = cv2.arcLength(c,True)

        approx = cv2.approxPolyDP(c,0.02*peri,True)

        if len(approx)==4:

            return approx.reshape(4,2)

    return None

# 이미지보정
def preprocess(path):

    image = cv2.imread(path)

    pts = detect_page(image)

    if pts is not None:

        image = four_point_transform(image,pts)

    gray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)

    bw = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        10
    )

    return bw

~~~

### template.py

~~~python

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

~~~

### fontbuild.py

~~~py
from fontTools.ttLib import TTFont

font = TTFont()
~~~

### glyph.py

~~~py
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



~~~

### segment.py

~~~py
import cv2
import os

from config import *

def crop_glyph(img):

    inv = 255 - img

    coords = cv2.findNonZero(inv)

    if coords is None:
        return img

    x,y,w,h = cv2.boundingRect(coords)

    return img[
        y:y+h,
        x:x+w
    ]

def segment(image, output_dir="data/glyphs"):

    os.makedirs(output_dir, exist_ok=True)

    h, w = image.shape

    cell_w = w // COLS
    cell_h = h // ROWS

    idx = 0

    for r in range(ROWS):

        for c in range(COLS):

            x = c * cell_w
            y = r * cell_h

            glyph = image[
                y:y+cell_h,
                x:x+cell_w
            ]
            # 여백 제거
            glyph = crop_glyph(glyph)

            # 크기 통일
            glyph = cv2.resize(
                glyph,
                (GLYPH_SIZE, GLYPH_SIZE),
                interpolation=cv2.INTER_AREA
            )

            cv2.imwrite(
                f"{output_dir}/{idx:03}.png",
                glyph
            )

            idx += 1

    print(f"{idx}개의 글자 저장 완료")
~~~

### vectorize.py

~~~py
import cv2
import numpy as np

# 외각선 찾기

def find_contours(img):

    # 흰색=배경
    # 검은색=글자

    binary = 255 - img

    contours, hierarchy = cv2.findContours(
        binary,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    return contours

# contour 확인
def draw_contours(img):

    color = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    contours = find_contours(img)

    cv2.drawContours(
        color,
        contours,
        -1,
        (0,0,255),
        2
    )

    return color


# svg로 저장
def contour_to_svg(contour):

    points = contour.squeeze()

    if len(points) < 2:
        return ""

    path = "M "

    for p in points:
        x,y = p
        path += f"{x},{y} "

    path += "Z"

    return path

# svg 파일로 저장
def save_svg(path_data, filename, size=800):

    svg = f'''<svg
xmlns="http://www.w3.org/2000/svg"
width="{size}"
height="{size}"
viewBox="0 0 {size} {size}">

<path
d="{path_data}"
fill="black"/>

</svg>
'''

    with open(filename,"w") as f:
        f.write(svg)

#png 테스트
img = cv2.imread(
    "data/glyphs/000.png",
    cv2.IMREAD_GRAYSCALE
)

contours = find_contours(img)

path = contour_to_svg(contours[0])

save_svg(
    path,
    "data/svg/000.svg"
)


# 여러 글자 자동 생성
from pathlib import Path

def convert_folder():

    Path("data/svg").mkdir(exist_ok=True)

    for file in sorted(Path("data/glyphs").glob("*.png")):

        img = cv2.imread(
            str(file),
            cv2.IMREAD_GRAYSCALE
        )

        contours = find_contours(img)

        if len(contours)==0:
            continue

        path = contour_to_svg(contours[0])

        save_svg(
            path,
            f"data/svg/{file.stem}.svg"
        )


def simplify(contour):

    return cv2.approxPolyDP(
        contour,
        2,
        True
    )
contour = simplify(contour)
~~~

### app.py

~~~py
# from pathlib import Path

# folders = [
#     "data/scans",
#     "data/glyphs",
#     "data/svg",
#     "output"
# ]

# for folder in folders:
#     Path(folder).mkdir(parents=True, exist_ok=True)

# print("프로젝트 준비 완료")


# from pathlib import Path

# from modules.template import create_template

# Path("output").mkdir(exist_ok=True)

# create_template()

# print("template.pdf 생성 완료")


# from modules.preprocess import preprocess

# img = preprocess("data/scans/photo.jpg")

# import cv2

# cv2.imwrite("output/clean_scan.png",img)

# print("완료")


import cv2

from modules.preprocess import preprocess
from modules.segment import segment

img = preprocess("data/scans/photo.jpg")

cv2.imwrite(
    "output/clean_scan.png",
    img
)

segment(img)

print("완료")


# vectorize.py 

convert_folder()

print("SVG 생성 완료")



def scale_point(x, y):

    x = x * 1000 / 800

    y = y * 1000 / 800

    return x, y
~~~

### config.py

~~~py
PAGE_MARGIN = 20  # mm

ROWS = 10
COLS = 10

CELL_SIZE = 18  # mm

FONT_SIZE = 16
GLYPH_SIZE = 800

#

UNITS_PER_EM = 1000

ASCENDER = 800

DESCENDER = -200

ADVANCE_WIDTH = 1000

~~~

### requirments.txt

~~~txt

fonttools
opencv-python
numpy
Pillow
reportlab
svgpathtools
scipy

~~~
