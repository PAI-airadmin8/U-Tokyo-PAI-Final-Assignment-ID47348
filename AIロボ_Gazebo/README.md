# AIロボ V3｜CRANE+・Gazeboの物理Pick & Place

## 実験の概要

既知位置にある模擬紙片を、固定側と可動側の**リアルタイム接触**によって把持し、Gazeboの物理演算で持ち上げ・搬送・放置まで実行しました。接触判定を省略せず、実際の関節角と対象物の位置を記録しています。

## 正式な連続実行（2026年11月3日）

| 検証項目 | 正式録画と同じ試行の結果 |
|---|---:|
| 単一制御入口による一括実行 | PASS |
| 両側のリアルタイム接触 | PASS |
| 紙片の実上昇 | 5.18 mm |
| 水平搬送 | 88.70 mm |
| 放置パッドの中心からのずれ | 1.92 mm |
| 解放・安全退避 | PASS |
| 正式無中断録画 | 62.17秒、1280×720 |

[日本語テロップ版](video/AIrobo_V3_Official_OnePass_JP.mp4)｜[正式無中断録画（元動画）](video/AIrobo_V3_Official_FINAL_Continuous_20261103.mp4)｜[実験報告PDF](report/AIrobo_V3_Final_Report_ID47348.pdf)｜[同一試行QA](qa/official_onepass_qa.json)｜[動画・QA対応記録](qa/official_video_manifest.json)

## 実行方法

**必要環境：** Ubuntu、ROS 2 Humble、Ignition Gazebo 6、Ignition Transport 11開発ファイル、C++17（g++）、Python 3。CRANE+のメッシュ・SDF関連リソースを配置したROS 2ワークスペースが必要です。

GitHubから取得後、Linuxコンテナ内ではこのフォルダから実行します。

```bash
bash run.sh
```

AA8-N-0061のWindowsホストでは、このフォルダのPowerShellスクリプトからDockerへコードをコピーして実行できます。

```powershell
.\run.ps1
```

コンテナ名を変更する場合は `-ContainerName` を指定します。デフォルトは `pai-crane-ai-base-20261101` です。

`run.sh` はC++常駐制御器をソースからビルドします。実行結果は `runs/` に日時を付けたQA JSONとして保存します。Gazeboのリソースパスは `IGN_GAZEBO_RESOURCE_PATH` で変更できます。

## 安全な動作順序

1. グリッパを開いて、事前に確認した姿勢へ移動
2. 把持前に一度だけ紙片を指定位置に配置
3. 固定側・可動側の両方のContactが成立してから把持を維持
4. 紙片が5 mm以上上昇し、両側接触が続くことを確認
5. Joint 1を小刻みに回転させ、対象が追従する間だけ搬送
6. 静的な実放置パッドへ開放し、静止と安全退避を確認

**制御の原則：** 目標角度を発行しただけでは成功とせず、実際の関節フィードバックを連続3回確認します。到達しない場合は最大2試行で停止します。上昇時は台座との干渉を避けるため、基本のJoint移動順序を Joint 3 → Joint 2 → Joint 4 としています。

## ソース・QA

- `autonomous_pick_place.py`：単一の上位動作入口
- `src/airobo_native_motion_owner.cpp`：Gazebo Transportの常駐送信・受信と両側Contact監視
- `run.sh`・`run.ps1`：コンテナ内／Windowsホストからの起動
- `worlds/`：CRANE+、模擬紙片、衝突あり放置パッドのSDF
- `qa/`：独立反復テスト3/3、Joint 3往復20/20、本番動画と同じ試行のQA
- `video/`・`report/`：正式録画・日本語テロップ版・実験報告書
- `scripts/`：正式撮影時に使用した画面準備・録画スクリプト（環境専用）

## 実験範囲と注意事項

紙片を再配置するのは**把持開始前の初期化**に限ります。把持開始後は紙片の位置を強制変更しません。DetachableJointなどの仮想接続は使用せず、Gazeboの衝突・摩擦・重力で把持と放置を検証します。

本検証は既知位置と事前に決めた関節経路を用いた教育用シミュレーションです。C81で作成したPICK/SKIP分類器をV3に自動接続したものではなく、未知位置への対応、実機での安全性、学校による受理は確認対象外です。
