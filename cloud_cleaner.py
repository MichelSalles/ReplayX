import os
import sqlite3
import time
from datetime import datetime, timezone

import cloudinary
import cloudinary.api
import cloudinary.uploader
from dateutil import parser
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "instance", "database.db")
DIAS = 7

cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET"),
    secure=True
)


def remover_registro(public_id):
    if not os.path.isfile(DATABASE_PATH):
        return

    try:
        with sqlite3.connect(DATABASE_PATH) as conexao:
            conexao.execute("DELETE FROM replay WHERE public_id = ?", (public_id,))
    except sqlite3.OperationalError:
        return


def limpar_cloudinary():
    cursor = None
    agora = datetime.now(timezone.utc)

    while True:
        parametros = {
            "type": "upload",
            "resource_type": "video",
            "prefix": "replays/",
            "max_results": 100
        }

        if cursor:
            parametros["next_cursor"] = cursor

        recursos = cloudinary.api.resources(**parametros)

        for recurso in recursos["resources"]:
            criado = parser.parse(recurso["created_at"])

            if (agora - criado).days >= DIAS:
                public_id = recurso["public_id"]
                print(f"APAGANDO: {public_id}")
                cloudinary.uploader.destroy(public_id, resource_type="video")
                remover_registro(public_id)
                print("REMOVIDO")

        cursor = recursos.get("next_cursor")
        if not cursor:
            break


if __name__ == "__main__":
    print("LIMPEZA CLOUDINARY ATIVA...")

    while True:
        limpar_cloudinary()
        time.sleep(3600)
