import os
from pathlib import Path

BASE_DIR = Path("dataset_pengujian")
VALID_EXTS = {".jpg", ".jpeg", ".png", ".jfif", ".webp"}


def cek_struktur_dataset(base_dir: Path):
    if not base_dir.exists():
        print(f"[ERROR] Folder '{base_dir}' tidak ditemukan!")
        return

    print(f"=== AUDIT STRUKTUR DATASET: {base_dir.resolve()} ===\n")

    subfolders = ["identitas", "terdaftar", "tidak_terdaftar"]
    data_map = {}

    for sub in subfolders:
        sub_path = base_dir / sub
        if not sub_path.exists():
            print(f"[WARNING] Subfolder '{sub}' tidak ditemukan!\n")
            continue

        print(f"📁 {sub}/")
        data_map[sub] = {}

        # Cek jika tidak_terdaftar berisi file langsung tanpa subfolder orang
        if sub == "tidak_terdaftar":
            direct_files = [
                f
                for f in sub_path.iterdir()
                if f.is_file() and f.suffix.lower() in VALID_EXTS
            ]
            sub_dirs = [d for d in sub_path.iterdir() if d.is_dir()]

            if direct_files:
                print(
                    f"   ├── [File Langsung] : {len(direct_files)} gambar valid"
                )
            for d in sorted(sub_dirs):
                imgs = [
                    f
                    for f in d.iterdir()
                    if f.is_file() and f.suffix.lower() in VALID_EXTS
                ]
                non_imgs = [
                    f
                    for f in d.iterdir()
                    if f.is_file() and f.suffix.lower() not in VALID_EXTS
                ]
                print(
                    f"   ├── {d.name:<15} : {len(imgs)} gambar"
                    + (
                        f" (⚠️ {len(non_imgs)} non-gambar)"
                        if non_imgs
                        else ""
                    )
                )
            print()
            continue

        # Untuk identitas/ dan terdaftar/ (berbasis folder nama orang)
        person_dirs = sorted([d for d in sub_path.iterdir() if d.is_dir()])
        if not person_dirs:
            print("   └── (Kosong - tidak ada folder kelas)\n")
            continue

        total_imgs = 0
        for p_dir in person_dirs:
            imgs = [
                f
                for f in p_dir.iterdir()
                if f.is_file() and f.suffix.lower() in VALID_EXTS
            ]
            non_imgs = [
                f
                for f in p_dir.iterdir()
                if f.is_file() and f.suffix.lower() not in VALID_EXTS
            ]

            data_map[sub][p_dir.name] = len(imgs)
            total_imgs += len(imgs)

            status = "✅" if len(imgs) > 0 else "❌ KOSONG"
            warn = (
                f" | ⚠️ {len(non_imgs)} file non-gambar" if non_imgs else ""
            )
            print(
                f"   ├── {p_dir.name:<15} : {len(imgs):>3} gambar {status}{warn}"
            )

        print(
            f"   └── TOTAL {sub}: {len(person_dirs)} orang, {total_imgs} gambar\n"
        )

    # Validasi Konsistensi Nama Folder antara 'identitas' dan 'terdaftar'
    if "identitas" in data_map and "terdaftar" in data_map:
        set_id = set(data_map["identitas"].keys())
        set_reg = set(data_map["terdaftar"].keys())

        print("=== VALIDASI KONSISTENSI KELAS (identitas vs terdaftar) ===")
        hanya_di_id = set_id - set_reg
        hanya_di_reg = set_reg - set_id

        if not hanya_di_id and not hanya_di_reg:
            print(
                "✅ Sinkron! Semua nama folder di 'identitas' dan 'terdaftar' cocok 100%."
            )
        else:
            if hanya_di_id:
                print(
                    f"⚠️ Ada di 'identitas', tapi HILANG di 'terdaftar' : {sorted(hanya_di_id)}"
                )
            if hanya_di_reg:
                print(
                    f"⚠️ Ada di 'terdaftar', tapi HILANG di 'identitas' : {sorted(hanya_di_reg)}"
                )


if __name__ == "__main__":
    cek_struktur_dataset(BASE_DIR)