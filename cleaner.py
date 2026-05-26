import os
import time

# =========================
# CONFIG
# =========================

PASTA_UPLOADS = "uploads"
PASTA_THUMBS = "thumbnails"

# apagar após X dias
DIAS = 7

# converter dias em segundos
LIMITE = DIAS * 24 * 60 * 60

# =========================
# LIMPAR ARQUIVOS
# =========================

def limpar_pasta(pasta):

    agora = time.time()

    for arquivo in os.listdir(pasta):

        caminho = os.path.join(pasta, arquivo)

        if os.path.isfile(caminho):

            tempo_arquivo = os.path.getmtime(caminho)

            idade = agora - tempo_arquivo

            if idade > LIMITE:

                os.remove(caminho)

                print(f"APAGADO: {caminho}")

# =========================
# LOOP
# =========================

print("LIMPEZA AUTOMÁTICA ATIVA...")

while True:

    limpar_pasta(PASTA_UPLOADS)

    limpar_pasta(PASTA_THUMBS)

    # verifica a cada 1 hora
    time.sleep(3600)