# AIロボ V3｜Gazebo・CRANE+ 実物理Pick & Place

## 本番QA（2026-11-03）

| 項目 | 正式連続動画と同一試行の結果 |
|---|---:|
| 単一入口による自動実行 | PASS |
| 固定側・可動側のリアル接触 | PASS |
| 紙片の実際の上昇 | 5.18 mm |
| 水平搬送 | 88.70 mm |
| 放置パッド中心誤差 | 1.92 mm |
| 解放・安全退避 | PASS |

[正式無中断動画](video/AIrobo_V3_Official_FINAL_Continuous_20261103.mp4) ｜ [報告PDF](report/AIrobo_V3_Final_Report_ID47348.pdf) ｜ [実行QA](qa/official_onepass_qa.json)

## 再現

AA8-N-0061のDockerホストから実行：

```powershell
docker exec pai-crane-ai-base-20261101 bash /home/ubuntu/airobot_ws/pai_airobo_v3_delivery/run.sh
```

`autonomous_pick_place.py` が唯一の上位運動入口。C++常駐Transport Publisher / SubscriberでJoint 1～4およびハンドを制御し、実関節の3回連続フィードバックと双側Contactで次段を許可します。未到位は最大2試行で停止します。

`worlds/` にSDF、`src/` にControllerソース、`qa/` に独立の試行ログを格納。Joint 3独立往復20/20、従前の独立自動実行3/3も確認済みです。

## 実験範囲・注意

紙片を既知位置に配置するのは**把持前の初期化のみ**。把持後は位置を強制上書きせず、摩擦・衝突・重力により上昇・搬送・放置を検証します。DetachableJointによる仮想吸着は使いません。

実機ではなくGazeboの教育用シミュレーションです。C81のPICK/SKIP分類とは別系統であり、未知物体のカメラ認識・任意位置の経路探索・実機での動作保証は本結果に含まれません。
