#!/usr/bin/env bash
# Linux / Steam Deck 启动包装：在脚本所在目录运行 fh6lang.py。
# 用法：chmod +x run.sh && ./run.sh
set -e
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then
    exec python3 fh6lang.py "$@"
elif command -v python >/dev/null 2>&1; then
    exec python fh6lang.py "$@"
else
    echo "未找到 python3。Steam Deck / 多数 Linux 发行版默认自带 python3，"
    echo "请安装 python3 后重试。"
    exit 1
fi
