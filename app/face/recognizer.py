import cv2
import numpy as np
import torch
import os
import base64
import tempfile

from pathlib import Path
from facenet_pytorch import InceptionResnetV1

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent.parent

SECRET_EMBEDDING = "/etc/secrets/reference_embeddings.b64"

CACHE_FILE = Path("/tmp/reference_embeddings.npz")

if os.path.isfile(SECRET_EMBEDDING):
    with open(SECRET_EMBEDDING, "rb") as f:
        encoded = f.read()

    CACHE_FILE.write_bytes(
        base64.b64decode(encoded)
    )
else:
    CACHE_FILE = (
        PROJECT_DIR
        / "embedding_baru"
        / "reference_embeddings.npz"
    )

# Threshold cosine similarity FaceNet
FACENET_THRESHOLD = 0.8

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)


# =========================================================
# VALIDASI FILE
# =========================================================

if not CACHE_FILE.is_file():
    raise SystemExit(
        f"File embedding tidak ditemukan:\n{CACHE_FILE}\n\n"
        "Jalankan 5.buat_embedding.py terlebih dahulu."
    )


# =========================================================
# LOAD MODEL FACENET
# =========================================================

print("Loading FaceNet...")

facenet = (
    InceptionResnetV1(
        pretrained="vggface2"
    )
    .eval()
    .to(DEVICE)
)

print("FaceNet loaded.")


# =========================================================
# LOAD REFERENCE EMBEDDINGS
# =========================================================

print("Loading reference embeddings...")

with np.load(
    CACHE_FILE,
    allow_pickle=False
) as data:

    FACENET_NAMES = data[
        "facenet_names"
    ].tolist()

    FACENET_VECTORS = np.asarray(
        data["facenet_vectors"],
        dtype=np.float32
    )

if len(FACENET_NAMES) == 0:
    raise SystemExit(
        "Tidak ada identitas di reference embeddings."
    )

if FACENET_VECTORS.ndim != 2:
    raise SystemExit(
        "Format FACENET_VECTORS tidak valid."
    )

if len(FACENET_NAMES) != len(FACENET_VECTORS):
    raise SystemExit(
        "Jumlah nama dan embedding tidak sesuai."
    )

if not np.isfinite(FACENET_VECTORS).all():
    raise SystemExit(
        "Embedding reference mengandung nilai tidak valid."
    )

# Pastikan seluruh template reference ternormalisasi.
norms = np.linalg.norm(
    FACENET_VECTORS,
    axis=1,
    keepdims=True
)

if np.any(norms < 1e-12):
    raise SystemExit(
        "Ada embedding reference dengan norm nol."
    )

FACENET_VECTORS = (
    FACENET_VECTORS / norms
).astype(np.float32)

print(
    f"Reference loaded: {len(FACENET_NAMES)} identitas"
)

print("Identitas:", FACENET_NAMES)
print("Device:", DEVICE)


# =========================================================
# NORMALIZE EMBEDDING
# =========================================================

def normalize_vector(vector):
    """
    Normalisasi L2 embedding.
    """

    vector = np.asarray(
        vector,
        dtype=np.float32
    ).reshape(-1)

    if vector.size == 0:
        raise ValueError(
            "Embedding kosong."
        )

    if not np.isfinite(vector).all():
        raise ValueError(
            "Embedding mengandung nilai tidak valid."
        )

    norm = float(
        np.linalg.norm(vector)
    )

    if norm < 1e-12:
        raise ValueError(
            "Norm embedding nol."
        )

    return vector / norm


# =========================================================
# FACENET EMBEDDING
# =========================================================

def get_facenet_embedding(face_bgr):
    """
    Menghasilkan embedding FaceNet dari crop wajah BGR.

    Input:
        face_bgr: gambar wajah dari OpenCV.

    Output:
        Vektor embedding FaceNet ternormalisasi.
    """

    if face_bgr is None or face_bgr.size == 0:
        raise ValueError(
            "Input crop wajah kosong."
        )

    # BGR ke RGB
    face_rgb = cv2.cvtColor(
        face_bgr,
        cv2.COLOR_BGR2RGB
    )

    # Resize menjadi 160x160
    face_rgb = cv2.resize(
        face_rgb,
        (160, 160),
        interpolation=cv2.INTER_AREA
    )

    # Normalisasi yang sesuai dengan preprocessing
    # FaceNet pada pipeline pembuatan embedding.
    face = face_rgb.astype(
        np.float32
    )

    face = (
        face - 127.5
    ) / 128.0

    # HWC menjadi CHW
    tensor = torch.from_numpy(
        face
    ).permute(
        2, 0, 1
    ).unsqueeze(0)

    tensor = tensor.to(DEVICE)

    with torch.no_grad():
        embedding = facenet(
            tensor
        )

    embedding = embedding.detach().cpu().numpy()[0]

    return normalize_vector(
        embedding
    )


# =========================================================
# COSINE SIMILARITY SEARCH
# =========================================================

def search_facenet(query_embedding):
    """
    Membandingkan embedding wajah dengan seluruh
    template reference menggunakan cosine similarity.
    """

    query_embedding = normalize_vector(
        query_embedding
    )

    if (
        query_embedding.shape[0]
        != FACENET_VECTORS.shape[1]
    ):
        raise ValueError(
            "Dimensi embedding wajah tidak sesuai "
            "dengan embedding reference."
        )

    # Karena query dan reference sudah ternormalisasi,
    # dot product menghasilkan cosine similarity.
    scores = np.dot(
        FACENET_VECTORS,
        query_embedding
    )

    best_index = int(
        np.argmax(scores)
    )

    best_score = float(
        scores[best_index]
    )

    best_name = FACENET_NAMES[
        best_index
    ]

    if best_score < FACENET_THRESHOLD:
        return "UNKNOWN", best_score

    return best_name, best_score


# =========================================================
# FACE RECOGNITION
# =========================================================

def recognize_face(face_bgr):
    """
    Pengenalan wajah menggunakan FaceNet saja.

    Input:
        face_bgr: crop wajah BGR.

    Output:
        Dictionary berisi nama dan similarity score.
    """

    try:
        embedding = get_facenet_embedding(
            face_bgr
        )

        name, score = search_facenet(
            embedding
        )

        return {
            "name": name,
            "facenet_name": name,
            "facenet_score": round(
                float(score),
                4
            )
        }

    except Exception as error:

        return {
            "name": "UNKNOWN",
            "facenet_name": "UNKNOWN",
            "facenet_score": 0.0,
            "error": str(error)
        }


# =========================================================
# TEST INFORMASI
# =========================================================

if __name__ == "__main__":

    print("\n========== FACENET READY ==========")
    print("Model       : FaceNet")
    print("Device      :", DEVICE)
    print("Identitas   :", len(FACENET_NAMES))
    print("Threshold   :", FACENET_THRESHOLD)
    print("Embedding   :", CACHE_FILE)
    print("===================================")