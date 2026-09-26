/* VINFILM 작업관리 서비스 워커 — "새 버전 알림" 전용.
   캐시는 전혀 하지 않는다(fetch 핸들러 없음 → 모든 요청은 평소처럼 네트워크로). 이 파일의 내용이 바뀌면
   브라우저가 새 버전으로 인식하므로, works/ 아래 파일이 커밋될 때 .githooks/pre-commit이 VERSION을 자동으로 바꾼다.
   새 워커는 설치돼도 기다리다가(waiting), 앱에서 [업데이트]를 누르면 SKIP_WAITING 메시지를 받고 넘어간다. */
const VERSION = '20260926151225';

// install 때 자동 skipWaiting 하지 않는다 — 쓰던 글이 날아가지 않게, 사용자가 누를 때만 적용.
self.addEventListener('install', () => {});
self.addEventListener('activate', (event) => { event.waitUntil(self.clients.claim()); });
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') self.skipWaiting();
});
