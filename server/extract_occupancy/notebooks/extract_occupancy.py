import cv2
import numpy as np

from ultralytics import YOLO

import json
import pathlib

import matplotlib.pyplot as plt

input_dir = "datasets/raw/images"
output_dir = "datasets/outputs"
_model = None


def get_model():
    global _model
    if _model is None:
        # _model = YOLO("models/yolov8n.pt")
        _model = YOLO("../../../runs/detect/train3/weights/best.pt")
        print(_model.names)
    return _model


def iou(boxA, boxB):
    """Calculate Intersection over Union (IoU) between two bounding boxes"""
    # box: [x1,y1,x2,y2]
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    inter = max(0, xB - xA) * max(0, yB - yA)
    if inter <= 0:
        return 0.0
    areaA = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    areaB = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    return inter / (areaA + areaB - inter + 1e-9)


def extract_occupancy_from_image(
    image_bgr: np.ndarray,
    nms_iou: float = 0.7,
    conf: float = 0.25,
    class_ids: list[int] | None = None,
) -> dict:
    """Perform YOLO object detection on an image"""
    model = get_model()
    results = model.predict(
        source=image_bgr,
        iou=nms_iou,
        conf=conf,
        classes=class_ids,
        verbose=False,
    )[0]
    # print(results)

    boxes = results.boxes
    print(boxes)
    if boxes is None or len(boxes) == 0:
        return {
            "detections": [],
        }

    detections = []

    for b in boxes:
        cls_id = int(b.cls[0])
        xyxy = b.xyxy[0].cpu().numpy().astype(float).tolist()
        score = float(b.conf[0])
        cls_name = results.names.get(cls_id, f"class_{cls_id}")

        detections.append(
            {
                "class_id": cls_id,
                "class_name": cls_name,
                "box": xyxy,
                "score": score,
            },
        )

    return {
        "detections": detections,
    }


def draw_debug(image_bgr: np.ndarray, occupancy: dict) -> np.ndarray:
    """Draw bounding boxes and labels on image for debugging"""
    img = image_bgr.copy()

    # Class colors
    class_colors = {
        0: (255, 0, 0),  # person: blue
        56: (0, 255, 0),  # chair: green
    }

    for i, det in enumerate(occupancy["detections"]):
        x1, y1, x2, y2 = map(int, det["box"])
        cls_id = det["class_id"]
        cls_name = det["class_name"]
        score = det["score"]

        # Get color (random for undefined classes)
        color = class_colors.get(
            cls_id,
            (
                (cls_id * 50) % 255,
                (cls_id * 100) % 255,
                (cls_id * 150) % 255,
            ),
        )

        # Draw bounding box
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

        # Draw label with background
        text = f"{cls_name} {score:.2f}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        position = (x1, max(0, y1 - 8))

        # Black outline
        cv2.putText(img, text, position, font, font_scale, (0, 0, 0), 4)
        # Colored text
        cv2.putText(img, text, position, font, font_scale, color, 2)

    # Summary info
    summary_text = f"Total detections: {len(occupancy['detections'])}"

    # Background rectangle
    cv2.rectangle(img, (5, 5), (400, 50), (0, 0, 0), -1)

    # Text
    cv2.putText(
        img,
        summary_text,
        (10, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (255, 255, 255),
        2,
    )

    return img


def main(
    file_name: str,
    nms_iou: float,
    conf: float,
    class_ids: list[int] | None = None,
) -> None:
    # 画像読み込み BGR
    img = cv2.imread(str(pathlib.Path(input_dir) / f"{file_name}.jpg"))
    occ = extract_occupancy_from_image(
        img,
        nms_iou=nms_iou,
        conf=conf,
        class_ids=class_ids,
    )
    # 出力ディレクトリを作成
    class_ids_str = "_".join(map(str, class_ids)) if class_ids else "all"
    output_subdir = (
        pathlib.Path(output_dir) / f"conf{conf}_iou{nms_iou}_classes{class_ids_str}"
    )
    output_subdir.mkdir(parents=True, exist_ok=True)
    # occ jsonで保存
    occ_json_path = output_subdir / f"{file_name}_occ.json"
    with open(occ_json_path, "w") as f:
        json.dump(occ, f, indent=2)
    debug = draw_debug(img, occ)
    # Notebook表示と保存
    plt.figure(figsize=(12, 8))
    plt.imshow(cv2.cvtColor(debug, cv2.COLOR_BGR2RGB))
    plt.axis("off")
    # 先に保存
    debug_img_path = output_subdir / f"{file_name}_debug.png"
    plt.savefig(debug_img_path, bbox_inches="tight", dpi=150)
    # その後に表示
    plt.show()


if __name__ == "__main__":
    main(
        file_name="sample1",
        nms_iou=0.7,
        conf=0.25,
        # class_id入れる
        # class_ids=None,
    )
