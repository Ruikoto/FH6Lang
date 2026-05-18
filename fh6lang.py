#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FH6Lang - Forza Horizon 6 Language Switcher / 极限竞速：地平线 6 语言切换工具

Swap language pack files under ./media/Stripped/StringTables/ and write
UserPreferredLang so the game runs with the chosen UI language + Japanese voice.

Supports: Chinese UI + JP voice, English UI + JP voice.
Zero dependencies (stdlib only). Windows (Steam / Xbox) & Linux Steam Deck.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

# 游戏识别字串集中放这里，命名如有变动改这一组即可
GAME_DISPLAY_NAME = "极限竞速：地平线 6 (Forza Horizon 6)"
GAME_STEAM_APPID = "2483190"
GAME_STEAM_NAME_PATTERN = re.compile(r"forza\s*horizon\s*6", re.IGNORECASE)
GAME_INSTALLDIR_HINTS = ("ForzaHorizon6", "Forza Horizon 6")
GAME_EXE_PATTERN = re.compile(r"^ForzaHorizon6.*\.exe$", re.IGNORECASE)
GAME_EXE_EXCLUDES = {
    "ForzaHorizon6Launcher.exe",
    "EasyAntiCheat.exe",
    "EasyAntiCheat_EOS.exe",
    "gamelaunchhelper.exe",
}

STRINGTABLES_REL = Path("media") / "Stripped" / "StringTables"
USER_PREF_DIR = "ForzaHorizon6"
USER_PREF_FILE = "UserPreferredLang"

SWAP_MODES: dict[str, dict] = {
    "chs+jp": {
        "label_zh": "中文 UI + 日语配音",
        "label_en": "Chinese UI + Japanese Voice",
        "files": ("CHS.zip", "JP.zip"),
        "pref": "JP",
    },
    "en+jp": {
        "label_zh": "英文 UI + 日语配音",
        "label_en": "English UI + Japanese Voice",
        "files": ("EN.zip", "JP.zip"),
        "pref": "JP",
    },
}
DEFAULT_MODE = "chs+jp"

APP_NAME = "FH6Lang"


# ---------------------------------------------------------------------------
# 本地化 / Localization
# ---------------------------------------------------------------------------

# 当前语言：None = 双语模式（语言选择前），"zh" 或 "en" = 单语模式
LANG: str | None = None

STRINGS: dict[str, dict[str, str]] = {
    "zh": {
        "banner_subtitle": "语言切换工具",
        "choose_lang": "请选择界面语言（语音固定为日语）：",
        "choose_version": "请选择游戏版本：",
        "steam_ver": "Steam 版",
        "xbox_ver": "Xbox / Microsoft Store / Game Pass 版",
        "xbox_win_only": "（仅 Windows）",
        "manual_path": "手动指定游戏目录",
        "quit": "退出",
        "enter_option": "请输入选项",
        "invalid_option": "无效选项，请重新输入。",
        "selected": "已选择：{label}",
        "uac_restart": "尝试以管理员身份重启（用于写入受保护路径）...",
        "uac_failed": "提权失败或被取消，继续以普通权限运行（Xbox 版可能写不进去）。",
        "detecting_steam": "正在检测 Steam 安装...",
        "steam_not_found": "未找到 Steam，可能未安装或路径非标。",
        "game_not_found_steam": "在 Steam 库里没找到「{name}」。",
        "detecting_xbox": "正在检测 Xbox / Game Pass 安装...",
        "game_not_found_xbox": "在 XboxGames 里没找到「{name}」。",
        "found_install_dir": "检测到安装目录: {dir}",
        "use_this_dir": "是否使用此目录？",
        "enter_install_path": "请粘贴游戏安装目录的完整路径（包含 media/Stripped/StringTables 的那一层）",
        "path_no_stringtables": "该路径下没有找到 {rel}/，请重新输入或留空退出。",
        "dir_not_found": "找不到目录: {dir}",
        "missing_lang_files": "缺少语言包文件: {files}",
        "validating": "正在校验游戏文件...",
        "found_stringtables": "找到 {path}",
        "game_running": "游戏进程正在运行，请先退出游戏。",
        "game_not_running": "游戏未运行",
        "calc_hash": "计算文件哈希...",
        "status_title": "当前状态：",
        "lang_pack_original": "语言包：原始",
        "lang_pack_swapped": "语言包：已互换（{a}<->{b}）",
        "lang_pack_unknown": "语言包：未知（可能游戏已更新或被手动改过）",
        "pref_no_path": "{file}：此平台无法定位（Linux 非 Steam 版？）",
        "pref_set": "{file}：已设置为 {val}",
        "pref_unset": "{file}：未设置",
        "pref_wrong": "{file}：当前值为 {val!r}（非 {expected}）",
        "actions": "操作选项：",
        "action_revert": "还原为原始语言包",
        "action_pref_only": "仅重写 UserPreferredLang（无操作 zip）",
        "action_apply": "应用：{label}",
        "please_select": "请选择",
        "hash_mismatch_fresh": "当前哈希与已知状态都不匹配，按全新原始状态处理（旧记录将被覆盖）。",
        "exec_swap": "执行互换...",
        "swap_done": "{a} <-> {b} 互换完成",
        "revert_done": "{a} <-> {b} 已交换回原状态",
        "state_saved": "状态已记录到 {path}",
        "state_save_fail": "写状态文件失败：{err}（不影响游戏，但下次启动可能识别不到状态）",
        "skip_pref": "跳过 {file}：当前平台无法定位 AppData 路径。",
        "pref_exists": "{file} 已存在且为 {val}，无需重写",
        "pref_written": "已写入 {path}",
        "pref_write_fail": "写 {file} 失败：{err}",
        "complete_apply": "完成！启动游戏后即可享受{label}。",
        "tip_update": "提示：游戏更新可能会还原 zip 互换，那时再跑一次本工具即可。",
        "exec_revert": "执行还原...",
        "revert_fail": "还原失败：{err}",
        "hash_mismatch_revert": "当前哈希与已知状态都不匹配，按全新原始状态处理（旧记录将被覆盖）。",
        "revert_state_fail": "写状态文件失败：{err}",
        "deleted_pref": "已删除 {path}",
        "delete_pref_fail": "删除 {file} 失败：{err}",
        "pref_changed": "{file} 内容已被改过，保留不动。",
        "complete_revert": "已还原。",
        "pref_no_path_short": "当前平台无法定位 AppData 路径。",
        "pref_write_fail_short": "写入失败：{err}",
        "interrupted": "已中断。",
        "unhandled_error": "未处理的异常：{err}",
        "press_enter": "\n按回车键退出...",
        "help_path": "直接指定游戏安装目录（跳过自动检测）",
        "help_lang": "语言模式：chs+jp（中文UI+日语音频）、en+jp（英文UI+日语音频）",
        "help_no_uac": "不在 Windows 上自动请求管理员",
        "help_no_pause": "结束时不暂停（CI / 脚本调用）",
    },
    "en": {
        "banner_subtitle": "Language Switcher",
        "choose_lang": "Choose UI language (voice is always Japanese):",
        "choose_version": "Choose game version:",
        "steam_ver": "Steam",
        "xbox_ver": "Xbox / Microsoft Store / Game Pass",
        "xbox_win_only": " (Windows only)",
        "manual_path": "Specify game directory manually",
        "quit": "Quit",
        "enter_option": "Enter option",
        "invalid_option": "Invalid option, please try again.",
        "selected": "Selected: {label}",
        "uac_restart": "Attempting to relaunch as administrator (for protected paths)...",
        "uac_failed": "UAC elevation failed or cancelled. Continuing without admin (Xbox version may not work).",
        "detecting_steam": "Detecting Steam installation...",
        "steam_not_found": "Steam not found. It may not be installed or uses a non-standard path.",
        "game_not_found_steam": "Could not find \"{name}\" in Steam libraries.",
        "detecting_xbox": "Detecting Xbox / Game Pass installation...",
        "game_not_found_xbox": "Could not find \"{name}\" in XboxGames.",
        "found_install_dir": "Detected install directory: {dir}",
        "use_this_dir": "Use this directory?",
        "enter_install_path": "Paste the full game install path (the folder containing media/Stripped/StringTables)",
        "path_no_stringtables": "{rel}/ not found under that path. Please re-enter or leave blank to quit.",
        "dir_not_found": "Directory not found: {dir}",
        "missing_lang_files": "Missing language pack files: {files}",
        "validating": "Validating game files...",
        "found_stringtables": "Found {path}",
        "game_running": "Game is running. Please exit the game first.",
        "game_not_running": "Game is not running",
        "calc_hash": "Computing file hashes...",
        "status_title": "Current status:",
        "lang_pack_original": "Language packs: Original",
        "lang_pack_swapped": "Language packs: Swapped ({a}<->{b})",
        "lang_pack_unknown": "Language packs: Unknown (game may have been updated or manually modified)",
        "pref_no_path": "{file}: Cannot locate on this platform (Linux non-Steam version?)",
        "pref_set": "{file}: Set to {val}",
        "pref_unset": "{file}: Not set",
        "pref_wrong": "{file}: Current value is {val!r} (expected {expected})",
        "actions": "Actions:",
        "action_revert": "Revert to original language packs",
        "action_pref_only": "Rewrite UserPreferredLang only (no zip swap)",
        "action_apply": "Apply: {label}",
        "please_select": "Select",
        "hash_mismatch_fresh": "Current hashes don't match any known state. Treating as fresh (old records will be overwritten).",
        "exec_swap": "Swapping...",
        "swap_done": "{a} <-> {b} swapped successfully",
        "revert_done": "{a} <-> {b} reverted successfully",
        "state_saved": "State saved to {path}",
        "state_save_fail": "Failed to save state: {err} (won't affect the game, but status may not be detected next time)",
        "skip_pref": "Skipping {file}: Cannot locate AppData path on this platform.",
        "pref_exists": "{file} already set to {val}, no need to rewrite",
        "pref_written": "Written to {path}",
        "pref_write_fail": "Failed to write {file}: {err}",
        "complete_apply": "Done! Launch the game to enjoy {label}.",
        "tip_update": "Tip: Game updates may revert the zip swap. Just run this tool again when that happens.",
        "exec_revert": "Reverting...",
        "revert_fail": "Revert failed: {err}",
        "hash_mismatch_revert": "Current hashes don't match any known state. Treating as fresh (old records will be overwritten).",
        "revert_state_fail": "Failed to save state: {err}",
        "deleted_pref": "Deleted {path}",
        "delete_pref_fail": "Failed to delete {file}: {err}",
        "pref_changed": "{file} has been modified externally. Leaving it as is.",
        "complete_revert": "Reverted.",
        "pref_no_path_short": "Cannot locate AppData path on this platform.",
        "pref_write_fail_short": "Write failed: {err}",
        "interrupted": "Interrupted.",
        "unhandled_error": "Unhandled exception: {err}",
        "press_enter": "\nPress Enter to exit...",
        "help_path": "Specify game install directory directly (skip auto-detection)",
        "help_lang": "Language mode: chs+jp (Chinese UI + JP voice), en+jp (English UI + JP voice)",
        "help_no_uac": "Don't request admin on Windows",
        "help_no_pause": "Don't pause on exit (for CI / scripts)",
    },
}


def t(key: str, **kwargs: object) -> str:
    """返回当前语言的字符串。LANG 为 None 时返回中文。"""
    lang = LANG or "zh"
    s = STRINGS[lang].get(key, key)
    return s.format(**kwargs) if kwargs else s


def t2(key: str, **kwargs: object) -> str:
    """返回 '中文 / English' 双语字符串。"""
    zh = STRINGS["zh"].get(key, key)
    en = STRINGS["en"].get(key, key)
    zh_s = zh.format(**kwargs) if kwargs else zh
    en_s = en.format(**kwargs) if kwargs else en
    if zh_s == en_s:
        return zh_s
    return f"{zh_s} / {en_s}"


# ---------------------------------------------------------------------------
# 终端着色
# ---------------------------------------------------------------------------

def _enable_vt_on_windows() -> bool:
    if not IS_WINDOWS:
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        if handle in (0, -1):
            return False
        mode = ctypes.c_ulong()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False


USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR") and _enable_vt_on_windows()


def _wrap(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


def red(s: str) -> str: return _wrap(s, "31")
def green(s: str) -> str: return _wrap(s, "32")
def yellow(s: str) -> str: return _wrap(s, "33")
def cyan(s: str) -> str: return _wrap(s, "36")
def bold(s: str) -> str: return _wrap(s, "1")


def info(msg: str) -> None: print(msg)
def ok(msg: str) -> None: print(green("  ✓ ") + msg)
def warn(msg: str) -> None: print(yellow("  ⚠ ") + msg)
def fail(msg: str) -> None: print(red("  ✗ ") + msg)


# ---------------------------------------------------------------------------
# Windows UAC 提权
# ---------------------------------------------------------------------------

def is_admin_windows() -> bool:
    if not IS_WINDOWS:
        return True
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin_windows() -> bool:
    """在 Windows 下以管理员身份重启自己。成功后返回 True，调用方应退出。"""
    if not IS_WINDOWS or is_admin_windows():
        return False
    try:
        if getattr(sys, "frozen", False):
            exe = sys.executable
            params = " ".join(f'"{a}"' for a in sys.argv[1:])
        else:
            exe = sys.executable
            params = " ".join(f'"{a}"' for a in [sys.argv[0]] + sys.argv[1:])
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
        return int(rc) > 32
    except Exception as e:
        warn(t("uac_failed"))
        return False


# ---------------------------------------------------------------------------
# 极简 VDF / ACF 解析器（Valve KeyValues v1）
# ---------------------------------------------------------------------------

def parse_vdf(text: str) -> dict:
    pos = 0
    n = len(text)

    def skip_ws():
        nonlocal pos
        while pos < n:
            ch = text[pos]
            if ch in " \t\r\n":
                pos += 1
            elif text[pos:pos + 2] == "//":
                while pos < n and text[pos] != "\n":
                    pos += 1
            else:
                break

    def read_str():
        nonlocal pos
        if pos >= n or text[pos] != '"':
            raise ValueError(f"VDF: 期望字符串于位置 {pos}")
        pos += 1
        out = []
        while pos < n:
            ch = text[pos]
            if ch == "\\" and pos + 1 < n:
                nxt = text[pos + 1]
                out.append({"n": "\n", "t": "\t", "\\": "\\", '"': '"'}.get(nxt, nxt))
                pos += 2
            elif ch == '"':
                pos += 1
                return "".join(out)
            else:
                out.append(ch)
                pos += 1
        raise ValueError("VDF: 字符串未结束")

    def read_obj():
        nonlocal pos
        obj = {}
        skip_ws()
        if pos < n and text[pos] == "{":
            pos += 1
        while True:
            skip_ws()
            if pos >= n:
                break
            if text[pos] == "}":
                pos += 1
                break
            key = read_str()
            skip_ws()
            if pos < n and text[pos] == "{":
                obj[key] = read_obj()
            else:
                obj[key] = read_str()
        return obj

    root = {}
    skip_ws()
    while pos < n:
        skip_ws()
        if pos >= n or text[pos] != '"':
            break
        key = read_str()
        skip_ws()
        if pos < n and text[pos] == "{":
            root[key] = read_obj()
        else:
            root[key] = read_str()
    return root


def _read_text_loose(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_bytes().decode("latin-1", errors="replace")


# ---------------------------------------------------------------------------
# Steam 路径检测
# ---------------------------------------------------------------------------

def find_steam_root() -> list[Path]:
    """返回所有候选 Steam 根目录（按可能性排序）。"""
    candidates: list[Path] = []

    if IS_WINDOWS:
        try:
            import winreg
            for hive, sub, val in (
                (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
            ):
                try:
                    with winreg.OpenKey(hive, sub) as key:
                        path, _ = winreg.QueryValueEx(key, val)
                        p = Path(path)
                        if p.exists() and p not in candidates:
                            candidates.append(p)
                except OSError:
                    pass
        except ImportError:
            pass
        for p in (Path(r"C:\Program Files (x86)\Steam"), Path(r"C:\Program Files\Steam")):
            if p.exists() and p not in candidates:
                candidates.append(p)
    elif IS_LINUX:
        home = Path.home()
        for rel in (
            ".steam/steam",
            ".local/share/Steam",
            ".steam/debian-installation",
            ".var/app/com.valvesoftware.Steam/data/Steam",
        ):
            p = home / rel
            try:
                p = p.resolve()
            except OSError:
                continue
            if p.exists() and p not in candidates:
                candidates.append(p)

    return candidates


def find_steam_libraries(steam_root: Path) -> list[Path]:
    """从 libraryfolders.vdf 枚举所有库目录。"""
    libs: list[Path] = []
    vdf_path = steam_root / "steamapps" / "libraryfolders.vdf"
    if vdf_path.exists():
        try:
            data = parse_vdf(_read_text_loose(vdf_path))
            folders = data.get("libraryfolders") or data.get("LibraryFolders") or {}
            if isinstance(folders, dict):
                for k, v in folders.items():
                    if not k.isdigit():
                        continue
                    path_str = v.get("path") if isinstance(v, dict) else v
                    if not path_str:
                        continue
                    p = Path(path_str)
                    if p.exists() and p not in libs:
                        libs.append(p)
        except Exception as e:
            warn(f"parse libraryfolders.vdf failed / 解析 libraryfolders.vdf 失败: {e}")
    if steam_root.exists() and steam_root not in libs:
        libs.insert(0, steam_root)
    return libs


def _read_acf_install(acf: Path) -> tuple[str, str, str] | None:
    """返回 (name, installdir, appid) 或 None。"""
    try:
        data = parse_vdf(_read_text_loose(acf))
    except Exception:
        return None
    app = data.get("AppState") or data.get("appstate")
    if not isinstance(app, dict):
        return None
    return app.get("name", ""), app.get("installdir", ""), app.get("appid", "")


def find_steam_game(steam_root: Path) -> tuple[Path, str] | None:
    """在所有 Steam 库里找 FH6。返回 (install_dir, appid) 或 None。"""
    libs = find_steam_libraries(steam_root)
    for lib in libs:
        acf = lib / "steamapps" / f"appmanifest_{GAME_STEAM_APPID}.acf"
        if not acf.exists():
            continue
        info_tuple = _read_acf_install(acf)
        if not info_tuple:
            continue
        _, installdir, appid = info_tuple
        if installdir:
            install_path = lib / "steamapps" / "common" / installdir
            if install_path.exists():
                return install_path, appid or GAME_STEAM_APPID
    for lib in libs:
        steamapps = lib / "steamapps"
        if not steamapps.exists():
            continue
        for acf in steamapps.glob("appmanifest_*.acf"):
            info_tuple = _read_acf_install(acf)
            if not info_tuple:
                continue
            name, installdir, appid = info_tuple
            if not (GAME_STEAM_NAME_PATTERN.search(name) or
                    any(h.lower() == installdir.lower() for h in GAME_INSTALLDIR_HINTS)):
                continue
            install_path = steamapps / "common" / installdir
            if install_path.exists():
                return install_path, appid
    return None


# ---------------------------------------------------------------------------
# Xbox 路径检测（仅 Windows）
# ---------------------------------------------------------------------------

def find_xbox_game() -> Path | None:
    if not IS_WINDOWS:
        return None
    try:
        import winreg
        root_key = r"SOFTWARE\Microsoft\GamingServices\PackageRepository\Root"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, root_key) as rk:
            i = 0
            while True:
                try:
                    guid = winreg.EnumKey(rk, i)
                except OSError:
                    break
                i += 1
                try:
                    with winreg.OpenKey(rk, guid) as gk:
                        j = 0
                        while True:
                            try:
                                idx = winreg.EnumKey(gk, j)
                            except OSError:
                                break
                            j += 1
                            try:
                                with winreg.OpenKey(gk, idx) as ek:
                                    root_val, _ = winreg.QueryValueEx(ek, "Root")
                                    p = Path(root_val)
                                    for candidate in (p, p.parent, p.parent.parent):
                                        if (candidate / STRINGTABLES_REL).exists():
                                            if GAME_STEAM_NAME_PATTERN.search(str(candidate)):
                                                return candidate
                            except OSError:
                                pass
                except OSError:
                    pass
    except (ImportError, OSError):
        pass

    drives = []
    try:
        import string
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for i, letter in enumerate(string.ascii_uppercase):
            if bitmask & (1 << i):
                drives.append(Path(f"{letter}:\\"))
    except Exception:
        drives = [Path(f"{d}:\\") for d in "CDEFGHIJ"]

    for drive in drives:
        gaming_root = drive / ".GamingRoot"
        xbox_dirs = [drive / "XboxGames"]
        if gaming_root.exists():
            try:
                raw = gaming_root.read_bytes()
                if raw[:4] in (b"RGBX", b"GBXR") and len(raw) > 4:
                    txt = raw[4:].decode("utf-16-le", errors="ignore").rstrip("\x00")
                    if txt:
                        rel = Path(txt.replace("\\", "/").lstrip("/").lstrip(":"))
                        custom = drive / rel
                        if custom.exists() and custom not in xbox_dirs:
                            xbox_dirs.append(custom)
            except Exception:
                pass
        for xb in xbox_dirs:
            if not xb.exists():
                continue
            for sub in xb.iterdir():
                if not sub.is_dir():
                    continue
                if not GAME_STEAM_NAME_PATTERN.search(sub.name):
                    continue
                content = sub / "Content"
                if (content / STRINGTABLES_REL).exists():
                    return content
                if (sub / STRINGTABLES_REL).exists():
                    return sub
    return None


# ---------------------------------------------------------------------------
# 进程检测
# ---------------------------------------------------------------------------

def is_game_running() -> bool:
    try:
        if IS_WINDOWS:
            flags = 0x08000000  # CREATE_NO_WINDOW
            out = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=10, creationflags=flags,
            )
            for line in out.stdout.splitlines():
                m = re.match(r'"([^"]+)"', line)
                if not m:
                    continue
                name = m.group(1)
                if name in GAME_EXE_EXCLUDES:
                    continue
                if GAME_EXE_PATTERN.match(name):
                    return True
        else:
            out = subprocess.run(
                ["pgrep", "-af", "ForzaHorizon6"],
                capture_output=True, text=True, timeout=10,
            )
            for line in out.stdout.splitlines():
                if any(ex in line for ex in GAME_EXE_EXCLUDES):
                    continue
                for token in line.split():
                    name = os.path.basename(token)
                    if name in GAME_EXE_EXCLUDES:
                        continue
                    if GAME_EXE_PATTERN.match(name):
                        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return False


# ---------------------------------------------------------------------------
# Hash 与状态文件
# ---------------------------------------------------------------------------

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def state_file_path() -> Path:
    if IS_WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return base / APP_NAME / "state.json"
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "fh6lang" / "state.json"


def load_state() -> dict:
    p = state_file_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        warn(f"read state failed / 读取状态文件失败: {e}")
        return {}


def save_state(state: dict) -> None:
    p = state_file_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# UserPreferredLang
# ---------------------------------------------------------------------------

def user_pref_path(version: str, steam_appid: str | None = None) -> Path | None:
    """返回该版本游戏对应的 UserPreferredLang 文件路径。"""
    if IS_WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return base / USER_PREF_DIR / USER_PREF_FILE
    if version not in ("steam", "manual"):
        return None
    appid = steam_appid or GAME_STEAM_APPID
    for root in find_steam_root():
        pfx = root / "steamapps" / "compatdata" / appid / "pfx"
        if pfx.exists():
            return (pfx / "drive_c" / "users" / "steamuser" /
                    "AppData" / "Local" / USER_PREF_DIR / USER_PREF_FILE)
    return None


def read_user_pref(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return path.read_bytes().decode("utf-8", errors="replace").strip()
    except Exception:
        return None


def write_user_pref(path: Path, value: str = "JP") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        f.write(value.encode("utf-8"))


# ---------------------------------------------------------------------------
# 互换 / 还原
# ---------------------------------------------------------------------------

class SwapError(Exception):
    pass


def swap_zips(stringtables_dir: Path, file_a: str, file_b: str) -> None:
    a = stringtables_dir / file_a
    b = stringtables_dir / file_b
    tmp = stringtables_dir / (file_a + ".fh6lang.tmp")
    if tmp.exists():
        raise SwapError(f"Temp file already exists (previous swap may be incomplete): {tmp}")
    os.rename(a, tmp)
    try:
        os.rename(b, a)
    except Exception:
        os.rename(tmp, a)
        raise
    try:
        os.rename(tmp, b)
    except Exception:
        os.rename(a, b)
        os.rename(tmp, a)
        raise


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def banner() -> None:
    print()
    print(cyan("=" * 60))
    print(bold(cyan(f"  {APP_NAME} - {GAME_DISPLAY_NAME}")))
    print(cyan(f"  {t2('banner_subtitle')}"))
    print(cyan("=" * 60))
    print()


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        ans = input(f"{prompt}{suffix}: ").strip()
    except EOFError:
        ans = ""
    return ans or default


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    while True:
        ans = ask(f"{prompt} [{d}]").lower()
        if not ans:
            return default
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False


def prompt_lang_choice() -> str:
    """双语语言选择菜单。返回 SWAP_MODES key，并设置全局 LANG。"""
    global LANG
    info(bold(t2("choose_lang")))
    modes = list(SWAP_MODES.items())
    for i, (key, mode) in enumerate(modes, 1):
        info(f"  [{i}] {mode['label_zh']} / {mode['label_en']}")
    info(f"  [Q] {t2('quit')}")
    while True:
        ans = ask(t2("enter_option")).lower()
        if ans in ("q", "quit", "exit"):
            sys.exit(0)
        try:
            idx = int(ans) - 1
            if 0 <= idx < len(modes):
                chosen_key = modes[idx][0]
                # 中文 UI → 中文界面，英文 UI → 英文界面
                LANG = "zh" if chosen_key == "chs+jp" else "en"
                return chosen_key
        except ValueError:
            pass
        warn(t2("invalid_option"))


def prompt_version_choice() -> str:
    info(bold(t("choose_version")))
    info(f"  [1] {t('steam_ver')}")
    xbox_label = t("xbox_ver")
    if not IS_WINDOWS:
        xbox_label += t("xbox_win_only")
    info(f"  [2] {xbox_label}")
    info(f"  [3] {t('manual_path')}")
    info(f"  [Q] {t('quit')}")
    while True:
        ans = ask(t("enter_option")).lower()
        if ans in ("1", "steam"):
            return "steam"
        if ans in ("2", "xbox") and IS_WINDOWS:
            return "xbox"
        if ans in ("3", "manual"):
            return "manual"
        if ans in ("q", "quit", "exit"):
            sys.exit(0)
        warn(t("invalid_option"))


def confirm_install_dir(candidate: Path | None) -> Path | None:
    if candidate is not None:
        info(t("found_install_dir", dir=bold(str(candidate))))
        if ask_yes_no(t("use_this_dir"), default=True):
            return candidate
    while True:
        manual = ask(t("enter_install_path"))
        if not manual:
            return None
        p = Path(manual).expanduser()
        if (p / STRINGTABLES_REL).exists():
            return p
        fail(t("path_no_stringtables", rel=STRINGTABLES_REL))


def validate_install(install_dir: Path, swap_files: tuple[str, str]) -> Path:
    st = install_dir / STRINGTABLES_REL
    if not st.exists():
        raise SwapError(t("dir_not_found", dir=st))
    missing = [f for f in swap_files if not (st / f).exists()]
    if missing:
        raise SwapError(t("missing_lang_files", files=", ".join(missing)))
    return st


def describe_state(install_key: str, stringtables: Path, pref_path: Path | None,
                   state: dict, swap_files: tuple[str, str],
                   pref_value: str) -> tuple[str, dict]:
    """返回 ('original' | 'swapped' | 'unknown', 当前 hash 字典)。"""
    info(t("calc_hash"))
    current = {f: sha256_of(stringtables / f) for f in swap_files}
    entry = state.get(install_key, {})
    orig = entry.get("original") or {}
    swap = entry.get("swapped") or {}
    if orig and all(orig.get(f) == current[f] for f in swap_files):
        status = "original"
    elif swap and all(swap.get(f) == current[f] for f in swap_files):
        status = "swapped"
    else:
        status = "unknown"

    info("")
    info(bold(t("status_title")))
    if status == "original":
        ok(green(t("lang_pack_original")))
    elif status == "swapped":
        ok(cyan(t("lang_pack_swapped", a=swap_files[0], b=swap_files[1])))
    else:
        warn(yellow(t("lang_pack_unknown")))

    if pref_path is None:
        warn(t("pref_no_path", file=USER_PREF_FILE))
    else:
        existing = read_user_pref(pref_path)
        if existing == pref_value:
            ok(t("pref_set", file=USER_PREF_FILE, val=pref_value))
        elif existing is None:
            warn(t("pref_unset", file=USER_PREF_FILE))
        else:
            warn(t("pref_wrong", file=USER_PREF_FILE, val=existing, expected=pref_value))
    return status, current


def pause_before_exit() -> None:
    try:
        input(t("press_enter"))
    except EOFError:
        pass


def detect_install(version: str) -> tuple[Path | None, str | None]:
    """根据版本检测安装目录。返回 (install_dir, steam_appid_if_steam)。"""
    if version == "steam":
        info(t("detecting_steam"))
        roots = find_steam_root()
        if not roots:
            warn(t("steam_not_found"))
            return None, None
        for root in roots:
            ok(f"Steam: {root}")
            hit = find_steam_game(root)
            if hit:
                return hit[0], hit[1]
        warn(t("game_not_found_steam", name=GAME_DISPLAY_NAME))
        return None, None
    if version == "xbox":
        info(t("detecting_xbox"))
        hit = find_xbox_game()
        if hit:
            return hit, None
        warn(t("game_not_found_xbox", name=GAME_DISPLAY_NAME))
        return None, None
    return None, None


def run(args: argparse.Namespace) -> int:
    banner()

    if IS_WINDOWS and not is_admin_windows() and not args.no_uac:
        info(t2("uac_restart"))
        if relaunch_as_admin_windows():
            return 0
        warn(t2("uac_failed"))

    # 选择语言模式
    if args.lang:
        mode_key = args.lang
        # 命令行模式：chs+jp → 中文界面，en+jp → 英文界面
        global LANG
        LANG = "zh" if mode_key == "chs+jp" else "en"
    else:
        mode_key = prompt_lang_choice()
    mode = SWAP_MODES[mode_key]
    swap_files = mode["files"]
    pref_value = mode["pref"]
    label = mode["label_zh"] if LANG == "zh" else mode["label_en"]
    info(t("selected", label=label))
    info("")

    if args.path:
        version = "manual"
        install_dir = Path(args.path).expanduser()
        steam_appid = None
    else:
        version = prompt_version_choice()
        install_dir, steam_appid = detect_install(version)
        install_dir = confirm_install_dir(install_dir)
    if install_dir is None:
        fail(t("dir_not_found", dir=""))
        return 1

    info("")
    info(t("validating"))
    try:
        stringtables = validate_install(install_dir, swap_files)
    except SwapError as e:
        fail(str(e))
        return 1
    ok(t("found_stringtables", path=stringtables))
    for f in swap_files:
        size = (stringtables / f).stat().st_size
        ok(f"{f} ({size / (1024 * 1024):.1f} MiB)")

    if is_game_running():
        fail(t("game_running"))
        return 1
    ok(t("game_not_running"))

    state = load_state()
    install_key = str(install_dir.resolve())
    pref_path = user_pref_path(version if version != "manual" else "steam", steam_appid)

    status, current_hashes = describe_state(install_key, stringtables, pref_path, state,
                                            swap_files, pref_value)

    info("")
    if status == "swapped":
        info(bold(t("actions")))
        info(f"  [1] {t('action_revert')}")
        info(f"  [2] {t('action_pref_only')}")
        info(f"  [Q] {t('quit')}")
        choice = ask(t("please_select"), default="Q").lower()
        if choice == "1":
            return do_revert(install_key, stringtables, pref_path, state,
                             swap_files, pref_value)
        if choice == "2":
            return do_pref_only(pref_path, pref_value)
        return 0

    info(bold(t("actions")))
    info(f"  [1] {t('action_apply', label=label)}")
    info(f"  [Q] {t('quit')}")
    choice = ask(t("please_select"), default="Q").lower()
    if choice == "1":
        return do_apply(install_key, stringtables, current_hashes, pref_path,
                        state, fresh=(status == "unknown"),
                        swap_files=swap_files, pref_value=pref_value,
                        mode_label=label)
    return 0


def do_apply(install_key: str, stringtables: Path, current_hashes: dict,
             pref_path: Path | None, state: dict, fresh: bool, *,
             swap_files: tuple[str, str], pref_value: str,
             mode_label: str) -> int:
    if fresh:
        warn(t("hash_mismatch_fresh"))
    info(t("exec_swap"))
    try:
        swap_zips(stringtables, swap_files[0], swap_files[1])
    except Exception as e:
        fail(t("revert_fail", err=e))
        return 1
    ok(t("swap_done", a=swap_files[0], b=swap_files[1]))

    swapped_hashes = {f: sha256_of(stringtables / f) for f in swap_files}
    state[install_key] = {"original": current_hashes, "swapped": swapped_hashes}
    try:
        save_state(state)
        ok(t("state_saved", path=state_file_path()))
    except Exception as e:
        warn(t("state_save_fail", err=e))

    if pref_path is None:
        warn(t("skip_pref", file=USER_PREF_FILE))
    else:
        existing = read_user_pref(pref_path)
        if existing == pref_value:
            ok(t("pref_exists", file=USER_PREF_FILE, val=pref_value))
        else:
            try:
                write_user_pref(pref_path, pref_value)
                ok(t("pref_written", path=pref_path))
            except Exception as e:
                fail(t("pref_write_fail", file=USER_PREF_FILE, err=e))

    info("")
    info(green(bold(t("complete_apply", label=mode_label))))
    info(yellow(t("tip_update")))
    return 0


def do_revert(install_key: str, stringtables: Path, pref_path: Path | None,
              state: dict, swap_files: tuple[str, str], pref_value: str) -> int:
    info(t("exec_revert"))
    try:
        swap_zips(stringtables, swap_files[0], swap_files[1])
    except Exception as e:
        fail(t("revert_fail", err=e))
        return 1
    ok(t("revert_done", a=swap_files[0], b=swap_files[1]))

    new_hashes = {f: sha256_of(stringtables / f) for f in swap_files}
    entry = state.get(install_key, {})
    entry["original"] = new_hashes
    entry.pop("swapped", None)
    state[install_key] = entry
    try:
        save_state(state)
    except Exception as e:
        warn(t("revert_state_fail", err=e))

    if pref_path is not None and pref_path.exists():
        if read_user_pref(pref_path) == pref_value:
            try:
                pref_path.unlink()
                ok(t("deleted_pref", path=pref_path))
            except Exception as e:
                warn(t("delete_pref_fail", file=USER_PREF_FILE, err=e))
        else:
            warn(t("pref_changed", file=USER_PREF_FILE))

    info(green(bold(t("complete_revert"))))
    return 0


def do_pref_only(pref_path: Path | None, pref_value: str) -> int:
    if pref_path is None:
        fail(t("pref_no_path_short"))
        return 1
    try:
        write_user_pref(pref_path, pref_value)
        ok(t("pref_written", path=pref_path))
        return 0
    except Exception as e:
        fail(t("pref_write_fail_short", err=e))
        return 1


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--path", help=t2("help_path"))
    p.add_argument("--lang", choices=list(SWAP_MODES.keys()),
                   help=t2("help_lang"))
    p.add_argument("--no-uac", action="store_true", help=t2("help_no_uac"))
    p.add_argument("--no-pause", action="store_true", help=t2("help_no_pause"))
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        rc = run(args)
    except KeyboardInterrupt:
        info(t2("interrupted"))
        rc = 130
    except Exception as e:
        fail(t2("unhandled_error", err=e))
        import traceback
        traceback.print_exc()
        rc = 2
    if not args.no_pause:
        pause_before_exit()
    return rc


if __name__ == "__main__":
    sys.exit(main())
