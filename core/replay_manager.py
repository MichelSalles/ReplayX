import os
from datetime import datetime


class ReplayManager:

    def __init__(self):
        self.base_path = "uploads"

    def create_replay_folder(self):

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        replay_id = f"replay_{timestamp}"

        replay_path = os.path.join(self.base_path, replay_id)

        os.makedirs(replay_path, exist_ok=True)

        return replay_id, replay_path