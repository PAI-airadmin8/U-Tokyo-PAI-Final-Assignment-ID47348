# AIロボ｜Physical AI 講座2026 応用編1 最終課題

ID47348。物体のPICK/SKIP判断と、CRANE+の物理Pick & Placeを教育用シミュレーションで検証しました。

| 実装 | 内容 | 結果 |
|---|---|---|
| [C81](C81/) | ROS 2・MuJoCoで分類・PICK/SKIP | 3配置、ごみ9件回収・私物3件SKIP |
| [AIロボ_Gazebo](AIロボ_Gazebo/) | CRANE+のリアル双側接触・把持・上昇・搬送・放置 | 独立自動QA3/3、本番連続実行PASS |

[正式動画](AIロボ_Gazebo/video/AIrobo_V3_Official_FINAL_Continuous_20261103.mp4) ｜ [報告PDF](AIロボ_Gazebo/report/AIrobo_V3_Final_Report_ID47348.pdf) ｜ [本番QA](AIロボ_Gazebo/qa/official_onepass_qa.json)

**範囲:** C81のAI判断とGazebo V3の動作は別々の実装。V3単独でカメラ画像から未知物体を分類したものではありません。Gazeboの物理演算を用いたシミュレーションであり、実機実験ではありません。学校への提出受理・採点は別です。
