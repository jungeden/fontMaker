import cv2
import numpy as np
from pathlib import Path

from config import APPROX_EPSILON


def _compute_depths(hierarchy):
    """각 contour의 중첩 깊이. 0=바깥 윤곽선, 1=구멍, 2=구멍 속 채움..."""
    n = len(hierarchy)
    depth = [None] * n

    def depth_of(i):
        if depth[i] is not None:
            return depth[i]
        parent = hierarchy[i][3]
        d = 0 if parent == -1 else depth_of(parent) + 1
        depth[i] = d
        return d

    for i in range(n):
        depth_of(i)
    return depth


def _estimate_ink_stroke_width(binary_mask):
    """잉크 전체 면적/둘레로 평균 획 굵기를 추정한다 (segment.py의
    _estimate_stroke_width와 동일한 근사법: area ≈ width*length,
    perimeter ≈ 2*length 이므로 width ≈ 2*area/perimeter)."""
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    area = cv2.countNonZero(binary_mask)
    perimeter = sum(cv2.arcLength(c, True) for c in contours)
    if perimeter <= 0:
        return 0
    return 2 * area / perimeter


def _contour_max_inscribed_width(contour, canvas_shape):
    """이 윤곽선 안에 들어가는 가장 큰 원의 지름(=윤곽선이 감싼 영역의
    실제 "폭"). 가는 틈(노이즈)은 이 값이 작고, 진짜 구멍은 크다."""
    mask = np.zeros(canvas_shape, dtype=np.uint8)
    cv2.drawContours(mask, [contour], -1, 255, thickness=cv2.FILLED)
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    max_val = float(dist.max()) if dist.size else 0.0
    return max_val * 2  # 반지름 -> 지름


def find_contours_with_holes(img, min_hole_width_ratio=None, force_solid=False):
    """
    바깥 윤곽선뿐 아니라 안쪽 구멍까지 찾는다.

    - force_solid=True: 바깥 윤곽선(depth 0)만 남기고 안쪽은 전부 버린다.
      ★,♥,●,■,◆,▲처럼 "항상 꽉 차야 함"이 이미 확정된 글자에 쓴다.
    - min_hole_width_ratio: 구멍 후보의 "최대 내접 폭"이 그 글자 전체
      획 굵기의 이 배수보다 좁으면 노이즈(손으로 칠할 때 생긴 가는 틈)로
      보고 버린다. 면적이 아니라 폭 기준이라서 글자 크기와 무관하게
      ㅇ,ㅎ,☆,○,□,◇,△ 같은 진짜 넓은 구멍과 구분된다.

    반환값: contours, hierarchy, depth (depth[i] 홀수=구멍, 짝수=채움)
    """
    binary = 255 - img

    contours, hierarchy = cv2.findContours(
        binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE,
    )

    if hierarchy is None:
        return [], np.zeros((0, 4), dtype=int), []

    hierarchy = hierarchy[0]
    n = len(contours)
    depth = _compute_depths(hierarchy)

    drop = [False] * n

    if force_solid:
        for i in range(n):
            if depth[i] != 0:
                drop[i] = True
    elif min_hole_width_ratio:
        stroke_width = _estimate_ink_stroke_width(binary)
        if stroke_width > 0:
            min_width = stroke_width * min_hole_width_ratio
            for i in range(n):
                if depth[i] % 2 != 1:
                    continue  # 구멍 후보(홀수 depth)만 검사
                hole_width = _contour_max_inscribed_width(contours[i], img.shape)
                if hole_width < min_width:
                    drop[i] = True

    if any(drop):
        changed = True
        while changed:
            changed = False
            for i in range(n):
                parent = hierarchy[i][3]
                if parent != -1 and drop[parent] and not drop[i]:
                    drop[i] = True
                    changed = True

    keep_idx = [i for i in range(n) if not drop[i]]
    remap = {old: new for new, old in enumerate(keep_idx)}

    kept_contours = [contours[i] for i in keep_idx]
    kept_hierarchy = []
    kept_depth = []
    for i in keep_idx:
        nxt, prev, child, parent = hierarchy[i]
        kept_hierarchy.append([
            remap.get(nxt, -1), remap.get(prev, -1),
            remap.get(child, -1), remap.get(parent, -1),
        ])
        kept_depth.append(depth[i])

    kept_hierarchy = (
        np.array(kept_hierarchy, dtype=int) if kept_hierarchy else np.zeros((0, 4), dtype=int)
    )

    return kept_contours, kept_hierarchy, kept_depth


def simplify(contour, epsilon=APPROX_EPSILON):
    return cv2.approxPolyDP(contour, epsilon, True)


def signed_area(pts):
    pts = np.asarray(pts, dtype=np.float64)
    x = pts[:, 0]
    y = pts[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)


def fix_winding(pts, is_hole):
    pts = np.asarray(pts, dtype=np.float64)
    area = signed_area(pts)
    should_be_positive = is_hole
    if should_be_positive and area < 0:
        pts = pts[::-1]
    elif not should_be_positive and area > 0:
        pts = pts[::-1]
    return pts

# ── 아래는 디버그/미리보기용 SVG 출력 (폰트 생성 파이프라인 필수 요소는 아님) ──

def contours_to_svg_path(contours, hierarchy):
    """holes를 포함한 여러 contour를 하나의 SVG path data로 합친다 (fill-rule=evenodd 사용)."""
    path = ""

    for contour in contours:
        pts = contour.squeeze()
        if pts.ndim != 2 or len(pts) < 2:
            continue

        path += "M " + " ".join(f"{x},{y}" for x, y in pts) + " Z "

    return path.strip()


def save_svg(path_data, filename, size=800):
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
<path d="{path_data}" fill="black" fill-rule="evenodd"/>
</svg>
'''
    with open(filename, "w") as f:
        f.write(svg)


def convert_folder(glyph_dir="data/glyphs", svg_dir="data/svg"):
    """data/glyphs 의 모든 PNG를 미리보기용 SVG로 변환한다 (디버깅용)."""
    Path(svg_dir).mkdir(parents=True, exist_ok=True)

    count = 0
    for file in sorted(Path(glyph_dir).glob("*.png")):
        img = cv2.imread(str(file), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue

        contours, hierarchy = find_contours_with_holes(img)
        if len(contours) == 0:
            continue

        simplified = [simplify(c) for c in contours]
        path = contours_to_svg_path(simplified, hierarchy)

        save_svg(path, f"{svg_dir}/{file.stem}.svg")
        count += 1

    print(f"SVG {count}개 생성 완료")
