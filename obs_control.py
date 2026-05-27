import os

from dotenv import load_dotenv
from obsws_python import ReqClient

load_dotenv()


def salvar_replay():
    client = ReqClient(
        host=os.getenv("OBS_HOST", "localhost"),
        port=int(os.getenv("OBS_PORT", "4455")),
        password=os.getenv("OBS_PASSWORD", "")
    )
    client.save_replay_buffer()
    print("REPLAY SALVO!")
