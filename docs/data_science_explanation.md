# オブジェクト検知 (Occupancy Detection) 実装解説

ハッカソンにおける「混雑状況可視化」を実現するための、Computer Vision (CV) パイプラインの実装詳細である。
YOLOv8/v11 をベースとした物体検知モデルの構築・学習から推論までのワークフローを以下の4つのスクリプトで構成している。

## Architecture Overview

- **Model**: YOLOv8n / YOLO11n (Pre-trained on COCO) followed by Finetuning
- **Task**: Object Detection (Custom Classes: `empty_seat`, `occupied_seat`)
- **Frameworks**: Ultralytics YOLO, OpenCV, Albumentations, PyTorch

---

## 1. Annotation Tool (`annotate_bbox.py`)
**Role: Ground Truth Generation**

OpenCVを利用した軽量なカスタムアノテーションツールである。撮影した座席画像に対して、バウンディングボックス(BBox)とクラスラベルを付与する。

- **Input**: Raw Images (`.jpg`)
- **Output**: YOLO format Labels (`.txt` in normalized coordinates)
  - Format: `<class_id> <x_center> <y_center> <width> <height>` (Normalized 0.0-1.0)
- **Features**:
  - `cv2.setMouseCallback` を用いたインタラクティブなBBox描画
  - リアルタイムでの正規化座標変換処理 (`normalized_yolo` メソッド)
  - プレビュー画像の自動生成によるQC(Quality Control)支援

## 2. Dataset Pipeline (`argument_dataset.py`)
**Role: Data Preprocessing & Augmentation**

Rawデータを学習用(Train)、検証用(Val)、評価用(Test)に分割し、学習データに対してのみ Data Augmentation (データ拡張) を適用する。

- **Split Strategy**:
  - `sklearn.model_selection.train_test_split` を使用
  - Ratio: Train: 70%, Val: 15%, Test: 15% (Approx.)
- **Augmentation Pipeline** (Powered by `albumentations`):
  - 実環境（Webカメラやスマホ撮影）での堅牢性を高めるため、以下の変換を確率的に適用:
    - **Blur/Noise**: MotionBlur, GaussianBlur, ISONoise (手ブレ、ピントズレ、高感度ノイズへの対策)
    - **Color/Brightness**: RandomBrightnessContrast, RandomGamma, HueSaturationValue (照明環境の変化への対策)
    - **Geometric**: Affine (Scale, Translate, Rotate, Shear) (カメラアングルの微小な変化への対策)
  - **BBox Safe Transform**: 変形によりBBoxが見切れた場合のフィルタリング (`min_visibility=0.25`) を適用し、学習データの品質を担保する。
- **Output**: Ultralytics YOLO形式のディレクトリ構造 (`images/{train,val,test}`, `labels/{train,val,test}`) および `data.yaml` の自動生成。

## 3. Training (`train_yolo.py`)
**Role: Model Finetuning**

Ultralytics ライブラリを使用し、事前学習済みモデルからの転移学習(Transfer Learning)を実行する。

- **Base Model**: `yolov8n.pt` or `yolo11n.pt` (Nanoモデルを採用し、推論速度とエッジデバイスへのデプロイ性を重視)
- **Hyperparameters**:
  - `imgsz=960`: 小さな物体（遠くの座席など）の検知精度向上のため、デフォルト(640)より高解像度で学習。
  - `epochs=80`: データセットサイズに応じた早期収束ポイントの設定。
  - `optimizer="AdamW"`: 汎化性能向上のため採用。
  - `freeze=10`: Backboneの初期層を凍結し、特徴抽出能力を維持しつつHeadのみを重点的に学習。
- **Monitoring**: `runs/detect/train` 配下に学習曲線やConfusion Matrix、F1-Curve等が自動保存され、モデル性能を定量評価する。

## 4. Inference Service (`extract_occupancy.py`)
**Role: Production Inference**

学習済みモデル (`best.pt`) をロードし、入力画像に対して推論を実行、結果を構造化データとして返却する。

- **Process Flow**:
  1. **Load Model**: 学習済みの重みをロード（シングルトンパターン推奨）。
  2. **Predict**: 入力画像 (BGR numpy array) に対して推論実行。
  3. **Post-Processing**:
      - **NMS (Non-Maximum Suppression)**: 重複するBBoxを `nms_iou` 閾値で削除。
      - **Confidence Filtering**: 信頼度スコアが `conf` 未満の検出除外。
  4. **Output**:
      - JSON: アプリケーション層で扱える形式 (`class_id`, `box`, `score`) で出力。
      - Debug Image: 可視化用にBBoxと信頼度スコアを描画した画像を生成。

---

## Summary for Engineers

| Module | Key Tech Stack | Description |
| --- | --- | --- |
| **Annotation** | OpenCV, pure Python | Custom lightweight tool for YOLO format generation. |
| **Data Pipeline** | Albumentations, scikit-learn | Automated split & robust augmentation pipeline handling geometric/intensity transforms. |
| **Training** | Ultralytics YOLO (PyTorch) | Transfer learning on Nano models with high-res input (`imgsz=960`) for small object detection. |
| **InferenceWrapper** | Ultralytics, NumPy | Production-ready wrapper with configurable NMS/Conf thresholds and structured JSON output. |

## 参考
また、以下のようなデータセットも参考もある
- https://universe.roboflow.com/studycafe/studycafe/dataset/10
- https://universe.roboflow.com/project/occupancy-detection-rzo4o/dataset/1
- https://universe.roboflow.com/stuthi-udupas-workspace/empty-seat-detection-vhhxe/dataset/3/images?split=train