
from pathlib import Path
import csv
import shutil

import numpy as np
import torch
from PIL import Image, ImageOps
from facenet_pytorch import MTCNN, InceptionResnetV1
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix,
)

# ==========================================
# KONFIGURASI
# ==========================================

BASE = Path(r"C:\Users\Langss\Music\absensi_web")

REGISTERED_DIR = BASE / "dataset_pengujian" / "terdaftar"
UNKNOWN_DIR = BASE / "dataset_pengujian" / "tidak_terdaftar"

EMBED_FILE = BASE / "embedding_baru" / "reference_embeddings.npz"
OUTPUT_DIR = BASE / "hasil_metrik"

THRESHOLD = 0.7
MIN_FACE_CONFIDENCE = 0.8

VALID_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp"
}

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

# Folder output
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LOW_DIR = OUTPUT_DIR / "similarity_di_bawah_080"
HIGH_DIR = OUTPUT_DIR / "similarity_080_ke_atas"

LOW_DIR.mkdir(parents=True, exist_ok=True)
HIGH_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# VALIDASI PATH DAN DATA
# ==========================================

for folder in (REGISTERED_DIR, UNKNOWN_DIR):
    if not folder.is_dir():
        raise FileNotFoundError(
            f"Folder tidak ditemukan: {folder}"
        )

if not EMBED_FILE.is_file():
    raise FileNotFoundError(
        f"File embedding tidak ditemukan: {EMBED_FILE}"
    )

print("=" * 60)
print("PENGUJIAN FACENET + MTCNN")
print("=" * 60)
print("Device:", DEVICE)
print("Threshold similarity:", THRESHOLD)

# ==========================================
# LOAD EMBEDDING REFERENSI
# ==========================================

print("\nMemuat embedding referensi...")

with np.load(EMBED_FILE, allow_pickle=False) as data:
    names = data["facenet_names"].astype(str)
    reference_vectors = data["facenet_vectors"].astype(
        np.float32
    )

if len(names) == 0 or len(reference_vectors) == 0:
    raise ValueError("Embedding referensi kosong.")

if len(names) != len(reference_vectors):
    raise ValueError(
        "Jumlah nama dan embedding referensi tidak sama."
    )

norms = np.linalg.norm(
    reference_vectors, axis=1, keepdims=True
)

if np.any(norms < 1e-10):
    raise ValueError(
        "Ada embedding referensi dengan nilai norm nol."
    )

reference_vectors = reference_vectors / norms

print("Identitas terdaftar:", sorted(set(names.tolist())))


# ==========================================
# LOAD MTCNN DAN FACENET
# ==========================================

print("\nMemuat model MTCNN dan FaceNet...")

detector = MTCNN(
    keep_all=True,
    device=DEVICE,
    post_process=False
)

model = InceptionResnetV1(
    pretrained="vggface2"
).eval().to(DEVICE)


# ==========================================
# EKSTRAK EMBEDDING
# ==========================================

def extract_embedding(image_path):
    try:
        with Image.open(image_path) as source:
            image = ImageOps.exif_transpose(
                source
            ).convert("RGB")

        boxes, probabilities = detector.detect(image)

        if boxes is None or probabilities is None:
            return None, "Wajah tidak terdeteksi"

        valid_faces = [
            i
            for i, probability in enumerate(probabilities)
            if probability is not None
            and np.isfinite(probability)
            and probability >= MIN_FACE_CONFIDENCE
        ]

        if not valid_faces:
            return None, "Confidence deteksi wajah terlalu rendah"

        # Pilih wajah terbesar jika terdapat beberapa wajah
        def face_area(index):
            x1, y1, x2, y2 = boxes[index]
            return max(0, x2 - x1) * max(0, y2 - y1)

        best_index = max(valid_faces, key=face_area)

        x1, y1, x2, y2 = boxes[best_index]
        width, height = image.size

        # Margin 15%
        margin_x = (x2 - x1) * 0.15
        margin_y = (y2 - y1) * 0.15

        x1 = max(0, int(x1 - margin_x))
        y1 = max(0, int(y1 - margin_y))
        x2 = min(width, int(x2 + margin_x))
        y2 = min(height, int(y2 + margin_y))

        if x2 <= x1 or y2 <= y1:
            return None, "Area wajah tidak valid"

        face = image.crop(
            (x1, y1, x2, y2)
        ).resize((160, 160))

        face_array = np.asarray(
            face, dtype=np.float32
        )

        # Normalisasi FaceNet
        face_array = (face_array - 127.5) / 128.0

        tensor = torch.from_numpy(face_array)
        tensor = tensor.permute(2, 0, 1).unsqueeze(0)
        tensor = tensor.to(DEVICE)

        with torch.no_grad():
            embedding = model(tensor).cpu().numpy()[0]

        norm = np.linalg.norm(embedding)

        if not np.isfinite(norm) or norm < 1e-10:
            return None, "Embedding tidak valid"

        embedding = embedding / norm

        return embedding, "OK"

    except Exception as error:
        return None, f"Error: {error}"


# ==========================================
# PREDIKSI IDENTITAS
# ==========================================

def predict_identity(embedding):
    similarities = reference_vectors @ embedding

    best_index = int(np.argmax(similarities))
    best_score = float(similarities[best_index])

    if best_score >= THRESHOLD:
        predicted_name = names[best_index]
    else:
        predicted_name = "UNKNOWN"

    return predicted_name, best_score


# ==========================================
# KUMPULKAN FILE PENGUJIAN
# ==========================================

known_files = sorted(
    path
    for path in REGISTERED_DIR.rglob("*")
    if path.is_file()
    and path.suffix.lower() in VALID_EXTENSIONS
)

unknown_files = sorted(
    path
    for path in UNKNOWN_DIR.rglob("*")
    if path.is_file()
    and path.suffix.lower() in VALID_EXTENSIONS
)

print(f"\nFoto terdaftar ditemukan: {len(known_files)}")
print(f"Foto orang asing ditemukan: {len(unknown_files)}")

results = []
skipped = []


# ==========================================
# UJI FOTO MAHASISWA TERDAFTAR
# ==========================================

print("\nMemproses foto mahasiswa terdaftar...")

for image_path in known_files:
    relative = image_path.relative_to(REGISTERED_DIR)
    actual_name = relative.parts[0]

    embedding, status = extract_embedding(image_path)

    if embedding is None:
        skipped.append({
            "file": str(image_path),
            "kategori": "TERDAFTAR",
            "alasan": status
        })

        print(f"[LEWATI] {image_path.name}: {status}")
        continue

    predicted, score = predict_identity(embedding)

    result = {
        "file": str(image_path),
        "kategori": "TERDAFTAR",
        "aktual": actual_name,
        "prediksi": predicted,
        "similarity": score,
        "diterima": predicted != "UNKNOWN",
        "benar": predicted == actual_name
    }

    results.append(result)

    print(
        f"[TERDAFTAR] {image_path.name} | "
        f"Asli={actual_name} | "
        f"Prediksi={predicted} | "
        f"Similarity={score:.4f}"
    )


# ==========================================
# UJI FOTO ORANG TIDAK TERDAFTAR
# ==========================================

print("\nMemproses foto orang tidak terdaftar...")

for image_path in unknown_files:
    embedding, status = extract_embedding(image_path)

    if embedding is None:
        skipped.append({
            "file": str(image_path),
            "kategori": "TIDAK_TERDAFTAR",
            "alasan": status
        })

        print(f"[LEWATI] {image_path.name}: {status}")
        continue

    predicted, score = predict_identity(embedding)
    accepted = predicted != "UNKNOWN"

    results.append({
        "file": str(image_path),
        "kategori": "TIDAK_TERDAFTAR",
        "aktual": "UNKNOWN",
        "prediksi": predicted,
        "similarity": score,
        "diterima": accepted,
        "benar": not accepted
    })

    status_prediksi = (
        "SALAH DITERIMA" if accepted else "DITOLAK"
    )

    print(
        f"[ASING] {image_path.name} | "
        f"Prediksi={predicted} | "
        f"Similarity={score:.4f} | "
        f"{status_prediksi}"
    )


# ==========================================
# PISAHKAN SALINAN FOTO TERDAFTAR
# BERDASARKAN SIMILARITY
# ==========================================

print("\nMemisahkan foto berdasarkan similarity...")

# Hapus salinan hasil proses sebelumnya saja agar tidak
# menyisakan file lama dari pengujian sebelumnya.
# Folder sumber dataset tidak disentuh.
for output_folder in (LOW_DIR, HIGH_DIR):
    for item in output_folder.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        elif item.is_file():
            item.unlink()

low_count = 0
high_count = 0

for result in results:
    if result["kategori"] != "TERDAFTAR":
        continue

    source = Path(result["file"])
    actual_name = result["aktual"]
    score = result["similarity"]

    if score < THRESHOLD:
        destination_folder = LOW_DIR / actual_name
        low_count += 1
    else:
        destination_folder = HIGH_DIR / actual_name
        high_count += 1

    destination_folder.mkdir(
        parents=True, exist_ok=True
    )

    destination = destination_folder / source.name

    # Hindari menimpa file jika ada nama yang sama
    if destination.exists():
        destination = destination_folder / (
            f"{source.stem}_{len(list(destination_folder.iterdir()))}"
            f"{source.suffix}"
        )

    shutil.copy2(source, destination)

print(f"Similarity < {THRESHOLD}: {low_count} foto")
print(f"Similarity >= {THRESHOLD}: {high_count} foto")
print("Folder similarity rendah:", LOW_DIR)
print("Folder similarity tinggi:", HIGH_DIR)


# ==========================================
# SIMPAN HASIL PREDIKSI KE CSV
# ==========================================

result_csv = OUTPUT_DIR / "hasil_prediksi.csv"

with open(
    result_csv,
    "w",
    newline="",
    encoding="utf-8-sig"
) as file:
    fieldnames = [
        "file",
        "kategori",
        "aktual",
        "prediksi",
        "similarity",
        "diterima",
        "benar"
    ]

    writer = csv.DictWriter(
        file, fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(results)


# ==========================================
# SIMPAN FOTO YANG DILEWATI
# ==========================================

skipped_csv = OUTPUT_DIR / "foto_dilewati.csv"

with open(
    skipped_csv,
    "w",
    newline="",
    encoding="utf-8-sig"
) as file:
    writer = csv.DictWriter(
        file,
        fieldnames=["file", "kategori", "alasan"]
    )

    writer.writeheader()
    writer.writerows(skipped)


# ==========================================
# F1-SCORE FOTO TERDAFTAR
# ==========================================

known_results = [
    result
    for result in results
    if result["kategori"] == "TERDAFTAR"
]

unknown_results = [
    result
    for result in results
    if result["kategori"] == "TIDAK_TERDAFTAR"
]

print("\n" + "=" * 60)
print("EVALUASI IDENTITAS - FOTO TERDAFTAR")
print("=" * 60)

if known_results:
    y_true = [result["aktual"] for result in known_results]
    y_pred = [result["prediksi"] for result in known_results]

    # Kelas identitas yang ada dalam data referensi
    labels = sorted(set(names.tolist()))

    accuracy = accuracy_score(y_true, y_pred)

    precision, recall, f1, _ = (
        precision_recall_fscore_support(
            y_true,
            y_pred,
            labels=labels,
            average="macro",
            zero_division=0
        )
    )

    print(f"Foto berhasil diuji: {len(known_results)}")
    print(f"Accuracy       : {accuracy:.4f}")
    print(f"Macro Precision: {precision:.4f}")
    print(f"Macro Recall   : {recall:.4f}")
    print(f"Macro F1-Score : {f1:.4f}")

    print("\nClassification Report:")
    report = classification_report(
        y_true,
        y_pred,
        labels=labels,
        zero_division=0
    )
    print(report)

    with open(
        OUTPUT_DIR / "classification_report.txt",
        "w",
        encoding="utf-8"
    ) as file:
        file.write(report)

    # Confusion matrix untuk identitas terdaftar.
    # UNKNOWN ditambahkan sebagai kolom prediksi.
    matrix_labels = labels + ["UNKNOWN"]

    matrix = confusion_matrix(
        y_true,
        y_pred,
        labels=matrix_labels
    )

    with open(
        OUTPUT_DIR / "confusion_matrix.csv",
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:
        writer = csv.writer(file)
        writer.writerow(["Aktual/Prediksi"] + matrix_labels)

        for label, row in zip(matrix_labels, matrix):
            writer.writerow([label] + row.tolist())

else:
    print("Tidak ada foto terdaftar yang berhasil diproses.")


# ==========================================
# FAR: ORANG ASING SALAH DITERIMA
# ==========================================

print("\n" + "=" * 60)
print("EVALUASI FAR")
print("=" * 60)

if unknown_results:
    false_accepts = sum(
        result["diterima"]
        for result in unknown_results
    )

    far = false_accepts / len(unknown_results)

    print(f"Foto asing diuji: {len(unknown_results)}")
    print(f"False Accepts: {false_accepts}")
    print(f"FAR: {far:.4%}")

else:
    print("FAR tidak dapat dihitung: tidak ada foto asing yang berhasil diproses.")


# ==========================================
# FRR: MAHASISWA TERDAFTAR SALAH DITOLAK
# ==========================================

print("\n" + "=" * 60)
print("EVALUASI FRR")
print("=" * 60)

if known_results:
    false_rejects = sum(
        not result["diterima"]
        for result in known_results
    )

    frr = false_rejects / len(known_results)

    print(f"Foto mahasiswa diuji: {len(known_results)}")
    print(f"False Rejects: {false_rejects}")
    print(f"FRR: {frr:.4%}")

else:
    print("FRR tidak dapat dihitung: tidak ada foto mahasiswa yang berhasil diproses.")


# ==========================================
# RINGKASAN AKHIR
# ==========================================

print("\n" + "=" * 60)
print("RINGKASAN PENGUJIAN")
print("=" * 60)

print(f"Threshold similarity : {THRESHOLD}")
print(f"Total berhasil       : {len(results)}")
print(f"Total dilewati       : {len(skipped)}")
print(f"Foto similarity rendah: {low_count}")
print(f"Foto similarity tinggi: {high_count}")

print("\nFile hasil:")
print("Prediksi       :", result_csv)
print("Foto dilewati  :", skipped_csv)
print("Laporan F1     :", OUTPUT_DIR / "classification_report.txt")
print("Confusion matrix:", OUTPUT_DIR / "confusion_matrix.csv")

print("\nFolder foto similarity rendah:")
print(LOW_DIR)

print("\nFolder foto similarity tinggi:")
print(HIGH_DIR)

print("\nPengujian selesai.")
