# VINFILM STUDIO 웹 프로젝트

영상 프로덕션 스튜디오(VINFILM STUDIO)의 공개 홈페이지 + 내부 작업 관리 도구. 순수 HTML/CSS/JS로, 빌드 과정이나 프레임워크 없이 파일 하나당 페이지 하나로 동작한다.

## 저장소 구조

- `index.html` — **공개 홈페이지** (루트, 커스텀 도메인 `www.vinfilmstudio.com`이 여기로 연결됨). 포트폴리오/소개/연락처.
- `admin/index.html` — 홈페이지 콘텐츠 관리자 화면. 비밀번호 게이트 + Firestore `siteContent/home` 문서 편집.
- `works/index.html` — **내부 작업 관리 앱** (기존 "작업 관리" 툴, 원래 루트에 있던 파일을 이전한 것). 장비목록/스케줄/프로젝트/공유 프로젝트/메모장 탭 구성. `?guest=1`로 외부 공유 모드 진입 가능.
- `works/장비목록 이미지/` — 장비 사진 에셋.
- `CNAME` — GitHub Pages 커스텀 도메인 설정 파일 (`www.vinfilmstudio.com`).
- 저장: `localStorage`가 기본, Firebase Firestore(compat SDK)로 클라우드 동기화. 인터넷이 없으면 Firebase 로딩이 조용히 실패하고 로컬 저장만으로 동작하도록 설계됨.

## 공개 홈페이지 (index.html)

다크 시네마틱 톤 랜딩 페이지. 히어로/최근 작업(넘버링 그리드)/서비스(풀블리드 컬러 섹션)/연락처/푸터로 구성. 콘텐츠(메인 영상 URL, 헤드라인, 작업 목록, 연락처 등)는 Firestore `siteContent/home` 문서에서 읽어오고, 문서가 없거나 로드 실패 시 `DEFAULT_CONTENT`로 폴백한다 — **`DEFAULT_CONTENT`는 index.html과 admin/index.html 양쪽에 동일하게 복제되어 있으니, 하나를 고치면 반드시 다른 쪽도 같이 고칠 것.**

## admin 페이지 (admin/index.html)

- 비밀번호는 파일 상단 `ADMIN_PASSWORD` 상수. **평문으로 코드에 들어있어 완전한 보안은 아님** — 개발자 도구로 소스를 보면 누구나 알 수 있는 수준의 방어. 실제 계정 기반 보안이 필요해지면 Firebase Authentication 연동으로 교체할 것.
- 저장 시 Firestore `siteContent/home` 문서를 통째로 `.set()`으로 덮어씀 (부분 업데이트 아님) — 필드 추가 시 admin 폼에도 같이 반영해야 유실되지 않는다.

## Firebase 관련 주의사항

- `FIREBASE_CONFIG`의 API 키는 **HTTP 리퍼러 제한이 걸려 있는 것으로 보임** — `http://localhost`에서 테스트하면 기존에 잘 동작하던 컬렉션까지 전부 `permission-denied`가 뜬다 (Firestore 규칙 문제가 아니라 Google Cloud Console의 API 키 애플리케이션 제한 때문으로 추정). 로컬에서 Firebase 연동을 확인하려면 실제 배포 도메인(GitHub Pages 또는 커스텀 도메인)에서 테스트해야 한다.
- 커스텀 도메인(`www.vinfilmstudio.com`)을 새로 연결했다면, Google Cloud Console → API 및 서비스 → 사용자 인증 정보에서 해당 API 키의 허용 리퍼러 목록에 `https://www.vinfilmstudio.com/*`를 추가해야 Firestore 호출이 정상 동작한다 (기존에는 `https://kj0010735-ai.github.io/*`만 등록돼 있었을 가능성이 높음).

## 외부 공유(guest) 모드 — works/index.html

`works/index.html?guest=1`로 접속하면 `GUEST_MODE`가 켜지며 사이드바에 장비목록/공유 프로젝트 탭만 보이고, 공유 프로젝트 탭의 추가/수정/삭제 버튼도 숨겨진다.

**주의: 이건 UI 상에서만 탭을 숨기는 것이지 실제 데이터 보안이 아니다.** Firebase 설정값이 공개 저장소에 그대로 노출돼 있어서, Firestore 보안 규칙이 허용하는 범위 내에서는 개발자 도구로 직접 호출해 데이터를 읽고 쓸 수 있다. guest 모드는 동기화되는 컬렉션을 `equipment`/`categories`/`sharedProjects`로만 제한해서 내부용 데이터가 외부 브라우저로 아예 내려받히지 않게는 해두었지만, 이것도 앱 코드 안에서의 완화일 뿐이다.

## 작업 시 유의사항

- 프레임워크 없이 바닐라 JS로 작성됨 — React/Vue 등 새 의존성을 임의로 추가하지 말 것.
- 파일을 열어 실제로 확인할 때는 `mcp__Claude_Browser__preview_start`로 직접 열어서 확인 가능하지만, Firebase 연동 확인은 위 주의사항대로 실제 배포 도메인에서 해야 한다.
- UI 텍스트는 전부 한국어. 새로 추가하는 문구도 기존 톤(간결한 한국어)에 맞출 것.
- 스튜디오 공식 표기는 **VINFILM STUDIO** (한글 음차 "빈필름스튜디오"를 임의로 쓰지 말 것).
