from ultralytics import YOLO


def main():
    # model = YOLO("models/yolov8n.pt")
    model = YOLO("yolo11n.pt")

    model.train(
        data="datasets/data.yaml",
        imgsz=960,
        epochs=80,
        batch=8,
        lr0=0.002,
        optimizer="AdamW",
        patience=20,
        freeze=10,  # 少データなので凍結多め
        close_mosaic=10,
        workers=4,
        device=0,  # GPUなければ device="cpu"
    )

    print("done. check runs/detect/train/weights/best.pt")


if __name__ == "__main__":
    main()
