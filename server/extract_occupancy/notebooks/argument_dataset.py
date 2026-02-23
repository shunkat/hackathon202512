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
SPLIT_DIR = Path("datasets/split")
DATA_YAML_PATH = Path("datasets/data.yaml")

SEED = 42

# 0/1 のクラス
NAMES = ["empty_seat", "occupied_seat"]

# trainだけ増やしたいときだけTrue
AUGMENT_TRAIN = True
N_AUG_PER_IMAGE = 10  # 50枚あるなら 10〜30 くらいで十分なことが多い

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


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def list_raw_images(in_img_dir: Path) -> list[Path]:
    return sorted(
        [
            p
            for p in in_img_dir.glob("*")
            if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]
        ],
    )


def copy_one_sample(
    img_path: Path, lbl_path: Path, out_img_dir: Path, out_lbl_dir: Path
) -> None:
    """画像とラベルをコピー(raw → split)"""
    shutil.copy2(img_path, out_img_dir / img_path.name)
    if lbl_path.exists():
        shutil.copy2(lbl_path, out_lbl_dir / lbl_path.name)


def augment_one_image_to_train(
    img_path: Path,
    lbl_path: Path,
    out_img_dir: Path,
    out_lbl_dir: Path,
    n_aug: int,
) -> None:
    """Train にだけ拡張を生成して書き出す"""
    stem = img_path.stem
    img = cv2.imread(str(img_path))
    if img is None:
        return

    class_ids, bboxes = read_yolo_label(lbl_path)

    # 元画像も train に残す(名前衝突回避のため _orig を付与)
    out_orig_stem = f"{stem}_orig"
    cv2.imwrite(str(out_img_dir / f"{out_orig_stem}{img_path.suffix}"), img)
    write_yolo_label(out_lbl_dir / f"{out_orig_stem}.txt", class_ids, bboxes)

    if not AUGMENT_TRAIN or n_aug <= 0:
        return

    for i in range(n_aug):
        aug = transform(image=img, bboxes=bboxes, class_ids=class_ids)
        aug_img = aug["image"]
        aug_boxes = aug["bboxes"]
        aug_cls = aug["class_ids"]

        # 変換で箱が全部消えたらスキップ
        if len(aug_boxes) == 0:
            continue

        out_stem = f"{stem}_aug{i:04d}"
        cv2.imwrite(str(out_img_dir / f"{out_stem}{img_path.suffix}"), aug_img)
        write_yolo_label(out_lbl_dir / f"{out_stem}.txt", aug_cls, aug_boxes)


def main():
    in_img_dir = RAW_DIR / "images"
    in_lbl_dir = RAW_DIR / "labels"

    img_paths = list_raw_images(in_img_dir)
    if not img_paths:
        raise RuntimeError(f"No images in {in_img_dir}")

    # ============================================
    # 先に raw を train/val/test に分割する
    # ============================================
    # まず test を切り出し、残りを train/val に分ける（70/15/15）
    trainval_imgs, test_imgs = train_test_split(
        img_paths,
        test_size=0.15,
        random_state=SEED,
        shuffle=True,
    )

    train_imgs, val_imgs = train_test_split(
        trainval_imgs,
        test_size=0.1765,  # 0.1765 * 0.85 ≒ 0.15 → valも約15%にするため
        random_state=SEED,
        shuffle=True,
    )

    # split ディレクトリを作り直し
    ensure_clean_dir(SPLIT_DIR)
    for split_name in ["train", "val", "test"]:
        (SPLIT_DIR / f"images/{split_name}").mkdir(parents=True, exist_ok=True)
        (SPLIT_DIR / f"labels/{split_name}").mkdir(parents=True, exist_ok=True)

    # ============================================
    # val/test は 拡張しない
    # ============================================
    def copy_split(img_list: list[Path], split_name: str) -> None:
        out_img_dir = SPLIT_DIR / "images" / split_name
        out_lbl_dir = SPLIT_DIR / "labels" / split_name
        for img_p in tqdm(img_list, desc=f"copy raw -> {split_name}"):
            lbl_p = in_lbl_dir / f"{img_p.stem}.txt"
            copy_one_sample(img_p, lbl_p, out_img_dir, out_lbl_dir)

    copy_split(val_imgs, "val")
    copy_split(test_imgs, "test")

    # ============================================
    # train は元画像をコピーして、それに拡張を加える
    # ============================================
    train_out_img_dir = SPLIT_DIR / "images" / "train"
    train_out_lbl_dir = SPLIT_DIR / "labels" / "train"

    for img_p in tqdm(train_imgs, desc="augment -> train"):
        lbl_p = in_lbl_dir / f"{img_p.stem}.txt"
        augment_one_image_to_train(
            img_path=img_p,
            lbl_path=lbl_p,
            out_img_dir=train_out_img_dir,
            out_lbl_dir=train_out_lbl_dir,
            n_aug=N_AUG_PER_IMAGE,
        )

    # data.yaml(train/val/test を明示)
    data_yaml = {
        "path": str(SPLIT_DIR.resolve()),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": dict(enumerate(NAMES)),
    }
    DATA_YAML_PATH.write_text(
        yaml.safe_dump(data_yaml, sort_keys=False),
        encoding="utf-8",
    )

    print("done:")
    print(
        f"  train raw count: {len(train_imgs)} (aug per image: {N_AUG_PER_IMAGE if AUGMENT_TRAIN else 0})"
    )
    print(f"  val raw count:   {len(val_imgs)}")
    print(f"  test raw count:  {len(test_imgs)}")
    print(f"  wrote: {DATA_YAML_PATH}")


if __name__ == "__main__":
    main()
