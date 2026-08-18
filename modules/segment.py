import json
import os
from pathlib import Path

import cv2
import numpy as np

from config import (
    ROWS, COLS, GLYPH_SIZE, TARGET_HEIGHT, BASELINE_MARGIN,
    STROKE_NORMALIZE, TARGET_STROKE_PX,
    STROKE_MAX_KERNEL_RADIUS, STROKE_MIN_AREA_RATIO, STROKE_MAX_ITERATIONS,
)

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


def _estimate_stroke_width(ink_mask):
    """
    전체 잉크 영역과 둘레 길이로 평균 획 굵기를 추정한다.

    가늘고 긴 직사각형이라고 가정하면 area ≈ width * length,
    perimeter ≈ 2 * length 이므로 width ≈ 2 * area / perimeter 로 근사할
    수 있다 (스켈레톤 추출 없이 빠르게 계산 가능한 표준적인 근사법).
    """
    contours, _ = cv2.findContours(ink_mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    area = cv2.countNonZero(ink_mask)
    perimeter = sum(cv2.arcLength(c, True) for c in contours)
    if perimeter <= 0:
        return 0
    return 2 * area / perimeter


def normalize_stroke_width(
    img,
    target_width=TARGET_STROKE_PX,
    max_kernel_radius=STROKE_MAX_KERNEL_RADIUS,
    min_area_ratio=STROKE_MIN_AREA_RATIO,
    max_iterations=STROKE_MAX_ITERATIONS,
):
    """
    모든 글자의 획 굵기가 서로 비슷해지도록 팽창(dilate)/침식(erode)으로
    보정한다.

    왜 필요한가: 벡터 도형을 확대/축소하면 획 굵기도 같이 확대/축소된다.
    한글은 자모마다 목표 높이(TARGET_HEIGHT)에 맞춰 강제로 확대/축소되고,
    라틴 문자는 사용자가 쓴 크기 그대로 들어가기 때문에, 아무 보정 없이는
    자모/문자마다 최종 획 굵기가 들쭉날쭉해진다.

    안전하게 보정하는 이유: 굵기 추정치(면적/둘레 비율)는 완벽하지 않다.
    특히 ㄲ,ㄸ처럼 여러 획이 겹치거나 꺾이는 부분이 많은 복잡한 모양은
    실제보다 두껍게 추정되기 쉬운데, 이 추정치를 과신해서 한 번에 크게
    깎아버리면 받침처럼 얇은 부분이 통째로 사라질 수 있다. 그래서
    - 한 번에 깎거나 붙이는 양을 max_kernel_radius로 제한하고,
    - 여러 번에 걸쳐 조금씩(다시 측정하면서) 목표에 다가가고,
    - 침식으로 잉크 면적이 min_area_ratio 밑으로 떨어지면 그 단계는
      즉시 취소한다(그 이전 상태를 그대로 유지).
    """
    if not STROKE_NORMALIZE:
        return img

    original_area = cv2.countNonZero(255 - img)
    if original_area == 0:
        return img

    current = img

    for _ in range(max_iterations):
        inv = 255 - current
        current_width = _estimate_stroke_width(inv)
        if current_width <= 1:
            break

        delta = (target_width - current_width) / 2  # 반지름 기준 보정량
        k = min(int(round(abs(delta))), max_kernel_radius)
        if k < 1:
            break

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k * 2 + 1, k * 2 + 1))

        if delta > 0:
            candidate = cv2.dilate(inv, kernel)
        else:
            candidate = cv2.erode(inv, kernel)
            if cv2.countNonZero(candidate) / original_area < min_area_ratio:
                break  # 더 깎으면 위험하니 여기서 멈추고 직전 상태를 유지

        current = 255 - candidate

    return current


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

    return normalize_stroke_width(canvas)


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

    전체적인 크기(대문자 기준 높이) 보정은 여기서 하지 않고
    modules/latin.py의 build_latin_glyphs()에서 폰트 좌표계로 변환한 뒤
    한 번에 처리한다 (모든 라틴 글자에 같은 배율을 적용해야 서로 비율이
    안 흐트러지기 때문).
    """
    inner = _inset(cell, margin_ratio=margin_ratio)
    if inner.shape[0] == 0 or inner.shape[1] == 0:
        return None
    resized = cv2.resize(inner, (canvas_size, canvas_size), interpolation=cv2.INTER_AREA)
    return normalize_stroke_width(resized)


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
