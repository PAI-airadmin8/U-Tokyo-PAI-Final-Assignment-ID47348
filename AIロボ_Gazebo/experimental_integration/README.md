# AIロボ｜C81 → ROS 2 → CRANE+ 統合ゲート（実験版）

## 位置づけ

既存の **C81 AI分類ノード** がROS 2トピックへ返したPICK/SKIP判定を検証し、PICKの場合だけ既存のCRANE+ Gazebo動作プログラムを起動する追加実験です。

**重要：この版の入力はC81で学習用に定義された合成特徴量です。Gazeboカメラ画像から対象を自動認識しているわけではありません。** 対象位置も既知であり、CRANE+は事前定義の関節軌道で動作します。未知物体・実機動作は検証していません。

## 実際につながった処理

1. 合成特徴量を `/pai_b/object_features` (std_msgs/String, JSON) にPublish
2. 既存の `C81/pai_c81_ai_node.py` が分類し `/pai_b/ai_classification` に返信
3. 新ゲートがセッションID、連番、ポリシーSHA、クラス、信頼度、SKIP規則を照合
4. **SKIP → 動作プロセスは一切起動しない**
5. **PICK → `--execute` が指定された場合に限り** `AIロボ_Gazebo/run.sh` を起動
6. 元の運動制御器が接触・実上昇・搬送・放置・退避を独立に検証

タイムアウト、不正応答、ポリシー相違はフェイルクローズ（動作禁止）。分類器をバイパスするローカルPICK固定値を採用していません。

## 2026-11-06 実行記録

| 検証 | 実測 |
|---|---|
| 私物 / ROS 2分類 | SKIP・confidence 0.977207・運動非起動 |
| 紙片 / ROS 2分類 | PICK・confidence 0.957433 |
| 紙片 / PICK連動Gazebo | exit code 0 / `pass: true` |
| 接触 | 両側の継続接触を確認 |
| 紙片実上昇 | 5.4097 mm |
| 水平搬送 | 84.6155 mm |
| 放置位置XY誤差 | 1.3792 mm |
| 解放・退避 | PASS |

証跡: [SKIP](qa/skip_ros_gate_20261106.json) / [PICK dry-run](qa/pick_dry_run_20261106.json) / [PICK→motion](qa/pick_to_motion_gate_20261106.json) / [物理動作QA](qa/motion_20261106.json)。

## 再現方法（ROS 2 Humble、Gazebo 6）

リポジトリのルートから、C81分類ノードを起動します。

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=84
python3 C81/pai_c81_ai_node.py
```

別の端末で **SKIP/ドライラン** を確認します。

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=84
python3 AIロボ_Gazebo/experimental_integration/integrated_entrypoint.py \
  --policy C81/pai_c81_ai_node.py --scenario personal
python3 AIロボ_Gazebo/experimental_integration/integrated_entrypoint.py \
  --policy C81/pai_c81_ai_node.py --scenario paper
```

紙片PICKから実動作へ進める場合のみ、動作専用環境で以下を実行します。**既存Gazeboが同じパーティションで動いていないこと、リソースが十分であることを確認してから実施します。**

```bash
export AIROBO_PARTITION=airobo_integrated_demo
python3 AIロボ_Gazebo/experimental_integration/integrated_entrypoint.py \
  --policy C81/pai_c81_ai_node.py --scenario paper \
  --motion-dir AIロボ_Gazebo --execute \
  --log /tmp/airobo_integrated_qa.json
```

ゲートのユニットテストは `python3 -m unittest discover -s AIロボ_Gazebo/experimental_integration -p 'test_*.py'` で実行します（7件）。

## 制限事項・正式提出との区別

- 本検証は**合成特徴量からのPICK/SKIP → ROS 2ゲート → CRANE+既存運動**の因果連携を示すものです。実際のカメラ画像解析ではありません。
- SKIPの判定は運動起動を抑止しますが、既存制御入口へ別プロセスから直接アクセスする利用者をOSレベルで遮断する仕組みではありません。
- Gazeboの描画と運動QAは別の証明です。正式な連続録画は新たに整合確認する必要があります。
- この変更は従来の正式提出物を上書きせず、独立レビュー用の実験ブランチに置きます。

## 同一試行の新しい連続動画（2026-11-06）

- [CRANE+連続動作動画（67秒・1366×768、15fps）](video/AIrobo_C81_ROS_CRANE_Continuous_20261106.mp4)
- [動画とROS 2判定を対応付けたQA](qa/video_trial_gate_20261106.json)
- [動画と物理動作を対応付けたQA](qa/video_trial_motion_20261106.json)
- [録画マニフェスト・SHA256](qa/video_trial_manifest_20261106.json)

動画と同じ2026年11月6日の試行で、実上昇 **5.8463 mm**、水平搬送 **89.2177 mm**、放置XY誤差 **1.4400 mm**、解放・退避PASS、運動プログラム終了コード0を記録しました。元の150.934秒のデスクトップ録画の79秒位置から67秒間を連続抽出しており、動作の途中を切り貼りしていません。開始直後にはレンダラ初期化画面が含まれます。

**注：** 分類入力は既知物体の合成特徴量で、実映像をAIに入力して分類するデモではありません。外部アプリでの採点・受理を示す動画でもありません。
