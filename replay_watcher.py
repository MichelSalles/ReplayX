import os
import shutil
import subprocess
import time
import cv2
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "core", "uploads")
THUMBNAIL_FOLDER = os.path.join(BASE_DIR, "core", "thumbnails")
VIDEO_EXTENSIONS = (".mp4", ".mkv")
DEFAULT_FFMPEG_PATH = os.path.abspath(
    os.path.join(BASE_DIR, "..", "..", "Ffmpeg", "bin", "ffmpeg.exe")
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMBNAIL_FOLDER, exist_ok=True)

# =========================
# CLOUDINARY
# =========================

cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET"),
    secure=True
)

# =========================
# CONTROLE DUPLICADOS
# =========================

arquivos_processados = set()

# =========================
# REMUX MKV PARA MP4
# =========================

def localizar_ffmpeg():

    configured_path = os.getenv("FFMPEG_PATH")

    for caminho in (configured_path, DEFAULT_FFMPEG_PATH):

        if caminho and os.path.isfile(caminho):
            return caminho

    return shutil.which("ffmpeg")


def aguardar_arquivo_finalizado(video_path, timeout=60):

    tamanho_anterior = -1
    leituras_estaveis = 0
    limite = time.time() + timeout

    while time.time() < limite:

        tamanho_atual = os.path.getsize(video_path)

        if tamanho_atual == tamanho_anterior and tamanho_atual > 0:
            leituras_estaveis += 1

            if leituras_estaveis >= 2:
                return

        else:
            leituras_estaveis = 0

        tamanho_anterior = tamanho_atual
        time.sleep(1)

    raise TimeoutError("Tempo esgotado aguardando o OBS finalizar o replay.")


def remuxar_para_mp4(video_path):

    ffmpeg_path = localizar_ffmpeg()

    if not ffmpeg_path:
        raise FileNotFoundError(
            "FFmpeg nao encontrado. Configure FFMPEG_PATH ou coloque "
            "ffmpeg.exe em Ffmpeg\\bin."
        )

    mp4_path = os.path.splitext(video_path)[0] + ".mp4"
    arquivos_processados.add(mp4_path)

    try:

        subprocess.run(
            [
                ffmpeg_path,
                "-y",
                "-i",
                video_path,
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                mp4_path
            ],
            check=True,
            capture_output=True,
            text=True
        )

    except subprocess.CalledProcessError:

        if os.path.exists(mp4_path):
            os.remove(mp4_path)

        raise

    os.remove(video_path)

    print(f"Remux concluido: {mp4_path}")

    return mp4_path

# =========================
# GERAR THUMBNAIL
# =========================

def gerar_thumbnail(video_path):

    nome_video = os.path.basename(video_path)

    thumb_path = os.path.join(THUMBNAIL_FOLDER, f"{nome_video}.jpg")

    cap = cv2.VideoCapture(video_path)

    success, frame = cap.read()

    if success:

        cv2.imwrite(thumb_path, frame)

        print(f"Thumbnail criada: {thumb_path}")

    else:

        print("ERRO AO GERAR THUMBNAIL")

    cap.release()

# =========================
# UPLOAD CLOUDINARY
# =========================

def upload_video(video_path):

    print("\nEnviando para Cloudinary...")

    resultado = cloudinary.uploader.upload_large(

        video_path,

        resource_type="video",

        folder="replays"

    )

    print("\nUPLOAD CONCLUÍDO!")

    print("URL:")

    print(resultado["secure_url"])

# =========================
# WATCHDOG
# =========================

class ReplayHandler(FileSystemEventHandler):

    def on_created(self, event):

        if event.is_directory:
            return

        if not event.src_path.lower().endswith(VIDEO_EXTENSIONS):
            return

        if event.src_path in arquivos_processados:
            return

        arquivos_processados.add(event.src_path)

        print(f"\nNovo replay detectado:")
        print(event.src_path)

        # espera OBS terminar gravação
        try:

            aguardar_arquivo_finalizado(event.src_path)

            video_path = event.src_path

            if video_path.lower().endswith(".mkv"):
                video_path = remuxar_para_mp4(video_path)

            gerar_thumbnail(video_path)

            upload_video(video_path)

        except Exception as erro:

            print("\nERRO:")
            print(erro)

# =========================
# INICIAR WATCHDOG
# =========================

observer = Observer()

observer.schedule(

    ReplayHandler(),

    path=UPLOAD_FOLDER,

    recursive=False

)

observer.start()

print("WATCHDOG ATIVO...")

try:

    while True:
        time.sleep(1)

except KeyboardInterrupt:

    observer.stop()

observer.join()
