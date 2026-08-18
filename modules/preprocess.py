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
        pts[np.argmax(diff)]    # 좌하
    ], dtype="float32")


def four_point_transform(image, pts):

    rect = order_points(pts)

    tl, tr, br, bl = rect

    widthA = np.linalg.norm(br-bl)
    widthB = np.linalg.norm(tr-tl)

    maxWidth = int(max(widthA, widthB))

    heightA = np.linalg.norm(tr-br)
    heightB = np.linalg.norm(tl-bl)

    maxHeight = int(max(heightA, heightB))

    dst = np.array([
        [0,0],
        [maxWidth-1,0],
        [maxWidth-1,maxHeight-1],
        [0,maxHeight-1]
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(rect,dst)

    return cv2.warpPerspective(image,M,(maxWidth,maxHeight))

# 문서 찾기
def detect_page(image):

    gray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)

    blur = cv2.GaussianBlur(gray,(5,5),0)

    edge = cv2.Canny(blur,75,200)

    contours,_ = cv2.findContours(
        edge,
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE
    )

    contours = sorted(contours,key=cv2.contourArea,reverse=True)

    for c in contours:

        peri = cv2.arcLength(c,True)

        approx = cv2.approxPolyDP(c,0.02*peri,True)

        if len(approx)==4:

            return approx.reshape(4,2)

    return None

# 이미지보정
def preprocess(path):

    image = cv2.imread(path)

    pts = detect_page(image)

    if pts is not None:

        image = four_point_transform(image,pts)

    gray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)

    bw = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        10
    )

    return bw