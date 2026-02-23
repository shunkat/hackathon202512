import cv2
import numpy as np
from google.cloud import storage


def download_blob_to_memory(bucket_name: str, blob_name: str) -> bytes:
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    return blob.download_as_bytes()


def image_bytes_to_bgr(image_bytes: bytes) -> np.ndarray:
    """Convert image bytes to OpenCV BGR format"""
    # Convert bytes to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)

    # Decode image
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Failed to decode image")

    return img


def bgr_to_image_bytes(image_bgr: np.ndarray, format: str = ".jpg") -> bytes:
    """Convert OpenCV BGR image to bytes"""
    success, encoded = cv2.imencode(format, image_bgr)

    if not success:
        raise ValueError(f"Failed to encode image as {format}")

    return encoded.tobytes()
