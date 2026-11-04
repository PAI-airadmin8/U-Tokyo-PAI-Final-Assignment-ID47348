#!/usr/bin/env bash
set -euo pipefail

# GitHubから取得したディレクトリを、そのまま実行基点として使う。
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if ! command -v g++ >/dev/null 2>&1 || ! pkg-config --exists ignition-transport11; then
  echo "エラー：g++ と ignition-transport11 の開発環境が必要です。" >&2
  exit 3
fi

mkdir -p bin runs
if [[ ! -x bin/airobo_native_motion_owner || src/airobo_native_motion_owner.cpp -nt bin/airobo_native_motion_owner ]]; then
  echo "Gazebo Transportの常駐制御器をビルドします。"
  g++ -O1 -std=c++17 src/airobo_native_motion_owner.cpp -o bin/airobo_native_motion_owner $(pkg-config --cflags --libs ignition-transport11)
fi

echo "AIロボ V3：物理Pick & Placeの自動検証を開始します。"
exec python3 -u "$ROOT/autonomous_pick_place.py"
