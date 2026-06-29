import cv2
import time
from pathlib import Path
from datetime import datetime

# =====================================================
# 攝影機連拍資料收集工具 ROI 版
# -----------------------------------------------------
# 操作方式：
#   0~5：切換目前要儲存的手勢類別
#   Space：開始 / 停止連拍
#   C：單張拍攝目前畫面
#   Q：離開
#
# 儲存位置：dataset_sorted/0 ~ dataset_sorted/5
# 只會儲存畫面中央綠色框框 ROI，不會儲存整張畫面
# =====================================================

DATASET_DIR = Path("dataset_sorted")
LABELS = ["0", "1", "2", "3", "4", "5"]

CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
ROI_SIZE = 360

# 連拍間隔，單位秒。0.20 秒約等於每秒 5 張
CAPTURE_INTERVAL = 0.20

# 圖片副檔名
IMAGE_EXT = ".jpg"


def ensure_folders():
    for label in LABELS:
        (DATASET_DIR / label).mkdir(parents=True, exist_ok=True)


def get_roi_rect(frame_width, frame_height):
    x = (frame_width - ROI_SIZE) // 2
    y = (frame_height - ROI_SIZE) // 2
    return x, y, ROI_SIZE, ROI_SIZE


def crop_roi(frame):
    h, w = frame.shape[:2]
    x, y, roi_w, roi_h = get_roi_rect(w, h)
    roi = frame[y:y + roi_h, x:x + roi_w]
    return roi


def count_existing_images(label):
    label_dir = DATASET_DIR / label
    count = 0
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp"]:
        count += len(list(label_dir.glob(ext)))
    return count


def save_roi(frame, label):
    roi = crop_roi(frame)

    label_dir = DATASET_DIR / label
    label_dir.mkdir(parents=True, exist_ok=True)

    index = count_existing_images(label) + 1
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = label_dir / f"roi_{label}_{timestamp}_{index:04d}{IMAGE_EXT}"

    cv2.imwrite(str(filename), roi)
    return filename


def draw_ui(frame, current_label, is_bursting, saved_count, last_saved_path):
    h, w = frame.shape[:2]
    x, y, roi_w, roi_h = get_roi_rect(w, h)

    # 半透明遮罩，讓 ROI 更明顯
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, y), (0, 0, 0), -1)
    cv2.rectangle(overlay, (0, y + roi_h), (w, h), (0, 0, 0), -1)
    cv2.rectangle(overlay, (0, y), (x, y + roi_h), (0, 0, 0), -1)
    cv2.rectangle(overlay, (x + roi_w, y), (w, y + roi_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.28, frame, 0.72, 0, frame)

    # ROI 綠框
    cv2.rectangle(frame, (x, y), (x + roi_w, y + roi_h), (0, 255, 80), 3)

    # 狀態文字背景
    top_bar_color = (30, 30, 30)
    cv2.rectangle(frame, (0, 0), (w, 86), top_bar_color, -1)

    status = "BURST ON" if is_bursting else "BURST OFF"
    status_color = (0, 255, 80) if is_bursting else (0, 180, 255)

    cv2.putText(
        frame,
        f"Label: {current_label} | {status} | Saved this run: {saved_count}",
        (18, 32),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        status_color,
        2,
        cv2.LINE_AA
    )

    cv2.putText(
        frame,
        "Keys: 0-5 label | SPACE start/stop | C single shot | Q quit",
        (18, 66),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (220, 220, 220),
        1,
        cv2.LINE_AA
    )

    cv2.putText(
        frame,
        "Put your hand inside the green box",
        (x + 35, y - 12),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.68,
        (0, 255, 80),
        2,
        cv2.LINE_AA
    )

    if last_saved_path:
        text = f"Last saved: {Path(last_saved_path).name}"
        cv2.rectangle(frame, (0, h - 42), (w, h), (0, 0, 0), -1)
        cv2.putText(
            frame,
            text,
            (18, h - 14),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 80),
            1,
            cv2.LINE_AA
        )

    return frame


def main():
    ensure_folders()

    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print("❌ 無法開啟攝影機。請確認攝影機沒有被其他程式占用。")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    current_label = "0"
    is_bursting = False
    last_capture_time = 0
    saved_count = 0
    last_saved_path = None

    print("✅ 攝影機已啟動")
    print("操作方式：")
    print("  0~5   ：切換儲存類別")
    print("  Space ：開始 / 停止連拍")
    print("  C     ：單張拍攝")
    print("  Q     ：離開")
    print()
    print(f"圖片會儲存在：{DATASET_DIR.resolve()}")

    while True:
        ret, frame = cap.read()

        if not ret:
            print("❌ 讀取攝影機畫面失敗")
            break

        # 鏡像，讓畫面跟使用者直覺一致
        frame = cv2.flip(frame, 1)

        now = time.time()

        if is_bursting and now - last_capture_time >= CAPTURE_INTERVAL:
            last_saved_path = save_roi(frame, current_label)
            saved_count += 1
            last_capture_time = now
            print(f"📸 已儲存：{last_saved_path}")

        display = frame.copy()
        display = draw_ui(display, current_label, is_bursting, saved_count, last_saved_path)

        cv2.imshow("ROI Burst Camera Capture", display)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q") or key == ord("Q"):
            break

        if key == ord(" "):
            is_bursting = not is_bursting
            last_capture_time = 0
            print("▶️ 開始連拍" if is_bursting else "⏸️ 停止連拍")

        if key == ord("c") or key == ord("C"):
            last_saved_path = save_roi(frame, current_label)
            saved_count += 1
            print(f"📸 單張儲存：{last_saved_path}")

        key_char = chr(key) if key != 255 else ""
        if key_char in LABELS:
            current_label = key_char
            is_bursting = False
            last_capture_time = 0
            print(f"✅ 已切換類別：{current_label}")

    cap.release()
    cv2.destroyAllWindows()
    print("✅ 已關閉攝影機")


if __name__ == "__main__":
    main()
