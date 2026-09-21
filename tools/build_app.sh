#!/bin/bash
# "프로젝트 정리.app"을 만든다. 코드를 고친 뒤 다시 실행하면 앱이 갱신된다.
# 앱은 파이썬 파일을 안에 복사해 넣기 때문에, 완성된 .app은 어디로 옮겨도(예: 응용 프로그램 폴더) 동작한다.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$DIR/프로젝트 정리.app"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$DIR/organize_project.py" "$DIR/organizer_app.py" "$APP/Contents/Resources/"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>프로젝트 정리</string>
  <key>CFBundleDisplayName</key><string>프로젝트 정리</string>
  <key>CFBundleIdentifier</key><string>com.vinfilmstudio.project-organizer</string>
  <key>CFBundleExecutable</key><string>launcher</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>LSUIElement</key><true/>
</dict></plist>
PLIST

cat > "$APP/Contents/MacOS/launcher" <<'SH'
#!/bin/bash
RES="$(cd "$(dirname "$0")/../Resources" && pwd)"
for PY in /usr/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  [ -x "$PY" ] && exec "$PY" "$RES/organizer_app.py"
done
osascript -e 'display dialog "python3를 찾을 수 없어요. 터미널에서 xcode-select --install 을 실행해 설치해 주세요." buttons {"확인"}'
SH
chmod +x "$APP/Contents/MacOS/launcher"

codesign --force --deep -s - "$APP" >/dev/null 2>&1 || true
echo "만들어졌어요: $APP"
