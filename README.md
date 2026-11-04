# AIロボ｜Physical AI 講座2026・応用編1 最終課題

**提出者：ID47348**  
**実施日：2026年11月3日**

物体を見分けて「拾う（PICK）／拾わない（SKIP）」を判断する実験と、CRANE+をGazeboの物理シミュレーションで動作させる発展実験をまとめています。

## 提出内容

| 実験 | 内容 | 検証結果 |
|---|---|---|
| [C81：AIごみ回収](C81/) | ROS 2・MuJoCoによる分類、回収判断、回収動作 | 3配置でごみ9件回収、私物3件をSKIP |
| [AIロボ V3：CRANE+](AIロボ_Gazebo/) | Gazeboのリアル接触・把持・上昇・搬送・放置 | 自動実行3/3、正式連続実行もPASS |

## 動画・資料

- [C81：日本語テロップ付き動画（85.17秒）](C81/video/PAI_C81_FINAL_3LAYOUTS_85s_JP.mp4)｜[無加工の元動画](C81/video/PAI_C81_FINAL_3LAYOUTS_85s.mp4)｜[C81独立QA](C81/qa/INDEPENDENT_QA.json)
- [CRANE+：日本語テロップ付き動画（62.17秒）](AIロボ_Gazebo/video/AIrobo_V3_Official_OnePass_JP.mp4)｜[無加工の正式無中断録画](AIロボ_Gazebo/video/AIrobo_V3_Official_FINAL_Continuous_20261103.mp4)
- [CRANE+：実験報告PDF](AIロボ_Gazebo/report/AIrobo_V3_Final_Report_ID47348.pdf)｜[録画と同じ試行のQA](AIロボ_Gazebo/qa/official_onepass_qa.json)

## 実験の位置づけ

- **C81とCRANE+は別々に検証した実装です。** C81のPICK/SKIP判断が、CRANE+の軌道を直接生成する段階には至っていません。
- C81はMuJoCoの仮想センサと簡略機構を利用します。CRANE+はGazeboで剛体接触・摩擦・重力を計算し、DetachableJointによる仮想吸着は利用していません。
- CRANE+の紙片は**把持前に一度だけ**指定位置へ配置します。把持後は物体を強制移動しません。
- いずれも**教育用シミュレーション**です。実機での成功、未知物体の汎用認識、学校の採点・受理を示すものではありません。

再現方法、実行環境、元の動画とQAの対応は各実装のREADMEに記載しています。
