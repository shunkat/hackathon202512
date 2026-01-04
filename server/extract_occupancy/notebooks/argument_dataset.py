from __future__ import annotations

import random
import shutil
from pathlib import Path

import cv2
import yaml
from sklearn.model_selection import train_test_split
from tqdm import tqdm
import albumentations as A

# ========= 設定 =========
RAW_DIR = Path("datasets/raw")
OUT_DIR = Path("datasets/augmented")
SPLIT_DIR = Path("datasets/split")

# 4枚なら 80〜200 が現実的。まず 120(=約480枚) 推奨
N_AUG_PER_IMAGE = 120
SEED = 42

# 0/1 のクラス
NAMES = ["empty_seat", "occupied_seat"]

# 椅子(小物)が消えにくい“安全寄り”Aug
transform = A.Compose(
    [
        # 画質劣化・ノイズ系
        A.OneOf(
            [
                # カメラの手ブレのようなボケ
                A.MotionBlur(blur_limit=5, p=0.4),
                # ピントが合っていないようなボケ
                A.GaussianBlur(blur_limit=3, p=0.4),
                # 暗所撮影のようなザラザラしたノイズ
                A.ISONoise(p=0.3),
            ],
            # 25%の確率で実行
            p=0.25,
        ),
        # 色・明るさ系
        A.OneOf(
            [
                # 明るさやコントラストを変える
                A.RandomBrightnessContrast(p=0.7),
                # ガンマ補正
                A.RandomGamma(p=0.4),
                # 色相・彩度を変える
                A.HueSaturationValue(p=0.3),
            ],
            # 85%の確率で実行
            p=0.85,
        ),
        # 位置変換系
        A.Affine(
            # 95%〜106%に拡大縮小
            scale=(0.95, 1.06),
            # 0%〜3%の移動
            translate_percent=(0.0, 0.03),
            # -4度〜4度の回転
            rotate=(-4, 4),
            # -3度〜3度の歪み
            shear=(-3, 3),
            # 80%の確率で実行
            p=0.8,
        ),
    ],
    # 画像を変形させたときに、バウンディングボックスも一緒に正しく変形させるための設定
    bbox_params=A.BboxParams(
        format="yolo",  # YOLOの (cx,cy,w,h) 正規化をそのまま扱う
        label_fields=["class_ids"],
        # 変形の結果、元の箱の 25%以上 が残っていないと(画面外に見切れたりしたら)、その箱は「見えなくなった」として削除
        min_visibility=0.25,
        # 箱が画像からはみ出さないようにクリップ
        clip=True,
    ),
)
# =======================

random.seed(SEED)


def read_yolo_label(
    label_path: Path,
) -> tuple[list[int], list[tuple[float, float, float, float]]]:
    """class_idとboxを取得"""
    class_ids, bboxes = [], []
    if not label_path.exists():
        return class_ids, bboxes
    text = label_path.read_text().strip()
    if not text:
        return class_ids, bboxes

    for line in text.splitlines():
        parts = line.strip().split()
        # class_id, centerX, centerY, width, heightの5つ
        if len(parts) != 5:
            continue
        cls = int(parts[0])
        x, y, w, h = map(float, parts[1:])
        class_ids.append(cls)
        bboxes.append((x, y, w, h))
    return class_ids, bboxes


def write_yolo_label(
    label_path: Path,
    class_ids: list[int],
    bboxes_yolo: list[tuple[float, float, float, float]],
) -> None:
    """YOLO形式のラベルを書き込む"""
    lines = []
    for cls, (x, y, w, h) in zip(class_ids, bboxes_yolo):
        if w <= 0 or h <= 0:
            continue
        if (w * h) < 1e-6:
            continue
        x = min(max(x, 0.0), 1.0)
        y = min(max(y, 0.0), 1.0)
        w = min(max(w, 0.0), 1.0)
        h = min(max(h, 0.0), 1.0)
        lines.append(f"{cls} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")

    label_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def main():
    in_img_dir = RAW_DIR / "images"
    in_lbl_dir = RAW_DIR / "labels"
    out_img_dir = OUT_DIR / "images"
    out_lbl_dir = OUT_DIR / "labels"
    out_img_dir.mkdir(parents=True, exist_ok=True)
    out_lbl_dir.mkdir(parents=True, exist_ok=True)

    img_paths = sorted(
        [
            p
            for p in in_img_dir.glob("*")
            if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]
        ],
    )
    if not img_paths:
        msg = f"No images in {in_img_dir}"
        raise RuntimeError(msg)

    for img_path in tqdm(img_paths, desc="augment"):
        stem = img_path.stem
        label_path = in_lbl_dir / f"{stem}.txt"

        img = cv2.imread(str(img_path))
        if img is None:
            continue

        class_ids, bboxes = read_yolo_label(label_path)

        # 元画像もコピー(学習安定)
        cv2.imwrite(str(out_img_dir / f"{stem}_orig{img_path.suffix}"), img)
        write_yolo_label(out_lbl_dir / f"{stem}_orig.txt", class_ids, bboxes)

        for i in range(N_AUG_PER_IMAGE):
            aug = transform(image=img, bboxes=bboxes, class_ids=class_ids)
            aug_img = aug["image"]
            aug_boxes = aug["bboxes"]
            aug_cls = aug["class_ids"]

            if len(aug_boxes) == 0:
                continue

            out_stem = f"{stem}_aug{i:04d}"
            cv2.imwrite(str(out_img_dir / f"{out_stem}{img_path.suffix}"), aug_img)
            write_yolo_label(out_lbl_dir / f"{out_stem}.txt", aug_cls, aug_boxes)

    print("done: augmented")

    # --- split into train/val ---
    if SPLIT_DIR.exists():
        shutil.rmtree(SPLIT_DIR)

    (SPLIT_DIR / "images/train").mkdir(parents=True, exist_ok=True)
    (SPLIT_DIR / "images/val").mkdir(parents=True, exist_ok=True)
    (SPLIT_DIR / "labels/train").mkdir(parents=True, exist_ok=True)
    (SPLIT_DIR / "labels/val").mkdir(parents=True, exist_ok=True)

    # 全画像のパスを取得
    all_images = sorted(
        [
            p
            for p in out_img_dir.glob("*")
            if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]
        ],
    )

    # 8:2 に分割
    train_imgs, val_imgs = train_test_split(
        all_images,
        test_size=0.2,
        random_state=SEED,
    )

    def copy_files(img_list: list[Path], split_name: str) -> None:
        for img_p in tqdm(img_list, desc=f"split {split_name}"):
            lbl_p = out_lbl_dir / f"{img_p.stem}.txt"

            shutil.copy2(img_p, SPLIT_DIR / "images" / split_name / img_p.name)
            if lbl_p.exists():
                shutil.copy2(lbl_p, SPLIT_DIR / "labels" / split_name / lbl_p.name)

    copy_files(train_imgs, "train")
    copy_files(val_imgs, "val")

    # data.yaml
    data_yaml = {
        "path": str(SPLIT_DIR.resolve()),
        "train": "images/train",
        "val": "images/val",
        "names": dict(enumerate(NAMES)),
    }
    Path("datasets/data.yaml").write_text(
        yaml.safe_dump(data_yaml, sort_keys=False),
        encoding="utf-8",
    )
    print("done: split + wrote data.yaml")


if __name__ == "__main__":
    main()
