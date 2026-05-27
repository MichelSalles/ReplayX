import hmac
import os
import secrets
import sqlite3
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_from_directory, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from obsws_python import ReqClient
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "instance", "database.db")
BRANDING_FOLDER = os.path.join(BASE_DIR, "instance", "branding")
ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg"}

os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
os.makedirs(BRANDING_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


class Tenant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(160), nullable=False)
    replay_token = db.Column(db.String(120), unique=True, nullable=False)
    watermark_text = db.Column(db.String(120))
    logo_filename = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100))
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(20), nullable=False, default="viewer")
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenant.id"))
    tenant = db.relationship("Tenant", backref="users")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.password = None

    def check_password(self, password):
        return bool(self.password_hash) and check_password_hash(self.password_hash, password)

    @property
    def is_master(self):
        return self.role == "master"


class Replay(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), unique=True, nullable=False)
    cloud_url = db.Column(db.String(1000), nullable=False)
    public_id = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenant.id"))


class CaptureRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenant.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    requested_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    replay_filename = db.Column(db.String(255))


def migrate_database():
    with sqlite3.connect(DATABASE_PATH) as connection:
        columns = {
            table: {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
            for table in ("user", "replay")
        }

        for name, definition in (
            ("password_hash", "VARCHAR(255)"),
            ("role", "VARCHAR(20) DEFAULT 'viewer'"),
            ("tenant_id", "INTEGER")
        ):
            if name not in columns["user"]:
                connection.execute(f"ALTER TABLE user ADD COLUMN {name} {definition}")

        if "tenant_id" not in columns["replay"]:
            connection.execute("ALTER TABLE replay ADD COLUMN tenant_id INTEGER")

        connection.execute("UPDATE user SET password = NULL WHERE password IS NOT NULL")


with app.app_context():
    db.create_all()
    migrate_database()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def master_required(view):
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_master:
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)

    wrapped.__name__ = view.__name__
    return wrapped


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"].strip()).first()

        if user and user.tenant_id and user.check_password(request.form["password"]):
            login_user(user)
            return redirect(url_for("master_dashboard" if user.is_master else "dashboard"))

        flash("Usuario ou senha invalidos.", "error")

    return render_template("login.html")


@app.route("/contratar", methods=["GET", "POST"])
def contratar():
    if request.method == "POST":
        business_name = request.form["business_name"].strip()
        username = request.form["username"].strip()
        password = request.form["password"]

        if len(password) < 8:
            flash("Use uma senha com pelo menos 8 caracteres.", "error")
            return render_template("signup.html")

        if User.query.filter_by(username=username).first():
            flash("Este usuario ja existe.", "error")
            return render_template("signup.html")

        tenant = Tenant(
            business_name=business_name,
            replay_token=secrets.token_urlsafe(32)
        )
        master = User(username=username, role="master", tenant=tenant)
        master.set_password(password)
        db.session.add_all([tenant, master])
        db.session.commit()
        login_user(master)
        flash("Servico ativado. Configure o token no dispositivo ESP32.", "success")
        return redirect(url_for("master_dashboard"))

    return render_template("signup.html")


@app.route("/dashboard")
@login_required
def dashboard():
    videos = Replay.query.filter_by(tenant_id=current_user.tenant_id).order_by(Replay.uploaded_at.desc()).all()
    return render_template("dashboard.html", videos=videos)


@app.route("/media/<int:replay_id>")
@login_required
def replay_media(replay_id):
    video = db.session.get(Replay, replay_id)

    if not video or video.tenant_id != current_user.tenant_id:
        abort(404)

    local_path = os.path.join(os.path.join(BASE_DIR, "core", "uploads"), video.filename)
    if os.path.isfile(local_path):
        return send_from_directory(os.path.dirname(local_path), video.filename)

    return redirect(video.cloud_url)


@app.route("/master", methods=["GET", "POST"])
@master_required
def master_dashboard():
    if request.method == "POST":
        watermark_text = request.form.get("watermark_text", "").strip()[:120]
        logo = request.files.get("logo")
        current_user.tenant.watermark_text = watermark_text or None

        if logo and logo.filename:
            extension = os.path.splitext(secure_filename(logo.filename))[1].lower()
            if extension not in ALLOWED_LOGO_EXTENSIONS:
                flash("Envie um logo PNG ou JPG.", "error")
                return redirect(url_for("master_dashboard"))

            logo_filename = f"tenant_{current_user.tenant_id}_logo{extension}"
            logo.save(os.path.join(BRANDING_FOLDER, logo_filename))
            current_user.tenant.logo_filename = logo_filename

        db.session.commit()
        flash("Marca dos proximos replays atualizada.", "success")

    viewers = User.query.filter_by(tenant_id=current_user.tenant_id, role="viewer").order_by(User.username).all()
    return render_template("master.html", tenant=current_user.tenant, viewers=viewers)


@app.post("/master/usuarios")
@master_required
def create_viewer():
    username = request.form["username"].strip()
    password = request.form["password"]

    if len(password) < 8:
        flash("Use uma senha com pelo menos 8 caracteres.", "error")
    elif User.query.filter_by(username=username).first():
        flash("Este usuario ja existe.", "error")
    else:
        viewer = User(username=username, role="viewer", tenant_id=current_user.tenant_id)
        viewer.set_password(password)
        db.session.add(viewer)
        db.session.commit()
        flash("Usuario de acesso aos replays criado.", "success")

    return redirect(url_for("master_dashboard"))


@app.post("/master/token")
@master_required
def rotate_token():
    current_user.tenant.replay_token = secrets.token_urlsafe(32)
    db.session.commit()
    flash("Token renovado. Atualize o ESP32 antes de usar o botao.", "success")
    return redirect(url_for("master_dashboard"))


def salvar_replay_obs():
    obs = ReqClient(
        host=os.getenv("OBS_HOST", "localhost"),
        port=int(os.getenv("OBS_PORT", "4455")),
        password=os.getenv("OBS_PASSWORD", "")
    )
    obs.save_replay_buffer()


@app.post("/replay")
def replay():
    supplied_token = request.headers.get("X-Replay-Token", "")
    tenant = next(
        (item for item in Tenant.query.all() if hmac.compare_digest(item.replay_token, supplied_token)),
        None
    )

    if not tenant:
        return jsonify({"erro": "Nao autorizado."}), 401

    capture = CaptureRequest(tenant_id=tenant.id)
    db.session.add(capture)
    db.session.commit()

    try:
        salvar_replay_obs()
    except Exception:
        capture.status = "failed"
        db.session.commit()
        app.logger.exception("Falha ao solicitar replay ao OBS.")
        return jsonify({"erro": "OBS indisponivel ou mal configurado."}), 503

    return jsonify({"mensagem": "Replay solicitado."})


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("landing"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
