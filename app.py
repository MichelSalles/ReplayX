import hmac
import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, url_for
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from obsws_python import ReqClient

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "core", "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))


class Replay(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), unique=True, nullable=False)
    cloud_url = db.Column(db.String(1000), nullable=False)
    public_id = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(
            username=request.form["username"],
            password=request.form["password"]
        ).first()

        if user:
            login_user(user)
            return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    videos = Replay.query.order_by(Replay.uploaded_at.desc()).all()
    return render_template("dashboard.html", videos=videos)


@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


def salvar_replay_obs():
    obs = ReqClient(
        host=os.getenv("OBS_HOST", "localhost"),
        port=int(os.getenv("OBS_PORT", "4455")),
        password=os.getenv("OBS_PASSWORD", "")
    )
    obs.save_replay_buffer()


@app.post("/replay")
def replay():
    expected_token = os.getenv("REPLAY_TOKEN")
    supplied_token = request.headers.get("X-Replay-Token", "")

    if not expected_token:
        return jsonify({"erro": "REPLAY_TOKEN nao configurado no servidor."}), 503

    if not hmac.compare_digest(supplied_token, expected_token):
        return jsonify({"erro": "Nao autorizado."}), 401

    try:
        salvar_replay_obs()
    except Exception:
        app.logger.exception("Falha ao solicitar replay ao OBS.")
        return jsonify({"erro": "OBS indisponivel ou mal configurado."}), 503

    return jsonify({"mensagem": "Replay solicitado."})


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/teste")
def teste():
    return "OK"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
