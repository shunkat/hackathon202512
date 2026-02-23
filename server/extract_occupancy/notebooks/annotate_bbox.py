from __future__ import annotations

import argparse
import cv2
from dataclasses import dataclass
from pathlib import Path


CLASS_NAMES = {
    0: "empty_seat",
    1: "occupied_seat",
}


@dataclass
class Box:
    cls: int
    x1: int
    y1: int
    x2: int
    y2: int

    def normalized_yolo(self, img_w: int, img_h: int) -> str:
        x1, x2 = sorted([self.x1, self.x2])
        y1, y2 = sorted([self.y1, self.y2])

        bw = max(0, x2 - x1)
        bh = max(0, y2 - y1)
        cx = x1 + bw / 2.0
        cy = y1 + bh / 2.0

        return f"{self.cls} {cx / img_w:.6f} {cy / img_h:.6f} {bw / img_w:.6f} {bh / img_h:.6f}"


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _resize_keep_aspect(img, max_side: int):
    h, w = img.shape[:2]
    if max(h, w) <= max_side:
        return img, 1.0  # scale=1.0 means no resize

    scale = max_side / float(max(h, w))
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized, scale


def _draw_hud(canvas, current_cls: int, n_boxes: int) -> None:
    hud = (
        f"class={current_cls}({CLASS_NAMES.get(current_cls, '?')})  boxes={n_boxes}  "
        "drag:draw  0-9:class  u:undo  c:clear  s:save  q/esc:quit"
    )
    cv2.putText(
        canvas,
        hud,
        (10, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2,
    )


def _draw_boxes(canvas, boxes_disp: list[Box]) -> None:
    for i, b in enumerate(boxes_disp):
        color = (0, 255, 0) if b.cls == 0 else (0, 0, 255)
        cv2.rectangle(canvas, (b.x1, b.y1), (b.x2, b.y2), color, 2)
        cv2.putText(
            canvas,
            f"{i}:{b.cls} {CLASS_NAMES.get(b.cls, '?')}",
            (b.x1, max(0, b.y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
        )


def annotate_image(
    image_path: Path,
    out_dir: Path,
    save_preview: bool,
    min_size: int,
    max_side: int,
    wait_ms: int,
) -> None:
    img_full = cv2.imread(str(image_path))
    if img_full is None:
        msg = f"Failed to read image: {image_path}"
        raise RuntimeError(msg)

    h_full, w_full = img_full.shape[:2]

    # 表示用に縮小(軽くする)
    img_disp, scale = _resize_keep_aspect(img_full, max_side=max_side)
    h_disp, w_disp = img_disp.shape[:2]

    # 表示上での座標 → 元画像に戻す用
    inv_scale = 1.0 / scale

    win = f"annotate_bbox - {image_path.name}"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, w_disp, h_disp)

    # box は「元画像座標」で保持する
    boxes_full: list[Box] = []
    current_cls = min(CLASS_NAMES.keys())

    # drag状態は「表示座標」で扱う
    drawing = False
    start: tuple[int, int] | None = None
    end: tuple[int, int] | None = None

    def disp_to_full(x: int, y: int) -> tuple[int, int]:
        # 表示座標 → 元画像座標
        xf = round(x * inv_scale)
        yf = round(y * inv_scale)
        xf = _clamp(xf, 0, w_full - 1)
        yf = _clamp(yf, 0, h_full - 1)
        return xf, yf

    def full_to_disp(x: int, y: int) -> tuple[int, int]:
        xd = round(x * scale)
        yd = round(y * scale)
        xd = _clamp(xd, 0, w_disp - 1)
        yd = _clamp(yd, 0, h_disp - 1)
        return xd, yd

    def on_mouse(event: int, x: int, y: int, flags: int, param: any) -> None:
        nonlocal drawing, start, end, boxes_full, current_cls

        x = _clamp(x, 0, w_disp - 1)
        y = _clamp(y, 0, h_disp - 1)

        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            start = (x, y)
            end = (x, y)

        elif event == cv2.EVENT_MOUSEMOVE and drawing:
            end = (x, y)

        elif event == cv2.EVENT_LBUTTONUP and drawing:
            drawing = False
            end = (x, y)

            if start and end:
                x1d, y1d = start
                x2d, y2d = end
                if abs(x2d - x1d) >= min_size and abs(y2d - y1d) >= min_size:
                    # 表示座標 → 元画像座標に戻して保存
                    x1f, y1f = disp_to_full(x1d, y1d)
                    x2f, y2f = disp_to_full(x2d, y2d)
                    boxes_full.append(Box(current_cls, x1f, y1f, x2f, y2f))

            start = None
            end = None

    cv2.setMouseCallback(win, on_mouse)

    while True:
        canvas = img_disp.copy()

        # 元画像座標の boxes を表示座標へ変換して描画
        boxes_disp = []
        for b in boxes_full:
            x1d, y1d = full_to_disp(b.x1, b.y1)
            x2d, y2d = full_to_disp(b.x2, b.y2)
            boxes_disp.append(Box(b.cls, x1d, y1d, x2d, y2d))

        _draw_boxes(canvas, boxes_disp)
        _draw_hud(canvas, current_cls, len(boxes_full))

        # drag中の矩形(表示座標)
        if drawing and start and end:
            cv2.rectangle(canvas, start, end, (255, 255, 0), 2)

        cv2.imshow(win, canvas)
        key = cv2.waitKey(wait_ms) & 0xFF  # wait_ms を小さくすると反応が良くなる

        if key in (27, ord("q")):
            break

        if ord("0") <= key <= ord("9"):
            k = int(chr(key))
            if k in CLASS_NAMES:
                current_cls = k
            continue

        if key == ord("u"):
            if boxes_full:
                boxes_full.pop()
            continue

        if key == ord("c"):
            boxes_full.clear()
            continue

        if key == ord("s"):
            out_dir.mkdir(parents=True, exist_ok=True)
            label_path = out_dir / f"{image_path.stem}.txt"
            lines = [b.normalized_yolo(w_full, h_full) for b in boxes_full]
            label_path.write_text(
                "\n".join(lines) + ("\n" if lines else ""),
                encoding="utf-8",
            )
            print(f"[saved] {label_path} (boxes={len(lines)})")

            if save_preview:
                prev_dir = out_dir / "_preview"
                prev_dir.mkdir(parents=True, exist_ok=True)
                prev_path = prev_dir / f"{image_path.stem}_preview.jpg"

                # 元画像に枠を描いたプレビューも保存
                prev = img_full.copy()
                for i, b in enumerate(boxes_full):
                    color = (0, 255, 0) if b.cls == 0 else (0, 0, 255)
                    cv2.rectangle(prev, (b.x1, b.y1), (b.x2, b.y2), color, 3)
                    cv2.putText(
                        prev,
                        f"{i}:{b.cls}",
                        (b.x1, max(0, b.y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.9,
                        color,
                        2,
                    )
                cv2.imwrite(str(prev_path), prev)
                print(f"[saved] {prev_path}")

    cv2.destroyWindow(win)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("image", type=str)
    p.add_argument("--out-dir", type=str, default="labels")
    p.add_argument("--save-preview", action="store_true")
    p.add_argument("--min-size", type=int, default=6)
    p.add_argument(
        "--max-side",
        type=int,
        default=1280,
        help="display max side length (downscale for responsiveness)",
    )
    p.add_argument(
        "--wait-ms",
        type=int,
        default=1,
        help="cv2.waitKey delay (smaller = more responsive)",
    )
    args = p.parse_args()

    annotate_image(
        image_path=Path(args.image),
        out_dir=Path(args.out_dir),
        save_preview=args.save_preview,
        min_size=args.min_size,
        max_side=args.max_side,
        wait_ms=args.wait_ms,
    )


if __name__ == "__main__":
    main()
