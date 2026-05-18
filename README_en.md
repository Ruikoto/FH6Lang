<p align="right">
  <a href="README.md">中文</a>
</p>

# FH6Lang

A lightweight tool to switch **Forza Horizon 6** to **Chinese UI + Japanese voice**.

## What It Does

The game bundles display language and voice language together. Under `./media/Stripped/StringTables/`, each language has its own zip file. This tool swaps `CHS.zip` and `JP.zip`, then writes `UserPreferredLang=JP` to AppData — giving you Chinese UI with Japanese audio.

It also auto-detects the game directory and remembers swap state across runs.

## Supported Platforms

- **Windows + Steam**
- **Windows + Xbox / Microsoft Store / Game Pass**
- **Steam Deck / Linux + Steam** (via Proton)

## Usage

### Windows

Download `FH6Lang.exe` from [Releases](../../releases) and double-click to run. It will auto-request UAC elevation if needed (useful for Xbox edition).

Or with Python installed:

```
python fh6lang.py
```

### Steam Deck / Linux

```
chmod +x run.sh
./run.sh
```

SteamOS ships with Python 3 — no extra dependencies needed.

## Workflow

1. Select game edition (Steam / Xbox / Manual path)
2. Auto-detect install directory, ask for confirmation
3. Show current state: Original / Swapped / Unknown
4. Choose "Apply" or "Revert"

## CLI Arguments

```
python fh6lang.py --path "D:\SteamLibrary\steamapps\common\ForzaHorizon6"
python fh6lang.py --no-uac       # Skip UAC prompt on Windows
python fh6lang.py --no-pause     # Don't pause on exit (for CI / scripts)
```

## State File

- Windows: `%LOCALAPPDATA%\FH6Lang\state.json`
- Linux: `~/.config/fh6lang/state.json`

Stores SHA-256 hashes of both zip files before and after swapping, used to detect current state.

## After a Game Update

A game update will restore the original `CHS.zip` and `JP.zip`, reverting your swap. Just run this tool again — it will detect the hash mismatch, record the new baseline, and re-swap.

The `UserPreferredLang` file lives under user AppData and is not touched by game updates, so it usually doesn't need rewriting.

## How It Works

- **Zip swap** uses `os.rename` in 3 atomic steps (CHS -> tmp, JP -> CHS, tmp -> JP). Any failure triggers an immediate reverse rollback.
- **Process detection** uses `tasklist` on Windows and `pgrep -af` on Linux (Proton preserves the exe name). Excludes launcher/helper processes.
- **No third-party dependencies** — Python standard library only.
