#!/usr/bin/env python3
"""VINFILM 리모트 — 아이폰을 맥의 트랙패드·키보드로 쓰는 작은 서버 (VINFILM STUDIO)

맥에서 실행하면 같은 와이파이의 아이폰이 http://{맥이름}.local:8765/?k={코드} 로 접속해
손가락으로 마우스를 움직이고(탭=클릭, 두 손가락=스크롤/오른쪽 클릭) 글자를 입력한다.
- 표준 라이브러리만 쓴다(웹소켓도 직접 구현). 입력은 ctypes로 CoreGraphics CGEvent를 보낸다.
- 아무나 조종하지 못하게 처음 실행할 때 비밀 코드를 만들어 두고(~/Library/Application Support/VINFILM Remote),
  웹소켓 첫 메시지로 그 코드를 확인한다. 맥 화면(127.0.0.1:8765/mac)의 QR에 코드가 들어 있다.
- 맥에서 입력을 보내려면 "손쉬운 사용" 권한이 필요하다(처음 실행 때 시스템이 물어봄).
- 맥이 아닌 곳(개발용)에서는 실제 입력 대신 로그만 찍는 가짜 입력으로 돈다.
"""
import base64
import hashlib
import json
import os
import secrets
import socket
import struct
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

IS_MAC = sys.platform == "darwin"
DEFAULT_PORT = 8765  # 다른 프로그램(Anki 등)이 쓰고 있으면 8766, 8767… 중 빈 번호를 찾아 config에 기억한다
HERE = Path(__file__).resolve().parent
WEB = HERE / "web"
SUPPORT = (Path.home() / "Library" / "Application Support" / "VINFILM Remote") if IS_MAC else (Path.home() / ".vinfilm-remote")
CONFIG = SUPPORT / "config.json"
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


# ───────────────────────── 설정(비밀 코드) ─────────────────────────

def load_config():
    try:
        cfg = json.loads(CONFIG.read_text())
        if isinstance(cfg.get("token"), str) and len(cfg["token"]) >= 16:
            return cfg
    except Exception:
        pass
    return new_token({})


def new_token(cfg):
    cfg["token"] = secrets.token_urlsafe(12)
    return save_config(cfg)


def save_config(cfg):
    SUPPORT.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg))
    try:
        os.chmod(CONFIG, 0o600)
    except Exception:
        pass
    return cfg


cfg = load_config()
PORT = int(os.environ.get("VF_REMOTE_PORT") or cfg.get("port") or DEFAULT_PORT)


# ───────────────────────── 맥 정보 ─────────────────────────

def run_out(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=3).stdout.strip()
    except Exception:
        return ""


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))  # 실제로 보내지 않음 — 어느 네트워크 카드로 나가는지만 확인
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def mac_names():
    local = run_out(["scutil", "--get", "LocalHostName"]) if IS_MAC else ""
    pretty = run_out(["scutil", "--get", "ComputerName"]) if IS_MAC else ""
    host = socket.gethostname().split(".")[0]
    return (local or host), (pretty or local or host)


# ───────────────────────── 입력 보내기 ─────────────────────────

# 미국 배열 기준 가상 키코드 — 단축키(⌘C 등)는 글자가 아니라 키코드로 보내야 앱이 알아듣는다
KEYCODES = {
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9, "b": 11, "q": 12,
    "w": 13, "e": 14, "r": 15, "y": 16, "t": 17, "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23,
    "=": 24, "9": 25, "7": 26, "-": 27, "8": 28, "0": 29, "]": 30, "o": 31, "u": 32, "[": 33, "i": 34,
    "p": 35, "l": 37, "j": 38, "'": 39, "k": 40, ";": 41, "\\": 42, ",": 43, "/": 44, "n": 45, "m": 46,
    ".": 47, "`": 50,
    "enter": 36, "tab": 48, "space": 49, "backspace": 51, "esc": 53, "delete": 117,
    "left": 123, "right": 124, "down": 125, "up": 126,
    "home": 115, "end": 119, "pageup": 116, "pagedown": 121,
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97, "f7": 98, "f8": 100,
    "f9": 101, "f10": 109, "f11": 103, "f12": 111,
}
SHIFTED = {'!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
           '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\', ':': ';', '"': "'", '<': ',', '>': '.', '?': '/', '~': '`'}
FLAGS = {"shift": 0x20000, "ctrl": 0x40000, "alt": 0x80000, "cmd": 0x100000}
ARROW_FLAGS = 0x800000 | 0x200000  # Fn + 숫자패드 — 실제 키보드 화살표와 같게(⌃↑ 미션 컨트롤 등)
MEDIA = {"play": 16, "next": 17, "prev": 18, "volup": 0, "voldown": 1, "mute": 7}


def resolve_key(name, mods):
    """'c' / 'C' / '?' / 'enter' → (키코드, 플래그)"""
    flags = 0
    for m in mods or []:
        flags |= FLAGS.get(m, 0)
    k = name if len(name) == 1 else name.lower()
    if len(k) == 1:
        if k in SHIFTED:
            k = SHIFTED[k]
            flags |= FLAGS["shift"]
        elif k.isalpha() and k.isupper():
            k = k.lower()
            flags |= FLAGS["shift"]
    code = KEYCODES.get(k)
    if code is None:
        return None, 0
    if k in ("left", "right", "up", "down"):
        flags |= ARROW_FLAGS
    return code, flags


class FakeInput:
    """맥이 아닐 때(개발용) — 받은 동작을 로그로만 남긴다"""
    def __init__(self):
        self.log = []

    def _note(self, *a):
        self.log.append(a)
        del self.log[:-200]
        if os.environ.get("VF_REMOTE_DEBUG"):
            print("input:", *a, flush=True)

    def access(self):
        return True

    def request_access(self):
        return True

    def move(self, dx, dy):
        self._note("move", dx, dy)

    def button(self, btn, down, clicks=None):
        self._note("button", btn, down, clicks)

    def scroll(self, dx, dy):
        self._note("scroll", dx, dy)

    def key(self, name, mods):
        self._note("key", name, mods)

    def text(self, s):
        self._note("text", s)

    def media(self, name):
        self._note("media", name)

    def release_all(self):
        self._note("release")


class MacInput:
    def __init__(self):
        import ctypes
        from ctypes import c_void_p, c_uint32, c_int32, c_int64, c_uint64, c_uint16, c_bool, c_double, c_ulong, c_long, c_short, POINTER
        self.ct = ctypes

        class CGPoint(ctypes.Structure):
            _fields_ = [("x", c_double), ("y", c_double)]

        class CGSize(ctypes.Structure):
            _fields_ = [("width", c_double), ("height", c_double)]

        class CGRect(ctypes.Structure):
            _fields_ = [("origin", CGPoint), ("size", CGSize)]

        self.CGPoint = CGPoint
        cg = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        cf = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")

        def fn(lib, name, res, args):
            f = getattr(lib, name)
            f.restype = res
            f.argtypes = args
            return f

        self.CGEventCreate = fn(cg, "CGEventCreate", c_void_p, [c_void_p])
        self.CGEventGetLocation = fn(cg, "CGEventGetLocation", CGPoint, [c_void_p])
        self.CGEventCreateMouseEvent = fn(cg, "CGEventCreateMouseEvent", c_void_p, [c_void_p, c_uint32, CGPoint, c_uint32])
        self.CGEventCreateKeyboardEvent = fn(cg, "CGEventCreateKeyboardEvent", c_void_p, [c_void_p, c_uint16, c_bool])
        # 가변 인자 버전(CGEventCreateScrollWheelEvent)은 Apple Silicon에서 ctypes로 부르면 깨져서 고정 인자 버전을 쓴다
        self.CGEventCreateScrollWheelEvent2 = fn(cg, "CGEventCreateScrollWheelEvent2", c_void_p, [c_void_p, c_uint32, c_uint32, c_int32, c_int32, c_int32])
        self.CGEventKeyboardSetUnicodeString = fn(cg, "CGEventKeyboardSetUnicodeString", None, [c_void_p, c_ulong, POINTER(c_uint16)])
        self.CGEventSetFlags = fn(cg, "CGEventSetFlags", None, [c_void_p, c_uint64])
        self.CGEventSetIntegerValueField = fn(cg, "CGEventSetIntegerValueField", None, [c_void_p, c_uint32, c_int64])
        self.CGEventPost = fn(cg, "CGEventPost", None, [c_uint32, c_void_p])
        self.CGGetActiveDisplayList = fn(cg, "CGGetActiveDisplayList", c_int32, [c_uint32, POINTER(c_uint32), POINTER(c_uint32)])
        self.CGDisplayBounds = fn(cg, "CGDisplayBounds", CGRect, [c_uint32])
        self.CFRelease = fn(cf, "CFRelease", None, [c_void_p])
        try:
            self.CGPreflightPostEventAccess = fn(cg, "CGPreflightPostEventAccess", c_bool, [])
            self.CGRequestPostEventAccess = fn(cg, "CGRequestPostEventAccess", c_bool, [])
        except AttributeError:  # macOS 10.14 이하
            self.CGPreflightPostEventAccess = self.CGRequestPostEventAccess = lambda: True

        self.down = {"l": False, "r": False}
        self.cur = None  # 소수점까지 기억하는 커서 위치 — 매번 정수 위치를 다시 읽으면 천천히 움직일 때 계단처럼 끊긴다
        self.last_click = (0.0, None, 0, (0.0, 0.0))  # 시각, 버튼, 연속 횟수, 위치 — 더블클릭 판단용
        self.disp_cache = (0.0, [])
        self.lock = threading.Lock()

        # 재생/볼륨 같은 미디어 키는 NSEvent(시스템 정의 이벤트)로만 만들 수 있어 Objective-C 런타임을 직접 부른다
        self.media_ok = False
        try:
            objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
            ctypes.cdll.LoadLibrary("/System/Library/Frameworks/AppKit.framework/AppKit")
            fn(objc, "objc_getClass", c_void_p, [ctypes.c_char_p])
            fn(objc, "sel_registerName", c_void_p, [ctypes.c_char_p])
            fn(objc, "objc_autoreleasePoolPush", c_void_p, [])
            fn(objc, "objc_autoreleasePoolPop", None, [c_void_p])
            addr = ctypes.cast(objc.objc_msgSend, c_void_p).value
            self._msg_event = ctypes.CFUNCTYPE(c_void_p, c_void_p, c_void_p, c_ulong, CGPoint, c_ulong, c_double, c_long, c_void_p, c_short, c_long, c_long)(addr)
            self._msg_obj = ctypes.CFUNCTYPE(c_void_p, c_void_p, c_void_p)(addr)
            self._NSEvent = objc.objc_getClass(b"NSEvent")
            self._sel_other = objc.sel_registerName(b"otherEventWithType:location:modifierFlags:timestamp:windowNumber:context:subtype:data1:data2:")
            self._sel_cg = objc.sel_registerName(b"CGEvent")
            self._objc = objc
            self.media_ok = bool(self._NSEvent)
        except Exception as e:
            print("미디어 키 준비 실패(재생은 스페이스로 대신):", e, flush=True)

    # 권한
    def access(self):
        return bool(self.CGPreflightPostEventAccess())

    def request_access(self):
        return bool(self.CGRequestPostEventAccess())

    # 내부 도우미
    def _post(self, ev):
        if ev:
            self.CGEventPost(0, ev)  # kCGHIDEventTap
            self.CFRelease(ev)

    def _pos(self):
        ev = self.CGEventCreate(None)
        p = self.CGEventGetLocation(ev)
        self.CFRelease(ev)
        return p.x, p.y

    def _displays(self):
        t, rects = self.disp_cache
        if time.time() - t < 3 and rects:
            return rects
        arr = (self.ct.c_uint32 * 16)()
        n = self.ct.c_uint32(0)
        self.CGGetActiveDisplayList(16, arr, self.ct.byref(n))
        rects = []
        for i in range(n.value):
            r = self.CGDisplayBounds(arr[i])
            rects.append((r.origin.x, r.origin.y, r.size.width, r.size.height))
        self.disp_cache = (time.time(), rects)
        return rects

    def _clamp(self, x, y):
        rects = self._displays()
        if not rects:
            return x, y
        best = None
        for rx, ry, rw, rh in rects:
            if rx <= x < rx + rw and ry <= y < ry + rh:
                return x, y
            cx = min(max(x, rx), rx + rw - 1)
            cy = min(max(y, ry), ry + rh - 1)
            d = (cx - x) ** 2 + (cy - y) ** 2
            if best is None or d < best[0]:
                best = (d, cx, cy)
        return best[1], best[2]

    # 동작
    def move(self, dx, dy):
        with self.lock:
            rx, ry = self._pos()
            cx, cy = self.cur or (rx, ry)
            if abs(rx - cx) > 2 or abs(ry - cy) > 2:  # 실제 마우스·트랙패드로 움직였으면 거기서부터
                cx, cy = rx, ry
            x, y = self._clamp(cx + dx, cy + dy)
            self.cur = (x, y)
            if self.down["l"]:
                t, b = 6, 0   # kCGEventLeftMouseDragged
            elif self.down["r"]:
                t, b = 7, 1   # kCGEventRightMouseDragged
            else:
                t, b = 5, 0   # kCGEventMouseMoved
            self._post(self.CGEventCreateMouseEvent(None, t, self.CGPoint(x, y), b))

    def button(self, btn, down, clicks=None):
        with self.lock:
            if btn not in self.down or self.down[btn] == down:
                return
            x, y = self._pos()
            if down:
                t0, b0, n0, (px, py) = self.last_click
                now = time.time()
                if clicks is None:
                    near = abs(px - x) < 8 and abs(py - y) < 8
                    clicks = n0 + 1 if (b0 == btn and now - t0 < 0.4 and near) else 1
                self.last_click = (now, btn, clicks, (x, y))
            else:
                clicks = self.last_click[2] if self.last_click[1] == btn else 1
            self.down[btn] = down
            t = {("l", True): 1, ("l", False): 2, ("r", True): 3, ("r", False): 4}[(btn, down)]
            ev = self.CGEventCreateMouseEvent(None, t, self.CGPoint(x, y), 0 if btn == "l" else 1)
            self.CGEventSetIntegerValueField(ev, 1, clicks)  # kCGMouseEventClickState
            self._post(ev)

    def scroll(self, dx, dy):
        with self.lock:
            self._post(self.CGEventCreateScrollWheelEvent2(None, 0, 2, int(dy), int(dx), 0))  # 픽셀 단위

    def key(self, name, mods):
        code, flags = resolve_key(name, mods)
        if code is None:
            return
        with self.lock:
            for down in (True, False):
                ev = self.CGEventCreateKeyboardEvent(None, code, down)
                self.CGEventSetFlags(ev, flags)
                self._post(ev)

    def text(self, s):
        with self.lock:
            for ch in s:
                if ch in "\r\n":
                    code, flags = 36, 0
                    for down in (True, False):
                        ev = self.CGEventCreateKeyboardEvent(None, code, down)
                        self.CGEventSetFlags(ev, flags)
                        self._post(ev)
                    continue
                units = ch.encode("utf-16-le")
                n = len(units) // 2
                buf = (self.ct.c_uint16 * n).from_buffer_copy(units)
                for down in (True, False):
                    ev = self.CGEventCreateKeyboardEvent(None, 0, down)
                    self.CGEventSetFlags(ev, 0)
                    self.CGEventKeyboardSetUnicodeString(ev, n, buf)
                    self._post(ev)
                time.sleep(0.002)

    def media(self, name):
        key = MEDIA.get(name)
        if key is None:
            return
        if not self.media_ok:
            if name == "play":
                self.key("space", [])
            else:
                volume_fallback(name)
            return
        with self.lock:
            pool = self._objc.objc_autoreleasePoolPush()
            try:
                for down in (True, False):
                    flags = 0xA00 if down else 0xB00
                    data1 = (key << 16) | ((0xA if down else 0xB) << 8)
                    ns = self._msg_event(self._NSEvent, self._sel_other, 14, self.CGPoint(0, 0), flags, 0.0, 0, None, 8, data1, -1)
                    cg = self._msg_obj(ns, self._sel_cg) if ns else None
                    if cg:
                        self.CGEventPost(0, cg)  # NSEvent가 가진 것이라 CFRelease 하지 않음
            finally:
                self._objc.objc_autoreleasePoolPop(pool)

    def release_all(self):
        for b in ("l", "r"):
            if self.down.get(b):
                self.button(b, False)


def volume_fallback(name):
    script = {
        "volup": "set volume output volume ((output volume of (get volume settings)) + 6)",
        "voldown": "set volume output volume ((output volume of (get volume settings)) - 6)",
        "mute": "set volume output muted (not (output muted of (get volume settings)))",
    }.get(name)
    if script and IS_MAC:
        subprocess.Popen(["osascript", "-e", script])


try:
    INPUT = MacInput() if IS_MAC else FakeInput()
except Exception as e:  # ctypes 준비 실패 — 화면은 띄우고 원인을 보여준다
    print("입력 준비 실패:", e, flush=True)
    INPUT = FakeInput()
    INPUT_ERROR = str(e)
else:
    INPUT_ERROR = ""


# ───────────────────────── 부드럽게 ─────────────────────────

class Glide:
    """와이파이는 아이폰 신호를 고르게 보내지 않는다 — 몰려 오기도 하고 가끔 늦게 오기도 한다.
    그래서 받은 움직임을 바로 쓰지 않고 '아이폰에서 손가락이 움직인 시각 + 버퍼(기본 50ms)'에 맞춰
    다시 재생한다(영상 스트리밍의 버퍼와 같은 원리). 버퍼보다 덜 늦게 온 신호는 끊김 없이 이어진다.
    시각(ts)이 없는 옛 화면에서 온 신호는 바로 짧게 흘려보낸다."""
    TICK = 0.004

    def __init__(self):
        self.buf = 0.05            # 초 — 아이폰 설정의 '부드러움'으로 바뀜
        self.segs = []             # [시작, 끝, dx, dy, 종류('m'|'s'), 이미 보낸 비율]
        self.hist = []             # (받은 시각, 받은 시각 − 아이폰 시각) — 최근 3초 중 최솟값이 두 시계의 차이
        self.last_ts = {"m": None, "s": None}
        self.rx = self.ry = 0.0    # 스크롤은 정수(픽셀)로만 보낼 수 있어 남은 소수점
        self.lock = threading.Lock()
        self.wake = threading.Event()
        threading.Thread(target=self._run, daemon=True).start()

    def set_buffer(self, ms):
        self.buf = max(0.0, min(0.2, ms / 1000.0))

    def add(self, kind, dx, dy, ts=None):
        now = time.monotonic()
        with self.lock:
            if not isinstance(ts, (int, float)) or ts != ts:
                start, end = now, now + 0.012
            else:
                t = ts / 1000.0
                self.hist.append((now, now - t))
                while self.hist and now - self.hist[0][0] > 3:
                    self.hist.pop(0)
                if len(self.hist) > 400:
                    del self.hist[:200]
                off = min(h[1] for h in self.hist)  # 가장 빨리 도착한 신호 기준
                end = t + off + self.buf
                prev = self.last_ts[kind]
                span = (ts - prev) / 1000.0 if prev is not None and 0 < ts - prev < 100 else 0.016
                start = end - min(max(span, 0.004), 0.05)
                self.last_ts[kind] = ts
                if end <= now:  # 버퍼보다 더 늦게 옴 — 밀린 만큼 짧게 따라잡는다
                    start, end = now, now + 0.012
            self.segs.append([start, end, dx, dy, kind, 0.0])
            self.wake.set()

    def flush(self):
        """클릭 직전에 — 아직 안 보낸 움직임을 다 보내서 클릭이 커서가 도착할 자리에서 일어나게"""
        mx = my = 0.0
        with self.lock:
            keep = []
            for sg in self.segs:
                if sg[4] == "m":
                    rest = 1.0 - sg[5]
                    mx += sg[2] * rest
                    my += sg[3] * rest
                else:
                    keep.append(sg)
            self.segs = keep
        if mx or my:
            INPUT.move(mx, my)

    def _run(self):
        while True:
            self.wake.wait()
            with self.lock:
                if not self.segs:
                    self.wake.clear()
                    continue
                now = time.monotonic()
                mx = my = sx = sy = 0.0
                keep = []
                for sg in self.segs:
                    st, en = sg[0], sg[1]
                    if now <= st:
                        keep.append(sg)
                        continue
                    f = 1.0 if now >= en else (now - st) / (en - st)
                    part = f - sg[5]
                    sg[5] = f
                    if sg[4] == "m":
                        mx += sg[2] * part
                        my += sg[3] * part
                    else:
                        sx += sg[2] * part
                        sy += sg[3] * part
                    if f < 1.0:
                        keep.append(sg)
                self.segs = keep
                self.rx += sx
                self.ry += sy
                ix, iy = int(self.rx), int(self.ry)
                self.rx -= ix
                self.ry -= iy
            try:
                if mx or my:
                    INPUT.move(mx, my)
                if ix or iy:
                    INPUT.scroll(ix, iy)
            except Exception:
                stats["err"] = traceback.format_exc(limit=3)[-600:]
            time.sleep(self.TICK)


# ───────────────────────── App Nap 막기 ─────────────────────────
# 리모트는 Dock에 안 보이는 앱이라 macOS가 '안 쓰는 앱'으로 보고 타이머를 느리게 돌린다(App Nap) → 커서가 가끔 끊김.
# 아이폰이 연결된 동안만 NSProcessInfo에 "지연에 민감한 작업 중"이라고 알려 막는다.

class LatencyActivity:
    def __init__(self):
        self.token = None
        self.ok = False
        if not IS_MAC:
            return
        try:
            import ctypes
            from ctypes import c_void_p, c_char_p, c_uint64
            objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
            ctypes.cdll.LoadLibrary("/System/Library/Frameworks/Foundation.framework/Foundation")
            objc.objc_getClass.restype = c_void_p
            objc.objc_getClass.argtypes = [c_char_p]
            objc.sel_registerName.restype = c_void_p
            objc.sel_registerName.argtypes = [c_char_p]
            addr = ctypes.cast(objc.objc_msgSend, c_void_p).value
            self._send0 = ctypes.CFUNCTYPE(c_void_p, c_void_p, c_void_p)(addr)
            self._send_str = ctypes.CFUNCTYPE(c_void_p, c_void_p, c_void_p, c_char_p)(addr)
            self._send_begin = ctypes.CFUNCTYPE(c_void_p, c_void_p, c_void_p, c_uint64, c_void_p)(addr)
            self._send_obj = ctypes.CFUNCTYPE(None, c_void_p, c_void_p, c_void_p)(addr)
            sel = objc.sel_registerName
            self._pi = self._send0(objc.objc_getClass(b"NSProcessInfo"), sel(b"processInfo"))
            self._reason = self._send0(self._send_str(objc.objc_getClass(b"NSString"), sel(b"stringWithUTF8String:"), "아이폰 리모트 입력".encode()), sel(b"retain"))
            self._sel_begin = sel(b"beginActivityWithOptions:reason:")
            self._sel_end = sel(b"endActivity:")
            self._sel_retain = sel(b"retain")
            self._sel_release = sel(b"release")
            self.ok = bool(self._pi)
        except Exception as e:
            print("App Nap 막기 준비 실패:", e, flush=True)

    def set(self, on):
        if not self.ok:
            return
        with clients_lock:
            self._set(on)

    def _set(self, on):
        try:
            if on and self.token is None:
                opts = 0x00FFFFFF | 0xFF00000000  # NSActivityUserInitiated | NSActivityLatencyCritical
                tok = self._send_begin(self._pi, self._sel_begin, opts, self._reason)
                self.token = self._send0(tok, self._sel_retain) if tok else None
            elif not on and self.token is not None:
                self._send_obj(self._pi, self._sel_end, self.token)
                self._send0(self.token, self._sel_release)
                self.token = None
        except Exception as e:
            print("App Nap 설정 실패:", e, flush=True)


ACTIVITY = LatencyActivity()


# ───────────────────────── 잠자기 방지 ─────────────────────────
# 아이폰이 연결돼 있는 동안만 caffeinate로 맥이 잠들지 않게(잠들면 와이파이가 끊겨 다시 깨울 수 없음)

clients = {}  # id → {"name", "since"}
clients_lock = threading.Lock()
caff = {"proc": None}


def update_caffeinate():
    if not IS_MAC:
        return
    with clients_lock:
        want = bool(clients)
    ACTIVITY.set(want)
    p = caff["proc"]
    if want and (p is None or p.poll() is not None):
        caff["proc"] = subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())])
    elif not want and p is not None:
        p.terminate()
        caff["proc"] = None


# ───────────────────────── 메시지 처리 ─────────────────────────

def num(v, lim=4000.0):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    if f != f:  # NaN
        return 0.0
    return max(-lim, min(lim, f))


stats = {"msgs": 0, "at": 0, "err": ""}  # 맥 화면에 보여줄 진단 정보 — 아이폰 입력이 맥까지 오는지, 오다가 어디서 실패하는지


GLIDE = None  # 서버가 뜰 때 만든다(아래 main)


def handle_msg(m):
    stats["msgs"] += 1
    stats["at"] = int(time.time() * 1000)
    t = m.get("t")
    if t == "m":
        GLIDE.add("m", num(m.get("x")), num(m.get("y")), m.get("ts"))
        return
    if t == "s":
        GLIDE.add("s", num(m.get("x"), 2000), num(m.get("y"), 2000), m.get("ts"))
        return
    if t == "cfg":
        GLIDE.set_buffer(num(m.get("buf"), 200))
        return
    GLIDE.flush()
    if t == "b":
        b = m.get("b")
        if b in ("l", "r"):
            n = m.get("n")
            INPUT.button(b, bool(m.get("d")), int(n) if isinstance(n, int) and 1 <= n <= 3 else None)
    elif t == "c":  # 클릭 한 번(누르고 떼기)
        b = m.get("b") if m.get("b") in ("l", "r") else "l"
        INPUT.button(b, True)
        INPUT.button(b, False)
    elif t == "k":
        name = m.get("c")
        mods = [x for x in (m.get("m") or []) if x in FLAGS]
        if isinstance(name, str) and 0 < len(name) <= 12:
            INPUT.key(name, mods)
    elif t == "txt":
        s = m.get("s")
        n = m.get("bs")
        if isinstance(n, int) and 0 < n <= 200:
            for _ in range(n):
                INPUT.key("backspace", [])
        if isinstance(s, str) and s:
            INPUT.text(s[:2000])
    elif t == "media":
        INPUT.media(m.get("k"))


# ───────────────────────── 웹소켓 (RFC 6455, 필요한 만큼만) ─────────────────────────

def ws_recv(rfile):
    """(opcode, payload) — 연결이 끊기면 None"""
    head = rfile.read(2)
    if len(head) < 2:
        return None
    b1, b2 = head
    op = b1 & 0x0F
    ln = b2 & 0x7F
    if ln == 126:
        ln = struct.unpack(">H", rfile.read(2))[0]
    elif ln == 127:
        ln = struct.unpack(">Q", rfile.read(8))[0]
    if ln > 1 << 20:
        return None
    mask = rfile.read(4) if b2 & 0x80 else None
    data = rfile.read(ln)
    if len(data) < ln:
        return None
    if mask:
        data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    return op, data


def ws_send(wfile, text, op=0x1):
    data = text.encode() if isinstance(text, str) else text
    ln = len(data)
    if ln < 126:
        head = struct.pack(">BB", 0x80 | op, ln)
    elif ln < 1 << 16:
        head = struct.pack(">BBH", 0x80 | op, 126, ln)
    else:
        head = struct.pack(">BBQ", 0x80 | op, 127, ln)
    wfile.write(head + data)
    wfile.flush()


# ───────────────────────── HTTP ─────────────────────────

state = {"server": None, "started": time.time()}


def info():
    local, pretty = mac_names()
    ip = lan_ip()
    tok = cfg["token"]
    with clients_lock:
        cl = [{"name": c["name"], "since": c["since"]} for c in clients.values()]
    return {
        "name": pretty,
        "url": "http://%s.local:%d/?k=%s" % (local, PORT, tok),
        "ipUrl": "http://%s:%d/?k=%s" % (ip, PORT, tok),
        "clients": cl,
        "access": INPUT.access(),
        "error": INPUT_ERROR,
        "input": type(INPUT).__name__,
        "msgs": stats["msgs"],
        "msgAt": stats["at"],
        "msgErr": stats["err"],
        "python": sys.executable,
        "isMac": IS_MAC,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "VinfilmRemote/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):  # 주소에 비밀 코드가 있어 요청 로그를 남기지 않는다
        pass

    def _loopback(self):
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]")
        return self.client_address[0] in ("127.0.0.1", "::1") and host in ("127.0.0.1", "localhost", "::1")

    def _send(self, code, body, ctype="text/plain; charset=utf-8", extra=None):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _file(self, name, ctype):
        try:
            self._send(200, (WEB / name).read_bytes(), ctype)
        except FileNotFoundError:
            self._send(404, "없음")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/ws":
            return self._ws()
        if path in ("/", "/index.html"):
            return self._file("remote.html", "text/html; charset=utf-8")
        if path == "/icon-180.png":
            return self._file("icon-180.png", "image/png")
        if path == "/ping":
            return self._send(200, "vinfilm-remote")
        # 맥 전용 화면 — 이 맥 안에서만(127.0.0.1)
        if path in ("/mac", "/qrcode.js", "/api/status"):
            if not self._loopback():
                return self._send(403, "이 화면은 맥에서만 열 수 있어요")
            if path == "/mac":
                return self._file("mac.html", "text/html; charset=utf-8")
            if path == "/qrcode.js":
                return self._file("qrcode.js", "text/javascript; charset=utf-8")
            return self._send(200, json.dumps(info()), "application/json")
        self._send(404, "없음")

    do_HEAD = do_GET

    def do_POST(self):
        path = urlparse(self.path).path
        origin = self.headers.get("Origin")
        if not self._loopback() or (origin and urlparse(origin).hostname not in ("127.0.0.1", "localhost")):
            return self._send(403, "이 맥에서만 쓸 수 있어요")
        ln = int(self.headers.get("Content-Length") or 0)
        if ln:
            self.rfile.read(min(ln, 4096))
        if path == "/api/request-access":
            INPUT.request_access()
            if IS_MAC:
                subprocess.Popen(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"])
            return self._send(200, json.dumps(info()), "application/json")
        if path == "/api/test-move":  # 아이폰 없이 이 맥에서 마우스가 움직이는지 — 네모를 한 바퀴 그린다
            try:
                for dx, dy in ((80, 0), (0, 80), (-80, 0), (0, -80)):
                    for _ in range(10):
                        INPUT.move(dx / 10, dy / 10)
                        time.sleep(0.015)
                if stats["err"].startswith("시험"):
                    stats["err"] = ""
            except Exception:
                stats["err"] = "시험 실패\n" + traceback.format_exc(limit=3)[-600:]
            return self._send(200, json.dumps(info()), "application/json")
        if path == "/api/new-token":
            new_token(cfg)
            return self._send(200, json.dumps(info()), "application/json")
        if path == "/api/quit":
            self._send(200, "{}", "application/json")
            threading.Thread(target=shutdown, daemon=True).start()
            return
        self._send(404, "없음")

    def _ws(self):
        key = self.headers.get("Sec-WebSocket-Key")
        if (self.headers.get("Upgrade") or "").lower() != "websocket" or not key:
            return self._send(400, "웹소켓 전용")
        # 다른 사이트가 이 맥을 조종하지 못하게: Origin은 이 서버 자신이어야 한다
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).netloc != (self.headers.get("Host") or ""):
            return self._send(403, "허용되지 않은 출처")
        accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()
        self.send_response(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
        self.close_connection = True
        cid = None
        try:
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.connection.settimeout(60)  # 폰은 20초마다 ping을 보낸다
            first = ws_recv(self.rfile)
            try:
                hello = json.loads(first[1].decode()) if first and first[0] == 0x1 else {}
            except Exception:
                hello = {}
            tok = hello.get("k") if isinstance(hello.get("k"), str) else ""
            if hello.get("t") != "auth" or not secrets.compare_digest(tok.encode(), cfg["token"].encode()):
                time.sleep(0.5)  # 코드 맞히기 시도를 느리게
                ws_send(self.wfile, json.dumps({"t": "denied"}))
                ws_send(self.wfile, b"\x03\xe8", 0x8)
                return
            cid = secrets.token_hex(4)
            dev = hello.get("dev") if isinstance(hello.get("dev"), str) else "아이폰"
            with clients_lock:
                clients[cid] = {"name": dev[:40], "since": int(time.time() * 1000)}
            update_caffeinate()
            ws_send(self.wfile, json.dumps({"t": "hello", "name": mac_names()[1], "access": INPUT.access()}))
            while True:
                fr = ws_recv(self.rfile)
                if fr is None:
                    break
                op, data = fr
                if op == 0x8:
                    break
                if op == 0x9:
                    ws_send(self.wfile, data, 0xA)
                    continue
                if op != 0x1:
                    continue
                try:
                    msg = json.loads(data.decode())
                except Exception:
                    continue
                if msg.get("t") == "ping":
                    ws_send(self.wfile, json.dumps({"t": "pong", "access": INPUT.access()}))
                    continue
                try:
                    handle_msg(msg)
                except Exception:
                    stats["err"] = traceback.format_exc(limit=3)[-600:]
                    print("처리 실패:", stats["err"], flush=True)
        except (OSError, ValueError):
            pass
        finally:
            if cid:
                with clients_lock:
                    clients.pop(cid, None)
                    left = bool(clients)
                if not left:
                    INPUT.release_all()  # 끌던 중에 끊기면 버튼이 눌린 채로 남지 않게
                update_caffeinate()


def shutdown():
    time.sleep(0.2)
    p = caff["proc"]
    if p is not None:
        p.terminate()
    if state["server"]:
        state["server"].shutdown()


def open_mac_page():
    url = "http://127.0.0.1:%d/mac" % PORT
    if not IS_MAC:
        print("맥 화면:", url, flush=True)
        return
    for b in ("/Applications/Google Chrome.app", "/Applications/Microsoft Edge.app", "/Applications/Brave Browser.app"):
        if os.path.isdir(b):
            subprocess.Popen(["open", "-na", b, "--args", "--app=" + url, "--window-size=460,720"])
            return
    subprocess.Popen(["open", url])


def already_running(port):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 시스템 프록시를 타지 않게
    try:
        with opener.open("http://127.0.0.1:%d/ping" % port, timeout=1.5) as r:
            return r.read() == b"vinfilm-remote"
    except Exception:
        return False


def port_busy(port):
    try:
        socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
        return True
    except OSError:
        return False


def self_test():
    """python3 remote_server.py --test — 터미널에서 원인을 한눈에 보는 자가진단"""
    print("── VINFILM 리모트 자가진단 ──")
    print("파이썬:", sys.executable, sys.version.split()[0])
    print("macOS:", run_out(["sw_vers", "-productVersion"]) if IS_MAC else "(맥 아님)")
    print("입력 방식:", type(INPUT).__name__, ("· 준비 실패: " + INPUT_ERROR) if INPUT_ERROR else "")
    print("손쉬운 사용 권한:", "허용됨" if INPUT.access() else "없음 ← 이 프로그램(터미널/앱)에 권한이 없어요")
    try:
        if isinstance(INPUT, MacInput):
            before = INPUT._pos()
            INPUT.move(150, 0)
            time.sleep(0.3)
            after = INPUT._pos()
            INPUT.move(-150, 0)
            print("마우스 위치: %s → %s" % (tuple(round(v) for v in before), tuple(round(v) for v in after)))
            print("결과:", "마우스가 움직였어요 ✓" if abs(after[0] - before[0]) > 50 else "마우스가 안 움직였어요 ✗ (권한이 막고 있을 가능성이 커요)")
    except Exception:
        traceback.print_exc()
    print("이미 켜진 리모트:", "있음(포트 %d)" % PORT if already_running(PORT) else "없음")


def main():
    global PORT, GLIDE
    if "--test" in sys.argv:
        return self_test()
    open_page = "--no-open" not in sys.argv
    ThreadingHTTPServer.daemon_threads = True
    ThreadingHTTPServer.allow_reuse_address = True
    # 기억해 둔 번호부터 시도 — 이미 이 리모트가 켜져 있으면 맥 화면만 다시 열고, 다른 프로그램이 쓰고 있으면 다음 번호로
    candidates = [PORT] + [p for p in range(DEFAULT_PORT, DEFAULT_PORT + 20) if p != PORT]
    srv, err = None, None
    for port in candidates:
        if already_running(port):
            PORT = port
            if open_page:
                open_mac_page()
            return
        if port_busy(port):  # 다른 프로그램이 127.0.0.1에서만 듣고 있으면 bind가 성공해 버릴 수 있어 먼저 확인
            continue
        try:
            srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
        except OSError as e:
            err = e
            continue
        PORT = port
        break
    if srv is None:
        msg = "리모트를 켤 빈 포트를 찾지 못했어요: %s" % err
        print(msg, flush=True)
        if IS_MAC:
            subprocess.run(["osascript", "-e", 'display dialog "%s" buttons {"확인"}' % msg.replace('"', "'")])
        sys.exit(1)
    if cfg.get("port") != PORT and not os.environ.get("VF_REMOTE_PORT"):
        cfg["port"] = PORT  # 번호가 바뀌면 아이폰 주소도 바뀌므로 다음부터 같은 번호를 쓴다
        save_config(cfg)
    state["server"] = srv
    GLIDE = Glide()
    if IS_MAC and not INPUT.access():
        INPUT.request_access()  # 시스템이 "손쉬운 사용" 허용을 물어본다
    print("VINFILM 리모트: %s" % info()["url"].split("?")[0], flush=True)
    if open_page:
        open_mac_page()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        p = caff["proc"]
        if p is not None:
            p.terminate()


if __name__ == "__main__":
    main()
