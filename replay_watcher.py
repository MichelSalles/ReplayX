import os
import time
import cv2
import cloudinary
import cloudinary.uploader

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# =========================
# CLOUDINARY
# =========================

cloudinary.config(
    cloud_name="REMOVED_CLOUD_NAME",
    api_key="REMOVED_API_KEY",
    api_secret="REMOVED_API_SECRET",
    secure=True
)

# =========================
# CONTROLE DUPLICADOS
# =========================

arquivos_processados = set()

# =========================
# GERAR THUMBNAIL
# =========================

def gerar_thumbnail(video_path):

    nome_video = os.path.basename(video_path)

    thumb_path = f"thumbnails/{nome_video}.jpg"

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

        if not event.src_path.endswith(".mp4"):
            return

        if event.src_path in arquivos_processados:
            return

        arquivos_processados.add(event.src_path)

        print(f"\nNovo replay detectado:")
        print(event.src_path)

        # espera OBS terminar gravação
        time.sleep(5)

        try:

            gerar_thumbnail(event.src_path)

            upload_video(event.src_path)

        except Exception as erro:

            print("\nERRO:")
            print(erro)

# =========================
# INICIAR WATCHDOG
# =========================

observer = Observer()

observer.schedule(

    ReplayHandler(),

    path="uploads",

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