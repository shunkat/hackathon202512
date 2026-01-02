import logging

import firebase_admin
from config.settings import BUCKET, REGION
from firebase_admin import firestore
from firebase_functions import https_fn, storage_fn

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("extract_occupancy")

# Firebaseの初期化
app = firebase_admin.initialize_app()
db = firestore.client()


# HTTPリクエストハンドラ
@https_fn.on_request(region=REGION)
def http_health_check(req: https_fn.Request) -> https_fn.Response:
    logger.info("HTTP health check")
    logger.info(f"Request: {req}")
    return https_fn.Response("Hello world!")


# Cloud Storageのトリガー
@storage_fn.on_object_finalized(region=REGION, bucket=BUCKET)
def storage_event_health_check(
    event: storage_fn.CloudEvent[storage_fn.StorageObjectData],
) -> None:
    logger.info("Storage event health check")
    logger.info(f"Event: {event}")

    obj = event.data
    bucket = obj.bucket  # バケット名
    name = obj.name  # オブジェクトパス
    content_type = obj.content_type

    logger.info(f"Bucket: {bucket}")
    logger.info(f"Name: {name}")
    logger.info(f"Content Type: {content_type}")

    return None
