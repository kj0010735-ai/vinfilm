#!/bin/bash
# 스트림덱용 켜고끄기 앱 2개를 만든다: "작업관리 켜고끄기.app"(여기), "수입지출 켜고끄기.app"(tools/ledger-app).
# 각각 Chrome에서 "앱으로 설치"한 VINFILM 작업관리 / VINFILM 수입지출(서로 다른 앱)을 켜고 끈다:
# 누르면 그 앱이 뜨고, 앞에 떠 있을 때 다시 누르면 숨긴다(종료가 아니라 숨김 — 다시 켤 때 로딩이 없다).
# 설치된 앱은 ~/Applications/Chrome 앱 폴더에서 주소로 찾는다 — Chrome에서 두 주소를 먼저 앱으로 설치한 뒤 실행할 것.
# tools/kakao-second/build_toggle.sh와 같은 방식(실행 파일이 bash라 이 앱 자체는 앞으로 안 나옴).
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
make() { # 이름, 키, 주소, 만들 폴더
  TARGET=""
  for A in "$HOME/Applications/Chrome Apps.localized"/*.app; do
    [ "$(/usr/libexec/PlistBuddy -c 'Print :CrAppModeShortcutURL' "$A/Contents/Info.plist" 2>/dev/null)" = "$3" ] && TARGET="$A"
  done
  [ -n "$TARGET" ] || { echo "건너뜀: Chrome 앱으로 설치된 $3 을 못 찾았어요 — Chrome에서 먼저 앱으로 설치하세요."; return 0; }
  BID="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$TARGET/Contents/Info.plist")"
  APP="$4/$1.app"; rm -rf "$APP"; mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
  cp "$4/AppIcon.icns" "$APP/Contents/Resources/AppIcon.icns"
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
R=\$(osascript -l JavaScript -e 'ObjC.import("AppKit"); var a=\$.NSRunningApplication.runningApplicationsWithBundleIdentifier("$BID"); if (Number(a.count) === 0) { "open" } else { var app=a.objectAtIndex(0); if (app.active) { app.hide; "hidden" } else { "open" } }')
# Chrome 앱 이름이 바뀌면(예: 작업관리 → WORKS) 앱 파일 이름도 바뀌므로 경로 대신 번들 id로 연다
[ "\$R" = "open" ] && { open -b "$BID" 2>/dev/null || open "$TARGET"; }
exit 0
SH
  chmod +x "$APP/Contents/MacOS/launcher"; codesign --force --deep -s - "$APP" >/dev/null 2>&1 || true
  echo "만들어졌어요: $APP → $TARGET"
}
make "작업관리 켜고끄기" "works" "https://www.vinfilmstudio.com/works/" "$DIR"
make "수입지출 켜고끄기" "ledger" "https://www.vinfilmstudio.com/ledger/" "$(cd "$DIR/../ledger-app" && pwd)"
