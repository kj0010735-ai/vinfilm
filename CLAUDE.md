# VINFILM STUDIO 웹 프로젝트

영상 프로덕션 스튜디오(VINFILM STUDIO)의 공개 홈페이지 + 내부 작업 관리 도구. 순수 HTML/CSS/JS로, 빌드 과정이나 프레임워크 없이 파일 하나당 페이지 하나로 동작한다.

## 저장소 구조

- `index.html` — **공개 홈페이지** (루트, 커스텀 도메인 `www.vinfilmstudio.com`이 여기로 연결됨). 포트폴리오/소개/연락처.
- `service.html` — 서비스 상세 페이지 (`?id=interview|sketch|mv|youtube`). index.html의 "무엇을 만드나요?" 목록에서 클릭하면 넘어옴. 서비스별 태그라인·소개문구·진행 단계도 `siteContent/home`의 `services` 필드에서 읽어온다.
- `admin/index.html` — 홈페이지 콘텐츠 관리자 화면. 비밀번호 게이트 + Firestore `siteContent/home` 문서 편집.
- `works/index.html` — **내부 작업 관리 앱** (기존 "작업 관리" 툴, 원래 루트에 있던 파일을 이전한 것). 장비목록/스케줄/프로젝트/공유 프로젝트/메모장 탭 구성. `?guest=1`로 외부 공유 모드 진입 가능.
- `works/장비목록 이미지/` — 장비 사진 에셋.
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

내부 앱도 공개 홈페이지와 같은 다크 웜톤(배경 `#0e0d0c`, 포인트 컬러 `#d98a3d`, Noto Sans KR 본문)을 쓴다 — `.app-shell`의 CSS 변수(`--bg`/`--accent`/`--font-body` 등)만 바꾸면 앱 전체에 적용되는 구조라 두 사이트 색이 어긋나지 않게 관리하기 쉽다. `--font-display`(Anton)는 한글을 지원하지 않는 폰트라 영문 라벨(예: "WORK MANAGEMENT" eyebrow, 코드/D-day 같은 영문·숫자)에만 쓰고, 한글 텍스트에는 절대 적용하지 말 것 — Anton은 한글을 렌더링하지 못해 그냥 폴백 폰트로 깨져 보인다.

**프로젝트 탭과 공유 프로젝트 탭 둘 다 칸반 보드가 아니라 같은 리스트형 게시판 UI**를 쓴다 (마감 임박순 정렬, 검색/상태 필터, `.proj-row`/`.proj-list`/`.proj-breadcrumb`/`.proj-parent-card`/`.proj-status-menu` 등 CSS 클래스를 두 탭이 공유). 로직은 각자 분리돼 있다 — 프로젝트는 `projItems`/`saveProjItems`/`PROJECT_COLUMNS`/`projRowHtml`, 공유 프로젝트는 `sharedProjItems`/`saveSharedProjItems`/`SHARED_STATUSES`/`sharedRowHtml`.

- **상태 변경 두 가지 경로**: ① 수정 모달(프로젝트는 라디오, 공유 프로젝트는 select), ② 상태 배지 우클릭 → 빠른 변경 메뉴 (프로젝트는 `data-status-menu-id`/`S.proj.statusMenu`, 공유 프로젝트는 `data-shared-status-menu-id`/`S.shared.statusMenu` — 같은 `contextmenu` 리스너 안에서 분기). 드래그로 상태를 바꾸던 옛 칸반 방식은 없앴다. 공유 프로젝트는 게스트 모드일 때 이 배지에 우클릭 트리거 자체가 안 붙는다.
- **하위 프로젝트(무제한 depth)**: `parentId` 필드로 트리를 이룬다. 행을 클릭하면 그 항목의 하위 목록으로 들어가고(`S.proj.currentParentId` / `S.shared.currentParentId`), 상단에 breadcrumb과 상위 항목 요약 카드(상태·메모·링크(공유만)·수정/삭제)가 뜬다. "+ 새 프로젝트"는 현재 보고 있는 depth의 하위 항목으로 생성되고, 상위를 삭제하면(`proj-confirm-delete-parent`/`shared-confirm-delete-parent`) 모든 하위 항목이 연쇄 삭제된다.
- **드릴다운은 `history.pushState`로 브라우저 히스토리에 쌓인다** (`{projParentId}` 또는 `{sharedParentId}` 상태 객체, `popstate`에서 둘 중 어느 키가 있는지로 구분해 복원). 이거 없으면 하위 프로젝트에 들어간 상태에서 마우스 뒤로가기를 눌렀을 때 앱을 완전히 벗어나 버린다 — 실제로 그 버그가 있었어서 추가한 것.

## works/index.html 로그인

- guest 모드가 아닐 때는 Google 로그인(`firebase.auth().onAuthStateChanged`)이 앱 전체를 가로막는다 — `bootApp()`은 로그인 성공 후에만 호출됨. `?guest=1`이면 로그인 절차를 아예 건너뛴다.
- 로그인 후에도 **실제 쓰기 권한은 Firestore 규칙(`isOwner()`, `kj0010735@gmail.com`)이 결정**한다 — 로그인 화면 통과는 UI 접근 제어일 뿐, 진짜 방어선은 규칙 쪽.
- Google 로그인 팝업이 뜨려면 Firebase 콘솔 Authentication → Settings → Authorized domains에 실제 서빙 도메인(`www.vinfilmstudio.com`, `kj0010735-ai.github.io`)이 등록돼 있어야 한다. 안 그러면 `auth/unauthorized-domain` 에러.

## Firebase 관련 주의사항

- 새 컬렉션을 코드에서 쓰기 시작하면 **`firestore.rules`에도 반드시 해당 컬렉션의 allow 규칙을 추가하고 배포할 것.** 규칙이 없으면 그 컬렉션은 조용히 `permission-denied`로 막히고, 앱은 로컬 저장(localStorage)만으로 동작하는 것처럼 보여서 눈치채기 어렵다 (실제로 `sharedProjects`/`siteContent` 컬렉션을 규칙 없이 써서 한동안 클라우드 동기화가 안 되고 있었다).
- Firestore 관련 문제가 생기면 브라우저 콘솔에서 `permission-denied` 에러부터 확인할 것 — 도메인/로컬호스트 문제가 아니라 대부분 규칙 누락이다.

## 외부 공유(guest) 모드 — works/index.html

`works/index.html?guest=1`로 접속하면 `GUEST_MODE`가 켜지며 사이드바에 장비목록/공유 프로젝트 탭만 보이고, 로그인 절차도 없다.

**게스트 권한은 탭마다 다르다** (둘 다 로그인 없이 접근):
- **공유 프로젝트**: 로그인 없는 공동작업자로서 같이 등록/수정 가능 — `sharedProjects`는 `allow read, write: if true`.
- **장비목록**: 보기 전용. 처음엔 게스트도 수정 가능하게 열어뒀다가, "장비는 게스트가 못 건드리게" 요청으로 다시 잠갔다 — `equipment`/`categories`는 `allow read: if true; allow write: if isOwner()`. UI에서도 GUEST_MODE일 때 등록/수정/삭제/카테고리 관리 버튼을 전부 숨기고, 클릭 핸들러 쪽에도 `EQ_WRITE_ACTIONS` 방어선을 하나 더 둠 (`works/index.html`의 `eq-` 관련 액션 처리부 참고).

`schedule`/`projects`/`shoots`/`presets`/`todayTasks`/`notes`처럼 guest 모드에 아예 노출 안 되는 컬렉션은 `isOwner()`로 로그인 필수 처리돼 있다.

즉 장비목록/공유 프로젝트는 **URL만 알면 로그인 없이 누구나 읽고 쓸 수 있는 상태**다 (의도된 설계). guest 모드는 그 위에서 UI 탭만 제한해 외부 협업자가 필요한 두 화면만 보게 하는 것이지, 데이터 자체를 잠그는 게 아니다.

## 작업 시 유의사항

- 프레임워크 없이 바닐라 JS로 작성됨 — React/Vue 등 새 의존성을 임의로 추가하지 말 것.
- 파일을 열어 실제로 확인할 때는 `mcp__Claude_Browser__preview_start`로 직접 열어서 확인 가능하지만, Firebase 연동 확인은 위 주의사항대로 실제 배포 도메인에서 해야 한다.
- UI 텍스트는 전부 한국어. 새로 추가하는 문구도 기존 톤(간결한 한국어)에 맞출 것.
- 스튜디오 공식 표기는 **VINFILM STUDIO** (한글 음차 "빈필름스튜디오"를 임의로 쓰지 말 것).
