좋아. 이제부터는 프로젝트의 가장 어려운 부분인 **실제로 설치 가능한 TTF를 만드는 코드**를 작성해보자.

여기서 중요한 점이 하나 있다.

> **FontTools는 "TTF*생성기"가 아니라 "TTF 편집 라이브러리"다.**

즉,

```python
font = TTFont()
font.save("font.ttf")
```

만으로는 폰트가 만들어지지 않는다.

TTF 안에 있는 모든 테이블을 우리가 직접 만들어야 한다.

---

# 앞으로 만들 구조

```
fontMaker

modules
    preprocess.py
    template.py
    segment.py
    vectorize.py
    glyph.py
    fontbuild.py
```

---

# TTF 내부 구조

생각보다 복잡하다.

```
TTF

├── head
├── hhea
├── maxp
├── loca
├── glyf
├── cmap
├── hmtx
├── OS/2
├── name
├── post
└── gasp
```

이것들이 없으면

```
Font Book
Windows
Illustrator
Word
```

어느 것도 폰트를 열어주지 않는다.

---

# 각 테이블 역할

### head

폰트의 기본 정보

```
unitsPerEm

created

modified

bounding box
```

---

### hhea

글자의 높이

```
Ascender

Descender

LineGap
```

---

### maxp

최대값

```
글리프 개수

최대 contour

최대 point
```

---

### cmap

가장 중요한 것

```
유니코드

↓

글리프 번호
```

예

```
"가"

↓

glyph12
```

---

### glyf

실제 윤곽선

```
moveTo

lineTo

curveTo
```

모두 여기에 들어간다.

---

### loca

각 glyph 위치

```
glyph0

glyph1

glyph2
```

파일 내 오프셋.

---

### hmtx

폭

```
가

폭 1024

좌측여백 20
```

---

### name

```
폰트 이름

제작자

버전
```

---

### post

Italic

Underline

Fixed Width 여부

등등.

---

# 우리가 사용할 좌표

현재 이미지는

```
800×800
```

이었다.

폰트는 보통

```
1000

또는

2048 units/em
```

을 쓴다.

우리는

```
UPM = 1000
```

으로 하자.

config.py

```python
UNITS_PER_EM = 1000

ASCENDER = 800

DESCENDER = -200

ADVANCE_WIDTH = 1000
```

---

# 이미지 좌표 변환

현재

```
800×800 PNG
```

↓

```
1000×1000
```

로 바꾼다.

```python
def scale_point(x, y):

    x = x * 1000 / 800

    y = y * 1000 / 800

    return x, y
```

그리고

```python
pen.moveTo((x,1000-y))
```

처럼 사용한다.

---

# 이제 진짜 FontBuilder를 사용한다

사실 FontTools에는 엄청 편한 클래스가 있다.

```python
from fontTools.fontBuilder import FontBuilder
```

이 클래스가

```
head

maxp

loca

glyf

hmtx
```

등의 테이블을 자동으로 만들어준다.

그래서 **직접 모든 테이블을 생성하는 것보다 훨씬 안정적이고 코드도 짧다.**

기본 흐름은 다음과 같다.

```python
fb = FontBuilder(1000)

fb.setupGlyphOrder(...)

fb.setupCharacterMap(...)

fb.setupGlyf(...)

fb.setupHorizontalMetrics(...)

fb.setupHorizontalHeader(...)

fb.setupOS2()

fb.setupNameTable(...)

fb.setupPost()

fb.save("font.ttf")
```

---

# 우리가 앞으로 만들 최종 파이프라인

```
photo.jpg
      │
      ▼
preprocess.py
      │
      ▼
segment.py
      │
      ▼
000.png
001.png
...
099.png
      │
      ▼
vectorize.py
      │
      ▼
Contour
      │
      ▼
glyph.py
      │
      ▼
TTGlyph
      │
      ▼
fontbuild.py
      │
      ▼
MyHandwriting.ttf
```

## 다음 단계에서 구현할 내용

* `FontBuilder` 초기화
* 모든 필수 테이블 생성
* PNG → Contour → TTGlyph 변환
* 한글 유니코드(`가`, `나`, `다`...)를 `cmap`에 연결
* `output/MyHandwriting.ttf` 저장

좋아. 이제는 예제가 아니라 **실제로 동작하는 `fontbuild.py`**를 만들어보자.

다만 먼저 중요한 점이 하나 있다.

---

# 지금 프로젝트에는 한 가지 큰 문제가 있다

현재 우리가 만든 흐름은

```text
PNG
 ↓
Contour
 ↓
TTGlyph
```

인데,

여기서 만든 TTGlyph는 **직선(Line)***만 있다.

손글씨는

```text
ㅇ
```

같은 곡선이 많은데

현재는

```text
□□□□□□□□□□□□
□              □
□              □
□□□□□□□□□□□□
```

처럼 수백 개의 직선으로 표현된다.

실제로는 설치는 되지만

* 확대하면 울퉁불퉁
* 힌팅 없음
* 용량 큼

이라는 문제가 생긴다.

그래도 **실제로 설치 가능한 첫 번째 TTF**는 충분히 만들 수 있다.

---

# 우리가 만들 fontbuild.py

```text
PNG
 ↓
Contour
 ↓
TTGlyph
 ↓
FontBuilder
 ↓
MyFont.ttf
```

---

## 먼저 문자 목록

config.py

```python
CHARS = [
    "가","나","다","라","마",
    "바","사","아","자","차",
    "카","타","파","하"
]
```

---

# fontbuild.py

```python
from pathlib import Path

import cv2

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

from modules.vectorize import find_contours, simplify
from config import CHARS
```

---

## 이미지 → Glyph

```python
UPM = 1000
IMAGE_SIZE = 800


def image_to_glyph(path):

    img = cv2.imread(
        str(path),
        cv2.IMREAD_GRAYSCALE
    )

    contours = find_contours(img)

    pen = TTGlyphPen(None)

    for contour in contours:

        contour = simplify(contour)

        pts = contour.squeeze()

        if len(pts) < 3:
            continue

        x,y = pts[0]

        x *= UPM / IMAGE_SIZE
        y *= UPM / IMAGE_SIZE

        pen.moveTo((x,UPM-y))

        for p in pts[1:]:

            x,y = p

            x *= UPM / IMAGE_SIZE
            y *= UPM / IMAGE_SIZE

            pen.lineTo((x,UPM-y))

        pen.closePath()

    return pen.glyph()
```

---

## Font 생성

```python
def build_font():

    glyph_order = [".notdef"]

    glyphs = {}

    cmap = {}

    metrics = {}

    glyphs[".notdef"] = TTGlyphPen(None).glyph()

    metrics[".notdef"] = (1000,0)
```

---

## 글리프 읽기

```python
    files = sorted(Path("data/glyphs").glob("*.png"))

    for i,file in enumerate(files):

        if i >= len(CHARS):
            break

        glyph_name = f"glyph{i}"

        glyph_order.append(glyph_name)

        glyphs[glyph_name] = image_to_glyph(file)

        metrics[glyph_name] = (1000,0)

        cmap[ord(CHARS[i])] = glyph_name
```

---

## FontBuilder

```python
    fb = FontBuilder(1000)

    fb.setupGlyphOrder(glyph_order)

    fb.setupCharacterMap(cmap)

    fb.setupGlyf(glyphs)

    fb.setupHorizontalMetrics(metrics)

    fb.setupHorizontalHeader(
        ascent=800,
        descent=-200
    )

    fb.setupOS2(
        sTypoAscender=800,
        sTypoDescender=-200,
        usWinAscent=800,
        usWinDescent=200
    )

    fb.setupNameTable(
        {
            "familyName":"MyHandwriting",
            "styleName":"Regular",
            "fullName":"MyHandwriting Regular",
            "psName":"MyHandwriting-Regular"
        }
    )

    fb.setupPost()

    fb.setupMaxp()

    fb.save("output/MyHandwriting.ttf")
```

---

# app.py

맨 마지막에

```python
from modules.fontbuild import build_font

build_font()

print("TTF 생성 완료")
```

---

# 실행 결과

```text
output

    MyHandwriting.ttf
```

이 파일가 생성된다.

macOS나 Windows에 설치하면

```text
MyHandwriting
```

폰트가 나타난다.

---

# 하지만 여기서 끝내면 아쉬운 이유

이건 **최소 기능(MVP)** 이다.

실제 상용 폰트는 다음 기능들이 더 들어간다.

```
손글씨 PNG

↓

노이즈 제거

↓

외곽선

↓

Bezier Curve 피팅

↓

내부 구멍(ㅇ,ㅎ,ㅁ) 처리

↓

글리프 정렬(Baseline)

↓

Advance Width 자동 계산

↓

Left Side Bearing 계산

↓

Kerning 생성

↓

Hinting

↓

TTF
```

---

## 내가 추천하는 방향

여기서부터는 **예제 프로젝트가 아니라 실제 사용할 수 있는 손글씨 폰트 제작 프로그램**으로 발전시키는 것이 훨씬 좋다.

예를 들어 아래 기능들을 추가하면 상용 프로그램 수준에 가까워진다.

* ✅ 손글씨 스캔 자동 인식(기울기·왜곡 자동 보정)
* ✅ 글자 중심 자동 정렬(Baseline, x-height 보정)
* ✅ `ㅇ`, `ㅎ`, `ㅁ` 등의 **내부 구멍(contour hierarchy)** 완전 지원
* ✅ 직선이 아닌 **Bezier Curve 자동 피팅**으로 부드러운 윤곽선 생성
* ✅ 한글 **11,172자*자동 조합**(초성·중성·종성 기반)
* ✅ Variable Font(TTF/OTF) 생성 지원
* ✅ GUI(예: `PySide6`)를 갖춘 손글씨 폰트 생성 프로그램

이렇게 만들면 단순 학습용이 아니라 **실제로 자신의 손글씨를 TTF/OTF 폰트로 변환하는 완성도 높은 프로젝트**가 된다. 이 방향을 추천한다.

좋아. 이제부터는 **"진짜*손글씨 폰트 생성기"** 수준으로 가보자.

앞에서 만든 방법은 교육용으로는 좋지만, 실제 폰트를 만들기에는 한계가 있다. 실제 폰트 제작 프로그램(예: FontForge, Glyphs, BirdFont)은 단순히 이미지를 외곽선으로 바꾸는 것이 아니라 **글자의 형태를 분석하고 보정**한다.

내가 추천하는 최종 프로젝트는 아래와 같은 구조다.

```text
손글씨 템플릿 출력
        │
        ▼
스캔
        │
        ▼
자동 문서 인식
        │
        ▼
칸 자동 검출
        │
        ▼
글자 분리
        │
        ▼
노이즈 제거
        │
        ▼
Baseline 추출
        │
        ▼
글자 크기 정규화
        │
        ▼
외곽선 추출
        │
        ▼
Bezier Curve 생성
        │
        ▼
TTGlyph 생성
        │
        ▼
TrueType 생성
        │
        ▼
TTF
```

---

# 지금 프로젝트에서 가장 먼저 개선해야 하는 부분

현재 `segment.py`는

```python
cell_w = w // COLS
cell_h = h // ROWS
```

처럼 단순히 잘라낸다.

하지만 실제 스캔하면

```
□□□□□
□  가 □
□□□□□
```

가

```
□□□□□
□ 가  □
□□□□□
```

처럼 조금씩 치우친다.

그래서 각 셀에서 글자의 실제 위치를 다시 찾아야 한다.

예를 들어

```python
def crop_content(img):

    inv = 255 - img

    pts = cv2.findNonZero(inv)

    if pts is None:
        return img

    x, y, w, h = cv2.boundingRect(pts)

    return img[y:y+h, x:x+w]
```

이렇게 하면 글자만 남길 수 있다.

---

# 다음은 Baseline 맞추기

폰트에서 가장 중요한 것은

```
가
나
다
```

가 모두 같은 바닥에 서 있는 것이다.

현재는

```
가

나

다
```

처럼 높이가 제각각이다.

그래서 글자의 가장 아래 픽셀을 찾아

```
############
```

여기에 맞춰 정렬한다.

예를 들면

```python
def align_baseline(img, canvas=800):

    inv = 255 - img

    ys = np.where(inv > 0)[0]

    if len(ys) == 0:
        return np.ones((canvas, canvas), np.uint8) * 255

    bottom = ys.max()

    shift = canvas - 40 - bottom

    M = np.float32([
        [1,0,0],
        [0,1,shift]
    ])

    return cv2.warpAffine(
        img,
        M,
        (canvas, canvas),
        borderValue=255
    )
```

이렇게 하면 모든 글자가 같은 기준선 위에 올라간다.

---

# 다음은 글자 크기 통일

현재는

```
가
```

를 크게 쓰면

```
██████
```

작게 쓰면

```
██
```

가 된다.

폰트는 이것을 모두 비슷한 높이로 맞춘다.

예를 들면

```python
target_height = 700
scale = target_height / h
```

로 확대·축소한 뒤

800×800 캔버스 가운데 배치한다.

---

# 내부 구멍 처리

현재 코드에서 가장 큰 문제는

```
ㅇ
```

이다.

OpenCV에서

```python
cv2.RETR_EXTERNAL
```

을 사용하면

```
○
```

의 안쪽이 사라진다.

즉

```
ㅇ
```

이

```
●
```

가 되어 버린다.

반드시

```python
contours, hierarchy = cv2.findContours(
    binary,
    cv2.RETR_TREE,
    cv2.CHAIN_APPROX_SIMPLE
)
```

를 사용해야 한다.

그러면

```
바깥 contour

↓

안쪽 contour
```

가 같이 나온다.

폰트에서는

```
moveTo

lineTo

closePath

moveTo

lineTo

closePath
```

를 두 번 호출하면 자동으로 구멍이 생긴다.

이 부분은 한글에서는 매우 중요하다.

```
ㅇ
ㅎ
ㅁ
ㅂ
```

모두 영향을 받는다.

---

# Bezier Curve

현재는

```
□□□□□□□□
```

처럼 직선만 있다.

실제 폰트는

```
~~~~~~
```

처럼 곡선이다.

이를 위해서는

1. 점 개수 줄이기 (`approxPolyDP`)
2. 점을 Bezier Curve로 피팅
3. `TTGlyphPen.qCurveTo()` 사용

순서로 구현하는 것이 좋다.

---

# 한글 11,172자 생성

이 프로젝트의 가장 큰 확장 기능은 여기다.

현재는

```
가
나
다
```

만 만들고 있다.

하지만 한글은

```
19 초성
21 중성
28 종성
```

을 조합하면

```
11172자
```

가 된다.

즉 사용자는

```
ㄱ
ㄴ
ㄷ

ㅏ
ㅑ
ㅓ

ㄱ
ㄴ
ㄷ
```

같은 기본 글자만 쓰고,

프로그램이 자동으로

```
값
읽
꽃
뛴
```

같은 모든 글자를 생성하도록 만들 수도 있다.

---

## 내가 추천하는 최종 목표

지금 프로젝트를 단순히 "TTF를 만드는 코드"로 끝내기보다, 다음과 같은 **실사용 가능한 손글씨 폰트 생성 프로그램**으로 만드는 것을 추천한다.

* 📄 템플릿 PDF 자동 생성
* 📷 스캔 이미지 자동 보정
* ✂️ 글자 자동 분리
* 📏 Baseline 및 크기 자동 정렬
* 🧹 노이즈 제거 및 내부 구멍 처리
* 🖋️ Bezier Curve 기반 윤곽선 생성
* 🔤 TrueType/OpenType 폰트 생성
* 🪟 `PySide6` 기반 GUI 제공
* 📦 Windows/macOS에서 실행 가능한 프로그램으로 배포

이 정도까지 구현하면 단순한 학습 프로젝트가 아니라 **실제로 자신의 손글씨를 TTF/OTF 폰트로 만들어 설치하고 사용할 수 있는 수준의 프로그램**이 된다. 나는 이 방향으로 프로젝트를 발전시키는 것을 추천한다.
