from __future__ import annotations

import ctypes
import os
import time
import threading
import webbrowser
from ctypes import wintypes
from typing import Callable


WM_DESTROY = 0x0002
WM_COMMAND = 0x0111
WM_USER = 0x0400
WM_TRAYICON = WM_USER + 20
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205

NIM_ADD = 0x00000000
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004

IDI_APPLICATION = 32512
IMAGE_ICON = 1
LR_SHARED = 0x00008000

MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
TPM_RIGHTBUTTON = 0x0002

SW_SHOWNORMAL = 1

ID_OPEN_CONFIG = 1001
ID_OPEN_DISPLAY = 1002
ID_EXIT = 1003


user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32

LRESULT = ctypes.c_ssize_t
HCURSOR = wintypes.HANDLE
HICON = wintypes.HANDLE
UINT_PTR = ctypes.c_size_t

WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", HICON),
        ("hCursor", HCURSOR),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class NOTIFYICONDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", HICON),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetLastError.argtypes = []
kernel32.GetLastError.restype = wintypes.DWORD

user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASS)]
user32.RegisterClassW.restype = wintypes.ATOM
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    wintypes.LPVOID,
]
user32.CreateWindowExW.restype = wintypes.HWND
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.LoadImageW.argtypes = [
    wintypes.HINSTANCE,
    wintypes.LPCWSTR,
    wintypes.UINT,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
user32.LoadImageW.restype = wintypes.HANDLE
user32.CreatePopupMenu.argtypes = []
user32.CreatePopupMenu.restype = wintypes.HMENU
user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, UINT_PTR, wintypes.LPCWSTR]
user32.AppendMenuW.restype = wintypes.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.TrackPopupMenu.argtypes = [
    wintypes.HMENU,
    wintypes.UINT,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.LPRECT,
]
user32.TrackPopupMenu.restype = wintypes.BOOL
user32.DestroyMenu.argtypes = [wintypes.HMENU]
user32.DestroyMenu.restype = wintypes.BOOL
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.PostQuitMessage.restype = None
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = wintypes.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.TranslateMessage.restype = wintypes.BOOL
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = LRESULT

shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATA)]
shell32.Shell_NotifyIconW.restype = wintypes.BOOL


class WindowsTrayApp:
    def __init__(self, host: str, port: int, on_exit: Callable[[], None] | None = None) -> None:
        self.host = host
        self.port = port
        self.on_exit = on_exit
        self.class_name = "NewsTalentMonitorPlusTray"
        self.hinstance = kernel32.GetModuleHandleW(None)
        self.hwnd = None
        self.icon_data = None
        self._wndproc = WNDPROC(self._handle_message)

    @property
    def config_url(self) -> str:
        return f"http://{self.host}:{self.port}/config"

    @property
    def display_url(self) -> str:
        return f"http://{self.host}:{self.port}/display"

    def run(self) -> None:
        self._create_window()
        try:
            self._add_icon()
        except OSError:
            while True:
                time.sleep(3600)
        self._message_loop()

    def _create_window(self) -> None:
        wndclass = WNDCLASS()
        wndclass.lpfnWndProc = self._wndproc
        wndclass.hInstance = self.hinstance
        wndclass.lpszClassName = self.class_name
        atom = user32.RegisterClassW(ctypes.byref(wndclass))
        if not atom and kernel32.GetLastError() != 1410:
            raise ctypes.WinError()

        self.hwnd = user32.CreateWindowExW(
            0,
            self.class_name,
            "News Talent Monitor+",
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            self.hinstance,
            None,
        )
        if not self.hwnd:
            raise ctypes.WinError()

    def _add_icon(self) -> None:
        icon = user32.LoadImageW(None, ctypes.cast(ctypes.c_void_p(IDI_APPLICATION), wintypes.LPCWSTR), IMAGE_ICON, 0, 0, LR_SHARED)
        icon_data = NOTIFYICONDATA()
        icon_data.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        icon_data.hWnd = self.hwnd
        icon_data.uID = 1
        icon_data.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        icon_data.uCallbackMessage = WM_TRAYICON
        icon_data.hIcon = icon
        icon_data.szTip = "News Talent Monitor+"
        if not shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(icon_data)):
            raise ctypes.WinError()
        self.icon_data = icon_data

    def _message_loop(self) -> None:
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def _handle_message(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAYICON:
            if lparam == WM_LBUTTONDBLCLK:
                self._open_config()
            elif lparam == WM_RBUTTONUP:
                self._show_menu()
            return 0
        if msg == WM_COMMAND:
            command_id = int(wparam) & 0xFFFF
            if command_id == ID_OPEN_CONFIG:
                self._open_config()
            elif command_id == ID_OPEN_DISPLAY:
                self._open_display()
            elif command_id == ID_EXIT:
                self._exit()
            return 0
        if msg == WM_DESTROY:
            self._remove_icon()
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _show_menu(self) -> None:
        menu = user32.CreatePopupMenu()
        user32.AppendMenuW(menu, MF_STRING, ID_OPEN_CONFIG, "Open Config")
        user32.AppendMenuW(menu, MF_STRING, ID_OPEN_DISPLAY, "Open Display")
        user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(menu, MF_STRING, ID_EXIT, "Stop News Talent Monitor+")

        point = POINT()
        user32.GetCursorPos(ctypes.byref(point))
        user32.SetForegroundWindow(self.hwnd)
        user32.TrackPopupMenu(menu, TPM_RIGHTBUTTON, point.x, point.y, 0, self.hwnd, None)
        user32.DestroyMenu(menu)

    def _open_config(self) -> None:
        threading.Thread(target=webbrowser.open, args=(self.config_url,), daemon=True).start()

    def _open_display(self) -> None:
        threading.Thread(target=webbrowser.open, args=(self.display_url,), daemon=True).start()

    def _remove_icon(self) -> None:
        if self.icon_data is not None:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.icon_data))
            self.icon_data = None

    def _exit(self) -> None:
        if self.on_exit:
            self.on_exit()
        self._remove_icon()
        user32.DestroyWindow(self.hwnd)
        os._exit(0)
