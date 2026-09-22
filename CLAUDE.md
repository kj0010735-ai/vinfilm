# VINFILM STUDIO 웹 프로젝트

영상 프로덕션 스튜디오(VINFILM STUDIO)의 공개 홈페이지 + 내부 작업 관리 도구. 순수 HTML/CSS/JS로, 빌드 과정이나 프레임워크 없이 파일 하나당 페이지 하나로 동작한다.

## 저장소 구조

- `index.html` — **공개 홈페이지** (루트, 커스텀 도메인 `www.vinfilmstudio.com`이 여기로 연결됨). 포트폴리오/소개/연락처.
- `service.html` — 서비스 상세 페이지 (`?id=interview|sketch|mv|youtube`). index.html의 "무엇을 만드나요?" 목록에서 클릭하면 넘어옴. 서비스별 태그라인·소개문구·진행 단계도 `siteContent/home`의 `services` 필드에서 읽어온다.
- `admin/index.html` — 홈페이지 콘텐츠 관리자 화면. 비밀번호 게이트 + Firestore `siteContent/home` 문서 편집.
- `works/index.html` — **내부 작업 관리 앱** (기존 "작업 관리" 툴, 원래 루트에 있던 파일을 이전한 것). 장비목록/스케줄/프로젝트/공유 프로젝트/메모장 탭 구성. `?guest=1`로 외부 공유 모드 진입 가능.
- `works/장비목록 이미지/` — 장비 사진 에셋.
- `ledger/index.html` — **통합장부(수입/지출 관리) 앱**. 원래 GPT(ChatGPT 캔버스/앱, `*.chatgpt.site` 도메인)에서 만들던 걸 로그인 게이트 때문에 그대로 가져올 수 없어서, 이 저장소의 바닐라 HTML/JS + works/index.html 패턴을 그대로 따라 새로 만든 것. 항목별 구분(수입/지출)·카테고리(자유입력+datalist 자동완성)·통화(KRW/USD)·매월 반복 여부·메모를 기록하고, 월별/연간 보기로 집계한다. 달러 항목은 상단 "적용 환율"(수동 입력, 기준일 표시)로 원화 환산해서 합계에 포함 — `settings.usdKrwRate`/`rateDate`, Firestore `ledgerSettings/main` 문서 하나로 관리. 재무 데이터라 guest 모드 없음, **owner(`kj0010735@gmail.com`)만 접근** — 로그인은 하되 그 이메일이 아니면 "접근 권한이 없어요" 화면만 보여주는 클라이언트 UI 게이트이고, 실제 방어선은 여전히 firestore.rules의 `isOwner()`. Firestore 컬렉션은 `ledgerEntries`(항목 배열, works의 `pushToCloud` diff-sync 패턴 그대로) + `ledgerSettings`(환율 설정, 단일 문서). `IS_LOCAL_DEV` 가드도 처음부터 동일하게 적용돼 있어 로컬 테스트가 운영 데이터를 건드리지 않는다.
  - **모달 안 버튼이 동작하려면 모달 wrapper에 `onclick="event.stopPropagation()"`을 달면 안 된다** — 클릭 위임(`document.addEventListener('click', ...)`)이 버블 단계에서 동작하는데, 모달 안쪽 아무 데나 클릭해도 오버레이가 안 닫히게 하려고 wrapper에 stopPropagation을 걸면 그 안의 취소/저장/삭제 버튼 클릭도 document까지 못 올라가서 전부 먹통이 된다(실제로 이 버그가 있었음). 오버레이 자체의 `data-action="ldg-close-modal"` 핸들러가 `e.target === btn`(클릭한 요소가 오버레이 자기 자신일 때만) 조건으로 이미 "안쪽 클릭으로는 안 닫힘"을 보장하므로 stopPropagation은 애초에 필요 없다 — 새 모달을 만들 때도 이 패턴(오버레이에 data-action + e.target 가드, wrapper엔 아무것도 안 닮)을 그대로 따를 것.
- `CNAME` — GitHub Pages 커스텀 도메인 설정 파일 (`www.vinfilmstudio.com`).
- `firestore.rules`, `firebase.json` — Firestore 보안 규칙 정의. `firebase deploy --only firestore:rules --project vinfilm-studio-app`로 배포.
- 저장: `localStorage`가 기본, Firebase Firestore(compat SDK)로 클라우드 동기화. 인터넷이 없으면 Firebase 로딩이 조용히 실패하고 로컬 저장만으로 동작하도록 설계됨. Firebase 프로젝트는 `vinfilm-studio-app` (VINFILM STUDIO 전용 — 예전에는 다른 무관한 사이트와 같은 프로젝트를 공유해서 쓰다가 분리했다).

## 공개 홈페이지 (index.html)

다크 시네마틱 톤 랜딩 페이지. 히어로/최근 작업(넘버링 그리드)/서비스(풀블리드 컬러 섹션)/연락처/푸터로 구성. 콘텐츠(메인 영상 URL, 헤드라인, 작업 목록, 연락처 등)는 Firestore `siteContent/home` 문서에서 읽어오고, 문서가 없거나 로드 실패 시 `DEFAULT_CONTENT`로 폴백한다 — **`DEFAULT_CONTENT`는 index.html과 admin/index.html 양쪽에 동일하게 복제되어 있으니, 하나를 고치면 반드시 다른 쪽도 같이 고칠 것.**

## admin 페이지 (admin/index.html)

- 로그인은 Google 계정(Firebase Authentication) — `signInWithPopup(GoogleAuthProvider)`. 처음엔 이메일/비밀번호 + 코드에 평문 비밀번호를 박아두는 방식이었는데, 실제 인증으로 교체했다.
- 저장 시 Firestore `siteContent/home` 문서를 통째로 `.set()`으로 덮어씀 (부분 업데이트 아님) — 다만 폼에 없는 필드(예: `styleVars`)는 `lastLoadedDoc`을 스프레드해서 그대로 보존하므로, admin에 입력칸이 없는 필드라고 admin 저장 시 사라지지는 않는다. 그래도 새 필드를 admin 폼으로 노출하고 싶으면 `loadContent`/`saveContent`/`DEFAULT_CONTENT` 세 군데 다 반영할 것.

## 홈페이지 인라인 편집 모드 (index.html?edit=1)

- 홈페이지 자체에서 화면을 보며 바로 수정하는 기능. `index.html?edit=1`로 접속하면 Google 로그인 게이트가 뜨고, `OWNER_EMAIL`(`kj0010735@gmail.com`)로 로그인해야 편집 모드가 켜진다 — UI 게이트일 뿐이고 실제 방어선은 여전히 Firestore `isOwner()` 규칙.
- 편집 모드에서는 헤드라인/서브카피/섹션 제목/작업 소개문구/연락처/작업 카드의 제목·클라이언트·연도·카테고리가 `contenteditable`로 바로 수정된다. 영상/썸네일 URL, 인스타그램/Vimeo 링크, 히어로 배경 영상은 텍스트가 아니라서 각 항목의 ✎ 버튼으로 prompt() 입력.
- 하단 툴바의 "크기 조절" 패널에서 헤드라인/섹션 제목/카드 제목 폰트 크기와 썸네일 크기를 슬라이더로 조절 — 값은 `siteContent/home` 문서의 `styleVars` 필드에 저장되고 CSS 변수(`--hero-headline-size` 등)로 적용됨.
- "저장" 버튼이 현재 편집 중인 콘텐츠 전체를 `siteContent/home`에 `.set()`으로 덮어씀 (admin 페이지와 동일한 문서, 같은 덮어쓰기 방식 — 즉 어느 쪽에서 편집하든 항상 최신 상태로 유지되게 신경 쓸 것).
- 작업 카드의 썸네일은 `thumbUrl`을 직접 안 넣어도 유튜브 링크면 `https://img.youtube.com/vi/{id}/hqdefault.jpg`로 자동 생성되고, Vimeo 링크는 로드 후 oEmbed API로 비동기로 가져온다 (`enhanceThumbnails`).
- "무엇을 만드나요?" 섹션 제목(`servicesTitle`)과 서비스 목록(`services` — 각 항목 `id`/`label`)도 같은 방식으로 편집된다. `service.html?id=...&edit=1`로 들어가면 그 서비스의 태그라인·소개문구(`body[]`)·진행 단계(`steps[]`)도 같은 로그인 게이트로 바로 수정 가능 — index.html의 서비스 목록 링크는 편집 모드일 때 자동으로 `&edit=1`을 붙여서 넘겨준다. `services`의 기본값(`DEFAULT_SERVICES`/`DEFAULT_CONTENT.services`)은 index.html과 service.html 양쪽에 동일하게 복제돼 있으니 문구를 코드로 바꿀 땐 둘 다 고칠 것.

## works/index.html 디자인 톤

내부 앱도 공개 홈페이지와 같은 다크 웜톤(배경 `#0e0d0c`, 포인트 컬러 `#d98a3d`, Noto Sans KR 본문)을 쓴다 — 색/폰트 CSS 변수(`--bg`/`--accent`/`--font-body` 등)만 바꾸면 앱 전체에 적용되는 구조라 두 사이트 색이 어긋나지 않게 관리하기 쉽다. **이 변수들은 `:root`에 정의돼 있다(예전엔 `.app-shell`에 있었는데, 스케줄 모달을 전역 렌더로 옮기면서 `.app-shell` 밖에서도 필요해져 `:root`로 옮김 — 아래 "프로젝트 ↔ 스케줄 연동" 항목 참고). 새 색/폰트 변수도 반드시 `:root`에 추가할 것, `.app-shell`에 추가하면 그 바깥(전역 모달 등)에서 안 먹혀서 화면이 까맣게 보이는 버그가 재발한다.** `--font-display`(Anton)는 한글을 지원하지 않는 폰트라 영문 라벨(예: "WORK MANAGEMENT" eyebrow, 코드/D-day 같은 영문·숫자)에만 쓰고, 한글 텍스트에는 절대 적용하지 말 것 — Anton은 한글을 렌더링하지 못해 그냥 폴백 폰트로 깨져 보인다.

**왼쪽 사이드바(`.side-nav`, `#sideNav`)는 항상 56px 고정폭이다.** 예전엔 마우스를 올리면 196px로 넓어지면서 라벨 텍스트가 옆에 나타나는 방식이었는데, 그 확장된 너비가 본문 콘텐츠 위를 덮어버려서("화면 왼쪽이 가려짐") 불편하다는 피드백으로 없앴다. 지금은 폭이 안 바뀌고, 각 아이콘에 마우스를 올리면 아이콘 오른쪽으로 작은 툴팁(`.side-nav-label`, `position:absolute; left:calc(100% + 8px)`)만 뜬다 — 순수 CSS `:hover`로만 동작하고(JS의 `mouseover`/`mouseout` 리스너로 `expanded` 클래스를 토글하던 예전 방식은 제거함), 본문(`.app-main`)의 `margin-left:56px`도 그대로라 사이드바 폭 변화에 맞춰 레이아웃이 흔들리는 일도 없다.

**프로젝트 탭과 공유 프로젝트 탭 둘 다 칸반 보드가 아니라 같은 리스트형 게시판 UI**를 쓴다 (마감 임박순 정렬, 검색/상태 필터, `.proj-row`/`.proj-list`/`.proj-breadcrumb`/`.proj-parent-card`/`.proj-status-menu` 등 CSS 클래스를 두 탭이 공유). 로직은 각자 분리돼 있다 — 프로젝트는 `projItems`/`saveProjItems`/`PROJECT_COLUMNS`/`projRowHtml`, 공유 프로젝트는 `sharedProjItems`/`saveSharedProjItems`/`SHARED_STATUSES`/`sharedRowHtml`.

- **상태 변경 두 가지 경로**: ① 수정 모달(프로젝트는 라디오, 공유 프로젝트는 select), ② 상태 배지 우클릭 → 빠른 변경 메뉴 (프로젝트는 `data-status-menu-id`/`S.proj.statusMenu`, 공유 프로젝트는 `data-shared-status-menu-id`/`S.shared.statusMenu` — 같은 `contextmenu` 리스너 안에서 분기). 드래그로 상태를 바꾸던 옛 칸반 방식은 없앴다. 공유 프로젝트는 게스트도 오너와 동일하게 이 배지 우클릭이 된다(게스트는 쓰기 가능한 탭이라 — 아래 "외부 공유(guest) 모드" 참고).
- **행 우클릭 → 수정/삭제 메뉴**: 상태 배지가 아닌 행의 다른 부분(제목·클라이언트·메모 등)을 우클릭하면 "✎ 수정"/"✕ 삭제" 메뉴가 뜬다 (`data-row-menu-id`/`S.proj.rowMenu`, 공유는 `data-shared-row-menu-id`/`S.shared.rowMenu` — 같은 `contextmenu` 리스너에서 상태 배지 다음 우선순위로 분기). 메뉴 버튼은 새 액션을 만들지 않고 기존 `proj-open-edit`/`proj-confirm-delete`(공유는 `shared-*`)를 그대로 재사용 — 그래서 이 두 케이스는 실행될 때 `rowMenu`도 같이 null로 정리해준다.
- **하위 프로젝트(무제한 depth)**: `parentId` 필드로 트리를 이룬다. 행을 클릭하면 그 항목의 하위 목록으로 들어가고(`S.proj.currentParentId` / `S.shared.currentParentId`), 상단에 breadcrumb과 상위 항목 요약 카드(상태·메모·링크(공유만)·수정/삭제)가 뜬다. "+ 새 프로젝트"는 현재 보고 있는 depth의 하위 항목으로 생성되고, 상위를 삭제하면(`proj-confirm-delete-parent`/`shared-confirm-delete-parent`) 모든 하위 항목이 연쇄 삭제된다.
- **드릴다운은 `history.pushState`로 브라우저 히스토리에 쌓인다** (`{projParentId}` 또는 `{sharedParentId}` 상태 객체, `popstate`에서 둘 중 어느 키가 있는지로 구분해 복원). 이거 없으면 하위 프로젝트에 들어간 상태에서 마우스 뒤로가기를 눌렀을 때 앱을 완전히 벗어나 버린다 — 실제로 그 버그가 있었어서 추가한 것.
- **프로젝트 종류 구분**: `PROJECT_TYPES`(`촬영`/`편집`/`기타`, `project.type` 필드)로 프로젝트를 분류한다. 수정 모달의 라디오로 고르고, 행/상위 요약 카드에 이모지 배지로 표시됨. 상태(`status`)와는 별개 필드.
- **프로젝트 ↔ 스케줄 연동**: 프로젝트의 상위 요약 카드에서 "+ 촬영 스케줄 만들기"를 누르면 그 프로젝트 제목이 미리 채워진 일정 등록 폼이 뜨고, 등록하면 프로젝트에는 `scheduleId`, 스케줄 항목에는 `projectId`가 서로 저장돼 양방향으로 연결된다. 이미 연결된 프로젝트는 대신 "📅 날짜" 배지가 뜨고 누르면 스케줄 탭으로 이동해 그 일정 상세를 바로 연다(`proj-view-schedule`/`today-open-project-detail`). **이 기능 때문에 `schedModalHtml()`은 더 이상 스케줄 탭 안에서만 렌더링되지 않고 전역 `render()`에서 항상 렌더링된다** — 어느 탭에 있든 `S.sched.modalOpen`을 켜면 뜨게 하기 위함. 스케줄 탭 자신의 렌더 함수에서 중복 호출하지 않도록 주의할 것.
- **오늘 할 일 탭에 월별 보기 추가**: `S.today.viewMode`(`today`/`month`)와 `S.today.month`(`YYYY-MM`)로 관리. "월별 보기"를 누르면 `‹`/`›` 버튼과 `<input type=month>`로 아무 달이나 이동해서 그 달의 일정을 날짜별로 묶어서 볼 수 있다.
- **스케줄 상세 안에서 촬영준비 체크리스트를 바로 체크할 수 있다**: `findShootForTitle()`로 스케줄 제목과 이름이 같은 `shoots` 항목을 찾아 연결한다(진짜 ID 연결이 아니라 이름 매칭이라 다소 허술함 — 이름을 바꾸면 연결이 끊긴다). 있으면 `shootPackListHtml()`을 그대로 재사용해 패킹 체크리스트를 임베드하고, 없으면 "🎒 촬영준비에서 만들기" 버튼만 보여준다. 이 재사용을 위해 패킹/회수 체크박스에 `data-shoot-id`를 추가해서 `S.shoot.selectedShootId`(촬영준비 탭 전용 상태)에 의존하지 않고 어느 화면에서 클릭해도 올바른 `shoots` 항목을 찾도록 일반화했다 — `shoot-set-mode`도 부분 갱신 대신 항상 `render()`로 바꿔서 스케줄 모달 안에서도 모드 전환이 반영되게 함. 단, 가방으로 드래그해서 옮기는 기능은 여전히 `S.shoot.selectedShootId` 기준이라 스케줄 상세에서는 동작하지 않음(체크박스만 동작).
- **클라이언트 입력은 `<datalist>`로 자동완성된다**: `getKnownClients()`가 `projItems`+`sharedProjItems`에서 실제 쓰인 클라이언트 값을 모아 정렬해서 만든다 — 별도의 "클라이언트 목록"을 관리하는 화면은 없고, 그냥 한 번 입력해서 저장되면 다음부터 그 값이 자동으로 후보에 뜬다. 촬영준비 탭의 `shootType`(`list="shootTypeList"`)과 같은 방식.
- **리스트 행에서 마감일/메모를 모달 없이 바로 수정 가능**: 마감은 `<input type="date" data-role="proj-due-inline">`(공유는 `shared-due-inline`, `change` 이벤트로 저장), 메모는 `contenteditable` `data-role="proj-notes-inline"`(공유는 `shared-notes-inline`, `focusout` 이벤트로 저장). 둘 다 행 전체의 `data-action="proj-drill-in"` 클릭을 가로채지 않도록 `onclick="event.stopPropagation()"`을 달아뒀다 — 이게 없으면 클릭이 버블링돼서 편집하려고 누른 게 하위 프로젝트로 드릴다운돼 버린다. 공유 프로젝트는 게스트도 오너와 동일하게 이 두 필드를 인라인으로 바로 수정할 수 있다(게스트는 쓰기 가능한 탭이라 — 아래 "외부 공유(guest) 모드" 참고).
- **레이아웃 순서**: breadcrumb + 상위 요약 카드는 헤더/툴바보다 아래, 리스트 바로 위에 렌더링된다(원래는 맨 위였는데 "리스트 바로 위가 낫다"는 피드백으로 옮김) — `renderProjectsTab`/`renderSharedProjectsTab`에서 순서: eyebrow → eq-header → eq-toolbar → breadcrumb → 상위 요약 카드 → 리스트.
- **리스트 맨 아래에도 추가 버튼이 있다**: 우측 상단 "+ 새 프로젝트"/"+ 새 공유 프로젝트" 버튼이 하위 프로젝트로 드릴다운했을 때 화면 맨 위라 멀게 느껴진다는 피드백으로, `projListHtml()`/`sharedListHtml()`이 리스트(또는 빈 상태 메시지) 바로 아래에 점선 테두리 `.proj-list-add-btn` 버튼을 하나 더 렌더링한다. 새 action이 아니라 기존 `proj-open-add`/`shared-open-add`를 그대로 재사용 — 현재 보고 있는 depth(`S.proj.currentParentId`/`S.shared.currentParentId`)에 등록되는 건 상단 버튼과 동일.
- **행 복제**: 액션 셀의 ⧉ 아이콘이나 행 우클릭 메뉴의 "⧉ 복제"로 그 항목을 복제한다(`proj-duplicate`/`shared-duplicate`). 제목에 " 복사본"을 붙이고 상태는 기본값으로, 마감일은 비움 — 클라이언트/메모/종류/parentId는 그대로 복사해서 반복적인 등록 작업(예: Lesson 1~N처럼 비슷한 항목 여러 개)을 빠르게 만들 수 있게 함.
- **행 순서를 드래그로 바꿀 수 있다**: 행 왼쪽 끝(`.proj-row-drag-cell`)의 ⠿ 핸들 아이콘만 `draggable`이다(행 전체를 드래그 가능하게 하면 메모 `contenteditable`의 텍스트 선택 제스처와 충돌해서 핸들로 분리함). 드롭하면 대상 행의 위/아래 절반 중 어디에 놓였는지로 그 앞/뒤에 삽입한다(`data-dropzone="proj-row"`, `dragstart`/`drop` 리스너). **같은 `parentId`끼리만 순서가 바뀐다** — 다른 계층으로 드래그하면 조용히 무시됨. 정렬은 여전히 상태(완료가 맨 아래)·마감일 우선이라, 마감일이 없고 상태가 같은 항목들끼리에서만 이 드래그 순서가 화면에 그대로 반영된다(JS 배열 정렬이 stable이라 동점일 때 배열 순서를 유지하는 걸 이용한 것). 모바일 폭(`@media (max-width: 860px)`)에서는 터치 네이티브 드래그가 사실상 안 먹혀서 핸들 자체를 숨김(`.proj-row-drag-cell { display:none; }`) — 그리드 컬럼 수도 원래 4컬럼으로 되돌아감.
- **행의 복제/수정/삭제는 우클릭 메뉴로만 한다**: 예전엔 행에 마우스오버하면 우측에 ⧉/✎/✕ 아이콘이 떴었는데, 우클릭 메뉴(`data-row-menu-id`/`data-shared-row-menu-id`)에 이미 같은 액션(복제/수정/삭제)이 다 있어서 중복이라 없앴다. 지금 행 우측에 남은 건 드릴다운 화살표(`.proj-row-chevron`)뿐 — 실제 쓰기 액션은 전부 우클릭 메뉴 경유.
- **체크박스로 다중 선택해서 일괄 상태 변경/삭제할 수 있다**: 평소엔 체크박스가 안 보이고, 툴바의 "☑ 선택" 버튼(`data-action="proj-toggle-select-mode"`/`shared-toggle-select-mode`, 상태는 `S.proj.selectMode`/`S.shared.selectMode`)을 눌러야 행 맨 왼쪽(`.proj-row-check-cell`)과 헤더에 체크박스가 나타난다 — 리스트 컨테이너에 `select-mode` 클래스가 붙으면서 그리드 컬럼도 그만큼 넓어짐(`.proj-list.select-mode .proj-row`). 헤더 체크박스는 현재 화면에 보이는 항목 전체를 선택하는 전체선택이다(`data-role="proj-select-all"`/`shared-select-all`, `data-ids`에 담긴 콤마구분 id 목록을 토글). 선택된 게 하나라도 있으면 리스트 위에 `.proj-bulk-bar`가 뜨는데, 상태별 일괄 변경 버튼(`PROJECT_COLUMNS`/`SHARED_STATUSES` 순회)과 일괄 삭제·선택 해제 버튼이 있다 — 개별 행의 상태 변경/삭제와 동일하게 `saveProjItems`/`saveSharedProjItems`를 한 번에 호출하고 끝나면 선택을 비운다(선택 모드 자체는 유지 — 계속 고를 수 있게). "선택 취소" 버튼을 누르거나 하위 프로젝트로 드릴다운/상위로 나가면(`proj-drill-in`/`proj-go-parent` 등) 선택 목록이 초기화된다. 공유 프로젝트는 게스트도 오너와 동일하게 "선택" 버튼과 다중선택/일괄작업을 다 쓸 수 있다(게스트는 쓰기 가능한 탭이라 — 아래 "외부 공유(guest) 모드" 참고). 모바일 폭에서는 드래그 핸들과 마찬가지로 체크박스 컬럼도 숨김 — `.proj-list.select-mode .proj-row`도 모바일 미디어쿼리에서 같은 4컬럼으로 되돌아가게 별도로 오버라이드해뒀다(안 그러면 선택모드 8컬럼 규칙이 특이도 때문에 모바일 규칙을 이겨버림). **선택 모드일 때는 체크박스뿐 아니라 행 아무 곳을 클릭해도 선택이 토글된다** — 체크박스만 정확히 눌러야 하는 게 불편하다는 피드백으로, `proj-drill-in`/`shared-drill-in` 핸들러 맨 앞에서 `selectMode`면 원래 하던 드릴다운 대신 선택 토글만 하고 끝내도록 분기했다(마감일 인풋/메모 `contenteditable`/드래그 핸들처럼 이미 `stopPropagation`이 걸린 요소는 여전히 자기 할 일을 하고 선택엔 안 걸림). 선택된 행은 `.proj-row.selected`로 배경이 옅은 강조색(`--accent-soft`)으로 칠해져서 체크박스를 보지 않아도 뭐가 선택됐는지 한눈에 보인다.
- **프로젝트에 상태와 별개로 커스텀 색상을 지정할 수 있다**: 수정 모달에 `project.color` 필드를 고르는 원형 스와치 피커가 있다(장비 카테고리에서 쓰던 `CATEGORY_COLOR_PALETTE` 14색을 그대로 재활용 + "기본"(무색) 옵션). 네이티브 라디오 버튼 + `:has(input:checked)` CSS만으로 선택 상태를 표시해서(`.eq-status-option`과 같은 패턴) 별도 JS 없이 `FormData`로 저장됨. 색이 지정되면 `colorMarkerStyle(color, basePadding)` 헬퍼가 리스트 행/상위 요약 카드에 적용할 인라인 스타일을 만든다 — 왼쪽 테두리 `border-left:6px solid {color}`(처음엔 3px였는데 "구분이 잘 안 보인다"는 피드백으로 두 배로 키움) + 행 전체에 옅게 깔리는 배경 틴트(`--row-tint:{color}22` CSS 변수, `.proj-row`/`.proj-parent-card`가 `background:var(--row-tint, ...)`로 읽음 — 커스텀 프로퍼티라서 hover/선택(`.selected`) 같은 더 구체적인 배경 규칙이 그 위에서 정상적으로 덮어써짐). 지정 안 하면 평소처럼 테두리/틴트 없음 — 상태(진행중/완료 등) 색과는 별개로 순수히 사용자가 구분하려고 붙이는 색이다. 프로젝트/공유 프로젝트 양쪽 다 동일하게 적용됨.

## works/index.html 로그인

- guest 모드가 아닐 때는 Google 로그인(`firebase.auth().onAuthStateChanged`)이 앱 전체를 가로막는다 — `bootApp()`은 로그인 성공 후에만 호출됨. `?guest=1`이면 로그인 절차를 아예 건너뛴다.
- 로그인 후에도 **실제 쓰기 권한은 Firestore 규칙(`isOwner()`, `kj0010735@gmail.com`)이 결정**한다 — 로그인 화면 통과는 UI 접근 제어일 뿐, 진짜 방어선은 규칙 쪽.
- Google 로그인 팝업이 뜨려면 Firebase 콘솔 Authentication → Settings → Authorized domains에 실제 서빙 도메인(`www.vinfilmstudio.com`, `kj0010735-ai.github.io`)이 등록돼 있어야 한다. 안 그러면 `auth/unauthorized-domain` 에러.

## Firebase 관련 주의사항

- 새 컬렉션을 코드에서 쓰기 시작하면 **`firestore.rules`에도 반드시 해당 컬렉션의 allow 규칙을 추가하고 배포할 것.** 규칙이 없으면 그 컬렉션은 조용히 `permission-denied`로 막히고, 앱은 로컬 저장(localStorage)만으로 동작하는 것처럼 보여서 눈치채기 어렵다 (실제로 `sharedProjects`/`siteContent` 컬렉션을 규칙 없이 써서 한동안 클라우드 동기화가 안 되고 있었다).
- Firestore 관련 문제가 생기면 브라우저 콘솔에서 `permission-denied` 에러부터 확인할 것 — 도메인/로컬호스트 문제가 아니라 대부분 규칙 누락이다.
- **`vinfilm-studio-app`은 Standard 등급 Firestore라 자동 백업/시점 복구(PITR)가 없다.** 한 번 지워진 데이터는 서버 쪽에서 되돌릴 방법이 없으니, 실제 데이터가 걸린 컬렉션(특히 `sharedProjects`, `projects`처럼 게스트도 쓰는 것)에 테스트/더미 데이터를 넣는 작업은 각별히 조심할 것.
- **`works/index.html`은 로컬(`localhost`/`127.0.0.1`/`file://`)로 열면 `IS_LOCAL_DEV`가 켜지면서 클라우드 동기화 자체가 꺼진다** (`initCloudSync()` 맨 위에서 조기 리턴, `window.cloudSyncReady`가 아예 안 켜짐 → `pushToCloud`가 항상 no-op). 실제 배포 도메인에서만 정상 동기화됨. 이건 안전장치이지 회피 수단이 아니다 — 예전에 `bootApp()`을 콘솔에서 직접 호출해 로그인 게이트를 우회하고 로컬 서버로 프로젝트/공유 프로젝트 탭을 테스트하다가, `saveProjItems`/`saveSharedProjItems`가 실제 운영 Firestore와 diff-sync(`pushToCloud`)를 태워서 실제 등록된 데이터를 지워버린 사고가 있었다 (로그인 여부와 무관하게 `initCloudSync()`가 켜졌고, `sharedProjects`는 `allow read, write: if true`라 막아주지도 않았음). 지금은 로컬에서 아무리 `saveXxxItems([])` 같은 걸 실행해도 `IS_LOCAL_DEV` 덕분에 localStorage만 바뀌고 실제 데이터는 안전하다 — 다만 이 안전장치를 믿고 방심하지 말고, 실제 배포 도메인에서 직접 확인해야 할 때는 되도록 읽기만 하고 쓰기 테스트는 피할 것.

## 외부 공유(guest) 모드 — works/index.html

`works/index.html?guest=1`로 접속하면 `GUEST_MODE`가 켜지며 사이드바에 장비목록/공유 프로젝트 탭만 보이고, 로그인 절차도 없다.

**게스트 권한은 탭마다 다르다** (둘 다 로그인 없이 접근):
- **공유 프로젝트**: 로그인 없는 공동작업자로서 같이 등록/수정 가능 — `sharedProjects`는 `allow read, write: if true`. **UI도 오너와 완전히 동일하게 다 열려 있어야 한다** — 등록(+ 버튼)/수정·삭제(우클릭 메뉴)/복제/드래그 순서변경/체크박스 다중선택/상태 우클릭 빠른 변경/마감일·메모 인라인 수정 전부. (한동안 프로젝트 목록에 기능을 하나씩 추가할 때마다 각 기능을 개별적으로 `!GUEST_MODE`로 막아버려서 게스트가 사실상 읽기 전용이 돼버린 적이 있었다 — 게스트 이름 입력 화면 문구가 "수정 기록에 표시할 이름을 알려주세요"인 것에서 보이듯 원래 의도는 계속 쓰기 가능하게 두는 것이었어서, `shared-*` action에 붙어있던 `GUEST_MODE` 가드들을 다시 다 걷어냈다. 새 기능을 공유 프로젝트 탭에 추가할 때 습관적으로 `!GUEST_MODE`를 붙이지 말 것 — 게스트도 오너와 동일하게 그 기능을 쓸 수 있어야 정상이다.)
- **장비목록**: 보기 전용. 처음엔 게스트도 수정 가능하게 열어뒀다가, "장비는 게스트가 못 건드리게" 요청으로 다시 잠갔다 — `equipment`/`categories`는 `allow read: if true; allow write: if isOwner()`. UI에서도 GUEST_MODE일 때 등록/수정/삭제/카테고리 관리 버튼을 전부 숨기고, 클릭 핸들러 쪽에도 `EQ_WRITE_ACTIONS` 방어선을 하나 더 둠 (`works/index.html`의 `eq-` 관련 액션 처리부 참고). **장비목록과 공유 프로젝트는 게스트 권한이 정반대이니 새 기능을 만들 때 두 탭을 헷갈리지 말 것.**

`schedule`/`projects`/`shoots`/`presets`/`todayTasks`/`notes`처럼 guest 모드에 아예 노출 안 되는 컬렉션은 `isOwner()`로 로그인 필수 처리돼 있다.

즉 장비목록/공유 프로젝트는 **URL만 알면 로그인 없이 누구나 읽고 쓸 수 있는 상태**다 (의도된 설계). guest 모드는 그 위에서 UI 탭만 제한해 외부 협업자가 필요한 두 화면만 보게 하는 것이지, 데이터 자체를 잠그는 게 아니다.

## 작업 시 유의사항

- 프레임워크 없이 바닐라 JS로 작성됨 — React/Vue 등 새 의존성을 임의로 추가하지 말 것.
- 파일을 열어 실제로 확인할 때는 `mcp__Claude_Browser__preview_start`로 직접 열어서 확인 가능하지만, Firebase 연동 확인은 위 주의사항대로 실제 배포 도메인에서 해야 한다.
- UI 텍스트는 전부 한국어. 새로 추가하는 문구도 기존 톤(간결한 한국어)에 맞출 것.
- 스튜디오 공식 표기는 **VINFILM STUDIO** (한글 음차 "빈필름스튜디오"를 임의로 쓰지 말 것).
