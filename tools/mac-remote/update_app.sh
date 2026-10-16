#!/bin/bash
# 이미 설치한 /Applications/VINFILM 리모트.app의 프로그램 파일(remote_server.py, web/)만 새것으로 바꾼다.
# 실행 파일(launcher)은 그대로라 "손쉬운 사용"·"로컬 네트워크" 권한을 다시 넣지 않아도 된다.
# (build_app.sh로 앱을 통째로 새로 만들면 서명이 바뀌어 권한을 지우고 다시 넣어야 한다 — 실행기를 고쳤을 때만 그렇게)
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
APP="${1:-/Applications/VINFILM 리모트.app}"
[ -d "$APP" ] || { echo "설치된 앱이 없어요: $APP — 먼저 build_app.sh로 만들어 응용 프로그램 폴더로 옮겨 주세요."; exit 1; }
pkill -f remote_server.py 2>/dev/null || true
pkill -f "VINFILM 리모트.app/Contents/MacOS/launcher" 2>/dev/null || true
sleep 1
xattr -cr "$DIR" 2>/dev/null || true
cp "$DIR/remote_server.py" "$APP/Contents/Resources/"
rm -rf "$APP/Contents/Resources/web"
cp -R "$DIR/web" "$APP/Contents/Resources/web"
open "$APP"
echo "업데이트했어요: $APP — 아이폰 리모컨 화면은 껐다 다시 열어 주세요."
