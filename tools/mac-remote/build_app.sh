#!/bin/bash
# "VINFILM 리모트.app"을 만든다 — 아이폰을 이 맥의 트랙패드·키보드로 쓰는 리모트(같은 와이파이).
# 실행하면 백그라운드에서 작은 서버(remote_server.py, 표준 라이브러리만)가 켜지고, 연결용 QR 화면이 뜬다.
# 코드(remote_server.py, web/)나 아이콘을 고친 뒤 이 스크립트를 다시 실행하면 앱이 갱신된다.
# 앱을 다시 만들면 서명이 바뀌어서 "손쉬운 사용" 권한을 한 번 껐다 켜야 할 수 있다.
# 아이콘: icon.svg → AppIcon.icns, 아이폰 홈 화면 아이콘은 icon-fullbleed.svg → web/icon-180.png
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$DIR/VINFILM 리모트.app"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$DIR/remote_server.py" "$DIR/AppIcon.icns" "$APP/Contents/Resources/"
cp -R "$DIR/web" "$APP/Contents/Resources/web"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>VINFILM 리모트</string>
  <key>CFBundleDisplayName</key><string>VINFILM 리모트</string>
  <key>CFBundleIdentifier</key><string>com.vinfilmstudio.remote</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundleExecutable</key><string>launcher</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>LSUIElement</key><true/>
  <key>NSLocalNetworkUsageDescription</key><string>같은 와이파이의 아이폰이 이 맥을 조종하려면 필요해요.</string>
</dict></plist>
PLIST

cat > "$APP/Contents/MacOS/launcher" <<'SH'
#!/bin/bash
RES="$(cd "$(dirname "$0")/../Resources" && pwd)"
for PY in /usr/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  [ -x "$PY" ] && exec "$PY" "$RES/remote_server.py"
done
osascript -e 'display dialog "python3를 찾을 수 없어요. 터미널에서 xcode-select --install 을 실행해 설치해 주세요." buttons {"확인"}'
SH
chmod +x "$APP/Contents/MacOS/launcher"

codesign --force --deep -s - "$APP" >/dev/null 2>&1 || true
echo "만들어졌어요: $APP"
