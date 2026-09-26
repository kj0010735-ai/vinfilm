#!/bin/bash
# "VINFILM 작업관리.app"을 만든다. 실행하면 작업 관리 사이트(www.vinfilmstudio.com/works/)를
# 주소창 없는 전용 창(Chrome 앱 모드)으로 연다 — Chrome 계열이 없으면 기본 브라우저로 연다.
# 아이콘(icon.svg → AppIcon.icns)을 바꾸면 이 스크립트를 다시 실행하면 된다. .icns는 아래로 만든다:
#   qlmanage -t -s 1024 -o . icon.svg 로 PNG를 뽑고, sips로 크기별 복사 후 iconutil -c icns
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$DIR/VINFILM 작업관리.app"
URL="https://www.vinfilmstudio.com/works/"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$DIR/AppIcon.icns" "$APP/Contents/Resources/"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>VINFILM 작업관리</string>
  <key>CFBundleDisplayName</key><string>VINFILM 작업관리</string>
  <key>CFBundleIdentifier</key><string>com.vinfilmstudio.works</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundleExecutable</key><string>launcher</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>LSUIElement</key><true/>
</dict></plist>
PLIST

cat > "$APP/Contents/MacOS/launcher" <<SH
#!/bin/bash
URL="$URL"
for B in "/Applications/Google Chrome.app" "/Applications/Microsoft Edge.app" "/Applications/Brave Browser.app" "/Applications/Chromium.app"; do
  if [ -d "\$B" ]; then
    exec open -na "\$B" --args --app="\$URL" --window-size=1360,900
  fi
done
exec open "\$URL"
SH
chmod +x "$APP/Contents/MacOS/launcher"

codesign --force --deep -s - "$APP" >/dev/null 2>&1 || true
echo "만들어졌어요: $APP"
