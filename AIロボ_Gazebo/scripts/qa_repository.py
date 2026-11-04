#!/usr/bin/env python3
"""GitHub提出物のコード・元動画・日本語表示版・PDF・QAの整合性を確認する。"""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
C81 = ROOT / "C81"
V3 = ROOT / "AIロボ_Gazebo"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for block in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


def check(name: str, result: bool, detail: str = "") -> None:
    status = "合格" if result else "不合格"
    print(f"[{status}] {name} {detail}")
    if not result:
        failures.append(name)


failures: list[str] = []

c81_video = C81 / "video/PAI_C81_FINAL_3LAYOUTS_85s.mp4"
c81_ja = C81 / "video/PAI_C81_FINAL_3LAYOUTS_85s_JP.mp4"
c81_qa = load(C81 / "qa/INDEPENDENT_QA.json")
check("C81独立QA", c81_qa["pass"] is True)
check("C81の3配置", len(c81_qa["runs"]) == 3)
check("C81元動画SHA256", digest(c81_video) == c81_qa["video"]["sha256"])
check("C81動画とQAの長さ", abs(duration(c81_video) - c81_qa["video"]["duration_s"]) < 0.1)
check("C81日本語字幕版", c81_ja.is_file() and abs(duration(c81_ja) - duration(c81_video)) < 0.1)

v3_video = V3 / "video/AIrobo_V3_Official_FINAL_Continuous_20261103.mp4"
v3_ja = V3 / "video/AIrobo_V3_Official_OnePass_JP.mp4"
v3_qa = load(V3 / "qa/official_onepass_qa.json")
v3_manifest = load(V3 / "qa/official_video_manifest.json")
v3_history = load(V3 / "qa/three_run_summary.json")
check("Gazebo連続実行の独立QA", v3_qa["pass"] is True)
check("Gazebo再現性検証", v3_history["pass"] is True)
check("正式録画とQAの対応", v3_manifest["qa_pass"] is True and v3_manifest["run_exit"] == 0)
original_duration = duration(v3_video)
check("Gazebo正式録画の長さ",
      abs(original_duration - float(v3_manifest["video_probe"]["format"]["duration"])) < 0.1)
check("Gazebo日本語字幕版",
      v3_ja.is_file() and abs(duration(v3_ja) - original_duration) < 0.1)
sdf = ET.parse(V3 / "worlds/base_no_detach.sdf").getroot()
has_detachable = any("DetachableJoint" in (p.get("name") or "") for p in sdf.iter("plugin"))
check("物体の仮想吸着を使用していない", not has_detachable)
check("正式動画と同じQAで実上昇",
      v3_qa["summary"]["real_lift_mm"] >= 5)
check("正式動画と同じQAで搬送",
      v3_qa["summary"]["transport_mm"] >= 80)
pdf = V3 / "report/AIrobo_V3_Final_Report_ID47348.pdf"
check("報告PDF", pdf.is_file() and pdf.read_bytes()[:4] == b"%PDF")
check("Gazebo再現コード",
      (V3 / "run.sh").is_file() and (V3 / "autonomous_pick_place.py").is_file()
      and (V3 / "src/airobo_native_motion_owner.cpp").is_file())
print(f"検証結果：{len(failures)}件の不合格")
sys.exit(1 if failures else 0)
