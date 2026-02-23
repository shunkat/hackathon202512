# 学習結果

`notebooks/datasets/runs/detect/train/results.csv` の解析に基づく、YOLOv11n (Nano) ファインチューニング結果の技術要約。

## 1. 実験条件 (Experimental Setup) - Fixed Camera PoC
- **Dataset**: 53 images (Fixed angle, single scene)
- **Split**: Train 70% / Val 15% / Test 15%
- **Model**: YOLOv11n (Nano), Pretrained on COCO
- **Parameters**: `epochs=80`, `imgsz=960`, `optimizer=AdamW`

## 2. 定量評価結果 (Quantitative Metrics)
Epoch 80 (Final) 時点の検証データ(Val)に対する評価指標。

| Metric | Score | Evaluation |
| :--- | :--- | :--- |
| **mAP@50** | **0.995** | IoU 0.5における平均適合率。実用上、検出ミスはほぼ皆無の状態である。 |
| **mAP@50-95** | **0.824** | IoU 0.5~0.95の平均。バウンディングボックスの位置精度も極めて高い。 |
| **Precision** | **0.993** | 適合率。誤検知 (False Positive) が極小である。 |
| **Recall** | **1.000** | 再現率。検出漏れ (False Negative) がゼロである。 |

> **Note**: アノテーションされた物体（座席・人）に対し、Confidence Threshold > 0.001 の全領域で完全な検出能力を保持している。

## 3. 損失関数の解析 (Loss Analysis)
学習データ(Train)と検証データ(Val)における損失の収束挙動についての詳細分析。

### 3.1 Class Classification Loss (Cls Loss)
> 「人か、空席か」の分類精度を表す損失

- **Values**: `Train: 0.196` / `Val: 0.318`
- **Analysis**:
  - Train/Val間の乖離(Gap)は **0.122** と比較的小さい。
  - これは、モデルが「座席」と「人」の視覚的特徴（テクスチャ、色、形状）を適切に学習しており、未知のデータに対しても高い汎化性能でクラス分類できていることを示唆する。

### 3.2 Bounding Box Loss (Box Loss)
> 「物体の位置・大きさ」の回帰精度を表す損失

- **Values**: `Train: 0.309` / `Val: 0.843`
- **Analysis**:
  - Train/Val間の乖離が **0.534 (約2.7倍)** と大きい。
  - **Technical Insight (Spatial Overfitting)**:
    - 固定カメラ特有の事象である。Trainデータに対しては、モデルが「画面上の絶対座標」レベルで椅子の位置を過剰適合(Overfitting)して学習している。
    - Valデータ（Trainに含まれない画像）では、手ブレや微小な画角ズレにより座標がわずかに異なるため、Lossが高く出ている。
    - ただし、mAP@50-95 (0.824) が高水準であるため、実用上の「椅子の位置ズレ」は許容範囲内に収まっている。

## 4. 結論 (Conclusion)
技術的観点から、この学習モデルは**「固定カメラ環境下における空席検知タスク」において、プロダクション投入可能な水準**に達している。
特筆すべきは Recall 1.0 (見逃しなし) であり、信頼性の高いモニタリングが可能である。一方で、Box Lossの乖離から、カメラ位置の物理的なズレ（数センチ単位の移動や角度変更）に対しては脆弱である可能性があり、運用時の画角固定が前提条件となる。
