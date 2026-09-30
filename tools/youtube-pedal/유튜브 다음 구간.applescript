-- 유튜브 구간 이동 (Stream Deck용) — 숫자 키 1~9 = 영상의 10~90% 지점, 0 = 처음
-- 마지막으로 누른 숫자를 임시 폴더 파일에 기억해 두고 이어서 누른다(원래 단축어와 같은 방식)
set stateFile to (POSIX path of (path to temporary items)) & "youtube_pedal_state.txt"
try
	set currentNumber to (do shell script "cat " & quoted form of stateFile) as integer
on error
	set currentNumber to 0
end try
set currentNumber to currentNumber + 1
if currentNumber > 9 then set currentNumber to 1
do shell script "echo " & currentNumber & " > " & quoted form of stateFile
tell application "System Events"
	keystroke (currentNumber as string)
end tell
