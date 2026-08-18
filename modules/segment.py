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