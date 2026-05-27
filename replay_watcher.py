import os
import shutil
import sqlite3
import subprocess
import time
from datetime import datetime, timezone

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "core", "uploads")
DATABASE_PATH = os.path.join(BASE_DIR, "instance", "database.db")
VIDEO_EXTENSIONS = (".mp4", ".mkv")
DEFAULT_FFMPEG_PATH = os.path.abspath(
    os.path.join(BASE_DIR, "..", "..", "Ffmpeg", "bin", "ffmpeg.exe")
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET"),
    secure=True
)

arquivos_em_processamento = set()
arquivos_concluidos = set()


def inicializar_banco():
    with sqlite3.connect(DATABASE_PATH) as conexao:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS replay (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename VARCHAR(255) NOT NULL UNIQUE,
                cloud_url VARCHAR(1000) NOT NULL,
                public_id VARCHAR(255) NOT NULL,
                uploaded_at DATETIME NOT NULL
            )
            """
        )


def registrar_upload(video_path, resultado):
    nome_video = os.path.basename(video_path)
    uploaded_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

    with sqlite3.connect(DATABASE_PATH) as conexao:
        conexao.execute(
            """
            INSERT INTO replay (filename, cloud_url, public_id, uploaded_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(filename) DO UPDATE SET
                cloud_url = excluded.cloud_url,
                public_id = excluded.public_id,
                uploaded_at = excluded.uploaded_at
            """,
            (
                nome_video,
                resultado["secure_url"],
                resultado["public_id"],
                uploaded_at
            )
        )


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


def upload_video(video_path):
    print("\nEnviando para Cloudinary...")
    resultado = cloudinary.uploader.upload_large(
        video_path,
        resource_type="video",
        folder="replays"
    )
    registrar_upload(video_path, resultado)
    print(f"Upload concluido: {os.path.basename(video_path)}")


def processar_replay(video_path):
    video_path = os.path.abspath(video_path)

    if video_path in arquivos_em_processamento or video_path in arquivos_concluidos:
        return

    if not video_path.lower().endswith(VIDEO_EXTENSIONS) or not os.path.isfile(video_path):
        return

    arquivos_em_processamento.add(video_path)

    try:
        aguardar_arquivo_finalizado(video_path)

        arquivo_final = video_path
        if arquivo_final.lower().endswith(".mkv"):
            arquivo_final = remuxar_para_mp4(arquivo_final)

        upload_video(arquivo_final)
        arquivos_concluidos.add(video_path)
        arquivos_concluidos.add(arquivo_final)
    except Exception as erro:
        print(f"\nERRO ao processar {video_path}:")
        print(erro)
    finally:
        arquivos_em_processamento.discard(video_path)


def processar_pendentes():
    for nome_video in sorted(os.listdir(UPLOAD_FOLDER)):
        processar_replay(os.path.join(UPLOAD_FOLDER, nome_video))


class ReplayHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            processar_replay(event.src_path)


if __name__ == "__main__":
    inicializar_banco()
    processar_pendentes()

    observer = Observer()
    observer.schedule(ReplayHandler(), path=UPLOAD_FOLDER, recursive=False)
    observer.start()
    print("WATCHDOG ATIVO...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
