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
        prefix, user_id, _, file_name = storage_file_name.split("/")
        collection_name = f"{prefix}/{user_id}/occupancy_events"

        empty_num = result.get("empty_seat_num", 0)
        occupied_num = result.get("occupied_seat_num", 0)
        total_num = empty_num + occupied_num
        occupancy_rate = occupied_num / total_num if total_num > 0 else 0.0

        doc_data = {
            "user_id": user_id,
            "file_name": file_name,
            "storage_path": f"{bucket_name}/{storage_file_name}",
            "detections_num": len(result.get("detections", [])),
            "empty_seat_num": empty_num,
            "occupied_seat_num": occupied_num,
            "occupancy_rate": occupancy_rate,
            "file_meta": {
                "content_type": processed_data["content_type"],
                # "image_bytes": processed_data["image_bytes"],
                # "image_bgr": processed_data["image_bgr"],
                "size": processed_data["size"],
            },
            "inference": {
                "model_name": processed_data["model_name"],
                "model_version": processed_data["model_version"],
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

    except Exception as e:
        raise ValueError(f"Failed to save result to Firestore: {str(e)}")
