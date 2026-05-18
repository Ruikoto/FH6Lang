# FH6Lang

**Forza Horizon 6 — Chinese UI + Japanese Voice Switcher**

**极限竞速：地平线 6 — 中文界面 + 日语配音切换工具**

---

## What It Does / 功能简介

The game bundles display language and voice language together. Under `./media/Stripped/StringTables/`, each language has its own zip file. This tool swaps `CHS.zip` and `JP.zip`, then writes `UserPreferredLang=JP` to AppData — giving you Chinese UI with Japanese audio.

游戏把"显示语言"和"配音语言"绑在了一起。`./media/Stripped/StringTables/` 下每个语言一个 zip。本工具将 `CHS.zip` 和 `JP.zip` 互换，并在 AppData 中写入 `UserPreferredLang=JP`，即可实现中文界面 + 日语配音。

## Supported Platforms / 支持平台

| Platform / 平台 | Edition / 版本 |
|---|---|
| Windows | Steam |
| Windows | Xbox / Microsoft Store / Game Pass |
| Steam Deck / Linux | Steam (Proton) |

## Download / 下载

Grab the latest `FH6Lang.exe` from [Releases](../../releases).

从 [Releases](../../releases) 页面下载最新的 `FH6Lang.exe`。

## Usage / 使用方法

### Windows

Double-click `FH6Lang.exe`. It will auto-request UAC elevation if needed (useful for Xbox edition).

双击运行 `FH6Lang.exe`，会自动弹出 UAC 提权（Xbox 版可能需要）。

Or with Python installed / 或者本地有 Python 3：

```bash
python fh6lang.py
```

### Steam Deck / Linux

```bash
chmod +x run.sh
./run.sh
```

SteamOS ships with Python 3 — no extra dependencies needed.

SteamOS 自带 Python 3，无需额外安装。

## Workflow / 工作流程

1. Select game edition (Steam / Xbox / Manual path)
   选择游戏版本（Steam / Xbox / 手动指定路径）

2. Auto-detect install directory, ask for confirmation
   自动检测安装目录，确认后继续

3. Show current state: Original / Swapped / Unknown
   显示当前状态：原始 / 已互换 / 未知

4. Choose "Apply" or "Revert"
   选择"应用"或"还原"

## CLI Arguments / 命令行参数

```
python fh6lang.py --path "D:\SteamLibrary\steamapps\common\ForzaHorizon6"
python fh6lang.py --no-uac       # Skip UAC prompt on Windows / Windows 不请求管理员
python fh6lang.py --no-pause     # Don't pause on exit (for CI / scripts) / 结束不暂停
```

## State File / 状态文件

| OS | Path |
|---|---|
| Windows | `%LOCALAPPDATA%\FH6Lang\state.json` |
| Linux | `~/.config/fh6lang/state.json` |

Stores SHA-256 hashes of both zip files before and after swapping, used to detect current state.

存储互换前后两个 zip 的 SHA-256，用于判断当前是原始还是已互换。

## After a Game Update / 游戏更新后

A game update will restore the original `CHS.zip` and `JP.zip`, reverting your swap. Just run this tool again — it will detect the hash mismatch, record the new baseline, and re-swap.

游戏更新会还原原版 `CHS.zip` 和 `JP.zip`。再跑一次本工具即可，它会检测到哈希变化，记录新基准并重新互换。

The `UserPreferredLang` file lives under user AppData and is not touched by game updates, so it usually doesn't need rewriting.

`UserPreferredLang` 位于用户 AppData 下，游戏更新不会动它，一般无需重写。

## How It Works / 工作原理

- **Zip swap** uses `os.rename` in 3 atomic steps (CHS -> tmp, JP -> CHS, tmp -> JP). Any failure triggers an immediate reverse rollback.
  **zip 互换**通过 `os.rename` 三步原子化执行（CHS -> tmp, JP -> CHS, tmp -> JP），任一步失败立即反向回滚。

- **Process detection** uses `tasklist` on Windows and `pgrep -af` on Linux (Proton preserves the exe name). Excludes launcher/helper processes.
  **进程检测**在 Windows 用 `tasklist`，Linux 用 `pgrep -af`（Proton 下 exe 名保留）。排除 Launcher 等辅助进程。

- **No third-party dependencies** — Python standard library only.
  **无第三方依赖**，仅使用 Python 标准库。
