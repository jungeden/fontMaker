## 1

### hangul.py

~~~py

"""
한글 조합형 폰트를 위한 자모 데이터 + 배치 좌표 테이블.

핵심 아이디어
-------------
11,172자를 전부 손글씨로 받는 대신, "모양이 실제로 달라지는" 최소 단위만
손글씨로 받고 나머지는 좌표 기반으로 자동 조합한다.

- 초성(19개): 받침 유무(2) x 뒤에 오는 모음의 방향(3: 세로/가로/복합) 에 따라
  글자의 폭/위치가 크게 달라지므로 6가지 형태를 모두 받는다.  19 x 6 = 114
- 중성(21개): 받침 유무(2)에 따라 세로 길이가 달라지므로 2가지 형태를 받는다.
  21 x 2 = 42
- 종성/받침(27개): 항상 글자 하단의 같은 자리에만 오므로 형태 변화가 없다.
  1가지만 받는다.  27 x 1 = 27

합계 114 + 42 + 27 = 183칸만 손글씨로 받으면, 11,172자 전체를 조합할 수 있다.
"""

# 유니코드 한글 자모 순서 (KS X 1001 / 완성형 인덱스 순서와 동일)
CHO_LIST = list("ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ")            # 19
JUNG_LIST = list("ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ")        # 21
JONG_LIST = list("ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ")  # 27 (받침 없음은 별도 처리)

assert len(CHO_LIST) == 19
assert len(JUNG_LIST) == 21
assert len(JONG_LIST) == 27

# 중성을 모음의 "방향/형태" 3그룹으로 분류
#  V(세로형): 초성 오른쪽에 세로 획으로 붙는 모음 -> 초성이 좁고 길쭉해야 함 (가,개,너...)
#  H(가로형): 초성 아래에 가로 획으로 붙는 모음   -> 초성이 넓고 납작해야 함 (고,누,드...)
#  C(복합형): 가로+세로가 결합된 모음             -> 초성이 작고, 모음이 아래+오른쪽을 감쌈 (과,궈,희...)
VOWEL_GROUP = {
    "ㅏ": "V", "ㅐ": "V", "ㅑ": "V", "ㅒ": "V",
    "ㅓ": "V", "ㅔ": "V", "ㅕ": "V", "ㅖ": "V", "ㅣ": "V",
    "ㅗ": "H", "ㅛ": "H", "ㅜ": "H", "ㅠ": "H", "ㅡ": "H",
    "ㅘ": "C", "ㅙ": "C", "ㅚ": "C", "ㅝ": "C", "ㅞ": "C", "ㅟ": "C", "ㅢ": "C",
}
assert set(VOWEL_GROUP) == set(JUNG_LIST)

GROUP_LABEL = {"V": "세로모음", "H": "가로모음", "C": "복합모음"}

# ────────────────────────────────────────────────────────────
# 조합 좌표(zone) 테이블
# UPM 800x800 정사각형 안에서, (받침유무, 모음그룹) 조합마다
# 초성/중성/종성이 차지할 사각형 영역(x0,y0,x1,y1)을 정의한다.
# y=0이 베이스라인, y=800이 글자 상단이다.
#
# ※ 눈대중으로 잡은 기본값이다. 실제로 폰트를 뽑아보고 자소가 서로
#   겹치거나 비율이 어색하면 이 표의 숫자만 조정하면 된다.
# ────────────────────────────────────────────────────────────
ZONE_LAYOUTS = {
    # 받침 없음 + 세로모음 (가, 나, 비...) : 좌우 배치
    (False, "V"): {
        "cho":  (0,   0, 500, 800),
        "jung": (500, 0, 800, 800),
        "jong": None,
    },
    # 받침 없음 + 가로모음 (고, 누, 드...) : 상하 배치
    (False, "H"): {
        "cho":  (0, 380, 800, 800),
        "jung": (0,   0, 800, 460),
        "jong": None,
    },
    # 받침 없음 + 복합모음 (과, 궈, 희...) : 초성은 좌상단, 모음이 아래+오른쪽 감쌈
    (False, "C"): {
        "cho":  (0, 500, 560, 800),
        "jung": (0,   0, 800, 620),
        "jong": None,
    },
    # 받침 있음 + 세로모음 (각, 닫, 빛...)
    (True, "V"): {
        "cho":  (0,   280, 500, 800),
        "jung": (500, 280, 800, 800),
        "jong": (0,     0, 800, 280),
    },
    # 받침 있음 + 가로모음 (곡, 녹, 숙...)
    (True, "H"): {
        "cho":  (0, 620, 800, 800),
        "jung": (0, 280, 800, 660),
        "jong": (0,   0, 800, 280),
    },
    # 받침 있음 + 복합모음 (곽, 궐, 휙...)
    (True, "C"): {
        "cho":  (0, 660, 560, 800),
        "jung": (0, 280, 800, 760),
        "jong": (0,   0, 800, 280),
    },
}


def component_id(kind, jamo, batchim=None, group=None):
    """컴포넌트를 유일하게 식별하는 문자열 id를 만든다."""
    if kind == "cho":
        b = "B" if batchim else "N"
        return f"cho_{jamo}_{b}_{group}"
    if kind == "jung":
        b = "B" if batchim else "N"
        return f"jung_{jamo}_{b}"
    if kind == "jong":
        return f"jong_{jamo}"
    raise ValueError(kind)


def compose_char(cho, jung, jong=None):
    """초/중/종성 자모로부터 실제 완성형 한글 한 글자를 조합한다 (예시 표시용)."""
    ci = CHO_LIST.index(cho)
    vi = JUNG_LIST.index(jung)
    ji = (JONG_LIST.index(jong) + 1) if jong else 0
    code = 0xAC00 + (ci * 21 + vi) * 28 + ji
    return chr(code)


def decompose_code(code):
    """완성형 한글 코드포인트(0xAC00~0xD7A3) -> (초성, 중성, 종성 or None)."""
    s_index = code - 0xAC00
    ci = s_index // (21 * 28)
    vi = (s_index % (21 * 28)) // 28
    ji = s_index % 28

    cho = CHO_LIST[ci]
    jung = JUNG_LIST[vi]
    jong = JONG_LIST[ji - 1] if ji > 0 else None
    return cho, jung, jong


def _example_for_cho(cho, batchim, group):
    # 해당 그룹에 속한 모음 중 아무거나 하나로 예시를 만든다.
    jung = next(v for v, g in VOWEL_GROUP.items() if g == group)
    jong = JONG_LIST[0] if batchim else None
    return compose_char(cho, jung, jong)


def _example_for_jung(jung, batchim):
    jong = JONG_LIST[0] if batchim else None
    return compose_char("ㄱ", jung, jong)


def _example_for_jong(jong):
    return compose_char("ㄱ", "ㅏ", jong)


def build_component_list():
    """
    손글씨로 받아야 할 183개 컴포넌트 목록을 순서대로 만든다.
    이 순서가 곧 템플릿 칸 순서 = data/glyphs 안 PNG 인덱스 순서가 된다.
    """
    components = []

    for cho in CHO_LIST:
        for batchim in (False, True):
            for group in ("V", "H", "C"):
                components.append({
                    "id": component_id("cho", cho, batchim, group),
                    "kind": "cho",
                    "jamo": cho,
                    "batchim": batchim,
                    "group": group,
                    "label": f"초성 {cho} · {'받침있음' if batchim else '받침없음'} · {GROUP_LABEL[group]}",
                    "example": _example_for_cho(cho, batchim, group),
                    "zone_shape": ZONE_LAYOUTS[(batchim, group)]["cho"],
                })

    for jung in JUNG_LIST:
        for batchim in (False, True):
            group = VOWEL_GROUP[jung]
            components.append({
                "id": component_id("jung", jung, batchim),
                "kind": "jung",
                "jamo": jung,
                "batchim": batchim,
                "group": None,
                "label": f"중성 {jung} · {'받침있음' if batchim else '받침없음'}",
                "example": _example_for_jung(jung, batchim),
                "zone_shape": ZONE_LAYOUTS[(batchim, group)]["jung"],
            })

    for jong in JONG_LIST:
        components.append({
            "id": component_id("jong", jong),
            "kind": "jong",
            "jamo": jong,
            "batchim": True,
            "group": None,
            "label": f"종성(받침) {jong}",
            "example": _example_for_jong(jong),
            "zone_shape": (0, 0, 800, 280),  # 임의의 받침 zone 하나 기준
        })

    return components


~~~

#### 질문

여기서 각 문자 파일은 800x800이라고 했을 때 조합할 때 위치만 조정하고 각 파일 비율은 안바뀌게 하는 방법 없어? 문자 모양이 찌그러지지 않았으면 좋겠어. 원본 비율대로 하고 싶어.

#### 답변

가능해. 오히려 **폰트를 만들 때는 그 방법이 더 좋다**고 생각해.

지금 `ZONE_LAYOUTS`를 보면 각 자모가 들어갈 **영역(zone)**만*정의되어 있는데, 만약 조합 코드에서

```python
800x800 원본 이미지
↓
zone 크기(예: 500x800)에 맞게 resize
↓
배치
```

이렇게 하고 있다면 글자가 납작하거나 길쭉하게 찌그러질 수밖에 없어.

---

## 원하는 방식

예를 들어 초성 ㄱ 이미지가 항상

```
800 x 800
```

이라면

```
원본 : 800x800
↓
비율 유지(scale 동일)
↓
x,y 위치만 이동
↓
800x800 캔버스에 합성
```

이렇게 하는 것이다.

즉

```
가

┌────────────────────┐
│      ㄱ            │
│                    │
│             ㅏ     │
│                    │
└────────────────────┘
```

여기서

* ㄱ는 크기 그대로
* ㅏ도 크기 그대로

단지 위치만 옮긴다.

---

# 그럼 ZONE 대신 OFFSET을 쓰면 된다

지금은

```python
"cho": (0,0,500,800)
```

처럼 영역을 저장하고 있는데

이걸

```python
"cho": (x, y)
"jung": (x, y)
"jong": (x, y)
```

만 저장하는 것이다.

예를 들면

```python
LAYOUT = {

(False,"V"):{

    "cho": (20,0),

    "jung": (390,0),

},

(False,"H"):{

    "cho": (0,180),

    "jung": (0,-160),

},

(True,"V"):{

    "cho": (20,120),

    "jung": (390,120),

    "jong": (0,-250),

}

}
```

이렇게.

---

그 다음 조합은

```python
canvas = Image.new("RGBA",(800,800),(0,0,0,0))

canvas.alpha_composite(cho_img, dest=(20,120))
canvas.alpha_composite(jung_img, dest=(390,120))
canvas.alpha_composite(jong_img, dest=(0,-250))
```

처럼 한다.

**resize는 전혀 하지 않는다.**

---

# 또는 "비율 유지 + 자동 축소"

더 좋은 방법도 있다.

만약

```
zone = 500 x 800
```

이고

원본이

```
800 x 800
```

이면

### 지금 방식

```
800x800
↓

500x800

(가로만 줄어서 찌그러짐)
```

---

### 추천 방식

```
800x800

↓

500x500

(비율 유지)

↓

가운데 배치
```

즉

```python
ratio = min(zone_w/img_w,
            zone_h/img_h)

new_w = img_w*ratio
new_h = img_h*ratio
```

이렇게 하면

```
800x800

↓

500x500
```

가 되고

```
남는 공간은

자동 가운데 정렬
```

된다.

그래서

```
ㅁ
```

처럼 정사각형 글자도

```
ㄱ
```

처럼 긴 글자도

절대 찌그러지지 않는다.

---

# 내가 추천하는 방법

폰트를 만들 목적이라면 저는 **위치 + 비율 유지 축소** 방식을 추천합니다.

* ✅ 원본 손글씨 비율이 유지됨
* ✅ 글자가 절대 찌그러지지 않음
* ✅ 너무 큰 자모만 필요한 만큼만 균일하게 축소됨
* ✅ `ZONE_LAYOUTS`도 그대로 활용 가능
* ✅ 자모 간 간격은 `ZONE_LAYOUTS` 숫자만 조정하면 쉽게 튜닝 가능

즉, 현재 `ZONE_LAYOUTS`는 유지하되 **이미지를 zone 크기에 강제로 늘이거나 줄이지 말고**, `min(width_ratio, height_ratio)`로 **비율을 유지하며 축소한 뒤 zone 내부에 배치**하는 것이 가장 자연스러운 결과를 얻는 방법입니다.

## 2

### conpose.py

#### 기존 conpose.py

~~~py

import json
from pathlib import Path

from fontTools.pens.ttGlyphPen import TTGlyphPen

from config import UNITS_PER_EM
from modules.glyph import image_to_contours, draw_contour
from modules.hangul import (
    VOWEL_GROUP,
    ZONE_LAYOUTS,
    component_id,
    decompose_code,
)

HANGUL_START = 0xAC00
HANGUL_END = 0xD7A3  # inclusive


def load_component_contours(glyph_dir="data/glyphs", manifest_path="data/manifest.json"):
    """
    manifest.json(템플릿 생성 시 저장된 183개 컴포넌트 순서)과
    data/glyphs 안의 인덱스별 PNG를 읽어서, id -> contour 데이터 캐시를 만든다.
    """
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    glyph_dir = Path(glyph_dir)

    cache = {}
    missing = []

    for i, comp in enumerate(manifest):
        png = glyph_dir / f"{i:03}.png"
        if not png.exists():
            missing.append(comp["id"])
            continue

        contours = image_to_contours(png)
        if contours:
            cache[comp["id"]] = contours
        else:
            missing.append(comp["id"])

    return cache, missing

def _transform_contours(contours, zone, upm=UNITS_PER_EM):
    """
    컴포넌트가 그려진 1000x1000 기준 좌표를, 실제 음절 안에서 이 컴포넌트가
    차지할 사각형(zone)으로 이동/확대(letterbox 없이 딱 맞춰 늘림)한다.
    """
    x0, y0, x1, y1 = zone
    sx = (x1 - x0) / upm
    sy = (y1 - y0) / upm

    out = []
    for pts, is_hole in contours:
        new_pts = [(x * sx + x0, y * sy + y0) for x, y in pts]
        out.append((new_pts, is_hole))
    return out


def compose_syllable_glyph(cache, cho, jung, jong=None):
    """초/중/종성 자모 하나로 완성형 음절 하나의 TTGlyph를 조합한다."""
    group = VOWEL_GROUP[jung]
    has_batchim = jong is not None
    layout = ZONE_LAYOUTS[(has_batchim, group)]

    cho_contours = cache.get(component_id("cho", cho, has_batchim, group))
    jung_contours = cache.get(component_id("jung", jung, has_batchim))

    if cho_contours is None or jung_contours is None:
        return None  # 아직 손글씨로 채워지지 않은 컴포넌트

    all_contours = []
    all_contours += _transform_contours(cho_contours, layout["cho"])
    all_contours += _transform_contours(jung_contours, layout["jung"])

    if has_batchim:
        jong_contours = cache.get(component_id("jong", jong))
        if jong_contours is None:
            return None
        all_contours += _transform_contours(jong_contours, layout["jong"])

    pen = TTGlyphPen(None)
    for pts, _is_hole in all_contours:
        draw_contour(pen, pts)

    return pen.glyph()


def compose_all(glyph_dir="data/glyphs", manifest_path="data/manifest.json"):
    """
    가(0xAC00) ~ 힣(0xD7A3) 완성형 한글 11,172자를 전부 조합한다.
    아직 손글씨가 채워지지 않은 컴포넌트가 필요한 음절은 건너뛴다
    (부분적으로만 손글씨를 채워도 그 범위 내에서 폰트를 만들어볼 수 있다).

    반환값: (glyphs: {glyph_name: TTGlyph}, cmap: {codepoint: glyph_name},
             built_count, skipped_count)
    """
    cache, missing = load_component_contours(glyph_dir, manifest_path)

    if missing:
        print(f"참고: {len(missing)}개 컴포넌트가 아직 없어서 관련 음절은 제외됩니다.")

    glyphs = {}
    cmap = {}
    built = 0
    skipped = 0

    for code in range(HANGUL_START, HANGUL_END + 1):
        cho, jung, jong = decompose_code(code)

        glyph = compose_syllable_glyph(cache, cho, jung, jong)
        if glyph is None:
            skipped += 1
            continue

        gname = f"uni{code:04X}"
        glyphs[gname] = glyph
        cmap[code] = gname
        built += 1

    return glyphs, cmap, built, skipped


~~~

#### 크기 불변으로 수정

~~~py

# 크기 불변
def _transform_contours(contours, zone, upm=UNITS_PER_EM):

    x0, y0, x1, y1 = zone

    zone_w = x1 - x0
    zone_h = y1 - y0

    offset_x = x0 + (zone_w - upm) / 2
    offset_y = y0 + (zone_h - upm) / 2

    out=[]

    for pts,is_hole in contours:
        new_pts=[
            (
                x + offset_x,
                y + offset_y,
            )
            for x,y in pts
        ]
        out.append((new_pts,is_hole))

    return out

# 이렇게 바꿨더니 문자끼리 겹치는 문제 + 각 문자 크기 차이가 심하거나 부자연스러운 문제 발생

~~~

#### 크기 가변, 비율 유지로 수정

~~~py

#크기 가변, 비율 유지
def _transform_contours(contours, zone, upm=UNITS_PER_EM):
    """
    원본 비율을 유지하면서 zone 안에 맞춘다.
    (letterbox 방식)
    """
    x0, y0, x1, y1 = zone

    zone_w = x1 - x0
    zone_h = y1 - y0

    # 하나의 배율만 사용
    scale = min(zone_w / upm, zone_h / upm)

    draw_w = upm * scale
    draw_h = upm * scale

    # 가운데 정렬
    offset_x = x0 + (zone_w - draw_w) / 2
    offset_y = y0 + (zone_h - draw_h) / 2

    out = []

    for pts, is_hole in contours:
        new_pts = [
            (
                x * scale + offset_x,
                y * scale + offset_y,
            )
            for x, y in pts
        ]
        out.append((new_pts, is_hole))

    return out

# 이렇게 바꿨더니 너무 작고 초성과 종성, 중성이 크기가 애매한 문제 발생
~~~

## 3

#### 질문

어떤 자음은 너무 크고 어떤 건 너무 작고 이런 문제는 어떻게 해결하지? 뭐가 문제야?

#### 답변

좋은 질문입니다. 이건 **한글 조합형 폰트에서 가장 어려운 문제** 중 하나입니다.

결론부터 말하면, **현재 코드에는 각 자모의 실제 크기를 고려하는 과정이 전혀 없습니다.**

지금은 모든 자모를

> "1000×1000 안을 가득 채운 그림"

이라고 가정하고 배치하고 있습니다.

하지만 실제 손글씨는 그렇지 않습니다.

예를 들어

```
ㄱ
```

은 실제로 차지하는 면적이 작고

```
ㅁ
```

은 거의 정사각형을 꽉 채우며

```
ㅇ
```

은 가운데가 비어 있어서 실제 외곽 크기가 다르고

```
ㅊ
```

은 위쪽으로 튀어나갑니다.

그래서 같은 배율을 적용하면

```
ㄱ  → 작아 보임
ㅁ  → 커 보임
ㅇ  → 작아 보임
ㅎ  → 커 보임
```

이렇게 됩니다.

---

# 지금 코드의 문제

현재 compose에서는

```python
_transform_contours(...)
```

에서

```
1000
↓

zone
```

으로만 변환합니다.

즉

```
ㄱ의 실제 폭 = 420

ㅁ의 실제 폭 = 830
```

이어도

둘 다

```
1000 기준
```

으로 취급합니다.

---

# 실제 폰트들은 어떻게 하나?

폰트들은 거의 항상 **Bounding Box(외곽*박스)** 를 이용합니다.

예를 들어

```
ㄱ
```

의 실제 윤곽이

```
폭 380

높이 720
```

이면

그걸 기준으로 확대합니다.

반면

```
ㅁ
```

은

```
폭 780

높이 780
```

이므로

조금만 확대합니다.

즉

```
scale = zone / 실제크기
```

를 사용합니다.

지금은

```
scale = zone / 1000
```

입니다.

이 차이가 큽니다.

---

# 해결방법 1 (추천)

컨투어의 Bounding Box를 먼저 구합니다.

예를 들면

```python
xs = [x for pts,_ in contours for x,y in pts]
ys = [y for pts,_ in contours for x,y in pts]

minx = min(xs)
maxx = max(xs)
miny = min(ys)
maxy = max(ys)

glyph_w = maxx - minx
glyph_h = maxy - miny
```

그러면

```
ㄱ

폭 390
높이 760
```

이 나옵니다.

그 다음

```python
scale = min(
    zone_w / glyph_w,
    zone_h / glyph_h
)
```

를 사용합니다.

그러면

```
ㄱ
```

도

```
ㅁ
```

도

비슷한 시각적인 크기가 됩니다.

---

# 해결방법 2 (추천)

Bounding Box로 확대한 뒤

가운데 정렬합니다.

```
offset_x =
zone_x +
(zone_w - glyph_w*scale)/2

offset_y =
zone_y +
(zone_h - glyph_h*scale)/2
```

그러면

```
ㄱ

□□□□
□ ㄱ □
□□□□
```

처럼 항상 중앙에 옵니다.

---

# 해결방법 3 (가장 많이 사용)

폰트마다

```
ㄱ 1.08배

ㄴ 1.04배

ㅁ 0.94배

ㅇ 1.15배

ㅎ 0.98배
```

처럼 **자모별 보정값**을 둡니다.

예를 들어

```python
COMPONENT_SCALE = {

"ㄱ":1.08,

"ㄴ":1.05,

"ㄷ":1.02,

"ㅁ":0.93,

"ㅇ":1.15,

"ㅎ":0.97,

}
```

이렇게 하면 훨씬 보기 좋아집니다.

대부분의 상용 폰트도 이런 미세 조정을 합니다.

---

# 제가 추천하는 구조

현재 프로젝트라면 다음 순서로 개선하는 것이 가장 효과적입니다.

1. **Bounding Box 기반 크기 계산** (필수)
2. **비율 유지(scale = min(...))** (필수)
3. **Zone 안에서 가운데 정렬** (필수)
4. **자모별 미세 Scale 보정 테이블** (선택)
5. **자모별 x/y 위치 보정 테이블** (선택)

이렇게 하면 지금처럼 **"ㄱ은*너무 작고 ㅁ은 너무 크고 ㅇ은 허전한"** 문제가 거의 해결됩니다.

현재 코드 구조에서는 `_transform_contours()` 하나만 개선해도 1~3번을 모두 적용할 수 있고, 이후 `hangul.py`에 자모별 보정값 테이블을 추가하면 4~5번도 자연스럽게 확장할 수 있습니다. 이 방식이 유지보수도 쉽고 실제 폰트 제작 방식과도 가장 가깝습니다.

가능합니다. 다만 **지금 제안한 1~5번을 전부 적용하려면 단순히 `compose.py`와 `hangul.py`만 수정해서는 끝나지 않습니다.**

현재 구조에서는 다음과 같은 추가 작업이 필요합니다.

* `compose.py`

  * Bounding Box 계산
  * 비율 유지 스케일
  * 중앙 정렬
  * 자모별 Scale 보정
  * 자모별 Offset 보정
* `hangul.py`

  * 1000 UPM 기준 Zone 재설계
  * Scale/Offset 보정 테이블 추가
* **`manifest.json` 또는 컴포넌트 메타데이터**

  * 자모 종류(초성/중성/종성)를 이용해 보정값을 적용하도록 구조를 조금 변경하는 것이 좋습니다.

이렇게 수정하면 **각 파일이 300~500줄 이상**으로 늘어나고, `compose.py` 하나만 해도 현재보다 훨씬 길어집니다.

한 번의 답변에는 출력 가능한 코드 길이에 제한이 있어서, **전체 수정본을 한 메시지에 모두 담을 수 없습니다.** 중간이 잘리거나 일부 코드가 누락되어 그대로 붙여 넣으면 실행되지 않는 상태가 될 가능성이 큽니다.

### 제가 추천하는 방식

실사용 가능한 형태로 아래 순서대로 전체 파일을 작성해드리겠습니다.

1. **1단계:** `hangul.py` 전체 (1000 UPM 복원 + Zone 재설계 + Scale/Offset 보정 테이블 추가)
2. **2단계:** `compose.py` 전체 (Bounding Box 기반 자동 스케일 + 중앙 정렬 + 보정값 적용)
3. **3단계:** 테스트용 예제와 조정 방법(어떤 숫자를 바꾸면 크기와 위치가 바뀌는지)

이렇게 하면 각 파일을 그대로 덮어써도 실행 가능한 완전한 코드가 됩니다.

또한 이 기회에 **상용 한글 폰트에서 사용하는 방식**처럼 다음 기능도 함께 넣어드리겠습니다.

* ✅ Bounding Box 기반 자동 크기 맞춤
* ✅ 비율 유지(절대 찌그러지지 않음)
* ✅ Zone 내부 자동 중앙 정렬
* ✅ 자모별 Scale 보정(`ㄱ`, `ㅇ`, `ㅁ` 등)
* ✅ 자모별 X/Y Offset 보정
* ✅ 초성/중성/종성별 기본 Scale
* ✅ 받침 유무에 따른 자동 보정
* ✅ 모음 그룹(V/H/C)별 자동 보정

이렇게 해두면 나중에는 `hangul.py`의 숫자만 조금 수정해서 폰트 전체의 인상을 쉽게 조정할 수 있습니다.

### glyph.py

~~~py

import cv2
import numpy as np

from fontTools.pens.ttGlyphPen import TTGlyphPen

from config import UNITS_PER_EM, GLYPH_SIZE, CURVE_SMOOTHING
from modules.vectorize import find_contours_with_holes, simplify, fix_winding


def _scale_flip(pt, upm=UNITS_PER_EM, image_size=GLYPH_SIZE):
    """
    이미지 픽셀 좌표(0~800, y가 아래로 증가) -> 폰트 유닛 좌표(0~1000, y가 위로 증가).
    """
    x, y = pt
    x = x * upm / image_size
    y = y * upm / image_size
    return (x, upm - y)


def _midpoint(a, b):
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def image_to_contours(path):
    """
    글자 PNG 한 장을 (font-space 점 리스트, is_hole) 튜플들의 리스트로 변환한다.
    pen에 바로 그리지 않고 "폰트 좌표계로 변환된 윤곽선 데이터"만 반환하므로,
    이후 compose.py에서 이 데이터를 이동/확대해서 여러 글자를 조합하는 데 재사용할 수 있다.

    - RETR_TREE 기반으로 안쪽 구멍(ㅇ,ㅎ,ㅁ,ㅂ 등)을 지원한다.
    - 각 contour의 winding(방향)을 TrueType 규칙에 맞게 보정해서 반환한다.
    """
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None

    contours, hierarchy = find_contours_with_holes(img)
    if len(contours) == 0:
        return []

    result = []
    for i, contour in enumerate(contours):
        simplified = simplify(contour)
        pts = simplified.squeeze()

        if pts.ndim != 2 or len(pts) < 3:
            continue

        is_hole = hierarchy[i][3] != -1  # parent가 있으면 구멍(내부 윤곽선)

        font_pts = np.array([_scale_flip(p) for p in pts])
        font_pts = fix_winding(font_pts, is_hole)

        result.append((font_pts.tolist(), is_hole))

    return result


def draw_contour(pen, pts, smooth=CURVE_SMOOTHING):
    """
    폰트 좌표계로 변환된 점들을 pen에 그린다.

    smooth=True 이면 다각형의 각 꼭짓점을 2차 베지어의 제어점으로 쓰고,
    변의 중점을 on-curve 점으로 사용해 부드러운 곡선을 만든다.
    """
    pts = [tuple(p) for p in pts]
    if len(pts) < 3:
        return

    if smooth:
        n = len(pts)
        start = _midpoint(pts[-1], pts[0])
        pen.moveTo(start)
        for i in range(n):
            control = pts[i]
            end = _midpoint(pts[i], pts[(i + 1) % n])
            pen.qCurveTo(control, end)
        pen.closePath()
    else:
        pen.moveTo(pts[0])
        for p in pts[1:]:
            pen.lineTo(p)
        pen.closePath()


def image_to_glyph(path, smooth=CURVE_SMOOTHING):
    """
    글자 PNG 한 장을 fontTools TTGlyph 객체로 바로 변환한다.
    (개별 컴포넌트 미리보기/디버깅용. 실제 11,172자 합성에는 compose.py가
    image_to_contours() + draw_contour()를 직접 사용한다.)
    """
    contours = image_to_contours(path)
    if not contours:
        return TTGlyphPen(None).glyph()

    pen = TTGlyphPen(None)
    for pts, _is_hole in contours:
        draw_contour(pen, pts, smooth=smooth)

    return pen.glyph()


def glyph_advance_width(path, upm=UNITS_PER_EM, image_size=GLYPH_SIZE,
                         side_bearing=60):
    """개별 컴포넌트(자모)만 단독 글자로 만들 때 쓰는 폭 계산 (디버깅/미리보기용)."""
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return upm, side_bearing

    inv = 255 - img
    pts = cv2.findNonZero(inv)
    if pts is None:
        return upm, side_bearing

    _, _, w, _ = cv2.boundingRect(pts)
    glyph_width = w * upm / image_size

    advance = int(round(glyph_width + side_bearing * 2))
    return advance, side_bearing


~~~

이 프로젝트라면 저는 단순히 숫자 몇 개 바꾸는 수준이 아니라 **조합 엔진 자체를 조금 개선**하는 것을 추천합니다.

현재 구조를 보니

* `glyph.py` : 이미지 → contour 변환 ✔️
* `compose.py` : contour 조합 ✔️
* `hangul.py` : 배치 정보 ✔️

이렇게 역할 분리가 잘 되어 있습니다.

그래서 **`glyph.py`는 그대로 두고**, `compose.py`와 `hangul.py`만 수정하면 됩니다.

---

## 제가 추가할 기능

### 1. Bounding Box 자동 계산

현재는

```
1000×1000
```

전체를 기준으로 확대하지만

앞으로는

```
실제 글자 크기
```

를 계산합니다.

예를 들어

```
ㄱ

bbox
x=120~510
```

이면

폭은

```
390
```

으로 계산됩니다.

---

### 2. 비율 유지

현재

```
sx
sy
```

를 따로 쓰는데

앞으로는

```
scale=min(...)
```

하나만 사용합니다.

절대 찌그러지지 않습니다.

---

### 3. 가운데 정렬

현재는

```
왼쪽 위 기준
```

인데

앞으로는

```
zone 중심
```

으로 자동 정렬됩니다.

---

### 4. 자모별 Scale

예를 들면

```
ㄱ 1.08

ㄴ 1.05

ㅇ 1.12

ㅁ 0.95

ㅎ 0.98
```

처럼 보정됩니다.

---

### 5. 자모별 Offset

예를 들면

```
ㄱ
←10

ㅇ
↓5

ㅊ
↑8
```

같은 미세 조정을 넣습니다.

---

### 6. 초성/중성/종성 기본 Scale

예를 들면

```
초성
0.98

중성
1.00

종성
0.88
```

처럼 전체적으로도 조정 가능합니다.

---

### 7. 그룹별 보정

예를 들면

```
세로모음

초성 조금 크게

가로모음

중성 조금 아래

복합모음

초성 조금 왼쪽
```

이런 것도 넣습니다.

---

# hangul.py도 바꿀 예정

지금은

```
ZONE_LAYOUTS
```

밖에 없는데

앞으로는

```
ZONE_LAYOUTS

↓

COMPONENT_SCALE

↓

COMPONENT_OFFSET

↓

GROUP_SCALE

↓

GROUP_OFFSET
```

까지 모두 관리합니다.

---

# compose.py도

지금

```
_transform_contours()
```

하나만 있는데

다음처럼 분리할 예정입니다.

```
_get_bbox()

↓

_compute_scale()

↓

_compute_offset()

↓

_apply_transform()
```

그래서 유지보수도 쉬워집니다.

---

# 결과

예를 들어 지금

```
ㄱ
```

이 너무 작고

```
ㅇ
```

이 허전하면

앞으로는

```python
COMPONENT_SCALE = {
    "ㄱ": 1.10,
    "ㅇ": 1.15,
}
```

숫자 하나만 바꾸면 끝입니다.

---

## 제가 추가로 넣을 기능 (상용 폰트 수준)

여기서 한 단계 더 가서 **자동 Optical Scale**도 넣어드릴 생각입니다.

Bounding Box만 쓰면

```
ㅣ
```

같은 얇은 글자는 여전히 작아 보입니다.

그래서

```
실제 면적

+

Bounding Box

+

가로세로 비율
```

을 이용해서 자동으로

```
ㅣ

↓

약간 확대

ㅁ

↓

약간 축소
```

까지 계산하도록 만들겠습니다.

이 기능을 넣으면 지금처럼 **"ㄱ은*너무 작고, ㅁ은 너무 크고, ㅣ는 너무 얇고, ㅇ은 허전한"** 문제가 훨씬 줄어듭니다.

---

다만 이 정도면 `compose.py`가 약 **350줄**, `hangul.py`도 약 **250줄** 정도로 커집니다. 한 번의 답변으로는 전체 코드를 모두 담을 수 없으므로, 다음 답변부터 **실행 가능한 전체 코드**를 파일 단위로 나누어 제공하겠습니다. 먼저 **`hangul.py` 전체 수정본**부터 완성해서 드리고, 그 다음에 **`compose.py` 전체 수정본**을 이어서 드리겠습니다.

좋습니다. 그런데 제가 코드를 쭉 분석해 보니 **중간에 구조를 한 번 바꾸는 것이 훨씬 낫습니다.**

지금 프로젝트는 단순히 `_transform_contours()`만 수정해서는 상용 폰트처럼 자연스럽게 만들기 어렵습니다.

제가 추천하는 최종 구조는 아래와 같습니다.

```
glyph.py
    │
    ├─ contour 추출
    ├─ bbox 추출
    ├─ 면적 계산
    └─ aspect ratio 계산

            ↓

compose.py
    │
    ├─ bbox 기반 자동 scale
    ├─ Optical Scale
    ├─ Component Scale
    ├─ Group Scale
    ├─ Offset
    ├─ Zone Align
    └─ 합성

            ↓

hangul.py
    │
    ├─ ZONE_LAYOUTS
    ├─ COMPONENT_SCALE
    ├─ COMPONENT_OFFSET
    ├─ GROUP_SCALE
    ├─ GROUP_OFFSET
    ├─ KIND_SCALE
    └─ KIND_OFFSET
```

이렇게 하면 **새 폰트를 만들어도 숫자만 조금 바꾸면 끝**입니다.

---

# 그런데 여기서 하나 더 개선하고 싶은 게 있습니다

현재는

```
data/glyphs/
000.png
001.png
...
182.png
```

를 읽어서

```
image_to_contours()
```

를 호출합니다.

그런데 이때 **매번 bbox를 다시 계산**합니다.

11172자를 만들면

```
183개의 bbox를

11172번 반복 계산
```

하게 됩니다.

굉장히 비효율적입니다.

---

## 제가 추천하는 방식

`load_component_contours()`에서

```python
cache[id] = {
    "contours": ...,
    "bbox": ...,
    "area": ...,
    "aspect": ...
}
```

로 저장합니다.

그러면

```
bbox 계산

183번
```

만 하면 됩니다.

그 다음

```
11172자 조합
```

에서는

```
cache["bbox"]
```

만 읽으면 됩니다.

속도도 훨씬 빨라집니다.

---

# 그리고 이것도 추가하려고 합니다

현재

```
ZONE_LAYOUTS
```

는

```
(0,0,500,1000)
```

처럼 하드코딩입니다.

그런데 저는

```
anchor
```

개념도 넣을 생각입니다.

예를 들어

```
초성

LEFT

CENTER

RIGHT
```

```
중성

TOP

CENTER

BOTTOM
```

```
받침

BOTTOM_CENTER
```

처럼요.

그러면

```
ㄱ
```

과

```
ㅁ
```

이 서로 크기가 달라도

자동으로 기준점이 맞습니다.

상용 폰트 대부분이 이런 방식을 씁니다.

---

# 최종적으로는

### 지금

```
zone

↓

resize

↓

붙이기
```

에서

### 앞으로

```
bbox

↓

optical scale

↓

component scale

↓

group scale

↓

offset

↓

anchor align

↓

zone

↓

합성
```

으로 바뀝니다.

---

## 이 정도까지 만들면

거의 **조합형 한글 폰트 엔진** 수준입니다.

그리고 이 구조는 앞으로

* Variable Font
* 굵기 자동 생성
* 기울임체
* 자간 자동 보정
* 받침 위치 자동 조절

같은 기능도 쉽게 추가할 수 있습니다.

---

## 제가 제안하는 다음 작업 순서

이 프로젝트를 오래 사용할 계획이라면 단순히 현재 코드를 수정하는 것보다 아래 순서가 훨씬 좋습니다.

1. **1단계**: `hangul.py`를 리팩터링하여 Zone, Scale, Offset, Anchor 설정을 모두 포함하도록 재설계
2. **2단계**: `compose.py`를 Bounding Box 기반 자동 조합 엔진으로 전면 교체
3. **3단계**: `glyph.py`를 약간 수정하여 Bounding Box와 면적 정보를 함께 캐싱하도록 개선(기존 코드와 호환 유지)
4. **4단계**: 숫자만 조정해서 폰트를 다듬을 수 있는 설정 파일 형태로 정리

이렇게 해두면 지금 만드는 프로젝트는 이후에도 계속 확장 가능한 구조가 됩니다. 저는 이 방향을 추천드립니다.

## 4

~~~json

[
  {
    "id": "cho_ㄱ_N_V",
    "kind": "cho",
    "jamo": "ㄱ",
    "batchim": false,
    "group": "V",
    "label": "초성 ㄱ · 받침없음 · 세로모음",
    "example": "가",
    "zone_shape": [
      0,
      0,
      500,
      1000
    ]
  },
  {
    "id": "cho_ㄱ_N_H",
    "kind": "cho",
    "jamo": "ㄱ",
    "batchim": false,
    "group": "H",
    "label": "초성 ㄱ · 받침없음 · 가로모음",
    "example": "고",
    "zone_shape": [
      0,
      380,
      1000,
      1000
    ]
  },
  // etc...
]

~~~

### compose.py 수정?

~~~py

import json
from pathlib import Path
from fontTools.pens.ttGlyphPen import TTGlyphPen

from config import UNITS_PER_EM
from modules.glyph import image_to_contours, draw_contour
from modules.hangul import (
    VOWEL_GROUP,
    ZONE_LAYOUTS,
    component_id,
    decompose_code,
    KIND_SCALE,
    COMPONENT_SCALE,
    COMPONENT_OFFSET,
)

HANGUL_START = 0xAC00
HANGUL_END = 0xD7A3


def load_component_contours(glyph_dir="data/glyphs", manifest_path="data/manifest.json"):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    glyph_dir = Path(glyph_dir)

    cache = {}
    missing = []

    for i, comp in enumerate(manifest):
        png = glyph_dir / f"{i:03}.png"
        if not png.exists():
            missing.append(comp["id"])
            continue

        contours = image_to_contours(png)
        if contours:
            cache[comp["id"]] = contours
        else:
            missing.append(comp["id"])

    return cache, missing


def _get_contours_bbox(contours):
    """윤곽선 데이터에서 실제 글씨가 차지하는 최소/최대 좌표(Bounding Box)를 계산합니다."""
    if not contours:
        return 0, 0, 0, 0
    
    all_x = []
    all_y = []
    for pts, _ in contours:
        for x, y in pts:
            all_x.append(x)
            all_y.append(y)
            
    if not all_x:
        return 0, 0, 0, 0
        
    return min(all_x), min(all_y), max(all_x), max(all_y)


def _transform_contours(contours, zone, kind, jamo, upm=UNITS_PER_EM):
    """
    원본 비율을 완벽히 유지하면서, 자모의 실제 Bounding Box를 기반으로 
    해당 가이드 영역(zone)의 중앙에 맞추고 보정값을 적용합니다.
    """
    x0, y0, x1, y1 = zone
    zone_w = x1 - x0
    zone_h = y1 - y0

    # 1. 실제 손글씨 윤곽선의 크기(Bounding Box) 추출
    g_x0, g_y0, g_x1, g_y1 = _get_contours_bbox(contours)
    glyph_w = g_x1 - g_x0
    glyph_h = g_y1 - g_y0

    # 예외 처리: 유효한 윤곽선이 없다면 변환 없이 반환
    if glyph_w <= 0 or glyph_h <= 0:
        return contours

    # 2. 기본 배율 계산: 원본 비율을 유지하면서 가이드 영역(zone)에 가득 차도록 함 (Letterbox 방식)
    base_scale = min(zone_w / glyph_w, zone_h / glyph_h)

    # 3. hangul.py에 설정된 자모별/유형별 보정값 적용
    k_scale = KIND_SCALE.get(kind, 1.0)
    c_scale = COMPONENT_SCALE.get(jamo, 1.0)
    final_scale = base_scale * k_scale * c_scale

    # 4. 배율이 적용된 최종 크기 계산
    draw_w = glyph_w * final_scale
    draw_h = glyph_h * final_scale

    # 5. 가이드 영역(zone)의 한가운데로 오도록 정렬 위치 계산
    center_x = x0 + (zone_w - draw_w) / 2
    center_y = y0 + (zone_h - draw_h) / 2

    # 6. 자모별 미세 위치 오프셋 값 가져오기
    offset_x, offset_y = COMPONENT_OFFSET.get(jamo, (0, 0))

    # 7. 실제 좌표 이동값 계산 (글자 고유의 시작점 g_x0, g_y0를 0으로 영점 조절 후 center로 이동)
    final_x = center_x + offset_x - (g_x0 * final_scale)
    final_y = center_y + offset_y - (g_y0 * final_scale)

    out = []
    for pts, is_hole in contours:
        new_pts = [
            (x * final_scale + final_x, y * final_scale + final_y)
            for x, y in pts
        ]
        out.append((new_pts, is_hole))
        
    return out


def compose_syllable_glyph(cache, cho, jung, jong=None):
    """초/중/종성 자모 하나로 완성형 음절 하나의 TTGlyph를 조합합니다."""
    group = VOWEL_GROUP[jung]
    has_batchim = jong is not None
    layout = ZONE_LAYOUTS[(has_batchim, group)]

    cho_contours = cache.get(component_id("cho", cho, has_batchim, group))
    jung_contours = cache.get(component_id("jung", jung, has_batchim))

    if cho_contours is None or jung_contours is None:
        return None  # 컴포넌트 부족 시 스킵

    all_contours = []
    # _transform_contours에 자모 종류(kind)와 실제 자모 글자(jamo)를 함께 전달합니다.
    all_contours += _transform_contours(cho_contours, layout["cho"], "cho", cho)
    all_contours += _transform_contours(jung_contours, layout["jung"], "jung", jung)

    if has_batchim:
        jong_contours = cache.get(component_id("jong", jong))
        if jong_contours is None:
            return None
        all_contours += _transform_contours(jong_contours, layout["jong"], "jong", jong)

    pen = TTGlyphPen(None)
    for pts, _is_hole in all_contours:
        draw_contour(pen, pts)

    return pen.glyph()


def compose_all(glyph_dir="data/glyphs", manifest_path="data/manifest.json"):
    cache, missing = load_component_contours(glyph_dir, manifest_path)

    if missing:
        print(f"참고: {len(missing)}개 컴포넌트가 아직 없어서 관련 음절은 제외됩니다.")

    glyphs = {}
    cmap = {}
    built = 0
    skipped = 0

    for code in range(HANGUL_START, HANGUL_END + 1):
        cho, jung, jong = decompose_code(code)

        glyph = compose_syllable_glyph(cache, cho, jung, jong)
        if glyph is None:
            skipped += 1
            continue

        gname = f"uni{code:04X}"
        glyphs[gname] = glyph
        cmap[code] = gname
        built += 1

    return glyphs, cmap, built, skipped

~~~

### hangul.py 수정?

~~~py

"""
한글 조합형 폰트를 위한 자모 데이터 + 배치 좌표 테이블.
"""

# 유니코드 한글 자모 순서
CHO_LIST = list("ㄱ%ㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ")            # 19
JUNG_LIST = list("ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ")        # 21
JONG_LIST = list("ㄱ%ㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ")  # 27

assert len(CHO_LIST) == 19
assert len(JUNG_LIST) == 21
assert len(JONG_LIST) == 27

# 중성 모음 방향 분류
VOWEL_GROUP = {
    "ㅏ": "V", "ㅐ": "V", "ㅑ": "V", "ㅒ": "V",
    "ㅓ": "V", "ㅔ": "V", "ㅕ": "V", "ㅖ": "V", "ㅣ": "V",
    "ㅗ": "H", "ㅛ": "H", "ㅜ": "H", "ㅠ": "H", "ㅡ": "H",
    "ㅘ": "C", "ㅙ": "C", "ㅚ": "C", "ㅝ": "C", "ㅞ": "C", "ㅟ": "C", "ㅢ": "C",
}
assert set(VOWEL_GROUP) == set(JUNG_LIST)

GROUP_LABEL = {"V": "세로모음", "H": "가로모음", "C": "복합모음"}

# 조합 좌표(zone) 테이블 (UPM 800x800 혹은 1000x1000 내에서 자모가 배치될 가이드 영역)
ZONE_LAYOUTS = {
    # 받침 없음 + 세로모음 (가, 나, 비...) : 좌우 배치
    (False, "V"): {
        "cho":  (100, 100, 450, 900), # 350
        "jung": (400, 100, 900, 900), # 500
        "jong": None,
    },
    # 받침 없음 + 가로모음 (고, 누, 드...) : 상하 배치
    (False, "H"): {
        "cho":  (200, 550, 800, 900), # 350
        "jung": (100,   0, 900, 480), # 480
        "jong": None,
    },
    # 받침 없음 + 복합모음 (과, 궈, 희...) : 초성은 좌상단, 모음이 아래+오른쪽 감쌈
    (False, "C"): {
        "cho":  (100, 550, 750, 900), # 350
        "jung": (0,   0, 1000, 600), # 600
        "jong": None,
    },
    # 받침 있음 + 세로모음 (각, 닫, 빛...)
    (True, "V"): {
        "cho":  (100, 550, 400, 1000), # 350
        "jung": (400, 500, 1000, 1000), # 500
        "jong": (100, 50, 900, 400), # 350
    },
    # 받침 있음 + 가로모음 (곡, 녹, 숙...)
    (True, "H"): {
        "cho":  (0, 650, 1000, 1000), # 350
        "jung": (100, 370, 900, 670), # 400
        "jong": (150,   0, 1000, 350), # 350
    },
    # 받침 있음 + 복합모음 (곽, 궐, 휙...)
    (True, "C"): {
        "cho":  (200, 700, 560, 1000), # 360
        "jung": (200, 360, 800, 850), # 490
        "jong": (200, 0, 900, 360), # 300
    },
}

# ==========================================
# 자모별 미세 조정 고급 설정 테이블 (추가된 부분)
# ==========================================

# 1. 초성/중성/종성 유형별 기본 배율 (원하는 경우 전체적인 균형 조절 가능)
KIND_SCALE = {
    "cho": 1.0,   # 초성이 살짝 작아야 중성/종성과 잘 어우러짐
    "jung": 1.0,
    "jong": 0.95,  # 받침은 보통 조금 작게 배치해야 안정감이 있음
}

# 2. 특정 글자별 크기 보정 (시각적으로 작아 보이는 글자는 키우고, 큰 글자는 줄임)
# COMPONENT_SCALE = {
#     "ㄱ": 1.08, "ㄴ": 1.04, "ㄷ": 1.02, "ㄹ": 1.00, "ㅁ": 0.92,
#     "ㅂ": 0.95, "ㅅ": 1.04, "ㅇ": 1.12, "ㅈ": 1.00, "ㅊ": 1.00,
#     "ㅋ": 1.04, "ㅌ": 1.02, "ㅍ": 1.00, "ㅎ": 0.96,
#     "ㅣ": 1.05, "ㅡ": 0.95
# }
COMPONENT_SCALE = {
    "ㄱ": 1.00, "ㄴ": 1.00, "ㄷ": 1, "ㄹ": 1.00, "ㅁ": 1,
    "ㅂ": 1, "ㅅ": 1, "ㅇ": 1, "ㅈ": 1.00, "ㅊ": 1.00,
    "ㅋ": 1, "ㅌ": 1, "ㅍ": 1.00, "ㅎ": 1,
    "ㅣ": 1, "ㅡ": 1, "ㅜ": 0.9
}

# 3. 특정 글자별 위치 보정 (X축 이동, Y축 이동)
# 예: "ㅇ은 약간 아래로 내려야 예쁘다" 혹은 "ㅊ은 위 꼭지가 기니 아래로 내려야 한다" 일 때 사용
COMPONENT_OFFSET = {
    "ㅇ": (0, -5),
    "ㅎ": (0, -5),
    "ㅊ": (0, -5),
    "ㄱ": (0, 0),
    "ㅜ": (0, -3),
}


def component_id(kind, jamo, batchim=None, group=None):
    if kind == "cho":
        b = "B" if batchim else "N"
        return f"cho_{jamo}_{b}_{group}"
    if kind == "jung":
        b = "B" if batchim else "N"
        return f"jung_{jamo}_{b}"
    if kind == "jong":
        return f"jong_{jamo}"
    raise ValueError(kind)

def compose_char(cho, jung, jong=None):
    ci = CHO_LIST.index(cho)
    vi = JUNG_LIST.index(jung)
    ji = (JONG_LIST.index(jong) + 1) if jong else 0
    code = 0xAC00 + (ci * 21 + vi) * 28 + ji
    return chr(code)

def decompose_code(code):
    s_index = code - 0xAC00
    ci = s_index // (21 * 28)
    vi = (s_index % (21 * 28)) // 28
    ji = s_index % 28
    return CHO_LIST[ci], JUNG_LIST[vi], JONG_LIST[ji - 1] if ji > 0 else None

def _example_for_cho(cho, batchim, group):
    jung = next(v for v, g in VOWEL_GROUP.items() if g == group)
    return compose_char(cho, jung, JONG_LIST[0] if batchim else None)

def _example_for_jung(jung, batchim):
    return compose_char("ㄱ", jung, JONG_LIST[0] if batchim else None)

def _example_for_jong(jong):
    return compose_char("ㄱ", "ㅏ", jong)

def build_component_list():
    components = []
    for cho in CHO_LIST:
        for batchim in (False, True):
            for group in ("V", "H", "C"):
                components.append({
                    "id": component_id("cho", cho, batchim, group),
                    "kind": "cho", "jamo": cho, "batchim": batchim, "group": group,
                    "label": f"초성 {cho} · {'받침있음' if batchim else '받침없음'} · {GROUP_LABEL[group]}",
                    "example": _example_for_cho(cho, batchim, group),
                    "zone_shape": ZONE_LAYOUTS[(batchim, group)]["cho"],
                })
    for jung in JUNG_LIST:
        for batchim in (False, True):
            group = VOWEL_GROUP[jung]
            components.append({
                "id": component_id("jung", jung, batchim),
                "kind": "jung", "jamo": jung, "batchim": batchim, "group": None,
                "label": f"중성 {jung} · {'받침있음' if batchim else '받침없음'}",
                "example": _example_for_jung(jung, batchim),
                "zone_shape": ZONE_LAYOUTS[(batchim, group)]["jung"],
            })
    for jong in JONG_LIST:
        components.append({
            "id": component_id("jong", jong),
            "kind": "jong", "jamo": jong, "batchim": True, "group": None,
            "label": f"종성(받침) {jong}", "example": _example_for_jong(jong),
            "zone_shape": (0, 0, 800, 280),
        })
    return components

~~~
