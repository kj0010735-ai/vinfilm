#!/bin/bash
# 맥 카카오톡을 계정 2개로 동시에 쓰기 위한 "KakaoTalk 2.app"(복사본)을 만든다.
# 원본(/Applications/KakaoTalk.app)은 건드리지 않고, 복사본의 번들 id만 바꿔 로그인·데이터를 따로 쓰게 한다.
# 카카오톡이 업데이트되면 복사본은 옛 버전으로 남으므로 이 스크립트를 다시 실행한다(두 번째 계정은 다시 로그인해야 할 수 있음).
# 카카오가 공식 지원하는 방식은 아니다.
set -e
SRC="/Applications/KakaoTalk.app"
DST="$HOME/Applications/KakaoTalk 2.app"
pkill -f "$DST/Contents/MacOS/KakaoTalk" 2>/dev/null || true
rm -rf "$DST"
cp -R "$SRC" "$DST"
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier com.kakao.KakaoTalkMac.second" "$DST/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleName KakaoTalk 2" "$DST/Contents/Info.plist"
rm -rf "$DST/Contents/_MASReceipt"
xattr -cr "$DST"
codesign --force --deep --sign - "$DST" >/dev/null 2>&1
# 원본과 구분되는 아이콘(검은 타일 + 흰 말풍선 + 2)을 Finder 사용자 아이콘으로 붙인다 — 서명된 파일은 건드리지 않음
DIR="$(cd "$(dirname "$0")" && pwd)"
osascript -l JavaScript -e 'ObjC.import("AppKit"); function run(a){ var img=$.NSImage.alloc.initWithContentsOfFile(a[0]); return $.NSWorkspace.sharedWorkspace.setIconForFileOptions(img, a[1], 0); }' "$DIR/AppIcon.icns" "$DST" >/dev/null
echo "만들어졌어요: $DST"
