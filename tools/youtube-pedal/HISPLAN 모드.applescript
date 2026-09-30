-- Stream Deck용: 단축어 앱의 "HISPLAN 모드" 단축어를 실행해 집중 모드를 바꾼다(단축어는 직접 만들어 둘 것)
try
	do shell script "shortcuts run " & quoted form of "HISPLAN 모드"
on error
	display notification "단축어 앱에 \"HISPLAN 모드\" 단축어가 있는지 확인해 주세요" with title "집중 모드 전환 실패"
end try
