import os

from dotenv import load_dotenv

# .env ファイルを読み込む
load_dotenv()

# 環境変数の取得
REGION = os.getenv("REGION", "asia-northeast1")
BUCKET = os.getenv("BUCKET", None)
NMS_IOU = float(os.getenv("NMS_IOU", 0.7))
CONF = float(os.getenv("CONF", 0.25))
CLASSES = os.getenv("CLASSES", None)
MODEL_NAME = os.getenv("MODEL_NAME", "yolov8n")
MODEL_VERSION = os.getenv("MODEL_VERSION", "8.2.0")
