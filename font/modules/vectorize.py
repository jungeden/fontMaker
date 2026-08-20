import cv2
import numpy as np
from pathlib import Path

from config import APPROX_EPSILON


def find_contours_with_holes(img):
    """
    바깥 윤곽선뿐 아니라 안쪽 구멍(ㅇ,ㅎ,ㅁ,ㅂ 등의 속이 빈 부분)까지 찾는다.

    기존 코드는 cv2.RETR_EXTERNAL 을 사용했는데, 이 모드는 가장 바깥
    윤곽선만 반환하기 때문에 "ㅇ"이 속이 꽉 찬 "●"으로 만들어지는
    문제가 있었다. RETR_TREE + hierarchy 를 사용해야 안쪽 구멍을
    별도 contour로 받아올 수 있다.

    반환값:
        contours  : contour 리스트
        hierarchy : 각 contour의 [next, prev, first_child, parent] (N,4) 배열
                    hierarchy[i][3] != -1 이면 i번째 contour는 "구멍"이다.
    """
    binary = 255 - img  # 흰색=배경 -> 0, 검은색(글자)=255 로 반전

    contours, hierarchy = cv2.findContours(
        binary,
        cv2.RETR_TREE,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    if hierarchy is None:
        return [], np.zeros((0, 4), dtype=int)

    return contours, hierarchy[0]  # cv2가 (1, N, 4) 형태로 주므로 [0]


def simplify(contour, epsilon=APPROX_EPSILON):
    """점 개수를 줄여 다각형을 단순화한다 (곡선화 이전 전처리)."""
    return cv2.approxPolyDP(contour, epsilon, True)


def signed_area(pts):
    """Shoelace 공식. y축이 위로 향하는(y-up) 좌표계 기준 부호 있는 면적."""
    pts = np.asarray(pts, dtype=np.float64)
    x = pts[:, 0]
    y = pts[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)


def fix_winding(pts, is_hole):
    """
    TrueType(glyf) 규칙:
      - 바깥 윤곽선은 시계방향(CW)  -> signed_area < 0
      - 안쪽 구멍(hole)은 반시계방향(CCW) -> signed_area > 0
    이 규칙과 반대로 감겨 있으면 점 순서를 뒤집어 바로잡는다.
    이 처리를 안 하면 구멍이 안 뚫리거나, 반대로 바깥 윤곽선이
    구멍 취급되어 글자가 통째로 사라질 수 있다.
    """
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
