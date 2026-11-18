
from pathlib import Path
import shutil

# =========================================
# KONFIGURASI FOLDER
# =========================================

BASE_DIR = Path(r"C:\Users\Langss\Music\absensi_web")

DATASET_BARU = BASE_DIR / "dataset_face_baru"
DATASET_MENTAH = BASE_DIR / "dataset_mentah"
OUTPUT_DIR = BASE_DIR / "dataset_face_new"

EKSTENSI_GAMBAR = {
    ".jpg", ".jpeg", ".png", ".jfif", ".webp"
}


# =========================================
# VALIDASI FOLDER
# =========================================

for folder in [DATASET_BARU, DATASET_MENTAH]:
    if not folder.is_dir():
        raise FileNotFoundError(
            f"Folder tidak ditemukan: {folder}"
        )

if OUTPUT_DIR.exists():
    raise FileExistsError(
        f"Folder output sudah ada: {OUTPUT_DIR}\n"
        "Ganti nama atau pindahkan folder output lama terlebih dahulu."
    )


# =========================================
# PROSES PERBANDINGAN
# =========================================

OUTPUT_DIR.mkdir(parents=True)

total_diperiksa = 0
total_sama = 0
total_baru = 0

for folder_mahasiswa in sorted(DATASET_MENTAH.iterdir()):

    if not folder_mahasiswa.is_dir():
        continue

    nama_mahasiswa = folder_mahasiswa.name

    # Folder mahasiswa di dataset pembanding
    folder_pembanding = next(
        (
            folder for folder in DATASET_BARU.iterdir()
            if folder.is_dir()
            and folder.name.casefold() == nama_mahasiswa.casefold()
        ),
        None
    )

    # Ambil nama file yang sudah ada di dataset_baru
    nama_file_lama = set()

    if folder_pembanding:
        nama_file_lama = {
            file.name.casefold()
            for file in folder_pembanding.iterdir()
            if file.is_file()
            and file.suffix.lower() in EKSTENSI_GAMBAR
        }

    # Siapkan folder mahasiswa di output
    folder_output = OUTPUT_DIR / nama_mahasiswa

    foto_diperiksa = 0
    foto_sama = 0
    foto_baru = 0

    for foto in folder_mahasiswa.iterdir():

        if not foto.is_file():
            continue

        if foto.suffix.lower() not in EKSTENSI_GAMBAR:
            continue

        total_diperiksa += 1
        foto_diperiksa += 1

        # Nama file sudah ada di dataset_baru?
        if foto.name.casefold() in nama_file_lama:
            total_sama += 1
            foto_sama += 1
            continue

        # Kalau belum ada, masukkan ke folder output
        folder_output.mkdir(parents=True, exist_ok=True)

        shutil.copy2(
            foto,
            folder_output / foto.name
        )

        total_baru += 1
        foto_baru += 1

    print(f"\nMahasiswa: {nama_mahasiswa}")
    print(f"  Foto diperiksa : {foto_diperiksa}")
    print(f"  Nama sudah ada : {foto_sama}")
    print(f"  Foto baru      : {foto_baru}")


# =========================================
# RINGKASAN
# =========================================

print("\n" + "=" * 50)
print("HASIL PEMBANDINGAN DATASET")
print("=" * 50)

print(f"Total foto diperiksa : {total_diperiksa}")
print(f"Nama file sudah ada  : {total_sama}")
print(f"Foto baru disalin    : {total_baru}")
print(f"Folder hasil         : {OUTPUT_DIR}")

print("\nSelesai!")