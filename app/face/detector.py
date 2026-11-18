import cv2
import numpy as np
from facenet_pytorch import MTCNN


ROI_WIDTH_RATIO = 0.55
ROI_HEIGHT_RATIO = 0.70
ROI_TOLERANCE = 10

MTCNN_FACE_THRESHOLD = 0.8


detector = MTCNN(
    image_size=160,
    margin=20,
    keep_all=True,
    post_process=False
)


def detect_face(image_bytes):

    # ========================================================
    # 1. BACA IMAGE
    # ========================================================

    image_array = np.frombuffer(
        image_bytes,
        dtype=np.uint8
    )

    image = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR
    )

    if image is None:

        return {
            "success": False,
            "message": "Gambar tidak bisa dibaca."
        }


    # ========================================================
    # 2. HITUNG ROI
    # ========================================================

    h, w = image.shape[:2]

    roi_width = int(
        w * ROI_WIDTH_RATIO
    )

    roi_height = int(
        h * ROI_HEIGHT_RATIO
    )

    roi_x1 = int(
        (w - roi_width) / 2
    )

    roi_y1 = int(
        (h - roi_height) / 2
    )

    roi_x2 = roi_x1 + roi_width
    roi_y2 = roi_y1 + roi_height


    # ========================================================
    # 3. MTCNN DETEKSI SEMUA WAJAH
    # ========================================================

    rgb = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2RGB
    )

    boxes, probs = detector.detect(rgb)


    if boxes is None or len(boxes) == 0:

        return {
            "success": False,
            "message": "Wajah tidak terdeteksi.",
            "roi": [
                roi_x1,
                roi_y1,
                roi_x2,
                roi_y2
            ]
        }


    # ========================================================
    # 4. FILTER CONFIDENCE + ROI
    # ========================================================

    valid_faces = []

    detected_faces = []

    for box, prob in zip(boxes, probs):

        if prob is None:
            continue

        if prob < MTCNN_FACE_THRESHOLD:
            continue


        x1, y1, x2, y2 = box

        x1 = int(x1)
        y1 = int(y1)
        x2 = int(x2)
        y2 = int(y2)

        detected_faces.append({
            "bbox": [
                x1,
                y1,
                x2,
                y2
            ],
            "confidence": float(prob)
        })


        # ====================================================
        # CEK APAKAH SELURUH WAJAH MASUK ROI
        # ====================================================

        inside_roi = (
            x1 >= roi_x1 - ROI_TOLERANCE
            and
            y1 >= roi_y1 - ROI_TOLERANCE
            and
            x2 <= roi_x2 + ROI_TOLERANCE
            and
            y2 <= roi_y2 + ROI_TOLERANCE
        )


        # Wajah di luar kotak → ABAIKAN
        if not inside_roi:
            continue


        # Wajah di dalam kotak → VALID
        valid_faces.append(
            (
                x1,
                y1,
                x2,
                y2,
                float(prob)
            )
        )


    # ========================================================
    # 5. TIDAK ADA WAJAH DI DALAM ROI
    # ========================================================

    if len(valid_faces) == 0:

        return {
            "success": False,
            "message": (
                "Wajah terdeteksi, "
                "tetapi posisikan seluruh wajah "
                "di dalam kotak."
            ),
            "roi": [
                roi_x1,
                roi_y1,
                roi_x2,
                roi_y2
            ],
            "detected_faces": detected_faces
        }


    # ========================================================
    # 6. LEBIH DARI SATU WAJAH DI DALAM ROI
    # ========================================================

    if len(valid_faces) > 1:

        return {
            "success": False,
            "message": (
                "Terdeteksi lebih dari satu wajah "
                "di dalam kotak."
            ),
            "roi": [
                roi_x1,
                roi_y1,
                roi_x2,
                roi_y2
            ],
            "detected_faces": detected_faces
        }


    # ========================================================
    # 7. TEPAT SATU WAJAH VALID
    # ========================================================

    x1, y1, x2, y2, confidence = valid_faces[0]


    return {
        "success": True,

        "bbox": [
            x1,
            y1,
            x2,
            y2
        ],

        "confidence": round(
            confidence,
            4
        ),

        "roi": [
            roi_x1,
            roi_y1,
            roi_x2,
            roi_y2
        ],

        "detected_faces": detected_faces
    }