from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os

# 获取 instance/secret_key.txt 的完整路径
INSTANCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance")
SECRET_KEY_FILE = os.path.join(INSTANCE_DIR, "secret_key.txt")

# 读取 SECRET_KEY（如果文件不存在则自动生成）
def get_secret_key():
    if not os.path.exists(SECRET_KEY_FILE):
        import secrets
        secret_key = secrets.token_hex(32)
        with open(SECRET_KEY_FILE, "w") as f:
            f.write(secret_key)
    else:
        with open(SECRET_KEY_FILE, "r") as f:
            secret_key = f.read().strip()
    return secret_key



app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # 使用SQLite数据库存储用户信息
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# 设置 Flask 的 SECRET_KEY
app.secret_key = get_secret_key()

# 用户表模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    employee_id = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)

# 用户登录记录表
class UserLoginLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)  # 登录时间
    ip_address = db.Column(db.String(50))  # 用户的IP地址
    user_agent = db.Column(db.String(255))  # 用户的User-Agent (浏览器信息)
    user = db.relationship('User', backref=db.backref('login_logs', lazy=True))  # 外键关系

# 加载用户
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('login'))  # 重定向到登录页面

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            # 登录成功，记录登录日志
            ip_address = request.remote_addr  # 获取IP地址
            user_agent = request.headers.get('User-Agent')  # 获取浏览器信息

            # 保存登录记录到数据库
            login_log = UserLoginLog(user_id=user.id, ip_address=ip_address, user_agent=user_agent)
            db.session.add(login_log)
            db.session.commit()

            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('登录失败，用户名或密码错误。')

    return render_template('login.html')

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    users = User.query.all()
    login_logs = UserLoginLog.query.order_by(UserLoginLog.login_time.desc()).all()

    if request.method == 'POST':
        action = request.form.get('action')
        user_id = request.form.get('user_id')

        if action == 'delete' and user_id:
            try:
                user_id = int(user_id)
                user = User.query.get(user_id)
                if user:
                    db.session.delete(user)
                    db.session.commit()
                    flash('用户已删除！')
                else:
                    flash('用户不存在！')
            except ValueError:
                flash('无效的用户ID')

        elif action == 'edit' and user_id:
            try:
                user_id = int(user_id)
                user = User.query.get(user_id)
                if user:
                    user.username = request.form.get('username')
                    user.role = request.form.get('role')
                    user.employee_id = request.form.get('employee_id')
                    user.name = request.form.get('name')
                    db.session.commit()
                    
                    # 如果是当前用户被修改，重新加载会话
                    if user.id == current_user.id:
                        login_user(user)  # 重新登录用户，防止会话失效

                    flash('用户信息已更新！')
                else:
                    flash('用户不存在！')
            except ValueError:
                flash('无效的用户ID')

        elif action == 'add':
            username = request.form['username']
            password = generate_password_hash(request.form['password'])
            role = request.form['role']
            employee_id = request.form['employee_id']
            name = request.form['name']
            new_user = User(username=username, password=password, role=role, employee_id=employee_id, name=name)
            db.session.add(new_user)
            db.session.commit()
            flash('新用户已添加！')

        return redirect(url_for('admin_dashboard'))

    return render_template('admin.html', users=users, login_logs=login_logs)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("您已成功登出！", "info")
    return redirect(url_for('login'))

if __name__ == '__main__':

    # 创建默认管理员用户
    def create_default_admin():
        # 检查数据库中是否已经有 admin 用户
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            # 如果没有 admin 用户，则创建一个
            hashed_password = generate_password_hash('210726')
            new_admin = User(username='admin', password=hashed_password, role='admin', employee_id='0001', name='管理员')
            db.session.add(new_admin)
            db.session.commit()
            print("默认 admin 用户已创建")

    # 在应用上下文中创建数据库表
    with app.app_context():
        db.create_all()  # 这行代码会确保所有定义的表都被创建
        create_default_admin()  # 创建默认管理员用户
    
    app.run(debug=True)

