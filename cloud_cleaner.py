import os
import time
from datetime import datetime, timezone
from dateutil import parser

import cloudinary
import cloudinary.api
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

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
# CONFIG
# =========================

DIAS = 7

# =========================
# LIMPAR CLOUDINARY
# =========================

def limpar_cloudinary():

    recursos = cloudinary.api.resources(
        type="upload",
        resource_type="video",
        prefix="replays/"
    )

    agora = datetime.now(timezone.utc)

    for recurso in recursos["resources"]:

        criado = parser.parse(recurso["created_at"])

        idade = (agora - criado).days

        if idade >= DIAS:

            public_id = recurso["public_id"]

            print(f"APAGANDO: {public_id}")

            cloudinary.uploader.destroy(
                public_id,
                resource_type="video"
            )

            print("REMOVIDO")

# =========================
# LOOP
# =========================

print("LIMPEZA CLOUDINARY ATIVA...")

while True:

    limpar_cloudinary()

    # verifica a cada 1 hora
    time.sleep(3600)
