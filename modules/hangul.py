"""
한글 조합형 폰트를 위한 자모 데이터 + 배치 좌표 테이블.

핵심 아이디어
-------------
11,172자를 전부 손글씨로 받는 대신, "모양이 실제로 달라지는" 최소 단위만
손글씨로 받고 나머지는 좌표 기반으로 자동 조합한다.

- 초성(19개): 받침 유무(2) x 뒤에 오는 모음의 세부 그룹(9) 에 따라 글자의
  폭/위치가 달라지므로 18가지 형태를 모두 받는다.  19 x 18 = 342
- 중성(21개): 받침 유무(2)에 따라 세로 길이가 달라지므로 2가지 형태를 받는다.
  21 x 2 = 42
- 종성/받침(27개): 항상 글자 하단의 같은 자리에만 오므로 형태 변화가 없다.
  1가지만 받는다.  27 x 1 = 27

합계 342 + 42 + 27 = 411칸만 손글씨로 받으면, 11,172자 전체를 조합할 수 있다.

모음 세부 그룹 (9개)
--------------------
큰 방향(세로형 V / 가로형 H / 복합형 C) 안에서도 초성이 붙는 모양이 살짝
달라지는 경우가 있어서, 아래처럼 3단계로 더 세분화한다.

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

# 중성을 9개 세부 그룹으로 분류 (모듈 docstring 참고)
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

# 세부 그룹 -> 상위 그룹(V/H/C) 매핑, 세부 그룹 목록
SUBGROUPS = {
    "V": ["V1", "V2", "V3"],
    "H": ["H1", "H2", "H3"],
    "C": ["C1", "C2", "C3"],
}
ALL_GROUPS = [g for subs in SUBGROUPS.values() for g in subs]  # 9개

GROUP_LABEL = {
    "V1": "세로모음(ㅏ계열)", "V2": "세로모음(ㅓ계열)", "V3": "세로모음(ㅣ계열)",
    "H1": "가로모음(ㅗ계열)", "H2": "가로모음(ㅜ계열)", "H3": "가로모음(ㅡ계열)",
    "C1": "복합모음(ㅘ계열)", "C2": "복합모음(ㅝ계열)", "C3": "복합모음(ㅢ계열)",
}

# ────────────────────────────────────────────────────────────
# 조합 좌표(zone) 테이블
# UPM 1000x1000 정사각형 안에서, (받침유무, 모음그룹) 조합마다
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
        "cho":  (100, 100, 450, 900),
        "jung": (400, 100, 900, 900),
        "jong": None,
    },
    # 받침 없음 + 가로모음 (고, 누, 드...) : 상하 배치
    (False, "H"): {
        "cho":  (200, 550, 800, 900),
        "jung": (100,   0, 900, 480),
        "jong": None,
    },
    # 받침 없음 + 복합모음 (과, 궈, 희...) : 초성은 좌상단, 모음이 아래+오른쪽 감쌈
    (False, "C"): {
        "cho":  (100, 550, 750, 900),
        "jung": (0,     0, 1000, 600),
        "jong": None,
    },
    # 받침 있음 + 세로모음 (각, 닫, 빛...)
    (True, "V"): {
        "cho":  (100, 550, 400, 1000),
        "jung": (400, 500, 1000, 1000),
        "jong": (100,  50, 900, 400),
    },
    # 받침 있음 + 가로모음 (곡, 녹, 숙...)
    (True, "H"): {
        "cho":  (0,   650, 1000, 1000),
        "jung": (100, 370, 900, 670),
        "jong": (150,   0, 1000, 350),
    },
    # 받침 있음 + 복합모음 (곽, 궐, 휙...)
    (True, "C"): {
        "cho":  (200, 700, 560, 1000),
        "jung": (200, 360, 800, 850),
        "jong": (200,   0, 900, 360),
    },
}

ZONE_LAYOUTS = {}
for (_batchim, _macro), _layout in _BASE_ZONE_LAYOUTS.items():
    for _sub in SUBGROUPS[_macro]:
        ZONE_LAYOUTS[(_batchim, _sub)] = dict(_layout)


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
    "jong": 1.0,
}

# 특정 (종류, 자모)별 배율 보정. 실제로 폰트를 뽑아보고 특정 자모가
# 너무 작거나 커 보이면 여기에 추가하면 된다. 예:
#   COMPONENT_SCALE = {("cho", "ㅇ"): 1.08, ("jong", "ㄹ"): 0.95}
COMPONENT_SCALE = {}

# 특정 (종류, 자모)별 위치 보정 (dx, dy), 폰트 유닛(UPM=1000) 기준. 예:
#   COMPONENT_OFFSET = {("cho", "ㅊ"): (0, -15)}
COMPONENT_OFFSET = {}


def get_component_scale(kind, jamo):
    return COMPONENT_SCALE.get((kind, jamo), 1.0)


def get_component_offset(kind, jamo):
    return COMPONENT_OFFSET.get((kind, jamo), (0, 0))


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
    # 해당 세부 그룹에 속한 모음 중 아무거나 하나로 예시를 만든다.
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
    손글씨로 받아야 할 411개 컴포넌트 목록을 순서대로 만든다.
    이 순서가 곧 템플릿 칸 순서 = data/glyphs 안 PNG 인덱스 순서가 된다.
    """
    components = []

    for cho in CHO_LIST:
        for batchim in (False, True):
            for group in ALL_GROUPS:
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
            "zone_shape": (0, 0, 1000, 280),  # 임의의 받침 zone 하나 기준 (안내용)
        })

    return components


# ────────────────────────────────────────────────────────────
# 단독 자모(조합되지 않은 낱자) 지원
#
# "ㄱ", "ㅏ" 처럼 완성형 음절이 아니라 낱자 하나만 입력해도 폰트가
# 적용되도록, 각 자모마다 대표로 쓸 컴포넌트를 하나씩 지정한다.
# - 초성 목록에 있는 자모(ㄱ,ㄴ,ㄷ... 19개)는 "받침없음 + ㅏ계열(V1)"
#   초성 컴포넌트를 대표로 쓴다 (가장 기본적인/친숙한 형태).
# - 중성(모음, 21개)은 "받침없음" 중성 컴포넌트를 대표로 쓴다.
# - 종성에만 있는 겹받침(ㄳ,ㄵ,ㄶ,ㄺ,ㄻ,ㄼ,ㄽ,ㄾ,ㄿ,ㅀ,ㅄ)은 종성
#   컴포넌트를 그대로 쓴다 (이 자모들은 초성으로 쓰이지 않기 때문).
# ────────────────────────────────────────────────────────────
STANDALONE_REPRESENTATIVE_GROUP = "V1"


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
