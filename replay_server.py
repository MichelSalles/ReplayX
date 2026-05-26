from flask import Flask
from obsws_python import ReqClient

app = Flask(__name__)

# =========================
# CONEXAO OBS
# =========================

obs = ReqClient(
    host='localhost',
    port=4455,
    password='123456'
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