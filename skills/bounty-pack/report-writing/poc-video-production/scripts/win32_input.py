"""Real UI input helpers for Windows screen-recording segments (Route D).

Driven by SendInput, so the input is genuine (a recording shows a real cursor doing real things)
and no GUI-automation driver is needed. Pitfall baked in: on x64 sizeof(INPUT) MUST be 40 and the
body MUST be a union of MOUSEINPUT/KEYBDINPUT/HARDWAREINPUT - a separately sized keyboard struct is
rejected by SendInput (returns 0) and the keypress silently never happens.

Usage:
    from win32_input import click, move, key, hotkey, wheel, to_foreground, visible_windows
    to_foreground()                 # find + focus the recorded window by title
    move(1117, 100); click(1117, 100)
    key(0x74)                       # F5
    hotkey("ctrl", "shift", "i")    # DevTools toggle
    wheel(-120, x=1150, y=500)      # negative delta = scroll DOWN

Sanity check (no input is sent):
    python win32_input.py
"""
import time
import ctypes
import ctypes.wintypes as wt

u32 = ctypes.windll.user32


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.c_size_t)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.c_size_t)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong), ("wParamL", ctypes.c_ushort),
                ("wParamH", ctypes.c_ushort)]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", ctypes.c_ulong), ("u", INPUT_UNION)]


MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 0x0002, 0x0004
MOUSEEVENTF_WHEEL = 0x0800
KEYEVENTF_KEYUP = 0x0002
INPUT_MOUSE, INPUT_KEYBOARD = 0, 1
VK = {"ctrl": 0x11, "shift": 0x10, "alt": 0x12}


def _send(inputs):
    n = u32.SendInput(len(inputs), ctypes.byref(inputs), ctypes.sizeof(INPUT))
    if n != len(inputs):
        raise RuntimeError(f"SendInput sent {n}/{len(inputs)} events "
                           f"(sizeof(INPUT)={ctypes.sizeof(INPUT)}, expected 40)")
    return n


def _vk(k):
    if isinstance(k, int):
        return k
    s = str(k).lower()
    if s in VK:
        return VK[s]
    if len(s) == 1 and s.isalpha():
        return ord(s.upper())
    if s.startswith("f") and s[1:].isdigit():
        return 0x70 + int(s[1:]) - 1
    raise ValueError(f"unknown key: {k}")


def move(x, y, pause=0.35):
    u32.SetCursorPos(int(x), int(y))
    time.sleep(pause)


def click(x, y, pause=0.2, x_before=None):
    """Move (optionally via an intermediate point so the cursor visibly travels), then click."""
    if x_before is not None:
        u32.SetCursorPos(int(x_before[0]), int(x_before[1]))
        time.sleep(0.2)
    u32.SetCursorPos(int(x), int(y))
    time.sleep(pause)
    arr = (INPUT * 2)()
    arr[0].type, arr[0].mi = INPUT_MOUSE, MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, 0)
    arr[1].type, arr[1].mi = INPUT_MOUSE, MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, 0)
    _send(arr)


def key(vk):
    arr = (INPUT * 2)()
    arr[0].type, arr[0].ki = INPUT_KEYBOARD, KEYBDINPUT(_vk(vk), 0, 0, 0, 0)
    arr[1].type, arr[1].ki = INPUT_KEYBOARD, KEYBDINPUT(_vk(vk), 0, KEYEVENTF_KEYUP, 0, 0)
    _send(arr)


def hotkey(*keys):
    """hotkey('ctrl','shift','i'), hotkey('f12'). Modifiers held, key pressed, reversed release."""
    vks = [_vk(k) for k in keys]
    for vk in vks:
        a = (INPUT * 1)()
        a[0].type, a[0].ki = INPUT_KEYBOARD, KEYBDINPUT(vk, 0, 0, 0, 0)
        _send(a)
        time.sleep(0.03)
    for vk in reversed(vks):
        a = (INPUT * 1)()
        a[0].type, a[0].ki = INPUT_KEYBOARD, KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP, 0, 0)
        _send(a)
        time.sleep(0.03)


def wheel(delta, x=None, y=None):
    """delta < 0 scrolls DOWN, > 0 scrolls UP. Measure px-per-tick before relying on it."""
    if x is not None:
        move(x, y, 0.2)
    arr = (INPUT * 1)()
    arr[0].type, arr[0].mi = INPUT_MOUSE, MOUSEINPUT(0, 0, int(delta), MOUSEEVENTF_WHEEL, 0, 0)
    _send(arr)


def find_window(title_substr):
    """First visible top-level window whose title contains title_substr."""
    hits = []
    for hwnd, title, rect in visible_windows():
        if title_substr.lower() in title.lower():
            hits.append((hwnd, title, rect))
    return hits[0] if hits else None


def to_foreground(title_substr, settle=0.4):
    hit = find_window(title_substr)
    if not hit:
        raise RuntimeError(f"no visible window matching {title_substr!r}")
    u32.SetForegroundWindow(hit[0])
    time.sleep(settle)
    return hit[0]


def visible_windows():
    """[(hwnd, title, (l, t, r, b)), ...]. The callback returns True on EVERY path - returning
    None/False halts EnumWindows at the first title-less window and yields an empty list."""
    out = []

    def cb(hwnd, _):
        try:
            if u32.IsWindowVisible(hwnd):
                ln = u32.GetWindowTextLengthW(hwnd)
                if ln:
                    buf = ctypes.create_unicode_buffer(ln + 1)
                    u32.GetWindowTextW(hwnd, buf, ln + 1)
                    r = wt.RECT()
                    u32.GetWindowRect(hwnd, ctypes.byref(r))
                    out.append((hwnd, buf.value, (r.left, r.top, r.right, r.bottom)))
        except Exception:
            pass
        return True

    ENUM = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    u32.EnumWindows(ENUM(cb), 0)
    return out


if __name__ == "__main__":
    print("sizeof(INPUT) =", ctypes.sizeof(INPUT), "(must be 40 on x64)")
    assert ctypes.sizeof(INPUT) == 40, "INPUT layout wrong - every SendInput call will fail"
    print("screen =", u32.GetSystemMetrics(0), "x", u32.GetSystemMetrics(1))
    for hwnd, title, rect in visible_windows()[:12]:
        print(f"  {hwnd:>10}  {rect}  {title[:70]}")
    print("no input sent; import and call click/key/hotkey/wheel to drive the UI")
