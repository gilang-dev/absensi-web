from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance
from torchvision.transforms import functional as TF
from torchvision.transforms import InterpolationMode

import csv
import shutil


# ==========================================
# KONFIGURASI
# ==========================================

INPUT_DIR = Path(
    r"C:\Users\Langss\Music\absensi_web\dataset_face_baru"
)

OUTPUT_DIR = Path(
    r"C:\Users\Langss\Music\absensi_web\dataset_face_augmented"
)

EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".webp"
}

JPEG_QUALITY = 95

JUMLAH_AUGMENTASI = 5


# ==========================================
# SIMPAN GAMBAR
# ==========================================

def save_image(image, path):
    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    image.convert("RGB").save(
        path,
        format="JPEG",
        quality=JPEG_QUALITY,
        optimize=True
    )


# ==========================================
# 5 VARIASI DARI 1 FOTO WAJAH
# ==========================================

def make_augmentations(image):

    variations = []

    # ------------------------------------------
    # 1. ROTASI -5 DERAJAT
    # ------------------------------------------

    variations.append((
        "rotate_-5",
        TF.rotate(
            image,
            angle=-5,
            interpolation=InterpolationMode.BILINEAR,
            fill=0
        )
    ))

    # ------------------------------------------
    # 2. ROTASI +5 DERAJAT
    # ------------------------------------------

    variations.append((
        "rotate_+5",
        TF.rotate(
            image,
            angle=5,
            interpolation=InterpolationMode.BILINEAR,
            fill=0
        )
    ))

    # ------------------------------------------
    # 3. PENCAHAYAAN LEBIH GELAP
    # ------------------------------------------

    variations.append((
        "brightness_0.85",
        ImageEnhance.Brightness(
            image
        ).enhance(0.85)
    ))

    # ------------------------------------------
    # 4. PENCAHAYAAN LEBIH TERANG
    # ------------------------------------------

    variations.append((
        "brightness_1.15",
        ImageEnhance.Brightness(
            image
        ).enhance(1.15)
    ))

    # ------------------------------------------
    # 5. PERGESERAN HORIZONTAL
    # ------------------------------------------

    width, height = image.size

    dx = max(
        1,
        round(width * 0.02)
    )

    shifted = TF.affine(
        image,
        angle=0,
        translate=[dx, 0],
        scale=1.0,
        shear=[0.0, 0.0],
        interpolation=InterpolationMode.BILINEAR,
        fill=0
    )

    variations.append((
        "shift_right",
        shifted
    ))

    return variations


# ==========================================
# PROSES AUGMENTASI
# ==========================================

def main():

    # ------------------------------------------
    # VALIDASI FOLDER INPUT
    # ------------------------------------------

    if not INPUT_DIR.is_dir():

        raise FileNotFoundError(
            f"Folder input tidak ditemukan:\n{INPUT_DIR}"
        )

    if INPUT_DIR.resolve() == OUTPUT_DIR.resolve():

        raise ValueError(
            "Folder input dan output tidak boleh sama."
        )

    # ------------------------------------------
    # BACA FOLDER IDENTITAS
    # ------------------------------------------

    identities = sorted(
        folder
        for folder in INPUT_DIR.iterdir()
        if folder.is_dir()
    )

    if not identities:

        raise RuntimeError(
            "Folder identitas tidak ditemukan. "
            "Pastikan setiap mahasiswa memiliki folder sendiri."
        )

    # ------------------------------------------
    # PERINGATAN OUTPUT LAMA
    # ------------------------------------------

    if OUTPUT_DIR.exists():

        print("=" * 60)
        print("PERINGATAN")
        print("=" * 60)

        print(
            "Folder output berikut akan dihapus "
            "beserta seluruh isinya:"
        )

        print(OUTPUT_DIR)

        print(
            "\nPastikan folder tersebut hanya berisi "
            "hasil augmentasi yang boleh dihapus."
        )

        konfirmasi = input(
            "\nKetik HAPUS untuk melanjutkan: "
        ).strip()

        if konfirmasi != "HAPUS":

            print(
                "\nProses dibatalkan. "
                "Folder output lama tidak dihapus."
            )

            return

        shutil.rmtree(OUTPUT_DIR)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # ------------------------------------------
    # INISIALISASI LAPORAN
    # ------------------------------------------

    report = []

    total_original = 0
    total_augmented = 0
    total_failed = 0

    print("\n" + "=" * 60)
    print("AUGMENTASI DATASET WAJAH")
    print("=" * 60)

    print(f"Folder input  : {INPUT_DIR}")
    print(f"Folder output : {OUTPUT_DIR}")
    print(f"Variasi       : {JUMLAH_AUGMENTASI}")
    print("Total per foto: 1 asli + 5 augmentasi")
    print()

    # ==========================================
    # PROSES SETIAP IDENTITAS
    # ==========================================

    for identity_dir in identities:

        identity = identity_dir.name

        files = sorted(
            path
            for path in identity_dir.rglob("*")
            if path.is_file()
            and path.suffix.lower() in EXTENSIONS
        )

        out_dir = OUTPUT_DIR / identity

        out_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        saved_identity = 0
        augmented_identity = 0
        failed_identity = 0

        print("-" * 60)
        print(f"IDENTITAS: {identity}")
        print(f"Jumlah foto input: {len(files)}")
        print("-" * 60)

        if not files:

            print("Tidak ada gambar pada folder ini.")
            continue

        # ======================================
        # PROSES SETIAP FOTO
        # ======================================

        for index, path in enumerate(files, start=1):

            try:

                # Buka gambar dan perbaiki orientasi EXIF
                with Image.open(path) as source:

                    image = ImageOps.exif_transpose(
                        source
                    ).convert("RGB").copy()

                # ----------------------------------
                # NAMA SUMBER
                # ----------------------------------

                source_id = path.relative_to(
                    identity_dir
                ).with_suffix("")

                source_id = "__".join(
                    source_id.parts
                )

                # ----------------------------------
                # SIMPAN FOTO ASLI
                # ----------------------------------

                original_path = (
                    out_dir /
                    f"{source_id}_original.jpg"
                )

                save_image(
                    image,
                    original_path
                )

                report.append([
                    identity,
                    str(path),
                    str(original_path),
                    "ORIGINAL",
                    "BERHASIL"
                ])

                total_original += 1
                saved_identity += 1

                # ----------------------------------
                # BUAT 5 AUGMENTASI
                # ----------------------------------

                variations = make_augmentations(
                    image
                )

                for suffix, augmented in variations:

                    output_path = (
                        out_dir /
                        f"{source_id}_{suffix}.jpg"
                    )

                    save_image(
                        augmented,
                        output_path
                    )

                    report.append([
                        identity,
                        str(path),
                        str(output_path),
                        suffix,
                        "BERHASIL"
                    ])

                    total_augmented += 1
                    augmented_identity += 1

                print(
                    f"[OK] {path.name} | "
                    f"{index}/{len(files)}"
                )

            except Exception as error:

                total_failed += 1
                failed_identity += 1

                report.append([
                    identity,
                    str(path),
                    "",
                    "ERROR",
                    str(error)
                ])

                print(
                    f"[GAGAL] {path}: {error}"
                )

        # ======================================
        # RINGKASAN IDENTITAS
        # ======================================

        print(
            f"\nRingkasan {identity}:"
        )

        print(
            f"Foto asli berhasil : {saved_identity}"
        )

        print(
            f"Augmentasi berhasil: {augmented_identity}"
        )

        print(
            f"Foto gagal         : {failed_identity}"
        )

        print(
            f"Total gambar       : "
            f"{saved_identity + augmented_identity}"
        )

    # ==========================================
    # SIMPAN LAPORAN CSV
    # ==========================================

    report_path = (
        OUTPUT_DIR / "laporan_augmentasi.csv"
    )

    with open(
        report_path,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "Identitas",
            "File_Input",
            "File_Output",
            "Jenis",
            "Status"
        ])

        writer.writerows(report)

    # ==========================================
    # LAPORAN AKHIR
    # ==========================================

    print("\n" + "=" * 60)
    print("PROSES AUGMENTASI SELESAI")
    print("=" * 60)

    print(
        f"Foto asli berhasil diproses : {total_original}"
    )

    print(
        f"Foto augmentasi berhasil    : {total_augmented}"
    )

    print(
        f"Foto gagal                  : {total_failed}"
    )

    print(
        f"Total gambar berhasil       : "
        f"{total_original + total_augmented}"
    )

    print(
        f"Output                      : {OUTPUT_DIR}"
    )

    print(
        f"Laporan                     : {report_path}"
    )

    print("=" * 60)


# ==========================================
# PROGRAM UTAMA
# ==========================================

if __name__ == "__main__":
    main()