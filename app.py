import os
import cv2
import cloudinary
import cloudinary.uploader
from obsws_python import ReqClient
from dotenv import load_dotenv
load_dotenv()

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_from_directory
)
from flask_sqlalchemy import SQLAlchemy


from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "core", "uploads")
THUMBNAIL_FOLDER = os.path.join(BASE_DIR, "core", "thumbnails")
VIDEO_EXTENSIONS = (".mp4",)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMBNAIL_FOLDER, exist_ok=True)

# =========================
# APP
# =========================

app = Flask(__name__)

obs = ReqClient(
    host=os.getenv("OBS_HOST", "localhost"),
    port=int(os.getenv("OBS_PORT", "4455")),
    password=os.getenv("OBS_PASSWORD", "")
)

print("OBS conectado")

cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET"),
    secure=True
)
# segurança
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

# banco
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)

# =========================
# LOGIN MANAGER
# =========================

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"

# =========================
# TABELA USUÁRIOS
# =========================

class User(UserMixin, db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(100),
        unique=True
    )

    password = db.Column(
        db.String(100)
    )

# =========================
# CARREGAR USUÁRIO
# =========================

@login_manager.user_loader
def load_user(user_id):

    return User.query.get(int(user_id))

# =========================
# LOGIN
# =========================

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]

        user = User.query.filter_by(

            username=username,
            password=password

        ).first()

        if user:

            login_user(user)

            return redirect(
                url_for("dashboard")
            )

    return render_template(
        "login.html"
    )

# =========================
# GERAR THUMBNAIL
# =========================

def gerar_thumbnail(video):

    thumb_path = os.path.join(THUMBNAIL_FOLDER, f"{video}.jpg")

    if not os.path.exists(thumb_path):

        video_path = os.path.join(UPLOAD_FOLDER, video)

        cap = cv2.VideoCapture(video_path)

        success, frame = cap.read()

        if success:

            cv2.imwrite(
                thumb_path,
                frame
            )

        cap.release()

    return thumb_path

def upload_video(video):

    video_path = os.path.join(UPLOAD_FOLDER, video)

    resultado = cloudinary.uploader.upload_large(

        video_path,

        resource_type="video",

        folder="replays"

    )

    return resultado["secure_url"]

# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
@login_required
def dashboard():
    videos = [

        video for video in os.listdir(UPLOAD_FOLDER)

        if video.lower().endswith(VIDEO_EXTENSIONS)

    ]

    lista_videos = []

    for video in sorted(
        videos,
        key=lambda nome: os.path.getmtime(os.path.join(UPLOAD_FOLDER, nome)),
        reverse=True
    ):

        thumb = gerar_thumbnail(video)

        lista_videos.append({

            "video": video,
            "thumb": thumb,
            "mime_type": "video/mp4"

        })

    return render_template(

        "dashboard.html",

        videos=lista_videos

    )
@app.route('/uploads/<filename>')
def uploaded_file(filename):

    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )
# =========================
# SALVAR REPLAY
# =========================

@app.route("/replay")
def replay():

    obs.save_replay_buffer()

    return "REPLAY SALVO!"

# =========================
# LOGOUT
# =========================

@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(
        url_for("login")
    )

# =========================
# INICIAR
# =========================
@app.route("/teste")
def teste():
    return "OK"

if __name__ == "__main__":

    with app.app_context():

        db.create_all()

        # cria admin automático
        if not User.query.filter_by(
            username="admin"
        ).first():

            admin = User(

                username="admin",
                password="123"

            )

            db.session.add(admin)

            db.session.commit()

    app.run(host="0.0.0.0", port=5000, debug=False)

