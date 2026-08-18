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

합계 114 + 42 + 27 = 183개만 손글씨로 받으면, 11,172자 전체를 조합할 수 있다.

손글씨(컴포넌트)와 배치 좌표(zone)는 분리되어 있다
----------------------------------------------------
"어떤 손글씨를 쓸지"는 위처럼 큰 방향(V/H/C) 3종류만 받지만, "그걸 어디에
배치할지"는 그보다 더 세밀하게 조정할 수 있다. 같은 세로모음(V)이라도
ㅏ 뒤에 오는 초성과 ㅓ 뒤에 오는 초성은 위치가 아주 살짝 다를 수 있기
때문에, 배치 좌표만 9개 세부 그룹(V1/V2/V3, H1/H2/H3, C1/C2/C3)으로
나눠서 독립적으로 조정할 수 있게 했다. 즉:

- 손글씨(컴포넌트) 종류: V, H, C (3종류만 손으로 씀)
- 배치 좌표(zone) 종류: V1, V2, V3, H1, H2, H3, C1, C2, C3 (9종류, 좌표만 세밀 조정)

예를 들어 초성 ㄱ을 "세로모음(V)" 한 번만 쓰면, "가"(V1)와 "거"(V2)를 조합할
때 같은 ㄱ 손글씨를 재사용하되, 정확히 어느 위치/크기로 놓을지는
ZONE_LAYOUTS[(False,"V1")]와 ZONE_LAYOUTS[(False,"V2")]를 따로 조정해서
미세하게 다르게 만들 수 있다.

모음 세부 그룹 (9개, 배치 좌표 전용)
------------------------------------
- V1 (ㅏ계열): ㅏ ㅑ ㅐ ㅒ
- V2 (ㅓ계열): ㅓ ㅕ ㅔ ㅖ
- V3 (ㅣ계열): ㅣ
- H1 (ㅗ계열): ㅗ ㅛ
- H2 (ㅜ계열): ㅜ ㅠ
- H3 (ㅡ계열): ㅡ
- C1 (ㅘ계열): ㅘ ㅚ ㅙ
- C2 (ㅝ계열): ㅝ ㅟ ㅞ
- C3 (ㅢ계열): ㅢ
"""

# 유니코드 한글 자모 순서 (KS X 1001 / 완성형 인덱스 순서와 동일)
CHO_LIST = list("ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ")            # 19
JUNG_LIST = list("ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ")        # 21
JONG_LIST = list("ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ")  # 27 (받침 없음은 별도 처리)

assert len(CHO_LIST) == 19
assert len(JUNG_LIST) == 21
assert len(JONG_LIST) == 27

# 중성을 9개 "세부" 그룹으로 분류 (배치 좌표 전용, 손글씨 종류와는 무관)
VOWEL_GROUP = {
    "ㅏ": "V1", "ㅑ": "V1", "ㅐ": "V1", "ㅒ": "V1",
    "ㅓ": "V2", "ㅕ": "V2", "ㅔ": "V2", "ㅖ": "V2",
    "ㅣ": "V3",
    "ㅗ": "H1", "ㅛ": "H1",
    "ㅜ": "H2", "ㅠ": "H2",
    "ㅡ": "H3",
    "ㅘ": "C1", "ㅚ": "C1", "ㅙ": "C1",
    "ㅝ": "C2", "ㅟ": "C2", "ㅞ": "C2",
    "ㅢ": "C3",
}
assert set(VOWEL_GROUP) == set(JUNG_LIST)

# 세부 그룹 -> 상위(손글씨) 그룹 매핑 및 상위 그룹 -> 세부 그룹 목록
SUBGROUPS = {
    "V": ["V1", "V2", "V3"],
    "H": ["H1", "H2", "H3"],
    "C": ["C1", "C2", "C3"],
}
ALL_SUBGROUPS = [g for subs in SUBGROUPS.values() for g in subs]  # 9개

GROUP_MACRO = {sub: macro for macro, subs in SUBGROUPS.items() for sub in subs}

MACRO_LABEL = {"V": "세로모음", "H": "가로모음", "C": "복합모음"}
GROUP_LABEL = {
    "V1": "세로모음(ㅏ계열)", "V2": "세로모음(ㅓ계열)", "V3": "세로모음(ㅣ계열)",
    "H1": "가로모음(ㅗ계열)", "H2": "가로모음(ㅜ계열)", "H3": "가로모음(ㅡ계열)",
    "C1": "복합모음(ㅘ계열)", "C2": "복합모음(ㅝ계열)", "C3": "복합모음(ㅢ계열)",
}

# ────────────────────────────────────────────────────────────
# 조합 좌표(zone) 테이블
# UPM 1000x1000 정사각형 안에서, (받침유무, 모음 세부그룹) 조합마다
# 초성/중성/종성이 차지할 사각형 영역(x0,y0,x1,y1)을 정의한다.
# y=0이 베이스라인, y=1000이 글자 상단이다.
#
# 상위 그룹(V/H/C) 하나에 대해 좌표를 정의해두면, 그 안의 세부 그룹
# (예: V -> V1/V2/V3) 3개가 전부 같은 값으로 시작한다. 처음에는 같은
# 값이라도, 세부 그룹별로 ZONE_LAYOUTS[(batchim, "V1")] 처럼 따로 접근해서
# 독립적으로 조정할 수 있다 (예: V1과 V2만 미세하게 다르게 만들기).
# ────────────────────────────────────────────────────────────
_BASE_ZONE_LAYOUTS = {
    # 받침 없음 + 세로모음 (가, 나, 비...) : 좌우 배치
    (False, "V"): {
        "cho":  (100, 100, 450, 900), # 350
        "jung": (400, 100, 900, 900), # 500
        "jong": None,
    },
    # 받침 없음 + 가로모음 (고, 누, 드...) : 상하 배치
    (False, "H"): {
        "cho":  (200, 550, 800, 900), # 350
        "jung": (100, 20, 900, 520), # 500
        "jong": None,
    },
    # 받침 없음 + 복합모음 (과, 궈, 희...) : 초성은 좌상단, 모음이 아래+오른쪽 감쌈
    (False, "C"): {
        "cho":  (100, 550, 750, 900),
        "jung": (0,  0, 1000, 600),
        "jong": None,
    },
    # 받침 있음 + 세로모음 (각, 닫, 빛...)
    (True, "V"): {
        "cho":  (100, 550, 450, 1000), # 350
        "jung": (400, 500, 1000, 1000), # 500
        "jong": (100,  50, 900, 400), # 350
    },
    # 받침 있음 + 가로모음 (곡, 녹, 숙...)
    (True, "H"): {
        "cho":  (0,   650, 1000, 1000), # 350
        "jung": (100, 370, 900, 670), # 300
        "jong": (150,   0, 1000, 350), # 350
    },
    # 받침 있음 + 복합모음 (곽, 궐, 휙...)
    (True, "C"): {
        "cho":  (200, 700, 560, 1000), # 300
        "jung": (200, 360, 800, 850), # 490
        "jong": (200,   0, 900, 360), # 360
    },
}

# 위 3그룹(V/H/C) 좌표를 9개 세부 그룹으로 그대로 복제해서 시작한다.
# (나중에 ZONE_LAYOUTS[(batchim, "V1")] 처럼 개별적으로 덮어써서 세밀 조정 가능)
ZONE_LAYOUTS = {}
for (_batchim, _macro), _layout in _BASE_ZONE_LAYOUTS.items():
    for _sub in SUBGROUPS[_macro]:
        ZONE_LAYOUTS[(_batchim, _sub)] = dict(_layout)

ZONE_LAYOUTS[(False, "H1")] = {
    "cho":  (200, 550, 800, 900), # 350
    "jung": (100, 50, 900, 550), # 500
    "jong": None,
}
ZONE_LAYOUTS[(False, "C1")] = {
    "cho":  (50, 300, 700, 650), # 350
    "jung": (0,  0, 1000, 600), # 600
    "jong": None,
}
ZONE_LAYOUTS[(False, "C2")] = {
    "cho":  (100, 400, 750, 750), # 350
    "jung": (0,  0, 1000, 600), # 600
    "jong": None,
}
ZONE_LAYOUTS[(False, "C3")] = {
    "cho":  (100, 300, 750, 650), # 350
    "jung": (0,  50, 1000, 650), # 600
    "jong": None,
}
ZONE_LAYOUTS[(True, "V2")] = {
    "cho":  (100, 550, 450, 1000), # 350
    "jung": (420, 500, 1000, 1000), # 570
    "jong": (100,  50, 900, 400), # 350
}
ZONE_LAYOUTS[(True, "H1")] = {
    "cho":  (0,   650, 1000, 1000), # 350
    "jung": (100, 350, 900, 750), # 400
    "jong": (0,   0, 1000, 350), # 350
}
ZONE_LAYOUTS[(True, "H2")] = {
    "cho":  (0,   650, 1000, 1000), # 350
    "jung": (100, 250, 900, 670), # 420
    "jong": (0,   0, 1000, 350), # 350
}
ZONE_LAYOUTS[(True, "H3")] = {
    "cho":  (0,   650, 1000, 1000), # 350
    "jung": (100, 300, 900, 700), # 400
    "jong": (0,   0, 1000, 350), # 350
}
ZONE_LAYOUTS[(True, "C1")] = {
    "cho":  (220, 650, 580, 1000), # 350
    "jung": (200, 300, 800, 850), # 550
    "jong": (200,   0, 900, 350), # 350
}
ZONE_LAYOUTS[(True, "C2")] = {
    "cho":  (200, 650, 560, 1000), # 350
    "jung": (200, 300, 800, 850), # 550
    "jong": (200,   0, 900, 350), # 350
}
ZONE_LAYOUTS[(True, "C3")] = {
    "cho":  (250, 650, 600, 1000), # 350
    "jung": (100, 300, 800, 850), # 550
    "jong": (100,   0, 900, 350), # 350
}
# ────────────────────────────────────────────────────────────
# 자모별 미세 보정 테이블 (선택 사항, 기본값은 "보정 없음")
#
# compose.py는 기본적으로 각 자모의 실제 손글씨 크기(bounding box)를
# 원본 비율 그대로 유지한 채(찌그러지지 않게) zone 안에 맞추고 중앙
# 정렬한다. 이것만으로도 대부분 자연스럽지만, 손글씨 특성상 어떤 자모는
# 상대적으로 작아 보이거나(예: ㄱ, ㅣ) 커 보일 수 있다(예: ㅁ, ㅇ). 그럴
# 때 아래 표의 숫자만 조정하면 해당 자모만 살짝 키우거나/줄이거나
# 위치를 옮길 수 있다 (다른 코드는 안 건드려도 됨).
#
# COMPONENT_SCALE/COMPONENT_OFFSET의 키는 (kind, jamo) 튜플이다.
# 예: ("cho","ㅇ")과 ("jong","ㅇ")은 서로 다른 손글씨 조각(초성 ㅇ vs
# 받침 ㅇ)이므로 따로따로 보정할 수 있다.
# ────────────────────────────────────────────────────────────

# 초성/중성/종성 유형별 기본 배율 (전체적인 균형 조절용)
KIND_SCALE = {
    "cho": 1.0,
    "jung": 1.0,
    "jong": 0.95,
}

# 특정 (종류, 자모)별 배율 보정. 실제로 폰트를 뽑아보고 특정 자모가
# 너무 작거나 커 보이면 여기에 추가하면 된다. 예:
#   COMPONENT_SCALE = {("cho", "ㅇ"): 1.08, ("jong", "ㄹ"): 0.95}
COMPONENT_SCALE = {
    ("cho", "ㄱ"): 1.2,
    ("cho", "ㄲ"): 1.8,
    ("cho", "ㄸ"): 1.8,
    ("cho", "ㅃ"): 2,
    ("cho", "ㅆ"): 2,
    ("cho", "ㅉ"): 2,
    ("cho", "ㅍ"): 1.8,
    ("jong", "ㄳ"): 1.3,
    ("jong", "ㄵ"): 1.3,
    ("jong", "ㄶ"): 1.3,
    ("jong", "ㄺ"): 1.3,
    ("jong", "ㄻ"): 1.3,
    ("jong", "ㄼ"): 1.3,
    ("jong", "ㄽ"): 1.3,
    ("jong", "ㄾ"): 1.3,
    ("jong", "ㄿ"): 1.3,
    ("jong", "ㅀ"): 1.3,
    

}

# 특정 (종류, 자모)별 위치 보정 (dx, dy), 폰트 유닛(UPM=1000) 기준. 예:
#   COMPONENT_OFFSET = {("cho", "ㅊ"): (0, -15)}
COMPONENT_OFFSET = {}


def get_component_scale(kind, jamo):
    return COMPONENT_SCALE.get((kind, jamo), 1.0)


def get_component_offset(kind, jamo):
    return COMPONENT_OFFSET.get((kind, jamo), (0, 0))


# ────────────────────────────────────────────────────────────
# 단독 자모("ㄱ", "ㅏ" 등 조합되지 않은 낱자) 표시 크기 조정
#
# 기본값(None)일 때는 그 자모가 "실제 음절 조합에 쓰일 때 차지하는 높이"를
# 그대로 재사용한다 (예: 단독 ㄱ = "가"에서 ㄱ이 차지하는 만큼의 크기).
# 숫자를 넣으면(폰트 유닛, UPM=1000 기준) 해당 종류(초성/중성/종성)의
# 단독 표시 높이가 항상 그 값으로 고정된다.
#
# 예: 단독으로 쓴 초성(ㄱ,ㄴ,ㄷ...)이 너무 크게 느껴지고, 조합 글자 속
# 자음의 평균적인 크기(예: 350) 정도가 더 자연스럽다면 아래처럼 바꾸면 된다.
#   STANDALONE_HEIGHT_OVERRIDE["cho"] = 350
# 중성(모음)은 그대로 두고 싶으면 "jung"은 None으로 유지하면 된다.
# ────────────────────────────────────────────────────────────
STANDALONE_HEIGHT_OVERRIDE = {
    "cho": 350,
    "jung": None,
    "jong": None,
}


def component_id(kind, jamo, batchim=None, group=None):
    """
    컴포넌트(손글씨 조각)를 유일하게 식별하는 문자열 id를 만든다.
    cho의 group은 항상 상위 그룹(V/H/C)이어야 한다 - 손글씨는 3종류만
    받기 때문. 세부 그룹(V1 등)은 zone 좌표를 찾을 때만 쓴다.
    """
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


def _example_for_cho(cho, batchim, macro):
    # 이 상위 그룹(macro)에 속하는 세부 그룹 중 아무 모음이나 하나로 예시를 만든다.
    jung = next(v for v, g in VOWEL_GROUP.items() if GROUP_MACRO[g] == macro)
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
            for macro in ("V", "H", "C"):
                # 이 컴포넌트가 실제로 쓰일 대표 예시(및 zone) 선택: 해당
                # 상위 그룹의 첫 번째 세부 그룹을 기준으로 안내 상자를 그린다.
                # (watermark/guide box는 이 예시 하나로 표시되지만, 실제
                # 조합 시에는 각 세부 그룹의 정확한 zone이 개별 적용된다)
                example = _example_for_cho(cho, batchim, macro)
                example_cho, example_jung, example_jong = decompose_code(ord(example))
                fine_group = VOWEL_GROUP[example_jung]

                components.append({
                    "id": component_id("cho", cho, batchim, macro),
                    "kind": "cho",
                    "jamo": cho,
                    "batchim": batchim,
                    "group": macro,
                    "label": f"초성 {cho} · {'받침있음' if batchim else '받침없음'} · {MACRO_LABEL[macro]}",
                    "example": example,
                    "zone_shape": ZONE_LAYOUTS[(batchim, fine_group)]["cho"],
                })

    for jung in JUNG_LIST:
        for batchim in (False, True):
            fine_group = VOWEL_GROUP[jung]
            components.append({
                "id": component_id("jung", jung, batchim),
                "kind": "jung",
                "jamo": jung,
                "batchim": batchim,
                "group": None,
                "label": f"중성 {jung} · {'받침있음' if batchim else '받침없음'}",
                "example": _example_for_jung(jung, batchim),
                "zone_shape": ZONE_LAYOUTS[(batchim, fine_group)]["jung"],
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
            "zone_shape": (0, 0, 1000, 280),  # 임의의 받침 zone 하나 기준 (안내용)
        })

    return components


# ────────────────────────────────────────────────────────────
# 단독 자모(조합되지 않은 낱자) 지원
#
# "ㄱ", "ㅏ" 처럼 완성형 음절이 아니라 낱자 하나만 입력해도 폰트가
# 적용되도록, 각 자모마다 대표로 쓸 컴포넌트를 하나씩 지정한다.
# - 초성 목록에 있는 자모(ㄱ,ㄴ,ㄷ... 19개)는 "받침없음 + 세로모음(V)"
#   초성 컴포넌트를 대표로 쓴다 (가장 기본적인/친숙한 형태).
# - 중성(모음, 21개)은 "받침없음" 중성 컴포넌트를 대표로 쓴다.
# - 종성에만 있는 겹받침(ㄳ,ㄵ,ㄶ,ㄺ,ㄻ,ㄼ,ㄽ,ㄾ,ㄿ,ㅀ,ㅄ)은 종성
#   컴포넌트를 그대로 쓴다 (이 자모들은 초성으로 쓰이지 않기 때문).
# ────────────────────────────────────────────────────────────
STANDALONE_REPRESENTATIVE_GROUP = "V"


def build_standalone_jamo_list():
    """
    단독 자모 51개(초성 19 + 종성전용 겹받침 11 + 중성 21) 각각에 대해
    (유니코드 코드포인트, 대표 컴포넌트 id)를 반환한다.
    """
    entries = []
    seen = set()

    for cho in CHO_LIST:
        comp_id = component_id("cho", cho, False, STANDALONE_REPRESENTATIVE_GROUP)
        entries.append((ord(cho), comp_id))
        seen.add(cho)

    for jong in JONG_LIST:
        if jong in seen:
            continue  # 이미 초성으로 등록됨 (같은 코드포인트)
        comp_id = component_id("jong", jong)
        entries.append((ord(jong), comp_id))
        seen.add(jong)

    for jung in JUNG_LIST:
        comp_id = component_id("jung", jung, False)
        entries.append((ord(jung), comp_id))

    return entries
