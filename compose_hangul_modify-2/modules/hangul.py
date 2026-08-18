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