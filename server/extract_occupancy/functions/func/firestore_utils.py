from datetime import datetime, timezone

from firebase_admin import firestore


def save_detection_result(
    db: firestore.Client,
    processed_data: dict,
    result: dict,
    storage_file_name: str,
    bucket_name: str,
) -> None:
    """Save the occupancy detection result to Firestore"""
    try:
        prefix, user_id, file_name = storage_file_name.split("/")
        collection_name = f"{prefix}/{user_id}/occupancy_events"
        doc_data = {
            "user_id": user_id,
            "file_name": file_name,
            "storage_path": f"{bucket_name}/{storage_file_name}",
            "detections_num": len(result.get("detections", [])),
            "persons_num": result.get("persons_num", 0),
            "chairs_num": result.get("chairs_num", 0),
            "occupied_chairs_num": result.get("occupied_chairs_num", 0),
            "occupancy_rate": result.get("occupancy_rate", 0),
            "file_meta": {
                "content_type": processed_data["content_type"],
                "image_bytes": processed_data["image_bytes"],
                "image_bgr": processed_data["image_bgr"],
                "size": processed_data["size"],
            },
            "inference": {
                "model_name": "yolov8n",
                "model_version": "8.2.0",
                "occupancy_method": processed_data["method"],
                "classes_filter": processed_data["class_ids"],
                "conf_threshold": processed_data["conf"],
                "nms_iou_threshold": processed_data["iou"],
                # "runtime_ms": processed_data["runtime_ms"],
            },
            "detections": result.get("detections", []),
            "captured_at": processed_data["updated"],
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }

        # Add a new document with an auto-generated ID
        _, doc_ref = db.collection(collection_name).add(doc_data)

        print(f"Saved detection result to Firestore: {doc_ref.id}")

    except Exception:
        print("Failed to save result to Firestore")
