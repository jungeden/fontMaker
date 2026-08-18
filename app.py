"""
손글씨 TTF 폰트 생성기 - 메인 실행 스크립트

사용법:
    python app.py template
        -> 손글씨 작성용 원고지 PDF 생성 (output/template.pdf)
           인쇄 후 손글씨로 채워서 스캔/촬영한 뒤 data/scans/photo.jpg 로 저장한다.

    python app.py build
        -> 전처리 -> 글자 분할 -> 폰트(.ttf) 생성까지 한 번에 실행
           결과물: output/MyHandwriting.ttf

    python app.py svg
        -> (선택) data/glyphs 안의 PNG들을 SVG로 미리보기 변환 (디버깅용)
"""

import sys
from pathlib import Path

import cv2

from modules.template import create_template
from modules.preprocess import preprocess
from modules.segment import segment
from modules.fontbuild import build_font
from modules.vectorize import convert_folder


def ensure_dirs():
    for folder in ["data/scans", "data/glyphs", "data/svg", "output"]:
        Path(folder).mkdir(parents=True, exist_ok=True)


def step_template():
    ensure_dirs()
    create_template()
    print("output/template.pdf 생성 완료. 인쇄 후 손글씨로 채워서 스캔하세요.")


def step_build(scan_path="data/scans/photo.jpg"):
    ensure_dirs()

    if not Path(scan_path).exists():
        print(f"스캔 이미지가 없습니다: {scan_path}")
        print("먼저 'python app.py template' 로 원고지를 만들고, 손글씨를 채운 뒤")
        print(f"스캔/촬영한 이미지를 {scan_path} 경로에 저장하세요.")
        return

    print("[1/3] 이미지 전처리 중...")
    img = preprocess(scan_path)
    cv2.imwrite("output/clean_scan.png", img)

    print("[2/3] 글자 분할 중...")
    segment(img)

    print("[3/3] 폰트 생성 중...")
    build_font()

    print("완료! output/MyHandwriting.ttf 를 설치해서 확인해보세요.")


def step_svg():
    ensure_dirs()
    convert_folder()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"

    if cmd == "template":
        step_template()
    elif cmd == "build":
        step_build()
    elif cmd == "svg":
        step_svg()
    else:
        print("알 수 없는 명령입니다. 'template', 'build', 'svg' 중 하나를 사용하세요.")
