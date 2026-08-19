# 손글씨 TTF 폰트 생성기

내 손글씨로 완성형 한글 11,172자(가~힣) + 조합되지 않은 단독 자모(ㄱ, ㅏ 등) + 영문 대소문자

+ 숫자 + 특수문자/기호까지 담은 TTF 폰트를 만드는 도구. 커닝(kerning)과 힌팅(hinting)까지
자동으로 적용된다.

11,172자를 전부 손으로 쓰는 대신, **모양이 실제로 달라지는 최소 단위(183개)만** 손글씨로
받고, 나머지는 초성/중성/종성 조합 공식으로 자동 조립한다. 영문/숫자/특수문자(129개)는
한글과 달리 조합되지 않으므로 한 칸에 한 글자씩 그대로 받는다.

총 **183(한글 컴포넌트) + 129(영문/숫자/특수문자) = 312칸**만 손글씨로 채우면 된다.

**전체 빌드 없이 빠르게 미리보기하려면 `preview.py`를 쓰면 된다** (아래 "빠른 미리보기"
섹션 참고). ZONE_LAYOUTS나 HANGUL_FILL_RATIO 등을 조정할 때마다 11,172자 전체를 다시 빌드할
필요 없이 1~5초 안에 결과를 확인할 수 있다.

## 왜 183개인가 (한글)

+ **초성(19개) × 6가지 = 114개** — 받침 유무(2) × 뒤에 오는 모음의 방향(세로형/가로형/복합형,
  3)에 따라 초성의 폭과 위치가 달라진다. (예: "가"의 ㄱ과 "곡"의 ㄱ은 모양이 다르다)
+ **중성(21개) × 2가지 = 42개** — 받침 유무에 따라 모음의 세로 길이가 달라진다.
+ **종성/받침(27개) × 1가지 = 27개** — 받침은 항상 글자 하단의 같은 자리에만 오므로
  형태 변화가 없다.

114 + 42 + 27 = **183개**만 쓰면, 유니코드 조합 공식
`코드 = 0xAC00 + (초성인덱스×21 + 중성인덱스)×28 + 종성인덱스` 으로 11,172자를 전부 조합할 수 있다.

### 손글씨(컴포넌트)와 배치 좌표(zone)는 분리되어 있다

"어떤 손글씨를 쓸지"는 위처럼 큰 방향(세로형/가로형/복합형) 3종류만 받지만, "그걸 어디에
배치할지"는 그보다 더 세밀하게 9종류로 나눠서 조정할 수 있다. 같은 세로모음이라도 ㅏ 뒤에
오는 초성과 ㅓ 뒤에 오는 초성은 위치가 아주 살짝 다를 수 있기 때문에, 배치 좌표만 아래처럼
세분화해뒀다 (손글씨를 더 받을 필요는 없음 — 같은 손글씨를 재사용하되 위치/크기만 미세하게
다르게 조정 가능).

| 세부그룹 | 모음 | 세부그룹 | 모음 | 세부그룹 | 모음 |
|---|---|---|---|---|---|
| V1 (ㅏ계열) | ㅏㅑㅐㅒ | H1 (ㅗ계열) | ㅗㅛ | C1 (ㅘ계열) | ㅘㅚㅙ |
| V2 (ㅓ계열) | ㅓㅕㅔㅖ | H2 (ㅜ계열) | ㅜㅠ | C2 (ㅝ계열) | ㅝㅟㅞ |
| V3 (ㅣ계열) | ㅣ | H3 (ㅡ계열) | ㅡ | C3 (ㅢ계열) | ㅢ |

`modules/hangul.py`의 `ZONE_LAYOUTS`가 이 9개 세부그룹 × 받침유무(2) = 18개 좌표 세트를
갖고 있다. 예를 들어 **"거"(V2)에서만 받침 위치가 어색하다**면, 아래처럼 그 세부그룹만
직접 덮어쓰면 된다 (다른 세부그룹/다른 코드는 전혀 건드릴 필요 없음):

```python
# modules/hangul.py 아무 곳에나 (ZONE_LAYOUTS 정의 이후) 추가
ZONE_LAYOUTS[(True, "V2")] = {
    "cho":  (100, 560, 400, 1000),
    "jung": (400, 510, 1000, 1000),
    "jong": (100,  40, 900, 390),
}
```

또는 이미 있는 `_BASE_ZONE_LAYOUTS`(V/H/C 3그룹 기준값)를 고치면 그 그룹에 속한 세부그룹
3개(예: V → V1,V2,V3)가 한꺼번에 바뀐다. "전체적으로 이 방향의 글자들이 다 이상하다"면
`_BASE_ZONE_LAYOUTS`를, "이 방향 중에서도 특정 모음 하나만 이상하다"면 위처럼
`ZONE_LAYOUTS[(batchim, "V1")]` 개별 항목을 고치면 된다.

## 한글 크기 / 굵기 / 자간 조정 (ZONE_LAYOUTS처럼 수치로 조정하기)

`ZONE_LAYOUTS`가 "위치"를 정하는 것과 별개로, "크기"·"굵기"·"자간(글자 사이 간격)"은
전부 `config.py` 한 곳에 모아뒀다. 아래 표를 보고 증상에 맞는 값을 조정하면 된다.

| 증상 | 조정할 값 | 위치 | 기본값 |
|---|---|---|---|
| 한글 글자가 상자 안에서 너무 작다 | `HANGUL_FILL_RATIO`를 올린다 | config.py | 0.93 |
| 특정 조합에서 자모의 자리나 크기가 어색하다 | 해당 조합의 `ZONE_LAYOUTS`를 조정한다 | modules/hangul.py | - |
| 특정 손글씨 컴포넌트만 크기를 바꾸고 싶다 | `COMPONENT_SCALE`에 component id별 배율을 넣는다 | modules/hangul.py | 1.0 |
| 특정 손글씨 컴포넌트만 옮기고 싶다 | `COMPONENT_OFFSET`에 component id별 `(dx, dy)`를 넣는다 | modules/hangul.py | (0, 0) |
| H2 같은 한 조합 위치의 초성 전체를 조절하고 싶다 | `LAYOUT_COMPONENT_SCALE` / `LAYOUT_COMPONENT_OFFSET`에 `(종류, 받침유무, 그룹)` 키를 넣는다 | modules/hangul.py | 1.0 / (0, 0) |
| 한글 자간(글자 사이 간격)이 너무 넓다/좁다 | `ADVANCE_WIDTH`를 줄이거나/늘린다 | config.py | 950 |
| 획이 너무 얇다/두껍다 (한글) | `TARGET_STROKE_PX`를 올리거나/내린다 | config.py | 34 |
| 획이 너무 얇다/두껍다 (영문/숫자/기호) | `LATIN_TARGET_STROKE_PX`를 올리거나/내린다 | config.py | 34 |
| 받침 등 일부가 잘려서 나온다 | `CELL_INSET_RATIO`를 낮춘다 (이미 0.05로 낮춰둔 상태) | config.py | 0.05 |
| 영문 커닝(자간 보정)이 들쭉날쭉하다 | `KERNING_MAX_ABS`를 올린다 | config.py | 150 |

### 자모별 배율 보정을 쓰지 않는 이유

`다`와 `동`의 초성 ㄷ은 서로 다른 조합 자리(zone)를 쓴다. 하나의 전역 배율을
둘에 함께 곱하면, 넓고 낮은 자리에서는 지나치게 작아지고 좁고 높은 자리에서는
다른 결과가 난다. 그래서 조합기는 자모별 배율/문맥별 중앙값/넘침 재축소를 하지
않고, 원본 자모의 비율을 유지해 각 zone 안에 한 번만 맞춘다. 특정 조합의 균형이
문제라면 자모 전체가 아니라 그 조합군의 `ZONE_LAYOUTS`를 조정한다.

## 단독 자모 (ㄱ, ㅏ 등)

183개 컴포넌트 중 51개(초성 19 + 종성전용 겹받침 11 + 중성 21)는, 완성형 음절이 아니라
낱자 하나만 입력했을 때도(예: 한글 자음/모음 입력, 사전 표기 등) 폰트가 적용되도록 별도
글리프로 자동 생성된다. 추가로 손글씨를 받을 필요는 없다 — 이미 조합에 쓰인 컴포넌트
(초성은 "받침없음 + 세로모음", 중성은 "받침없음", 종성전용 겹받침은 종성 컴포넌트를 그대로)
를 재활용한다.

기본값은 **그 자모가 실제 음절 조합에 쓰일 때와 똑같은 크기**로 나온다 (예: 단독 ㄱ =
"가"에서 ㄱ이 차지하는 만큼의 크기). 위치만 조합 시의 한쪽으로 치우친 자리 대신 전체
박스 정중앙으로 옮겨서 표시한다.

**단독 자음 크기를 직접 지정하고 싶다면** `modules/hangul.py`의 `STANDALONE_HEIGHT_OVERRIDE`를
쓰면 된다:

```python
# modules/hangul.py
STANDALONE_HEIGHT_OVERRIDE = {
    "cho": 350,   # 단독 초성(ㄱ,ㄴ,ㄷ...) 표시 높이를 350(폰트 유닛)으로 고정
    "jung": None, # 모음은 그대로(자동, 조합 시와 동일한 크기) 유지
    "jong": None,
}
```

숫자를 넣으면 그 종류(초성/중성/종성)의 단독 표시가 항상 그 높이로 고정되고, `None`으로
두면 기존처럼 "실제 조합 시 크기"를 자동으로 재사용한다.

단독 자모만 따로 미세 조정하려면 `STANDALONE_JAMO_SCALE`과
`STANDALONE_JAMO_OFFSET`을 쓴다. 예를 들어 `{"ㄷ": 1.08}`은 단독 ㄷ만 8% 키우며,
완성형 음절 속 ㄷ에는 영향을 주지 않는다.

## 영문/숫자/특수문자 (129개)

출력 가능한 기본 ASCII 문자 전체(`!` ~ `~`, 94자)에 더해, 모바일 키보드 기호 화면 등에서
자주 쓰는 문자 35개(말줄임표 …, 스마트 따옴표 " " ' ', 대시 — –, 낫표 「」『』【】, 별/하트/
동그라미 등 기호 ★☆♥♡○●□■◇◆△▲, 화살표 →←↑↓, 통화/저작권 기호 ₩©®™)를 추가로
지원한다. 공백은 글자 모양이 없으므로 폭 값만 자동으로 채워진다.

### 한글과 크기/굵기를 맞추는 자동 보정

+ **크기**: 한글 자모는 `segment.py`에서 잉크만 잘라내지 않고 동일한 칸 캔버스로 보존한다.
  라틴 문자는 g/y/p 같은 내림선 글자의 baseline 정보를 지키기 위해 그런 보정을 하지 않는다.
  그대로 두면 사용자가 쓴 크기 그대로 들어가서 한글 옆에 있을 때 상대적으로 작아 보이는
  문제가 있었다. → 대문자 A~Z의 실제 손글씨 높이(중앙값)를 측정해서, 라틴 문자 전체에
  (개별 문자마다 다르게 적용하면 서로 비율이 깨지므로 반드시 전체에 동일하게) 배율 하나를
  곱해서 한글과 비슷한 시각적 무게감이 나도록 자동 보정한다 (`modules/latin.py`의
  `TARGET_CAP_HEIGHT`, 기본값 780 — 여전히 작아 보이면 이 값을 더 올리면 된다).
+ **굵기**: 벡터 도형을 확대/축소하면 획 굵기도 같이 확대/축소되기 때문에, 자모/문자마다
  확대 비율이 다르면 최종 굵기도 들쭉날쭉해진다. → 분할·정규화가 끝난 각 글자 이미지에서
  실제 획 굵기를 추정(잉크 면적 대비 둘레 길이 비율)한 뒤, 목표 굵기에 맞춰 팽창(dilate)/
  침식(erode) 처리로 보정한다 (`modules/segment.py`의 `normalize_stroke_width`,
  `config.py`의 `TARGET_STROKE_PX`).

  굵기 추정치는 완벽하지 않다 — 특히 ㄲ,ㄸ,ㄶ처럼 여러 획이 겹치거나 꺾이는 부분이 많은
  복잡한 모양은 실제보다 두껍게 추정되기 쉬운데, 이 추정치를 과신해서 한 번에 크게
  깎아버리면 받침처럼 얇은 부분이 통째로 사라지는 문제가 있었다. 그래서 지금은 한 번에
  깎는 양을 제한하고(`STROKE_MAX_KERNEL_RADIUS`), 여러 번에 걸쳐 조금씩 목표에
  다가가며(`STROKE_MAX_ITERATIONS`), 침식으로 잉크가 일정 비율 이상
  사라지면(`STROKE_MIN_AREA_RATIO`) 그 단계를 즉시 취소하고 직전 상태를 유지한다. 그래도
  여전히 너무 얇게 나온다면 `config.py`의 `TARGET_STROKE_PX`를 올리면 된다.

## 원고지 가이드는 자동으로 지워진다

원고지 각 칸의 점선 상자, 번호, 예시 글자, baseline 안내선은 모두 **아주 연한 회색**으로
인쇄된다. 종이에서 보기엔 충분히 진하지만, 전처리 단계(`preprocess.py`)에서 이 밝기보다
밝은 픽셀은 전부 흰 배경으로 자동 처리하기 때문에 스캔한 뒤 사람이 직접 지울 필요가 없다.
실제 손글씨(검은 펜/연필)는 훨씬 어두우므로 영향받지 않는다. 칸을 나누는 검정 실선 테두리만
남아서 `segment.py`가 칸을 나누는 기준으로 쓴다.

한글 칸에는 예시 음절 전체("가", "곽" 등)가 큰 워터마크로 깔려 있어서, 내가 쓰는 자모가
전체 글자 안에서 어느 크기/위치에 있어야 하는지 보면서 쓸 수 있다. 점선 상자 = 실제 쓰기
한계선이라고 생각하면 된다 (상자를 벗어나면 조합했을 때 옆 자모와 겹칠 수 있음).

라틴 문자 칸은 **실선 상자 = 실제 사용 가능한 전체 높이**(위쪽 끝 = ascender, 아래쪽 끝 =
descender)다. 이 상자를 벗어나면 글자가 잘린다. 상자 안의 굵은 가로선이 baseline이고,
대부분의 글자는 이 선 위에 앉지만 g, y, p, q, j 는 이 선 아래(상자 하단까지)로 내려가면 된다.

(만약 그래도 가이드가 스캔 상태에 따라 완전히 지워지지 않는다면, `python app.py template`
실행 시 함께 만들어지는 `output/grid_overlay_page*.png`(격자선만 있는 투명 배경 PNG)를 이용해
직접 손으로 편집한 손글씨 이미지에 격자를 합성해서 올려도 된다.)

## 사용법

```bash
pip install -r requirements.txt

# 1) 원고지 PDF 생성 (312칸, 여러 페이지 + 범례 페이지 포함)
python app.py template
# -> output/template.pdf, output/grid_overlay_page*.png, data/manifest.json 생성됨

# 2) 인쇄해서 손글씨로 채운 뒤, 페이지 순서대로 스캔/촬영
#    data/scans/page1.jpg, data/scans/page2.jpg ... 로 저장

# 3) 전처리 -> 컴포넌트 분할 -> 한글 11,172자 자동 조합 + 단독 자모 + 영문/숫자/특수문자
#    -> 크기/굵기 자동 보정 -> 커닝 -> 힌팅 -> TTF 생성
python app.py build
# -> output/MyHandwriting.ttf
```

컴포넌트를 일부만 채워도, 그 컴포넌트로 조합/생성 가능한 글자만 생성된다(나머지는 자동 제외).

## 빠른 미리보기 (전체 빌드 없이)

`ZONE_LAYOUTS`, `COMPONENT_OFFSET`,
`STANDALONE_HEIGHT_OVERRIDE`, `TARGET_STROKE_PX`, `TARGET_CAP_HEIGHT` 같은 값을 조금씩
바꿔가며 확인하고 싶을 때, 매번 `python app.py build`로 11,172자 전체를 다시 만들면 너무
느리다 (수십 초). `preview.py`는 **지정한 대표 글자 몇 개만** 담은 작은 미리보기 폰트를
1~5초 안에 만들어서 바로 이미지로 보여준다.

```bash
python preview.py hangul     # 한글 대표 음절 미리보기 (9개 모음 세부그룹 +
                              #   받침 유무 + 자음별 크기 + 겹받침, 한 장의 이미지로)
python preview.py latin      # 영문/숫자/특수문자 미리보기
python preview.py kerning    # 커닝 적용 전/후 비교
python preview.py stroke     # 획 굵기 보정 전/후 비교 (실제 컴포넌트 PNG 기준)
python preview.py hinting    # 힌팅 적용 전/후 비교 (작은 크기로 렌더링)
python preview.py all        # 위 다섯 가지를 전부 실행
```

결과 이미지는 `output/preview_*.png`로 저장된다. 내부적으로 최종 빌드
(`modules/fontbuild.py`)와 **완전히 같은 함수**(`compose_syllable_glyph`,
`build_latin_glyphs`, `build_kern_feature`, `assemble_fontbuilder`)를 그대로 재사용하기
때문에, 여기서 본 결과와 `python app.py build`의 최종 완성본은 항상 일치한다 — 한글만
11,172자 전체가 아니라 지정한 샘플 글자만 넣어서 빠른 것뿐이다.

미리보기에 어떤 글자를 넣을지는 `preview.py` 맨 위쪽의 `HANGUL_PREVIEW_ROWS`,
`DEFAULT_LATIN_SAMPLE`을 고쳐서 자유롭게 바꿀 수 있다. 이 도구는 `data/glyphs`에 이미
분할된 컴포넌트 PNG가 있어야 동작한다 (즉 `python app.py build`를 최소 한 번 실행해서
스캔 → 분할 단계를 거친 뒤 쓸 수 있다). 그 이후로는 손글씨를 다시 스캔하지 않는 한
`preview.py`만으로 빠르게 튜닝을 반복하고, 만족스러우면 마지막에 한 번만
`python app.py build`로 전체 폰트를 완성하면 된다.

### 저장할 때마다 자동으로 다시 그리기 (watch 모드)

```bash
python preview.py watch            # hangul 미리보기를 감시 (기본값)
python preview.py watch hangul latin  # 여러 모드를 한꺼번에 감시
```

`config.py`, `modules/hangul.py`, `modules/compose.py`, `modules/latin.py`,
`modules/kerning.py`, `modules/segment.py`, `modules/fontbuild.py` 중 아무 파일이나
저장할 때마다 지정한 미리보기를 자동으로 다시 만든다. VSCode 같은 에디터에서
`output/preview_hangul.png`를 열어두면(이미지 탭은 파일이 바뀌면 자동으로 다시
읽어온다), 코드를 고치고 저장하기만 하면 바로 갱신된 결과를 볼 수 있다 — 마크다운
미리보기 창과 비슷한 경험이다. `Ctrl+C`로 종료한다.

(완전한 실시간 GUI는 아니고 "저장 -> 자동 재생성"이다. 매번 새 파이썬 프로세스로
다시 실행하는 방식이라 코드를 고친 내용이 항상 정확히 반영된다.)

## 구조 (모듈별 상세 설명)

```
fontMaker
├── data
│   ├── scans/            # 스캔한 원고지 사진 (page1.jpg, page2.jpg ...)
│   ├── glyphs/            # 분할된 컴포넌트 PNG (000.png ~ 311.png)
│   └── manifest.json      # 312개 컴포넌트 정의 (template.py가 생성, segment/compose/latin이 사용)
├── modules/                # 아래에 파일별로 상세 설명
├── output/                 # template.pdf, grid_overlay_page*.png, MyHandwriting.ttf, preview_*.png
├── app.py                  # 전체 파이프라인 실행 (template / build)
├── preview.py              # 빠른 미리보기 도구 (위 섹션 참고)
├── config.py                # 전역 설정값
└── requirements.txt
```

아래는 `modules/` 안 각 파일이 어떤 일을 하고, 어떤 함수들이 있는지에 대한 설명이다.
더 자세한 구현 설명은 각 파일 안의 주석에 있다 — 여기서는 "이 파일이 왜 있고, 어떤
함수를 호출하면 무슨 일이 일어나는지" 정도의 지도 역할만 한다.

### `hangul.py` — 한글 자모 데이터 + 조합 좌표 + 자모별 보정 테이블

한글 조합의 "설계도"에 해당하는 모든 상수/테이블이 모여 있는 파일. 실제 이미지 처리나
폰트 생성 코드는 없고, 순수하게 데이터와 좌표 계산만 담당한다.

+ `CHO_LIST`, `JUNG_LIST`, `JONG_LIST`: 초성 19개/중성 21개/종성 27개의 유니코드 순서 목록.
+ `VOWEL_GROUP`: 중성 21개 각각이 어느 세부그룹(V1~C3, 9종류)에 속하는지 매핑.
+ `SUBGROUPS`, `GROUP_MACRO`: 세부그룹(V1 등)과 상위 그룹(V 등) 사이를 서로 변환하는 표.
  (컴포넌트는 상위 그룹 기준 3종류만 있고, 배치 좌표는 세부그룹 9종류로 나뉘기 때문에
  이 둘을 서로 변환할 일이 자주 있다)
+ `ZONE_LAYOUTS`: (받침유무, 세부그룹) → 초성/중성/종성이 차지할 사각형 좌표. 이 프로젝트에서
  가장 자주 조정하게 될 테이블.
+ `COMPONENT_SCALE`, `COMPONENT_OFFSET`: component id별 크기/위치 보정 표. 둘은 독립적으로 적용된다.
+ `STANDALONE_JAMO_SCALE`, `STANDALONE_JAMO_OFFSET`: 단독 자모 글리프에만 적용되는 별도
  크기/위치 조정 표.
+ `STANDALONE_HEIGHT_OVERRIDE`: 단독 자모(ㄱ, ㅏ 등) 표시 크기를 직접 지정하고 싶을 때 쓰는 표.
+ `component_id(kind, jamo, batchim, group)`: 컴포넌트를 식별하는 문자열 id를 만든다
  (예: `"cho_ㄱ_N_V"`). `data/glyphs/000.png` 같은 실제 파일과 이 id를 연결하는
  `data/manifest.json`이 `template.py`에 의해 만들어진다.
+ `compose_char(cho, jung, jong)`: 초/중/종성 자모로 실제 완성형 한글 한 글자를 조합한다
  (예: `compose_char("ㄱ","ㅏ")` → `"가"`). 원고지에 예시를 표시할 때, 미리보기 도구에서
  샘플을 만들 때 등 여러 곳에서 쓰인다.
+ `decompose_code(code)`: 완성형 한글 코드포인트를 (초성, 중성, 종성)으로 분해한다.
  `compose_char`의 반대 방향. `compose.py`가 11,172자를 하나씩 돌면서 이 함수로 분해한 뒤
  조합한다.
+ `build_component_list()`: 손글씨로 받아야 할 183개 컴포넌트 전체 목록을 만든다. 이 목록의
  순서가 곧 원고지 칸 순서 = `data/glyphs` 안 PNG 파일 인덱스 순서가 된다.
  `template.py`가 원고지를 그릴 때, `segment.py`가 칸을 나눌 때 이 함수를 쓴다.
+ `build_standalone_jamo_list()`: 단독 자모 51개 각각에 대해 (유니코드 코드포인트, 대표
  컴포넌트 id)를 만든다. `compose.py`의 `build_standalone_glyphs()`가 이 목록을 써서
  실제 글리프를 만든다.

### `latin.py` — 영문/숫자/특수문자 컴포넌트 + 개별 글리프 생성

한글과 달리 라틴 문자는 서로 조합되지 않으므로, 이 파일은 "PNG 한 장 = 글리프 하나"를
직접 만드는 역할을 한다.

+ `ASCII_CHARS`, `EXTRA_CHARS`, `LATIN_CHARS`: 지원하는 문자 목록(94 + 35 = 129자).
+ `BASELINE_RATIO`: 라틴 문자 칸에서 baseline이 칸 높이의 몇 %에 위치하는지
  (`config.py`의 ASCENDER/DESCENDER로부터 계산됨). `template.py`가 원고지에 baseline
  안내선을 그릴 때, 이 파일이 이미지→폰트좌표 변환을 할 때 똑같이 쓴다 — 두 곳이 어긋나면
  안 되므로 반드시 이 상수 하나를 공유한다.
+ `build_component_list()`: 129개 컴포넌트 목록 (한글의 `build_component_list`와 대응).
+ `image_to_contours_latin(path)`: PNG 한 장을 (다각형 점 목록, 구멍여부) 튜플 리스트로
  변환한다. 한글용 `glyph.py`의 `image_to_contours`와 비슷하지만, baseline 위치를 살리는
  좌표 변환(`_scale_flip_latin`)을 쓴다는 점이 다르다.
+ `_calc_global_scale(raw_glyphs)`: 대문자 A~Z의 실제 높이 중앙값을 측정해서, 그 값이
  `TARGET_CAP_HEIGHT`에 오도록 하는 배율 하나를 계산한다. "한글과 크기를 맞추는 자동 보정"
  섹션 참고.
+ `build_latin_glyphs(glyph_dir, manifest)`: 위 함수들을 이용해 129개 전체의 최종 TTGlyph +
  advance width를 만든다. `fontbuild.py`와 `preview.py`가 이 함수를 호출한다.

### `template.py` — 원고지 PDF 생성

+ `_zone_to_rect(x, y, cell, zone_shape)`: (칸의 위치, zone 좌표) → 실제 PDF 위의 사각형
  좌표로 변환하는 핵심 함수. 안내 상자(점선/실선)와 한글 워터마크가 **반드시 같은 함수**를
  써야 위치가 정확히 일치하므로, 이 함수 하나로 통일했다.
+ `_draw_hangul_watermark`, `_draw_guide_box`, `_draw_latin_guide`, `_draw_cell`: 칸 하나를
  그리는 세부 함수들.
+ `create_template(filename, manifest_path)`: 전체 원고지 PDF + 범례 페이지를 만들고,
  `data/manifest.json`을 저장한다. `app.py`의 `template` 명령이 이 함수를 호출한다.
+ `create_grid_overlay(n_pages, ...)`: 격자선만 있는 투명 배경 PNG를 페이지별로 만든다
  (가이드 자동 제거가 잘 안 될 때 수동으로 합성하기 위한 보조 파일).

### `preprocess.py` — 스캔 이미지 보정

+ `detect_page(image)`, `four_point_transform(image, pts)`: 사진 속에서 원고지 용지의
  네 꼭짓점을 찾아 반듯하게 펴는(기울기 보정) 역할.
+ `preprocess(path)`: 위 보정 + 노이즈 제거 + 연한 회색 가이드 자동 제거
  (`GUIDE_STRIP_THRESHOLD`) + 흑백 이진화까지 한 번에 처리한다. `app.py`가 스캔 페이지마다
  이 함수를 호출한다.

### `segment.py` — 원고지 칸 → 컴포넌트 PNG 분할

+ `_inset(cell)`: 칸 테두리(격자선)가 잉크로 오인식되지 않도록 가장자리를 살짝 잘라낸다
  (`config.py`의 `CELL_INSET_RATIO`, 기본 0.05 — 너무 크면 받침처럼 가장자리에 붙여 쓰는
  컴포넌트가 잘릴 수 있어서 작게 잡았다).
+ `has_content(cell)`: 칸이 비어있는지 확인 (빈 칸 자동 스킵용).
+ `touches_edge(cell)`: 잉크가 칸 가장자리에 닿아 있는지 확인한다. 닿아 있으면 실제
  손글씨가 칸 밖으로 나가서 잘렸을 가능성이 있다는 뜻이며, `segment()`가 이런 컴포넌트
  목록을 빌드 마지막에 경고로 알려준다.
+ `normalize_hangul_cell(cell)`: **한글용**. 실제 잉크 bbox로 자르지 않고, 테두리만 뺀
  동일한 원고지 칸 전체를 정사각형 캔버스로 저장한다. 손글씨의 실제 크기·여백·위치가
  조합 단계까지 유지된다.
+ `normalize_latin_cell(cell)`: **라틴용**. `normalize_glyph`와 달리 baseline 위치 정보를
  지키기 위해 내용 기준으로 재정렬하지 않고, 칸을 있는 그대로 정사각형으로 리사이즈만 한다.
+ `_estimate_stroke_width(ink_mask)`, `normalize_stroke_width(img, target_width)`: 획 굵기
  자동 보정 (위 "한글과 크기/굵기를 맞추는 자동 보정" 섹션 참고). 한글은
  `config.TARGET_STROKE_PX`, 라틴은 `config.LATIN_TARGET_STROKE_PX`를 각각 목표로 쓴다.
+ `segment(images, output_dir, manifest_path)`: 페이지 이미지들을 받아서 칸을 나누고,
  컴포넌트 종류(한글/라틴)에 따라 위 정규화 함수들을 적용한 뒤 `data/glyphs/{idx}.png`로
  저장한다. `app.py`의 `build` 명령이 이 함수를 호출한다.

### `vectorize.py` — PNG → 윤곽선 검출

+ `find_contours_with_holes(img)`: `cv2.RETR_TREE`로 바깥 윤곽선과 안쪽 구멍(ㅇ,ㅎ,ㅁ,ㅂ의
  속 빈 부분)을 모두 찾는다. 일반적인 `RETR_EXTERNAL`을 쓰면 ㅇ이 속이 꽉 찬 원이 되어버린다.
+ `simplify(contour)`: 점 개수를 줄여 다각형을 단순화한다 (베지어 곡선화 전 전처리).
+ `signed_area(pts)`, `fix_winding(pts, is_hole)`: TrueType 규칙(바깥 윤곽선=시계방향,
  구멍=반시계방향)에 맞게 점의 순서를 보정한다. 이걸 안 하면 구멍이 안 뚫리거나 글자
  전체가 사라질 수 있다.
+ `convert_folder(...)`: (선택 기능) `data/glyphs`의 PNG들을 SVG로 변환하는 디버깅용 함수.

### `glyph.py` — 윤곽선 → 폰트 좌표계 변환 + 곡선화 (한글용)

+ `_scale_flip(pt)`: 이미지 픽셀 좌표(0~800, y 아래로 증가) → 폰트 유닛 좌표(0~1000, y
  위로 증가) 변환.
+ `image_to_contours(path)`: PNG 한 장을 (font-space 점 목록, 구멍여부) 튜플 리스트로
  변환한다. `vectorize.py`의 함수들 + 위 좌표 변환을 합친 것. `compose.py`가 컴포넌트를
  로드할 때 이 함수를 쓴다.
+ `draw_contour(pen, pts)`: 점 목록을 2차 베지어 곡선으로 부드럽게 그린다 (각 변의 중점을
  on-curve 점으로 써서 각진 다각형이 아니라 곡선처럼 보이게 한다).
+ `image_to_glyph(path)`: 위 두 함수를 합쳐 PNG → TTGlyph를 바로 만든다 (개별 컴포넌트
  미리보기/디버깅용).

### `compose.py` — 183개 컴포넌트로 11,172자 + 단독 자모 조합

이 프로젝트의 핵심 로직이 있는 파일. 자세한 설계 배경은 파일 맨 위 docstring 참고.
`FILL_RATIO`는 `config.py`의 `HANGUL_FILL_RATIO`를 그대로 가져와 쓴다.

+ `load_component_contours(glyph_dir, manifest_path)`: `data/glyphs`의 PNG들을 읽어서
  `{컴포넌트id: {"contours":[...], "bbox":(...), "frame":(...)}}` 캐시를 만든다. bbox는
  빈 컴포넌트 검증용이고, 모든 조합 배율/기준점은 공통 `frame`을 기준으로 계산한다.
+ `build_calibration(cache)`: 이전 호출부와의 호환을 위한 빈 설정값을 반환한다. 문맥별
  중앙값 크기 보정은 사용하지 않는다.
+ `_fit_contours(entry, zone, component)`: 컴포넌트 하나를 원본 비율 유지 + 중앙 정렬로
  배치한다. 모든 자모의 공통 `frame`을 기준으로 한 번만 스케일하므로 잉크 bbox에 따른
  자동 크기 보정이 없다. `COMPONENT_SCALE`과 `COMPONENT_OFFSET`은 독립적으로 적용된다.
+ `compose_syllable_glyph(cache, calibration, cho, jung, jong)`: 초/중/종성 자모 하나로
  완성형 음절 하나의 TTGlyph를 만든다. `preview.py`가 샘플 글자 몇 개만 빠르게 만들 때도
  이 함수를 직접 호출한다.
+ `compose_from_cache(cache, calibration)`, `compose_all(...)`: 가(0xAC00)~힣(0xD7A3)
  11,172자 전체를 조합한다. `compose_from_cache`는 캐시/calibration을 미리 계산해서
  넘길 때, `compose_all`은 파일 경로만 주고 한 번에 실행할 때 쓴다.
+ `build_standalone_glyphs(cache, calibration)`: 단독 자모 51개의 글리프를 만든다
  ("단독 자모" 섹션 참고).

### `kerning.py` — 라틴 문자 쌍 자동 커닝

+ `_contours_of(glyph, glyf)`: 컴파일된 TTGlyph에서 윤곽선 점 목록을 다시 꺼낸다.
+ `_profile(contours, ascender, descender)`: 글자를 위아래로 잘게 나눠서, 각 높이에서
  잉크의 왼쪽 끝/오른쪽 끝 x좌표를 계산한다 (커닝 계산의 기초 자료).
+ `build_kern_feature(font, latin_cmap, target_gap)`: 라틴 129자의 모든 쌍에 대해 두
  글자를 나란히 놓았을 때의 간격을 위 프로파일로 계산하고, 이상적인 간격(target_gap)과
  차이가 크면 GPOS `kern` 피처로 보정값을 추가한다. 보정량 한도는
  `max(advance × KERNING_MAX_RATIO, KERNING_MAX_ABS)`로 계산한다 — 마침표처럼 폭이 좁은
  글자도 `KERNING_MAX_ABS`만큼은 최소 보정 여유를 보장받는다 (그렇지 않으면 좁은 글자의
  자간만 유독 덜 보정되어 들쭉날쭉해 보인다). `fontbuild.py`와 `preview.py`(kerning
  모드)가 이 함수를 호출한다.

### `fontbuild.py` — 최종 .ttf 조립

+ `assemble_fontbuilder(hangul_glyphs, ..., latin_metrics, family_name, style_name)`:
  글리프/cmap/지표를 모아 `fontTools.fontBuilder.FontBuilder`를 조립하는 공용 로직.
  `build_font()`(전체 완성 빌드)와 `preview.py`(대표 글자만 넣는 빠른 미리보기)가 이
  함수를 공유한다 — 그래서 미리보기 결과와 최종 완성본이 항상 일치한다.
+ `_apply_hinting(unhinted_path, output_path)`: 시스템에 `ttfautohint`가 설치되어 있으면
  자동으로 힌팅을 적용한다 (없으면 힌팅 없이 저장 + 설치 안내).
+ `build_font(...)`: 위 함수들을 전부 연결해서 `data/glyphs` → 최종 `output/MyHandwriting.ttf`
  까지 만드는 최상위 함수. `app.py`의 `build` 명령이 이 함수를 호출한다.

### `app.py` — 전체 파이프라인 실행 (CLI 진입점)

+ `step_template()`: `template.py`로 원고지 PDF + 격자 오버레이를 만든다 (`template` 명령).
+ `_find_scan_pages(scan_dir)`: `data/scans` 안의 `page1.jpg, page2.jpg ...`를 순서대로 찾는다.
+ `step_build()`: 스캔 페이지들을 `preprocess.py`로 보정 → `segment.py`로 분할 →
  `fontbuild.py`로 최종 폰트 생성까지 전체 파이프라인을 실행한다 (`build` 명령).

### `preview.py` — 빠른 미리보기 도구

"빠른 미리보기" 섹션 참고.

## Kerning(커닝)과 Hinting(힌팅)이란?

**커닝**: 특정 두 글자를 나란히 놓았을 때 생기는 시각적인 간격 차이를 보정하는 것.
예를 들어 활자에서 "AV"를 그냥 이어붙이면 사이에 불필요하게 큰 틈이 생기는데, 커닝으로
이 틈을 좁혀서 다른 글자 쌍과 비슷한 간격으로 보이게 만든다. 이 프로젝트는 라틴 문자
129개의 모든 쌍(약 1만 6천 쌍)에 대해 실제 손글씨 윤곽선을 분석해서, 너무 붙거나 너무 뜬
쌍만 자동으로 보정하는 커닝을 적용한다 (`modules/kerning.py`). 한글 음절/단독 자모는 전부
같은 폭의 정사각형 칸에 들어가는 전각 문자라서 커닝을 적용하지 않는다 (표준적인 한글
조판 방식).

**힌팅**: 작은 크기(특히 저해상도 화면)에서 글자 획이 흐릿하거나 삐뚤어지지 않게, 폰트
안에 "이 크기에서는 이 획을 픽셀 격자에 맞춰 그려라"라는 지시를 추가하는 작업. 이 지시는
폰트 전용 바이트코드 언어로 작성해야 해서 직접 구현하기는 매우 복잡하지만, 널리 쓰이는
오픈소스 자동 힌팅 도구인 **ttfautohint**가 시스템에 설치되어 있으면 빌드 마지막 단계에서
자동으로 적용된다 (없으면 힌팅 없이 저장하고 설치 방법을 안내한다).

```bash
# ttfautohint 설치 (선택 사항 - 없어도 폰트는 정상적으로 만들어진다)
brew install ttfautohint          # macOS
sudo apt install ttfautohint      # Linux
# Windows: https://freetype.org/ttfautohint/#download
```

## 한계

+ 초성 6종류 분류는 실제 정식 폰트 제작사가 쓰는 세밀한 분류(보통 더 많은 변형)보다는
  단순화된 버전이다. 배치 좌표는 9개 세부그룹으로 조정 가능하지만, 손글씨 자체는 3종류만
  받으므로 예를 들어 "ㅏ" 뒤 초성과 "ㅓ" 뒤 초성이 형태 자체는 완전히 같다.
+ 완성형 자모의 크기는 각 조합군의 zone이 결정한다. 특정 조합군이 어색하면 전역 자모
  배율 대신 해당 `ZONE_LAYOUTS`를 조정해야 한다. 이렇게 해야 다른 모음/받침 문맥을
  함께 망가뜨리지 않는다.
+ 획 굵기 자동 보정은 잉크 면적/둘레 비율 기반의 근사치라 완벽하게 균일하지는 않다.
  안전장치(단계적 보정 + 면적 가드)로 받침 등이 통째로 사라지는 것은 방지하지만, 그래도
  이상하다면 `config.py`의 `TARGET_STROKE_PX`나 `STROKE_MAX_KERNEL_RADIUS`를 조정하면 된다.
+ 라틴 문자의 baseline 정렬은 스캔이 원고지 인쇄 비율과 잘 맞아떨어진다고 가정한다. 스캔이
  심하게 기울어지거나 왜곡되면 g/y/p 같은 글자의 baseline이 살짝 어긋날 수 있다.
+ 진짜 폰트 제작사 수준의 정교한 곡선 피팅(최소자승 베지어 피팅)은 구현하지 않았다
  (2차 베지어 근사만 사용).
+ `preview.py`의 힌팅 비교는 화면 배율/이미지 뷰어에 따라 차이가 잘 안 보일 수 있다 —
  이미지를 픽셀 100%로 확대해서 보는 것을 권장한다.
