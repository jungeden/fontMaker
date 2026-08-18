
# timeline

## ☑︎ `v1`

- v1_Readme.md
- v1_guide.md

### ▶︎ user

~~~md
ttf 파일 만드는 python 코드 프로젝트 하고 있는데 여기서 수정해야할 부분이랑 추가해야할 부분 고려해서 최종 완성해줘. 필요한 정보나 파일이나 자료 말하면 답해줄게.
~~~

### ▷ cluade.ai

Good, Noto Sans CJK is available. Let me build a synthetic test scan to smoke-test the whole pipeline.Now let's run the full pipeline (template → build) to smoke-test everything:Found a real bug — the cell border lines are leaking into content detection (all 100 cells register as "having content" because of the grid lines). Let me fix that.Now let's re-run the full test to confirm the fix and check the resulting font:Now exactly 50 glyphs (matching the 50-char set), no false positives. Let's verify the TTF is valid and actually renders the holes (ㅇ,ㅎ,ㅁ) correctly by rendering a sample glyph:The 오 glyph correctly has 2 contours (outer + the ㅇ hole) — the hole-detection fix works. Let me visually render a few glyphs to confirm the shapes and holes look right, not inverted:Both render correctly — 오 shows a proper hollow ㅇ (not a filled dot), and 가 renders as a clean solid character with smoothed curves. The full pipeline works end-to-end. Now let me package everything and write a summary of changes.Clean. Now let's present it:프로젝트 전체를 실제로 돌려보면서(합성 스캔 이미지로 파이프라인 전체 테스트, 폰트 유효성 검증, 글리프 렌더링까지 확인) 고치고 완성했어. 주요 수정/추가 사항은 다음과 같아.

**치명적 버그**

- `template.py`: `Helvetica` 폰트로 한글을 그리고 있어서 원고지에 안내 글자가 아예 안 나왔음 → ReportLab 내장 CJK 폰트(`HYSMyeongJo-Medium`)로 교체
- `vectorize.py`: `RETR_EXTERNAL`만 써서 ㅇ/ㅎ/ㅁ/ㅂ의 안쪽 구멍이 사라지고 통짜로 채워졌음 → `RETR_TREE` + hierarchy로 구멍 검출, TrueType 규칙(바깥=시계방향, 구멍=반시계방향)에 맞춰 winding 보정 추가
- `glyph.py`: `lineTo`만 있어서 손글씨 곡선이 전부 각진 다각형이 됨 → 2차 베지어(`qCurveTo`)로 부드럽게 그리도록 재작성
- `config.py`의 `CHARS`가 `template.py`(50자)와 `fontbuild.py` 예시(14자)에서 서로 달랐음 → 한 곳(config.py)으로 통일
- `segment.py`: 칸을 격자선 경계에 딱 맞춰 자르다 보니 옆 칸 테두리 선이 "글자"로 오인식돼 빈 칸까지 전부 저장되던 버그 발견·수정 (테스트 중 실제로 발생해서 잡음)

**guide.md에서 "다음에 할 일"로 남겨둔 것들 구현**

- 칸 안에서 글자가 치우쳐도 실제 잉크 영역만 크롭 (`crop_content`)
- 빈 칸 자동 스킵 (`has_content`)
- Baseline 정렬 + 글자 크기 정규화 (`normalize_glyph`) — 폭이 너무 넓은 글자가 캔버스를 넘던 엣지케이스도 수정
- 글자 폭에 맞춘 advance width 자동 계산 (기존엔 전부 고정값 1000)

**구조 정리**

- `app.py`: 지저분한 주석 잔해 제거 → `python app.py template` / `build` / `svg` 세 명령으로 정리
- `requirments.txt` → `requirements.txt` 오타 수정

**한계 (guide.md 로드맵 중 아직 미구현)**

- 한글 11,172자 자동 조합(초성·중성·종성)
- Kerning, Hinting
- GUI(PySide6)

이제 필요한 거 있으면 알려줘 — 예를 들어:

1. 실제로 손글씨를 채운 스캔 이미지가 있으면 같이 돌려서 결과 TTF까지 만들어줄게
2. `CHARS`를 지금 50자 대신 다른 글자셋(예: 자모 낱자만)으로 바꾸고 싶은지
3. 11,172자 자동 조합이나 GUI 쪽을 다음 단계로 진행할지

~~~md
↳ v2
~~~

<br>
<br>
<br>
<br>
<br>
<br>
<br>

## ☑︎ `v2`






<!-- ## 방법 3: 확장 프로그램(Extension)을 이용해 아예 로컬 전역 등록하기


   1. VS Code 마켓플레이스(Cmd + Shift + X)에서 Markdown Preview Enhanced 설치.
   2. Cmd + Shift + P 누른 후 Markdown Preview Enhanced: Customize CSS 검색 및 실행.
   3. 열리는 파일 창에 내 깃허브 주소에 적어둔 CSS 내용들을 그대로 복사·붙여넣기 한 후 저장.
   4. 마크다운 파일 우클릭 ➡️ Markdown Preview Enhanced: Open Preview로 열기. -->
