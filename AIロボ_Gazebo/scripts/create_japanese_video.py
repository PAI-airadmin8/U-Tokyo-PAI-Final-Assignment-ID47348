#!/usr/bin/env python3
"""C81とCRANE+の無加工動画から、日本語字幕付きの閲覧用動画を生成する。"""
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import subprocess

ROOT = Path(__file__).resolve().parents[2]
FONT = os.environ.get(
    "AIROBO_JAPANESE_FONT",
    "/usr/share/fonts/truetype/takao-gothic/TakaoGothic.ttf",
)


def annotate(source: Path, destination: Path, captions: dict, c81: bool) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"元動画が見つかりません：{source}")
    if not Path(FONT).is_file():
        raise FileNotFoundError(f"日本語フォントが見つかりません：{FONT}")
    with TemporaryDirectory(prefix="airobo_ja_") as work:
        directory = Path(work)
        for name, value in captions.items():
            (directory / f"{name}.txt").write_text(value, encoding="utf-8")

        def draw(name: str, x: int, y: int):
            return (
                f"drawtext=fontfile={FONT}:textfile={directory / (name + '.txt')}:"
                f"fontsize=18:fontcolor=white:x={x}:y={y}"
            )

        if c81:
            filters = [
                "drawbox=x=0:y=0:w=iw:h=78:color=black@1:t=fill",
                "drawbox=x=0:y=443:w=iw:h=37:color=black@1:t=fill",
                draw("title", 12, 8),
                draw("subtitle", 12, 44),
                draw("part1", 14, 452) + ":enable='between(t,0,28.375)'",
                draw("part2", 14, 452) + ":enable='between(t,28.375,56.520)'",
                draw("part3", 14, 452) + ":enable='gte(t,56.520)'",
            ]
        else:
            filters = [
                "drawbox=x=0:y=0:w=iw:h=38:color=black@1:t=fill",
                "drawbox=x=0:y=680:w=iw:h=40:color=black@0.78:t=fill",
                draw("title", 15, 8),
                draw("subtitle", 20, 686),
            ]

        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(source), "-vf", ",".join(filters),
                "-an", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "24", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", str(destination),
            ],
            check=True,
        )
        print(f"日本語字幕版を生成しました：{destination}")


def main() -> None:
    annotate(
        ROOT / "C81/video/PAI_C81_FINAL_3LAYOUTS_85s.mp4",
        ROOT / "C81/video/PAI_C81_FINAL_3LAYOUTS_85s_JP.mp4",
        {
            "title": "AIロボ C81｜ごみ・私物の判定と回収（MuJoCo）",
            "subtitle": "3配置：ごみ9件を回収、私物3件は回収しない",
            "part1": "配置1｜仮想センサ → PICK / SKIP → 回収",
            "part2": "配置2｜別の初期配置でも判定と回収を検証",
            "part3": "配置3｜私物を残して模擬ごみを回収",
        },
        c81=True,
    )
    annotate(
        ROOT / "AIロボ_Gazebo/video/AIrobo_V3_Official_FINAL_Continuous_20261103.mp4",
        ROOT / "AIロボ_Gazebo/video/AIrobo_V3_Official_OnePass_JP.mp4",
        {
            "title": "AIロボ V3｜CRANE+・Gazebo 物理把持",
            "subtitle": "双側の接触確認 → 実上昇 → 搬送 → 放置",
        },
        c81=False,
    )


if __name__ == "__main__":
    main()
