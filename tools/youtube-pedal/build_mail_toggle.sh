#!/bin/bash
# 스트림덱용 "네이버메일 … 켜고끄기" 앱: 누르면 그 크롬 프로필로 네이버 메일을 열고,
# 방금 이 버튼으로 연 메일이 크롬 맨 앞 탭에 떠 있을 때 다시 누르면 그 탭을 닫는다.
# (크롬은 창이 어느 프로필인지 알려주지 않아서, 마지막으로 누른 버튼을 임시 파일에 적어 구분한다)
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
make() { # 이름, 키, 크롬 프로필 폴더
  APP="$DIR/$1.app"; rm -rf "$APP"; mkdir -p "$APP/Contents/MacOS"
  cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>$1</string>
  <key>CFBundleIdentifier</key><string>com.vinfilmstudio.toggle.navermail.$2</string>
  <key>CFBundleExecutable</key><string>launcher</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSUIElement</key><true/>
  <key>NSAppleEventsUsageDescription</key><string>네이버 메일 탭이 열려 있는지 확인하고 닫기 위해 Chrome을 제어합니다.</string>
</dict></plist>
PLIST
  cat > "$APP/Contents/MacOS/launcher" <<SH
#!/bin/bash
STATE="\${TMPDIR:-/tmp}/vinfilm-navermail-last"
FRONT=\$(lsappinfo info -only bundleid "\$(lsappinfo front)" 2>/dev/null)
if [[ "\$FRONT" == *com.google.Chrome* ]] && [ "\$(cat "\$STATE" 2>/dev/null)" = "$2" ]; then
  URL=\$(osascript -e 'tell application "Google Chrome" to get URL of active tab of front window' 2>/dev/null)
  if [[ "\$URL" == *mail.naver.com* ]]; then
    osascript -e 'tell application "Google Chrome" to close active tab of front window' >/dev/null 2>&1
    rm -f "\$STATE"; exit 0
  fi
fi
echo "$2" > "\$STATE"
open -na "Google Chrome" --args --profile-directory="$3" "https://mail.naver.com"
SH
  chmod +x "$APP/Contents/MacOS/launcher"; codesign --force --deep -s - "$APP" >/dev/null 2>&1 || true
  echo "만들어졌어요: $APP"
}
make "네이버메일 김규빈 켜고끄기" "kyubin" "Default"
make "네이버메일 HISPLAN 켜고끄기" "hisplan" "Profile 1"
