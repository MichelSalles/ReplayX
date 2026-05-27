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
BRANDING_FOLDER = os.path.join(BASE_DIR, "instance", "branding")
VIDEO_EXTENSIONS = (".mp4", ".mkv")
DEFAULT_FFMPEG_PATH = os.path.abspath(
    os.path.join(BASE_DIR, "..", "..", "Ffmpeg", "bin", "ffmpeg.exe")
)
FONT_PATH = "C\\:/Windows/Fonts/arial.ttf"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
os.makedirs(BRANDING_FOLDER, exist_ok=True)

cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET"),
    secure=True
)

arquivos_em_processamento = set()
arquivos_concluidos = set()


def inicializar_banco():
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS capture_request (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL,
                status VARCHAR(20) NOT NULL,
                requested_at DATETIME NOT NULL,
                replay_filename VARCHAR(255)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS replay (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename VARCHAR(255) NOT NULL UNIQUE,
                cloud_url VARCHAR(1000) NOT NULL,
                public_id VARCHAR(255) NOT NULL,
                uploaded_at DATETIME NOT NULL,
                tenant_id INTEGER
            )
            """
        )

        replay_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(replay)")
        }
        if "tenant_id" not in replay_columns:
            connection.execute("ALTER TABLE replay ADD COLUMN tenant_id INTEGER")


def reservar_captura():
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        request_row = connection.execute(
            """
            SELECT c.id, c.tenant_id, t.watermark_text, t.logo_filename
            FROM capture_request c
            JOIN tenant t ON t.id = c.tenant_id
            WHERE c.status = 'pending'
            ORDER BY c.requested_at, c.id
            LIMIT 1
            """
        ).fetchone()

        if not request_row:
            return None

        connection.execute(
            "UPDATE capture_request SET status = 'processing' WHERE id = ?",
            (request_row["id"],)
        )
        return dict(request_row)


def finalizar_captura(capture_id, filename):
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            UPDATE capture_request
            SET status = 'completed', replay_filename = ?
            WHERE id = ?
            """,
            (filename, capture_id)
        )


def liberar_captura(capture_id):
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            "UPDATE capture_request SET status = 'pending' WHERE id = ?",
            (capture_id,)
        )


def registrar_upload(video_path, resultado, tenant_id):
    nome_video = os.path.basename(video_path)
    uploaded_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            INSERT INTO replay (filename, cloud_url, public_id, uploaded_at, tenant_id)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(filename) DO UPDATE SET
                cloud_url = excluded.cloud_url,
                public_id = excluded.public_id,
                uploaded_at = excluded.uploaded_at,
                tenant_id = excluded.tenant_id
            """,
            (
                nome_video,
                resultado["secure_url"],
                resultado["public_id"],
                uploaded_at,
                tenant_id
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
    executar_ffmpeg([
        ffmpeg_path, "-y", "-i", video_path, "-c", "copy",
        "-movflags", "+faststart", mp4_path
    ])
    os.remove(video_path)
    print(f"Remux concluido: {mp4_path}")
    return mp4_path


def executar_ffmpeg(command):
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        mensagem = error.stderr.strip().splitlines()[-1] if error.stderr else str(error)
        raise RuntimeError(f"FFmpeg falhou: {mensagem}") from error


def escapar_texto_ffmpeg(texto):
    return (
        texto.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
    )


def aplicar_branding(video_path, capture):
    watermark = (capture.get("watermark_text") or "").strip()
    logo_filename = capture.get("logo_filename")
    logo_path = os.path.join(BRANDING_FOLDER, logo_filename) if logo_filename else None
    tem_logo = bool(logo_path and os.path.isfile(logo_path))

    if not watermark and not tem_logo:
        return video_path

    ffmpeg_path = localizar_ffmpeg()
    if not ffmpeg_path:
        raise FileNotFoundError("FFmpeg nao encontrado para aplicar marca.")

    output_path = os.path.splitext(video_path)[0] + "_branded.mp4"
    arquivos_em_processamento.add(output_path)
    command = [ffmpeg_path, "-y", "-i", video_path]

    if tem_logo:
        command.extend(["-i", logo_path])

    filtros = []
    corrente = "[0:v]"

    if tem_logo:
        filtros.append("[1:v]scale=180:-1[brand]")
        filtros.append(f"{corrente}[brand]overlay=W-w-30:H-h-30[logo]")
        corrente = "[logo]"

    if watermark:
        texto = escapar_texto_ffmpeg(watermark)
        filtros.append(
            f"{corrente}drawtext=fontfile='{FONT_PATH}':text='{texto}':"
            "fontcolor=white:fontsize=28:box=1:boxcolor=black@0.55:"
            "boxborderw=10:x=w-tw-30:y=h-th-30[final]"
        )
        corrente = "[final]"

    command.extend([
        "-filter_complex", ";".join(filtros),
        "-map", corrente,
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-c:a", "copy",
        "-movflags", "+faststart",
        output_path
    ])

    try:
        executar_ffmpeg(command)
    except Exception:
        if os.path.exists(output_path):
            os.remove(output_path)
        raise

    print(f"Marca aplicada: {output_path}")
    return output_path


def upload_video(video_path, tenant_id):
    print("\nEnviando para Cloudinary...")
    resultado = cloudinary.uploader.upload_large(
        video_path,
        resource_type="video",
        folder=f"replays/{tenant_id}"
    )
    registrar_upload(video_path, resultado, tenant_id)
    print(f"Upload concluido: {os.path.basename(video_path)}")


def processar_replay(video_path):
    video_path = os.path.abspath(video_path)

    if video_path in arquivos_em_processamento or video_path in arquivos_concluidos:
        return

    if "_branded.mp4" in video_path.lower():
        return

    if not video_path.lower().endswith(VIDEO_EXTENSIONS) or not os.path.isfile(video_path):
        return

    capture = reservar_captura()
    if not capture:
        print(f"Replay sem solicitacao vinculada, aguardando: {video_path}")
        return

    arquivos_em_processamento.add(video_path)
    arquivo_final = video_path

    try:
        aguardar_arquivo_finalizado(video_path)

        if arquivo_final.lower().endswith(".mkv"):
            arquivo_final = remuxar_para_mp4(arquivo_final)

        arquivo_publicado = aplicar_branding(arquivo_final, capture)
        upload_video(arquivo_publicado, capture["tenant_id"])
        finalizar_captura(capture["id"], os.path.basename(arquivo_publicado))
        arquivos_concluidos.update({video_path, arquivo_final, arquivo_publicado})
    except Exception as error:
        liberar_captura(capture["id"])
        print(f"\nERRO ao processar {video_path}:")
        print(error)
    finally:
        arquivos_em_processamento.discard(video_path)
        arquivos_em_processamento.discard(arquivo_final)


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
        ultima_varredura = 0
        while True:
            time.sleep(1)
            if time.time() - ultima_varredura >= 10:
                processar_pendentes()
                ultima_varredura = time.time()
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
