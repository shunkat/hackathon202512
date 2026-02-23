import logging
import sys
import traceback

import firebase_admin
from firebase_admin import firestore
from firebase_functions import https_fn
from firebase_functions import storage_fn, options

from config.settings import (
    BUCKET,
    REGION,
    NMS_IOU,
    CONF,
    CLASSES,
    MODEL_NAME,
    MODEL_VERSION,
)
from func.occupancy_detector import extract_occupancy_from_image
from func.firestore_utils import save_detection_result
from func.storage_utils import (
    download_blob_to_memory,
    image_bytes_to_bgr,
)


# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,  # 明示的にstdoutに出力
)
logger = logging.getLogger("extract_occupancy")

# Firebaseの初期化
app = firebase_admin.initialize_app()
db = firestore.client()


# @https_fn.on_request(
#     region=REGION,
#     timeout_sec=300,
# )
# def http_health_check(req: https_fn.Request) -> https_fn.Response:
#     # logger.info("HTTP health check")
#     # logger.info(f"Request: {req}")
#     print("HTTP health check")
#     print(f"Request: {req}")
#     return https_fn.Response("Hello world!")


# Cloud Storageのトリガー
@storage_fn.on_object_finalized(
    region=REGION,
    bucket=BUCKET,
    # memory=options.MemoryOption.MB_512,
    memory=1024,
    timeout_sec=300,
)
def storage_event_health_check(
    event: storage_fn.CloudEvent[storage_fn.StorageObjectData],
) -> None:
    obj = event.data
    bucket = obj.bucket
    name = obj.name
    content_type = obj.content_type

    print(f"event obj: {obj}")

    print(f"Storage event triggered: bucket={bucket}, name={name}, type={content_type}")

    # Only process image files
    if not content_type or not content_type.startswith("image/"):
        print(f"Skipping non-image file: {content_type}")
        return

    try:
        # Download image from Cloud Storage
        print(f"Downloading image: {name}")
        image_bytes = download_blob_to_memory(bucket, name)

        # Convert to OpenCV format
        print("Converting image to BGR format")
        image_bgr = image_bytes_to_bgr(image_bytes)

        # Run occupancy detection
        print("Running occupancy detection")
        result = extract_occupancy_from_image(
            image_bgr,
            nms_iou=NMS_IOU,
            conf=CONF,
            class_ids=CLASSES,
        )

        unique_class_ids = set()
        for detection in result["detections"]:
            unique_class_ids.add(detection["class_id"])

        processed_data = {
            "bucket": obj.bucket,
            "name": obj.name,
            "content_type": obj.content_type,
            "metadata": obj.metadata,
            "size": obj.size,
            "time_created": obj.time_created,
            "updated": obj.updated,
            "image_bytes": image_bytes,
            "image_bgr": image_bgr,
            "iou": NMS_IOU,
            "conf": CONF,
            "class_ids": list(unique_class_ids),
            "method": "method1",
            "model_name": MODEL_NAME,
            "model_version": MODEL_VERSION,
        }

        print(f"Detection complete: {len(result['detections'])} objects detected")
        print(f"result: {result}")

        # Save validation results to Firestore
        print("Saving result to Firestore...")
        save_detection_result(db, processed_data, result, name, bucket)

        print(f"Processing complete for: {name}")

    except Exception as e:
        print(f"Error processing image {name}: {str(e)}")
        traceback.print_exc()
        raise
