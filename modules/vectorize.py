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