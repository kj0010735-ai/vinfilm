# WORKS (아이폰 앱)

www.vinfilmstudio.com/works/ (VINFILM STUDIO 작업 관리)를 앱 화면으로 띄우고 애플 푸시(APNs)를 받는 대표님용 앱.
**대표님 혼자 쓰는 앱이라 TestFlight·App Store Connect 등록은 안 한다.** 개발 서명(Debug)으로 아이폰에 직접 설치한다.

- 번들 ID: com.kj.vinfilmworks · 팀 XWP2GSVVQ6 · 홈 화면 이름: WORKS
- 틀: HISPLAN 'WORK' 앱(`~/Documents/hisplan-app`, connect54/work-ios)과 같다. 코드는 `App/WorksApp.swift` 하나.
- 프로젝트 만들기: `xcodegen generate` (project.yml) — 만들어진 `Works.xcodeproj`·`build/`는 git에 안 올린다.

## 사이트와의 약속 (works/index.html의 `workAppIos()`)
- 앱 → 웹: `window.__workApp = { platform:'ios', push:{ permission, token, env } }` + `workapp:push` 이벤트
- 웹 → 앱: `webkit.messageHandlers.workApp.postMessage({ type: 'enablePush' | 'badge' | 'openSettings' })`
- 사이트가 토큰을 Firestore `pushSubs/apns-{해시}` = `{ apns:{token, env}, device, at }`로 적는다. 보내는 쪽은 `tools/studio-bridge/push.mjs`(+ `apns.mjs`).
- Debug 빌드의 토큰은 **sandbox** 환경이다(`#if DEBUG`). `apns.mjs`는 문서의 `env`를 보고 sandbox/production 주소를 고른다.

## 아이폰에 직접 설치 (Debug, 개발 서명)
아이폰 15 Pro가 맥에 연결돼 있고 개발자 모드가 켜져 있어야 한다.
```sh
xcodegen generate
DEV=00008130-0010482C1191001C   # 김규빈 15pro (xcrun devicectl list devices 로 확인)
xcodebuild -project Works.xcodeproj -scheme Works -configuration Debug -destination "id=$DEV" -derivedDataPath build/dev -allowProvisioningUpdates build
xcrun devicectl device install app --device $DEV build/dev/Build/Products/Debug-iphoneos/WORKS.app
xcrun devicectl device process launch --device $DEV com.kj.vinfilmworks
```
- **개발 프로필은 2027-11-11에 만료**된다. 그 전에 위 순서로 다시 빌드·설치할 것(안 하면 앱이 안 열린다).
- 프로필에 등록된 기기에서만 설치된다(Xcode가 `-allowProvisioningUpdates`로 알아서 관리).

## 시뮬레이터 시험 (서명 없이)
```sh
xcodebuild -project Works.xcodeproj -scheme Works -configuration Debug -destination 'generic/platform=iOS Simulator' -derivedDataPath build/sim CODE_SIGNING_ALLOWED=NO build
```

## 알림 시험 (앱 설정(⚙️) → 알림 → '알림 켜기'를 누른 뒤)
홈 화면에는 알림·설치 안내 배너가 없다. 알림 켜기는 설정 창에만 있다.
`node tools/studio-bridge/push.mjs "제목" "내용" /works/` — 웹 푸시와 앱 푸시 모두에 간다. 키(.p8)는 저장소 밖 `~/Library/Application Support/VINFILM Studio/`.
Mac이 켜져 있고 이 프로그램이 돌 때만 알림이 간다(보내는 서버 = Mac).

## 알아 둘 것
- 앱은 라이브 사이트를 읽는다. **works/index.html의 앱 알림 코드가 배포(커밋·푸시)돼야** 앱의 알림 허용·토큰 저장이 동작한다.
- 구글 로그인은 앱 안 팝업(firebaseapp.com)으로 뜬다. 처음 설치한 기기에서 로그인이 되는지 꼭 확인할 것(안 되면 알려 주세요).
- 서비스 워커가 WKWebView에는 없어서 '새 버전이 나왔어요' 토스트는 앱에서 안 뜬다. 대신 20분 넘게 쉬었다 돌아오면 새로 읽는다.
- 견적서 인쇄/PDF(`window.print()`)는 앱에서 지원이 약하다 — 그건 맥에서.
- (참고, 안 씀) TestFlight로 올리려면 App Store Connect에 앱 레코드를 만든 뒤 `export.plist`(destination=upload)로 `-exportArchive` 한다.
