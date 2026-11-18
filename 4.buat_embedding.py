
from pathlib import Path
import csv

import numpy as np
import torch

from PIL import Image, ImageOps
from facenet_pytorch import MTCNN, InceptionResnetV1


# ============================================================
# 1. KONFIGURASI
# ============================================================

BASE_DIR = Path(
    r"C:\Users\Langss\Music\absensi_web"
)

# Folder foto reference hasil split
REFERENCE_DIR = BASE_DIR / "dataset_split" / "Reference"

# Folder penyimpanan embedding
OUTPUT_DIR = BASE_DIR / "embedding_baru"

# File hasil embedding
OUTPUT_FILE = OUTPUT_DIR / "reference_embeddings.npz"

# File laporan foto gagal
ERROR_FILE = OUTPUT_DIR / "embedding_errors.csv"

# Format gambar yang didukung
EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp"
}

# Batas confidence deteksi wajah MTCNN
MIN_FACE_CONFIDENCE = 0.80

# Perangkat yang digunakan
DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)


# ============================================================
# 2. VALIDASI FOLDER
# ============================================================

if not REFERENCE_DIR.is_dir():
    raise SystemExit(
        f"\nFolder reference tidak ditemukan:\n"
        f"{REFERENCE_DIR}\n\n"
        "Pastikan struktur folder seperti berikut:\n"
        "dataset_split/\n"
        "└── Reference/\n"
        "    ├── Aimar/\n"
        "    ├── Andra/\n"
        "    └── Gilang/\n"
    )

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

people = sorted(
    folder
    for folder in REFERENCE_DIR.iterdir()
    if folder.is_dir()
)

if not people:
    raise SystemExit(
        f"Tidak ditemukan folder identitas di:\n"
        f"{REFERENCE_DIR}"
    )


# ============================================================
# 3. INFORMASI AWAL
# ============================================================

print("=" * 65)
print("PEMBUATAN EMBEDDING FACENET")
print("=" * 65)

print(f"Folder reference : {REFERENCE_DIR}")
print(f"Folder output    : {OUTPUT_DIR}")
print(f"File embedding   : {OUTPUT_FILE}")
print(f"Device           : {DEVICE}")

if DEVICE.type == "cuda":
    print(
        "GPU              :",
        torch.cuda.get_device_name(0)
    )

print("=" * 65)


# ============================================================
# 4. LOAD MTCNN
# ============================================================

print("\n[1/4] Memuat MTCNN...")

mtcnn = MTCNN(
    image_size=160,
    margin=20,
    keep_all=True,
    post_process=True,
    device=DEVICE
)

print("MTCNN berhasil dimuat.")


# ============================================================
# 5. LOAD FACENET
# ============================================================

print("\n[2/4] Memuat model FaceNet...")

facenet = InceptionResnetV1(
    pretrained="vggface2"
).eval().to(DEVICE)

print("FaceNet berhasil dimuat.")


# ============================================================
# 6. FUNGSI NORMALISASI EMBEDDING
# ============================================================

def normalize_embedding(vector):
    """
    Mengubah embedding menjadi vektor float32
    dengan normalisasi L2.
    """

    try:
        vector = np.asarray(
            vector,
            dtype=np.float32
        ).reshape(-1)

    except (TypeError, ValueError, OverflowError):
        return None

    if vector.size == 0:
        return None

    if not np.isfinite(vector).all():
        return None

    norm = float(np.linalg.norm(vector))

    if not np.isfinite(norm) or norm < 1e-12:
        return None

    return (vector / norm).astype(np.float32)


# ============================================================
# 7. FUNGSI EKSTRAKSI EMBEDDING FACENET
# ============================================================

def extract_facenet(rgb_image):
    """
    1. Mendeteksi wajah menggunakan MTCNN.
    2. Memilih wajah dengan area terbesar.
    3. Memotong wajah menggunakan MTCNN.
    4. Menghasilkan embedding menggunakan FaceNet.

    Jika tidak ditemukan wajah dengan confidence yang cukup,
    foto dicatat gagal dan tidak digunakan untuk embedding.
    """

    # --------------------------------------------------------
    # DETEKSI WAJAH
    # --------------------------------------------------------

    boxes, probabilities = mtcnn.detect(
        rgb_image
    )

    if boxes is None or probabilities is None:
        return None, "Wajah tidak terdeteksi"

    try:
        boxes = np.asarray(
            boxes,
            dtype=np.float32
        ).reshape(-1, 4)

        probabilities = np.asarray(
            probabilities,
            dtype=np.float32
        ).reshape(-1)

    except (TypeError, ValueError, OverflowError):
        return None, "Hasil deteksi MTCNN tidak valid"

    if len(boxes) != len(probabilities):
        return None, "Jumlah bounding box tidak sesuai"

    # --------------------------------------------------------
    # PILIH WAJAH VALID
    # --------------------------------------------------------

    candidates = []

    for index, (box, confidence) in enumerate(
        zip(boxes, probabilities)
    ):

        if not np.isfinite(box).all():
            continue

        if not np.isfinite(confidence):
            continue

        if confidence < MIN_FACE_CONFIDENCE:
            continue

        x1, y1, x2, y2 = box

        width = max(
            0.0,
            x2 - x1
        )

        height = max(
            0.0,
            y2 - y1
        )

        area = width * height

        if area <= 0:
            continue

        candidates.append(
            (index, area, float(confidence))
        )

    if not candidates:
        return None, "Confidence wajah di bawah batas"

    # Pilih wajah terbesar apabila terdeteksi beberapa wajah.
    best_index, _, best_confidence = max(
        candidates,
        key=lambda item: item[1]
    )

    selected_box = boxes[
        best_index:best_index + 1
    ]

    # --------------------------------------------------------
    # EKSTRAKSI CROP WAJAH MTCNN
    # --------------------------------------------------------

    try:
        face_tensor = mtcnn.extract(
            rgb_image,
            selected_box,
            None
        )

    except Exception as error:
        return None, f"Gagal crop wajah: {error}"

    if face_tensor is None:
        return None, "Crop wajah kosong"

    if face_tensor.ndim == 3:
        face_tensor = face_tensor.unsqueeze(0)

    face_tensor = face_tensor.to(DEVICE)

    # --------------------------------------------------------
    # EKSTRAKSI EMBEDDING FACENET
    # --------------------------------------------------------

    try:
        with torch.no_grad():
            output = facenet(
                face_tensor
            )

        vector = output[0].detach().cpu().numpy()

    except Exception as error:
        return None, f"Gagal ekstraksi FaceNet: {error}"

    vector = normalize_embedding(
        vector
    )

    if vector is None:
        return None, "Embedding FaceNet tidak valid"

    return vector, f"OK (confidence={best_confidence:.3f})"


# ============================================================
# 8. PROSES SEMUA IDENTITAS
# ============================================================

facenet_names = []
facenet_vectors = []

error_rows = []

total_images = 0
successful_images = 0
failed_images = 0

print("\n[3/4] Memproses dataset reference...")


for person_dir in people:

    person_name = person_dir.name

    # Ambil seluruh gambar, termasuk yang berada
    # dalam subfolder identitas.
    files = sorted(
        path
        for path in person_dir.rglob("*")
        if path.is_file()
        and path.suffix.lower() in EXTENSIONS
    )

    if not files:
        print(
            f"\n[LEWATI] {person_name}: "
            "tidak ada foto."
        )
        continue

    total_images += len(files)

    person_embeddings = []

    print(
        f"\nMemproses {person_name}: "
        f"{len(files)} foto"
    )

    for index, image_path in enumerate(
        files,
        start=1
    ):

        # ----------------------------------------------------
        # BACA FOTO
        # ----------------------------------------------------

        try:
            with Image.open(image_path) as source:
                rgb_image = ImageOps.exif_transpose(
                    source
                ).convert("RGB")

        except Exception as error:

            failed_images += 1

            error_rows.append([
                person_name,
                str(image_path),
                "Gagal membaca gambar: " + str(error)
            ])

            print(
                f"  [{index}/{len(files)}] "
                f"GAGAL BACA: {image_path.name}"
            )

            continue

        # ----------------------------------------------------
        # EKSTRAKSI FACENET
        # ----------------------------------------------------

        try:
            vector, status = extract_facenet(
                rgb_image
            )

        except Exception as error:

            vector = None
            status = (
                f"{type(error).__name__}: {error}"
            )

        if vector is not None:

            person_embeddings.append(
                vector
            )

            successful_images += 1

            print(
                f"  [{index}/{len(files)}] "
                f"OK: {image_path.name} | {status}"
            )

        else:

            failed_images += 1

            error_rows.append([
                person_name,
                str(image_path),
                status
            ])

            print(
                f"  [{index}/{len(files)}] "
                f"GAGAL: {image_path.name} | {status}"
            )

    # --------------------------------------------------------
    # RATA-RATA EMBEDDING SETIAP IDENTITAS
    # --------------------------------------------------------

    if not person_embeddings:

        print(
            f"\n[PERINGATAN] {person_name}: "
            "tidak memiliki embedding valid."
        )

        continue

    embeddings_array = np.stack(
        person_embeddings,
        axis=0
    ).astype(np.float32)

    mean_embedding = np.mean(
        embeddings_array,
        axis=0
    )

    mean_embedding = normalize_embedding(
        mean_embedding
    )

    if mean_embedding is None:

        print(
            f"[PERINGATAN] {person_name}: "
            "rata-rata embedding tidak valid."
        )

        continue

    facenet_names.append(
        person_name
    )

    facenet_vectors.append(
        mean_embedding
    )

    print(
        f"  TEMPLATE BERHASIL: {person_name}"
    )

    print(
        f"  Foto berhasil: {len(person_embeddings)}"
    )


# ============================================================
# 9. VALIDASI HASIL
# ============================================================

if not facenet_vectors:
    raise SystemExit(
        "\nTidak ada embedding FaceNet yang berhasil dibuat.\n"
        "Periksa dataset dan laporan error."
    )


# ============================================================
# 10. SIMPAN EMBEDDING
# ============================================================

print("\n[4/4] Menyimpan embedding...")

names_array = np.asarray(
    facenet_names,
    dtype=str
)

vectors_array = np.asarray(
    facenet_vectors,
    dtype=np.float32
)

np.savez_compressed(
    OUTPUT_FILE,
    facenet_names=names_array,
    facenet_vectors=vectors_array
)


# ============================================================
# 11. SIMPAN LAPORAN FOTO GAGAL
# ============================================================

with open(
    ERROR_FILE,
    "w",
    newline="",
    encoding="utf-8-sig"
) as file:

    writer = csv.writer(file)

    writer.writerow([
        "Identitas",
        "File",
        "Alasan"
    ])

    writer.writerows(
        error_rows
    )


# ============================================================
# 12. RINGKASAN
# ============================================================

print("\n" + "=" * 65)
print("PEMBUATAN EMBEDDING FACENET SELESAI")
print("=" * 65)

print(f"Device                  : {DEVICE}")
print(f"Total foto               : {total_images}")
print(f"Foto berhasil            : {successful_images}")
print(f"Foto gagal               : {failed_images}")
print(f"Jumlah identitas         : {len(facenet_names)}")

print(f"\nIdentitas:")
for name in facenet_names:
    print(f"  - {name}")

print(
    "\nUkuran embedding:",
    vectors_array.shape
)

print(f"\nFile embedding:")
print(OUTPUT_FILE)

print(f"\nLaporan error:")
print(ERROR_FILE)

print("=" * 65)