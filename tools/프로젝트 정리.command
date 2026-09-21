#!/bin/bash
# 더블클릭용 실행 파일 — 폴더 선택 창 → 미리보기 → 확인 → 정리
DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$DIR/organize_project.py"

FOLDER=$(osascript -e 'POSIX path of (choose folder with prompt "정리할 프리미어 프로젝트 폴더를 선택하세요")' 2>/dev/null)
[ -z "$FOLDER" ] && exit 0

clear
python3 "$SCRIPT" "$FOLDER" --dry-run

MODE=$(osascript -e 'button returned of (display dialog "위 계획대로 정리할까요?\n\n이동: 파일을 옮김 (빠름, 나중에 되돌리기 가능)\n복사: 원본을 그대로 두고 복사" buttons {"취소", "복사", "이동"} default button "이동" cancel button "취소" with title "프로젝트 정리")' 2>/dev/null)

case "$MODE" in
  이동) python3 "$SCRIPT" "$FOLDER" --yes ;;
  복사) python3 "$SCRIPT" "$FOLDER" --yes --copy ;;
  *) echo "취소했어요." ;;
esac

echo
echo "창을 닫아도 됩니다."
