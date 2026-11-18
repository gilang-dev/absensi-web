
from pathlib import Path
from PIL import Image

# GANTI sesuai lokasi dataset baru lu
DATASET_DIR = Path(r"C:\Users\Langss\Music\absensi_web\dataset_pengujian\terdaftar")

EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".webp"
}

if not DATASET_DIR.exists():
    print(f"Folder tidak ditemukan: {DATASET_DIR}")
    raise SystemExit(1)

total = 0
rusak = []

print("=== AUDIT DATASET ABSENSI ===\n")

for person_dir in sorted(DATASET_DIR.iterdir()):
    if not person_dir.is_dir():
        continue

    files = [
        p for p in person_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in EXTENSIONS
    ]

    valid = 0

    for path in files:
        try:
            with Image.open(path) as img:
                img.verify()
            valid += 1
        except Exception:
            rusak.append(str(path))

    total += len(files)

    print(f"{person_dir.name}:")
    print(f"  Total foto : {len(files)}")
    print(f"  File valid : {valid}")
    print(f"  File rusak : {len(files) - valid}")

print(f"\nTOTAL FOTO: {total}")
print(f"TOTAL FILE RUSAK: {len(rusak)}")

if rusak:
    print("\n=== FILE RUSAK ===")
    for path in rusak:
        print(path)
