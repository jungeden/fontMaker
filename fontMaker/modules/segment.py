import json
import os
from pathlib import Path

import cv2
import numpy as np

from config import ROWS, COLS, GLYPH_SIZE, TARGET_HEIGHT, BASELINE_MARGIN

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

    return canvas


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
    """
    inner = _inset(cell, margin_ratio=margin_ratio)
    if inner.shape[0] == 0 or inner.shape[1] == 0:
        return None
    return cv2.resize(inner, (canvas_size, canvas_size), interpolation=cv2.INTER_AREA)


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
