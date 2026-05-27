import os

from dotenv import load_dotenv
from flask import Flask
from obsws_python import ReqClient

load_dotenv()

app = Flask(__name__)

# =========================
# CONEXAO OBS
# =========================

obs = ReqClient(
    host=os.getenv("OBS_HOST", "localhost"),
    port=int(os.getenv("OBS_PORT", "4455")),
    password=os.getenv("OBS_PASSWORD", "")
)

print("Conectado ao OBS!")

# =========================
# ROTA REPLAY
# =========================

@app.route('/replay')

def replay():

    print("SALVANDO REPLAY!")

    obs.save_replay_buffer()

    return "Replay salvo!"

# =========================
# SERVIDOR
# =========================

app.run(host='0.0.0.0', port=5000)
