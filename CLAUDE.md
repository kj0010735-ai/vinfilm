# 빈필름스튜디오 작업 관리 앱

영상 프로덕션 스튜디오(빈필름스튜디오)의 업무 관리 도구. 순수 HTML/CSS/JS 단일 파일 앱으로, 빌드 과정이나 프레임워크 없이 `index.html` 하나로 동작한다.

## 구조

- `index.html` — 전체 앱 (마크업 + 스타일 + 로직이 한 파일에 있음, ~2000줄)
- `장비목록 이미지/` — 장비 사진 에셋 (카메라, 렌즈, 조명, 가방 등)
- 저장: `localStorage`가 기본, Firebase Firestore(compat SDK)로 선택적 클라우드 동기화. 인터넷이 없으면 Firebase 로딩이 조용히 실패하고 로컬 저장만으로 정상 동작하도록 설계됨.

## 주요 탭 (NAV_ITEMS, index.html:193)

- 오늘 할 일 (today)
- 장비목록 (equipment) — 카메라/렌즈/조명 등 장비 재고 및 상태 관리
- 촬영준비 (shootprep) — 촬영 프리셋, 이동수단/장소/패킹 옵션 기반 준비물 체크
- 스케줄 (schedule) — ICS 캘린더 파싱/병합 지원
- 프로젝트 (projects) — 칸반 보드 (진행중/진행완료 등, PJ-001 형식 시리얼)
- 공유 프로젝트 (shared) — 외부 협업자와 공유하는 목록 (SP-001 형식 시리얼). 마감일순 정렬된 플랫 리스트, 칸반 아님.
- 메모장 (notes)

## 외부 공유(guest) 모드

`index.html?guest=1`로 접속하면 `GUEST_MODE`가 켜지며 사이드바에 장비목록/공유 프로젝트 탭만 보이고, 공유 프로젝트 탭의 추가/수정/삭제 버튼도 숨겨진다 (index.html:198-206 근처 `GUEST_MODE`/`GUEST_ALLOWED_TABS` 참고).

**주의: 이건 UI 상에서만 탭을 숨기는 것이지 실제 데이터 보안이 아니다.** Firebase 설정값(`FIREBASE_CONFIG`)이 이 공개 저장소의 `index.html`에 그대로 노출돼 있고, Firestore 보안 규칙이 열려 있다면 누구든 브라우저 개발자도구에서 Firestore를 직접 호출해 모든 컬렉션을 읽고 쓸 수 있다. guest 모드는 `GUEST_CLOUD_COLLECTIONS`로 동기화되는 컬렉션을 `equipment`/`categories`/`sharedProjects`로만 제한해서 내부용 데이터(스케줄·메모·오늘 할 일 등)가 외부 브라우저로 아예 내려받히지 않게는 해두었지만, 이것도 우리 앱 코드 안에서의 완화일 뿐 Firestore 규칙 자체를 대체하지 않는다. 실제로 접근을 막아야 하는 민감한 정보라면 Firebase 콘솔에서 Firestore 보안 규칙을 확인/강화해야 한다.

## 작업 시 유의사항

- 프레임워크 없이 바닐라 JS로 작성됨 — React/Vue 등 새 의존성을 임의로 추가하지 말 것.
- 파일을 열어 실제로 확인할 때는 `mcp__Claude_Browser__preview_start`로 index.html을 직접 열어서 확인 가능 (별도 서버 설정 불필요).
- UI 텍스트는 전부 한국어. 새로 추가하는 문구도 기존 톤(간결한 한국어)에 맞출 것.
