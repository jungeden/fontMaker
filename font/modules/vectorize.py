import cv2
import numpy as np
from pathlib import Path

from config import APPROX_EPSILON


def _compute_depths(hierarchy):
    """각 contour의 중첩 깊이. 0=바깥 윤곽선, 1=구멍, 2=구멍 속 채움(예: @의 안쪽 원)..."""
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


def find_contours_with_holes(img, min_hole_area_ratio=None):
    """
    바깥 윤곽선뿐 아니라 안쪽 구멍까지 찾는다.

    min_hole_area_ratio: 구멍 후보의 면적이 "바로 위" 부모 윤곽선 면적의
    이 비율보다 작으면, 의도한 구멍(ㅇ,ㅎ,☆,○,□,◇,△ 등)이 아니라 손으로
    칠할 때 생긴 작은 흰 얼룩(스캔/필기 노이즈)으로 보고 버린다(뚫지 않음).
    ★,♥,●,■,◆,▲ 처럼 원래 꽉 차야 하는 도형에서 노이즈 때문에 구멍이
    뚫리던 문제를 이걸로 막는다. 노이즈로 판정된 윤곽선의 자손(그 안에
    또 중첩된 것)도 같이 버린다.

    반환값: contours, hierarchy, depth (depth[i]가 홀수면 구멍, 짝수면 채움)
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
    if min_hole_area_ratio:
        areas = [cv2.contourArea(c) for c in contours]
        for i in range(n):
            parent = hierarchy[i][3]
            if parent == -1:
                continue
            parent_area = areas[parent]
            if parent_area > 0 and areas[i] / parent_area < min_hole_area_ratio:
                drop[i] = True

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
