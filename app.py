"""
손글씨 TTF 폰트 생성기 - 메인 실행 스크립트
(한글 11,172자 자동 조합 + 영문/숫자/특수문자 지원)

사용법:
    python app.py template
        -> 손글씨 작성용 원고지 PDF 생성 (output/template.pdf, 여러 페이지 + 범례)
           한글 컴포넌트 183개(초성 6종/중성 2종/종성 1종) +
           영문 대소문자/숫자/특수문자 94개, 총 277개 컴포넌트 정보는
           data/manifest.json 에 저장된다.
           인쇄 후 손글씨로 채워서, 페이지 순서대로 스캔/촬영한 뒤
           data/scans/page1.jpg, page2.jpg ... 로 저장한다.

    python app.py build
        -> data/scans 안의 모든 page*.jpg 를 순서대로 전처리 -> 컴포넌트 분할
           -> 한글 11,172자(가능한 만큼) 자동 조합 + 영문/숫자/특수문자
           -> 폰트(.ttf) 생성까지 한 번에 실행
           결과물: output/MyHandwriting.ttf
           (컴포넌트를 일부만 채워도, 그 컴포넌트로 만들 수 있는 글자만 생성된다)
"""

import re
import sys
from pathlib import Path

import cv2

from modules.template import create_template
from modules.preprocess import preprocess
from modules.segment import segment
from modules.fontbuild import build_font


def ensure_dirs():
    for folder in ["data/scans", "data/glyphs", "output"]:
        Path(folder).mkdir(parents=True, exist_ok=True)


def step_template():
    ensure_dirs()
    create_template()
    print("output/template.pdf 생성 완료. 인쇄 후 손글씨로 채워서 스캔하세요.")
    print("스캔 파일은 data/scans/page1.jpg, page2.jpg ... 순서로 저장하세요.")


def _find_scan_pages(scan_dir="data/scans"):
    files = list(Path(scan_dir).glob("page*.jpg")) + list(Path(scan_dir).glob("page*.png"))

    def page_num(p):
        m = re.search(r"(\d+)", p.stem)
        return int(m.group(1)) if m else 0

    return sorted(files, key=page_num)


def step_build():
    ensure_dirs()

    pages = _find_scan_pages()

    if not pages:
        print("스캔 이미지가 없습니다 (data/scans/page1.jpg, page2.jpg ...).")
        print("먼저 'python app.py template' 로 원고지를 만들고, 손글씨를 채운 뒤")
        print("페이지 순서대로 스캔/촬영한 이미지를 data/scans 에 저장하세요.")
        return

    print(f"[1/3] 이미지 전처리 중... ({len(pages)}페이지)")
    images = []
    for p in pages:
        img = preprocess(str(p))
        cv2.imwrite(f"output/clean_{p.stem}.png", img)
        images.append(img)

    print("[2/3] 컴포넌트 분할 중...")
    segment(images)

    print("[3/3] 11,172자 자동 조합 + 폰트 생성 중...")
    build_font()

    print("완료! output/MyHandwriting.ttf 를 설치해서 확인해보세요.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"

    if cmd == "template":
        step_template()
    elif cmd == "build":
        step_build()
    else:
        print("알 수 없는 명령입니다. 'template' 또는 'build'를 사용하세요.")
