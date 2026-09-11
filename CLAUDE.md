# VINFILM STUDIO 웹 프로젝트

영상 프로덕션 스튜디오(VINFILM STUDIO)의 공개 홈페이지 + 내부 작업 관리 도구. 순수 HTML/CSS/JS로, 빌드 과정이나 프레임워크 없이 파일 하나당 페이지 하나로 동작한다.

## 저장소 구조

- `index.html` — **공개 홈페이지** (루트, 커스텀 도메인 `www.vinfilmstudio.com`이 여기로 연결됨). 포트폴리오/소개/연락처.
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
- 저장 시 Firestore `siteContent/home` 문서를 통째로 `.set()`으로 덮어씀 (부분 업데이트 아님) — 필드 추가 시 admin 폼에도 같이 반영해야 유실되지 않는다.

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
