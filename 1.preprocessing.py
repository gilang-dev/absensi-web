
from pathlib import Path
from PIL import Image, ImageOps
from facenet_pytorch import MTCNN
import csv
import re
import torch

# ============================================================
# KONFIGURASI FOLDER
# ============================================================

# Sesuaikan dengan lokasi dataset di komputer lu.
# Contoh struktur:
# dataset_pemilah/
# ├── Aimar/
# │   ├── Tanpa_Kacamata/
# │   │   ├── foto1.jpg
# │   │   └── foto2.jpg
# │   └── Pakai_Kacamata/
# ├── Andra/
# └── Gilang/

DATASET_DIR = Path(
    r"C:\Users\Langss\Music\absensi_web\dataset_pemilah"
)

OUTPUT_DIR = Path(
    r"C:\Users\Langss\Music\absensi_web\dataset_face_baru"
)

EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp"
}

IMAGE_SIZE = 160
MARGIN = 20
CONFIDENCE_MIN = 0.80
MARGIN_RATIO = 0.15

# True  = simpan semua wajah yang terdeteksi.
# False = simpan wajah dengan confidence tertinggi saja.
SAVE_ALL_FACES = True

# ============================================================
# VALIDASI FOLDER
# ============================================================

if not DATASET_DIR.exists():
    raise FileNotFoundError(
        f"Folder dataset tidak ditemukan:\n{DATASET_DIR}\n"
        "Periksa kembali lokasi folder dan nama akun Windows."
    )

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

device = "cuda" if torch.cuda.is_available() else "cpu"

print("=" * 60)
print("PREPROCESSING DATASET MENGGUNAKAN MTCNN")
print("=" * 60)
print(f"Input  : {DATASET_DIR}")
print(f"Output : {OUTPUT_DIR}")
print(f"Device : {device}")
print("=" * 60)

# ============================================================
# INISIALISASI MTCNN
# ============================================================

detector = MTCNN(
    image_size=IMAGE_SIZE,
    margin=MARGIN,
    keep_all=True,
    post_process=False,
    device=device
)

# ============================================================
# FUNGSI BANTU
# ============================================================

def safe_filename(name):
    """Membersihkan karakter yang tidak aman dalam nama file."""
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    return name.strip(" .") or "gambar"


def make_unique_path(path):
    """Mencegah file hasil menimpa file yang sudah ada."""
    if not path.exists():
        return path

    counter = 1

    while True:
        candidate = path.with_name(
            f"{path.stem}_{counter}{path.suffix}"
        )

        if not candidate.exists():
            return candidate

        counter += 1


def save_image(image, output_path):
    """Menyimpan gambar sebagai JPEG berkualitas tinggi."""
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = make_unique_path(output_path)

    image.convert("RGB").save(
        output_path,
        format="JPEG",
        quality=95
    )

    return output_path


def center_crop_square(image):
    """
    Fallback ketika wajah tidak terdeteksi.
    Memotong bagian tengah gambar menjadi persegi,
    kemudian mengubah ukurannya menjadi 160 x 160.
    """
    width, height = image.size
    side = min(width, height)

    left = (width - side) // 2
    top = (height - side) // 2

    cropped = image.crop((
        left,
        top,
        left + side,
        top + side
    ))

    return cropped.resize(
        (IMAGE_SIZE, IMAGE_SIZE),
        Image.Resampling.LANCZOS
    )


def crop_face(image, box):
    """
    Memotong wajah berdasarkan bounding box MTCNN,
    menambahkan margin 15%, lalu resize menjadi 160 x 160.
    """
    width, height = image.size

    x1, y1, x2, y2 = map(float, box)

    face_width = x2 - x1
    face_height = y2 - y1

    margin_x = face_width * MARGIN_RATIO
    margin_y = face_height * MARGIN_RATIO

    x1 = max(0, int(x1 - margin_x))
    y1 = max(0, int(y1 - margin_y))
    x2 = min(width, int(x2 + margin_x))
    y2 = min(height, int(y2 + margin_y))

    if x2 <= x1 or y2 <= y1:
        return None

    face = image.crop((x1, y1, x2, y2))

    return face.resize(
        (IMAGE_SIZE, IMAGE_SIZE),
        Image.Resampling.LANCZOS
    )


def build_output_name(person_dir, image_path, suffix):
    """
    Membuat nama output berdasarkan struktur relatif foto.

    Contoh:
    Aimar/Tanpa_Kacamata/foto1.jpg

    Menjadi:
    Tanpa_Kacamata__foto1__jpg_face_1.jpg
    """
    relative = image_path.relative_to(person_dir)

    parts = list(relative.parts)

    filename = Path(parts[-1])
    stem = filename.stem
    extension = filename.suffix.lower().lstrip(".")

    parts[-1] = f"{stem}__{extension}"

    base_name = "__".join(
        safe_filename(part)
        for part in parts
    )

    return f"{base_name}_{suffix}.jpg"


# ============================================================
# PENCARIAN FOLDER IDENTITAS
# ============================================================

person_folders = sorted(
    folder
    for folder in DATASET_DIR.iterdir()
    if folder.is_dir()
)

if not person_folders:
    raise RuntimeError(
        "Tidak ditemukan folder identitas di dalam DATASET_DIR."
    )

# ============================================================
# STATISTIK
# ============================================================

total_images = 0
saved_images = 0
detected_images = 0
no_face_images = 0
low_confidence_images = 0
error_images = 0

report_rows = []

# ============================================================
# PROSES DATASET
# ============================================================

for person_dir in person_folders:

    print("\n" + "=" * 60)
    print(f"IDENTITAS: {person_dir.name}")
    print("=" * 60)

    # Mencari seluruh gambar sampai ke subfolder terdalam.
    # Contoh: Aimar/Tanpa_Kacamata/foto1.jpg

    image_files = sorted(
        path
        for path in person_dir.rglob("*")
        if path.is_file()
        and path.suffix.lower() in EXTENSIONS
        and OUTPUT_DIR not in path.parents
    )

    person_output_dir = OUTPUT_DIR / person_dir.name
    person_output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    print(f"Total foto ditemukan: {len(image_files)}")

    for index, path in enumerate(image_files, start=1):

        total_images += 1

        print(
            f"\n[{index}/{len(image_files)}] "
            f"{path.relative_to(person_dir)}"
        )

        # Folder output mempertahankan struktur subfolder asli.
        relative_parent = path.relative_to(
            person_dir
        ).parent

        output_subdir = (
            person_output_dir / relative_parent
        )

        output_subdir.mkdir(
            parents=True,
            exist_ok=True
        )

        try:
            # ------------------------------------------------
            # 1. BACA GAMBAR
            # ------------------------------------------------

            with Image.open(path) as source:
                image = ImageOps.exif_transpose(
                    source
                ).convert("RGB")

            # ------------------------------------------------
            # 2. DETEKSI WAJAH MENGGUNAKAN MTCNN
            # ------------------------------------------------

            boxes, probs = detector.detect(image)

            detected_faces = []

            if boxes is not None and probs is not None:

                for box, probability in zip(boxes, probs):

                    if box is None or probability is None:
                        continue

                    confidence = float(probability)

                    if not all(
                        value is not None
                        for value in box
                    ):
                        continue

                    detected_faces.append(
                        (box, confidence)
                    )

            valid_faces = [
                (box, confidence)
                for box, confidence in detected_faces
                if confidence >= CONFIDENCE_MIN
            ]

            # ------------------------------------------------
            # 3. JIKA WAJAH TERDETEKSI
            # ------------------------------------------------

            if detected_faces:

                detected_images += 1

                if not valid_faces:
                    low_confidence_images += 1

                print(
                    f"Wajah terdeteksi: "
                    f"{len(detected_faces)}"
                )

                # Confidence rendah tetap diproses.
                # Semua wajah disimpan jika SAVE_ALL_FACES=True.

                if SAVE_ALL_FACES:
                    faces_to_save = detected_faces
                else:
                    faces_to_save = [
                        max(
                            detected_faces,
                            key=lambda item: item[1]
                        )
                    ]

                saved_for_this_photo = 0

                for face_index, (box, confidence) in enumerate(
                    faces_to_save,
                    start=1
                ):

                    face = crop_face(image, box)

                    if face is None:
                        print(
                            "Crop wajah gagal. "
                            "Mencoba fallback."
                        )
                        continue

                    output_name = build_output_name(
                        person_dir,
                        path,
                        f"face_{face_index}"
                    )

                    output_path = save_image(
                        face,
                        output_subdir / output_name
                    )

                    saved_images += 1
                    saved_for_this_photo += 1

                    print(
                        f"Tersimpan: {output_path.name} "
                        f"| Confidence: {confidence:.4f}"
                    )

                    report_rows.append({
                        "identitas": person_dir.name,
                        "file_asli": str(path),
                        "file_output": str(output_path),
                        "status": "WAJAH_TERDETEKSI",
                        "confidence": round(confidence, 4),
                        "jumlah_wajah": len(detected_faces)
                    })

                # Jika seluruh crop gagal, foto tetap disimpan.
                if saved_for_this_photo == 0:

                    fallback = center_crop_square(image)

                    output_name = build_output_name(
                        person_dir,
                        path,
                        "center_crop"
                    )

                    output_path = save_image(
                        fallback,
                        output_subdir / output_name
                    )

                    saved_images += 1

                    print(
                        f"Fallback tersimpan: {output_path.name}"
                    )

                    report_rows.append({
                        "identitas": person_dir.name,
                        "file_asli": str(path),
                        "file_output": str(output_path),
                        "status": "FALLBACK_CROP_GAGAL",
                        "confidence": "",
                        "jumlah_wajah": len(detected_faces)
                    })

            # ------------------------------------------------
            # 4. JIKA WAJAH TIDAK TERDETEKSI
            # ------------------------------------------------

            else:

                no_face_images += 1

                print(
                    "Wajah tidak terdeteksi. "
                    "Menggunakan center crop."
                )

                fallback = center_crop_square(image)

                output_name = build_output_name(
                    person_dir,
                    path,
                    "center_crop"
                )

                output_path = save_image(
                    fallback,
                    output_subdir / output_name
                )

                saved_images += 1

                print(
                    f"Fallback tersimpan: {output_path.name}"
                )

                report_rows.append({
                    "identitas": person_dir.name,
                    "file_asli": str(path),
                    "file_output": str(output_path),
                    "status": "WAJAH_TIDAK_TERDETEKSI_FALLBACK",
                    "confidence": "",
                    "jumlah_wajah": 0
                })

        except Exception as error:

            error_images += 1

            print(f"Error saat memproses gambar: {error}")

            # ------------------------------------------------
            # 5. COBA FALLBACK JIKA TERJADI ERROR
            # ------------------------------------------------

            try:
                with Image.open(path) as source:
                    image = ImageOps.exif_transpose(
                        source
                    ).convert("RGB")

                fallback = center_crop_square(image)

                output_name = build_output_name(
                    person_dir,
                    path,
                    "error_fallback"
                )

                output_path = save_image(
                    fallback,
                    output_subdir / output_name
                )

                saved_images += 1

                print(
                    f"Fallback error tersimpan: "
                    f"{output_path.name}"
                )

                report_rows.append({
                    "identitas": person_dir.name,
                    "file_asli": str(path),
                    "file_output": str(output_path),
                    "status": f"ERROR_TAPI_TERSIMPAN: {error}",
                    "confidence": "",
                    "jumlah_wajah": 0
                })

            except Exception as fallback_error:

                print(
                    f"Gagal menyimpan gambar: {fallback_error}"
                )

                report_rows.append({
                    "identitas": person_dir.name,
                    "file_asli": str(path),
                    "file_output": "",
                    "status": f"GAGAL_TOTAL: {fallback_error}",
                    "confidence": "",
                    "jumlah_wajah": 0
                })

# ============================================================
# SIMPAN LAPORAN CSV
# ============================================================

report_path = OUTPUT_DIR / "laporan_preprocessing.csv"

with open(
    report_path,
    "w",
    newline="",
    encoding="utf-8-sig"
) as csvfile:

    fieldnames = [
        "identitas",
        "file_asli",
        "file_output",
        "status",
        "confidence",
        "jumlah_wajah"
    ]

    writer = csv.DictWriter(
        csvfile,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(report_rows)

# ============================================================
# HASIL AKHIR
# ============================================================

print("\n")
print("=" * 60)
print("PREPROCESSING SELESAI")
print("=" * 60)

print(f"Total foto input               : {total_images}")
print(f"Foto dengan wajah terdeteksi   : {detected_images}")
print(f"Foto tanpa wajah terdeteksi    : {no_face_images}")
print(f"Foto confidence rendah         : {low_confidence_images}")
print(f"Foto yang mengalami error      : {error_images}")
print(f"Total gambar hasil tersimpan   : {saved_images}")

print(f"\nFolder output:")
print(OUTPUT_DIR)

print(f"\nLaporan CSV:")
print(report_path)

print("=" * 60)