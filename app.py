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