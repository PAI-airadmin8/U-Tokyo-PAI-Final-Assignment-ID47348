# C81｜AIごみ回収ロボット（ROS 2・MuJoCo）

## 目的

ロボットがごみを回収するとき、私物まで拾わないようにするため、物体の色・寸法などの仮想センサ情報からPICK（拾う）／SKIP（拾わない）を判断する実験です。

## 実験結果

| 検証項目 | 結果 |
|---|---|
| 異なる初期配置 | 3配置 |
| ごみの回収 | 9件 |
| 私物の回収回避 | 3件（SKIP） |
| 独立QA | PASS |
| 実行動画 | 85.17秒・H.264（3配置の映像をまとめたもの） |

[日本語テロップ版](video/PAI_C81_FINAL_3LAYOUTS_85s_JP.mp4)｜[元の実行動画（無加工）](video/PAI_C81_FINAL_3LAYOUTS_85s.mp4)｜[独立QA](qa/INDEPENDENT_QA.json)

各配置の実行要約： [配置1](qa/layout_0_summary.json) ・ [配置2](qa/layout_1_summary.json) ・ [配置3](qa/layout_2_summary.json)

## ソースコードと実行

主要なファイルは、`pai_c81_ai_node.py`（分類・判断）、`pai_c81_robot_runtime.py`（ロボット動作・状態管理）、`pai_c81_mujoco.py`（シミュレーション）、`pai_c81_independent_qa.py`（独立検証）、`test_pai_c81_protocol.py`（単体テスト）です。

必要環境：ROS 2 Humble、MuJoCo 3.14.0、NumPy、ffmpeg、画面表示環境。

```bash
bash run_pai_c81_final3.sh
```

実行結果は既定で `/tmp/pai_c81_v3_isolated_qa` に生成します。保存先は環境変数 `PAI_C81_OUT_ROOT` で変更できます。

## 検証上の注意点

- 実カメラではなく、MuJoCo上の**仮想センサ**を用います。
- 台車は簡略化した移動モデル、アームは簡略3軸モデルです。
- 把持は接触後に有効化される仮想拘束で、CRANE+の摩擦による指把持とは異なります。
- 動画は3つの初期配置の試験をまとめています。日本語版は字幕表示のみで、動作・時間・速度を変更していません。3配置すべてを一度の無中断動作として実行したという意味ではありません。
- 実機への導入結果やフルSLAM、自動運転性能を示すものではありません。
