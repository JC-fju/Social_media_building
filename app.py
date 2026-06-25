import os
import time
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename # 新增：用來過濾危險的檔案名稱
from dotenv import load_dotenv

load_dotenv() 

app = Flask(__name__)

# --- 設定上傳檔案的資料夾與允許的格式 ---
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'} # 允許圖片與影片格式
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 如果 uploads 資料夾不存在，程式啟動時自動建立
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 檢查副檔名的輔助函式
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- 資料庫設定 ---
app.secret_key = os.environ.get("SECRET_KEY", "fallback_secret_key")
db_url = os.environ.get("DATABASE_URL", "sqlite:///eden.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 1. 既有的最新消息模型
class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    tag = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    link = db.Column(db.String(500), nullable=False, unique=True)

# 2. 會員資料模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    # 與貼文建立一對多關聯
    posts = db.relationship('Post', backref='author', lazy=True)

# 3. 論壇貼文模型
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    # 新增這行：用來儲存影音檔案的路徑 (允許為空)
    media_url = db.Column(db.String(200), nullable=True) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# 初始化資料表
with app.app_context():
    db.create_all()

# --- 網頁路由處理 ---

last_scrape_time = 0 

@app.route("/")
def home():
    global last_scrape_time
    current_time = time.time()
    
    # 設定：距離上次爬取超過 1 小時 (3600秒)，或伺服器剛啟動時，才觸發爬蟲
    if current_time - last_scrape_time > 3600:
        from fju_scraper import run_scraper
        run_scraper(db, News, app.app_context())
        last_scrape_time = current_time
        print("🕒 觸發爬蟲更新資料")
    else:
        print("⚡ 讀取資料庫快取，略過爬蟲")
        
    all_news = News.query.order_by(News.id.desc()).limit(6).all()
    return render_template("index.html", news_list=all_news)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return "帳號已存在，請換一個名字！"
            
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))
        
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    error_msg = None  # 準備一個變數裝錯誤訊息
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["username"] = user.username
            return redirect(url_for("forum"))
        else:
            # 發生錯誤時，不要 return 字串，而是設定錯誤訊息
            error_msg = "帳號或密碼錯誤，請檢查後再試一次！"
            
    # 將錯誤訊息傳給登入頁面
    return render_template("login.html", error=error_msg)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/forum", methods=["GET", "POST"])
def forum():
    if "user_id" not in session:
        return redirect(url_for("login"))
        
    if request.method == "POST":
        content = request.form.get("content")
        file = request.files.get("media_file") # 接收上傳的檔案
        media_url = None
        
        # 處理檔案上傳
        if file and allowed_file(file.filename):
            # 把檔名過濾掉危險字元，並加上時間戳記防止檔名重複覆蓋
            original_filename = secure_filename(file.filename)
            filename = f"{int(time.time())}_{original_filename}"
            
            # 儲存檔案到 static/uploads/ 裡面
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # 存入資料庫的路徑字串 (給 url_for 用的相對路徑)
            media_url = f"uploads/{filename}"

        if content and content.strip():
            # 新增貼文時，把 media_url 也存進去
            new_post = Post(content=content.strip(), user_id=session["user_id"], media_url=media_url)
            db.session.add(new_post)
            db.session.commit()
            return redirect(url_for("forum"))
            
    all_posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("forum.html", current_user=session["username"], posts=all_posts)

@app.route("/about")
def about(): return render_template("about.html")

@app.route("/achievements")
def achievements(): return render_template("achievements.html")

@app.route("/contact")
def contact(): return render_template("contact.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", debug=True, port=port)