#!/bin/bash
# 스트림덱용 켜고끄기 앱 2개를 만든다: "작업관리 켜고끄기.app"(여기), "수입지출 켜고끄기.app"(tools/ledger-app).
# 둘 다 Chrome 앱으로 설치한 "VINFILM 작업관리" 한 창을 쓴다(수입지출은 그 앱 안의 화면 — manifest scope가 사이트 전체).
#  - 누르면 그 화면으로 앱이 뜨고, 그 화면이 앞에 떠 있을 때 같은 버튼을 다시 누르면 숨긴다(종료가 아니라 숨김).
#  - 화면 전환은 Chrome에 "--app-id + 주소"로 실행을 넘기고, 페이지의 launchQueue 처리(works/ledger index.html)가 같은 창에서 이동한다.
#  - "지금 어느 화면인지"는 마지막으로 누른 버튼을 ~/.vinfilm-works-toggle 에 적어 두고 판단한다(앱 안 메뉴로 옮겨 다녔으면 한 번 더 눌러야 할 수 있음).
# 번들 id·앱 id는 Chrome이 설치 때 정한 값(주소가 같으면 다시 설치해도 그대로), 프로필은 Default.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
ID="kifhpkmeipjeilnbklflmfejdalnbgih"
BID="com.google.Chrome.app.$ID"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
make() { # 이름, 화면 키, 주소, 만들 폴더
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
STATE="\$HOME/.vinfilm-works-toggle"
LAST=\$(cat "\$STATE" 2>/dev/null)
R=\$(osascript -l JavaScript -e 'ObjC.import("AppKit"); var a=\$.NSRunningApplication.runningApplicationsWithBundleIdentifier("$BID"); if (Number(a.count) === 0) { "open" } else { var app=a.objectAtIndex(0); if (app.active && "'"\$LAST"'" === "$2") { app.hide; "hidden" } else { "open" } }')
if [ "\$R" = "open" ]; then
  echo "$2" > "\$STATE"
  "$CHROME" --profile-directory=Default --app-id=$ID "--app-launch-url-for-shortcuts-menu-item=$3" >/dev/null 2>&1 &
fi
exit 0
SH
  chmod +x "$APP/Contents/MacOS/launcher"; codesign --force --deep -s - "$APP" >/dev/null 2>&1 || true
  echo "만들어졌어요: $APP"
}
make "작업관리 켜고끄기" "works" "https://www.vinfilmstudio.com/works/" "$DIR"
make "수입지출 켜고끄기" "ledger" "https://www.vinfilmstudio.com/ledger/" "$DIR/../ledger-app"
