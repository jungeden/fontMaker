import cv2
import numpy as np
import os

from config import ROWS, COLS, GLYPH_SIZE, TARGET_HEIGHT, BASELINE_MARGIN, CHARS


def _inset(cell, margin_ratio=0.12):
    """
    칸의 테두리 선(원고지 격자선) 자체가 글자로 오인식되는 것을 막기 위해
    칸 가장자리를 안쪽으로 살짝 잘라낸다.
    (원래 코드는 칸을 격자선 경계에 딱 맞춰 잘랐기 때문에, 실제 스캔에서는
    옆 칸과 공유하는 테두리 선이 'content'로 잡혀 빈 칸도 전부 글자가
    있는 것으로 오판되는 문제가 있었다.)
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
    """
    칸 정중앙이 아니라 살짝 치우쳐 쓰인 글자도 실제 잉크 영역 기준으로
    바운딩 박스만 잘라낸다. (guide.md에서 지적한 '칸 안에서 치우침' 문제 해결)
    테두리 선을 피하기 위해 먼저 칸 가장자리를 안쪽으로 inset한다.
    """
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
    비율을 유지한 채 글자 높이를 target_height 로 맞추고,
    모든 글자의 밑변이 같은 baseline 위에 놓이도록 정렬한 뒤
    canvas_size x canvas_size 크기의 흰색 캔버스에 배치한다.
    (guide.md의 '글자 크기 통일' + 'Baseline 맞추기' 두 단계를 한 번에 처리)
    """
    h, w = glyph.shape
    if h == 0 or w == 0:
        return None

    scale = target_height / h
    new_w = max(1, round(w * scale))
    new_h = max(1, round(h * scale))

    # 옆으로 아주 넓은 글자(예: 받침 없이 가로로 퍼진 손글씨)는 높이 기준으로
    # 맞추면 캔버스 폭을 넘어설 수 있으므로, 폭도 캔버스 안에 들어오도록
    # 한 번 더 제한한다.
    max_w = canvas_size - 2  # 최소한의 여백
    if new_w > max_w:
        scale *= max_w / new_w
        new_w = max(1, round(w * scale))
        new_h = max(1, round(h * scale))

    resized = cv2.resize(glyph, (new_w, new_h), interpolation=cv2.INTER_AREA)

    canvas = np.full((canvas_size, canvas_size), 255, dtype=np.uint8)

    x_offset = (canvas_size - new_w) // 2
    y_offset = canvas_size - baseline_margin - new_h  # 모든 글자를 같은 밑선에 정렬

    x_offset = max(0, min(x_offset, canvas_size - new_w))
    y_offset = max(0, min(y_offset, canvas_size - new_h))

    canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

    return canvas


def segment(image, output_dir="data/glyphs"):
    os.makedirs(output_dir, exist_ok=True)

    h, w = image.shape
    cell_w = w // COLS
    cell_h = h // ROWS

    idx = 0
    saved = 0

    for r in range(ROWS):
        for c in range(COLS):
            x = c * cell_w
            y = r * cell_h

            cell = image[y:y + cell_h, x:x + cell_w]

            # 사용자가 쓰지 않은 빈 칸은 저장하지 않는다.
            if not has_content(cell):
                idx += 1
                continue

            glyph = crop_content(cell)
            if glyph is None:
                idx += 1
                continue

            glyph = normalize_glyph(glyph)
            if glyph is None:
                idx += 1
                continue

            cv2.imwrite(f"{output_dir}/{idx:03}.png", glyph)
            saved += 1
            idx += 1

    total_defined = min(idx, len(CHARS))
    print(f"{saved}개의 글자 저장 완료 (문자셋 {total_defined}자 중)")
