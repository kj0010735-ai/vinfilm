-- Stream Deck용: 맥 받아쓰기(음성 입력)를 켜고 끈다.
-- 받아쓰기 단축키(시스템 설정 → 키보드 → 받아쓰기 → 단축키 → 사용자화)를 ⌃⌥⌘D 로 맞춰 둬야 하고,
-- 이 앱에 손쉬운 사용 권한(시스템 설정 → 개인정보 보호 및 보안 → 손쉬운 사용)을 줘야 키를 보낼 수 있다.
tell application "System Events" to keystroke "d" using {control down, option down, command down}
