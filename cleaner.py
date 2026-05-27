import os
import time

# =========================
# CONFIG
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_UPLOADS = os.path.join(BASE_DIR, "core", "uploads")

os.makedirs(PASTA_UPLOADS, exist_ok=True)

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

    # verifica a cada 1 hora
    time.sleep(3600)
