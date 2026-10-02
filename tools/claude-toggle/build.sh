#!/bin/bash
# 스트림덱용 "비서실 켜고끄기.app": 누르면 Claude 앱 창이 앞으로 나오고, 앞에 떠 있을 때 다시 누르면 숨긴다(종료 아님).
# 카카오톡 켜고끄기와 같은 방식 — NSRunningApplication.hide라 손쉬운 사용 권한이 필요 없고, 실행 파일이 bash라 이 앱 자체는 앞으로 나오지 않는다.
# Claude 앱은 설치 위치가 기기마다 달라서(이 맥은 /Applications가 아님) 경로 대신 번들 id로 연다.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$DIR/비서실 켜고끄기.app"; BID="com.anthropic.claudefordesktop"
rm -rf "$APP"; mkdir -p "$APP/Contents/MacOS"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>비서실 켜고끄기</string>
  <key>CFBundleIdentifier</key><string>com.vinfilmstudio.toggle.claude</string>
  <key>CFBundleExecutable</key><string>launcher</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSUIElement</key><true/>
</dict></plist>
PLIST
cat > "$APP/Contents/MacOS/launcher" <<SH
#!/bin/bash
R=\$(osascript -l JavaScript -e 'ObjC.import("AppKit"); var a=\$.NSRunningApplication.runningApplicationsWithBundleIdentifier("$BID"); if (a.count === 0) { "open" } else { var app=a.objectAtIndex(0); if (app.active) { app.hide; "hidden" } else { "open" } }')
[ "\$R" = "open" ] && open -b "$BID"
exit 0
SH
chmod +x "$APP/Contents/MacOS/launcher"; codesign --force --deep -s - "$APP" >/dev/null 2>&1 || true
echo "만들어졌어요: $APP"
