#!/bin/bash
# 스트림덱용 "카카오톡 켜고끄기" 앱 2개를 만든다: 누르면 카카오톡 창이 뜨고, 앞에 떠 있을 때 다시 누르면 숨긴다(종료가 아니라 숨김 — 알림은 계속 옴).
# 실행 파일이 bash라 이 앱 자체는 화면 앞으로 나오지 않는다(그래야 "카카오톡이 지금 앞에 있는지"를 제대로 판단함).
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
make() { # 이름, 번들 id, 열 앱 경로, 아이콘(.icns 또는 빈 값)
  APP="$DIR/$1.app"; rm -rf "$APP"; mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
  [ -n "$4" ] && cp "$4" "$APP/Contents/Resources/AppIcon.icns"
  cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>$1</string>
  <key>CFBundleIdentifier</key><string>com.vinfilmstudio.toggle.$2</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundleExecutable</key><string>launcher</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSUIElement</key><true/>
</dict></plist>
PLIST
  cat > "$APP/Contents/MacOS/launcher" <<SH
#!/bin/bash
R=\$(osascript -l JavaScript -e 'ObjC.import("AppKit"); var a=\$.NSRunningApplication.runningApplicationsWithBundleIdentifier("$2"); if (a.count === 0) { "open" } else { var app=a.objectAtIndex(0); if (app.active) { app.hide; "hidden" } else { "open" } }')
[ "\$R" = "open" ] && open "$3"
exit 0
SH
  chmod +x "$APP/Contents/MacOS/launcher"; codesign --force --deep -s - "$APP" >/dev/null 2>&1 || true
  echo "만들어졌어요: $APP"
}
make "카카오톡 켜고끄기" "com.kakao.KakaoTalkMac" "/Applications/KakaoTalk.app" ""
make "카카오톡 V 켜고끄기" "com.kakao.KakaoTalkMac.second" "$HOME/Applications/KakaoTalk 2.app" "$DIR/AppIcon.icns"
