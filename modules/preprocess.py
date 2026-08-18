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
        pts[np.argmax(diff)],   # 좌하
    ], dtype="float32")


def four_point_transform(image, pts):
    rect = order_points(pts)
    tl, tr, br, bl = rect

    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxWidth = int(max(widthA, widthB))

    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxHeight = int(max(heightA, heightB))

    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1],
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)

    return cv2.warpPerspective(image, M, (maxWidth, maxHeight))


def detect_page(image):
    """용지(문서) 외곽 4개 꼭짓점을 찾는다. 못 찾으면 None."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edge = cv2.Canny(blur, 75, 200)

    # 경계선이 끊어져 있으면 4각형 검출이 잘 안 되므로 살짝 팽창시켜 연결한다.
    edge = cv2.dilate(edge, np.ones((3, 3), np.uint8), iterations=1)

    contours, _ = cv2.findContours(
        edge, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
    )
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    image_area = image.shape[0] * image.shape[1]

    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        # 문서 검출이 너무 작은 잡음 컨투어를 잡지 않도록 최소 면적 제한을 둔다.
        if len(approx) == 4 and cv2.contourArea(approx) > image_area * 0.2:
            return approx.reshape(4, 2)

    return None


def preprocess(path):
    image = cv2.imread(path)

    if image is None:
        raise FileNotFoundError(f"이미지를 열 수 없습니다: {path}")

    pts = detect_page(image)

    if pts is not None:
        image = four_point_transform(image, pts)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 스캔/사진 촬영 시 생기는 잡음 제거 (기존 코드에 없던 부분 추가)
    gray = cv2.medianBlur(gray, 3)

    bw = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        10,
    )

    return bw
