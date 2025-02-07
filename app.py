from flask import Flask, render_template, request, redirect, url_for, flash,session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os
from flask import Response
import csv
from io import StringIO
from flask_migrate import Migrate


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
migrate = Migrate(app, db)  # 绑定 Migrate 到 Flask 和 SQLAlchemy

# 用户表模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    employee_id = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)

    # 这里用 `back_populates` 代替 `backref`
    login_logs = db.relationship('UserLoginLog', back_populates='user', cascade="all, delete-orphan", lazy=True)

    # 确保角色合法
    def set_role(self, role):
        if role not in ['admin', 'user']:
            raise ValueError("角色必须是 'admin' 或 'user'")
        self.role = role

    # Flask-Login 需要的方法
    def is_active(self):
        return True  # 所有用户默认都是活跃的

    def is_authenticated(self):
        return True  # 用户默认已认证

    def is_anonymous(self):
        return False  # 不是匿名用户

    def __repr__(self):
        return f"<User {self.username}, Role: {self.role}>"


# 用户登录记录表
class UserLoginLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50), nullable=False, default="0.0.0.0")
    user_agent = db.Column(db.String(255), nullable=True)

    # 这里去掉了 `backref`，改为 `back_populates`
    user = db.relationship('User', back_populates='login_logs')

    def __repr__(self):
        return f"<UserLoginLog user_id={self.user_id}, time={self.login_time}, IP={self.ip_address}>"

# 加载用户
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('index'))  # 已登录用户跳转到 index.html
    return redirect(url_for('login'))  # 未登录用户跳转到 login.html

@app.route('/index')
@login_required
def index():
    return render_template('index.html', user_id=session.get('username'), role=session.get('role'))


# 用户登录
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)  # Flask-Login 记录登录状态

            # 存储用户信息到 session
            session['user_id'] = user.id
            session['username'] = user.name  # 这里确保存储的是姓名
            session['role'] = user.role

            # 记录用户登录日志（确保 user_id 不为空）
            if user.id:
                login_log = UserLoginLog(
                    user_id=user.id,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
                db.session.add(login_log)
                db.session.commit()

            # 判断角色并跳转
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('index'))  # 普通用户进入 index.html
        else:
            flash('用户名或密码错误！')

    return render_template('login.html')


# admin.html中，用户登录历史记录相关
@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    # 获取当前页数（默认第1页）
    page = request.args.get('page', 1, type=int)
    per_page = 50  # 每页 50 条记录

    # 获取所有用户
    users = User.query.all()

    # 获取登录历史，并分页
    login_logs_paginated = UserLoginLog.query.order_by(UserLoginLog.login_time.desc()).paginate(page=page, per_page=per_page, error_out=False)

    if request.method == 'POST':
        action = request.form.get('action')
        user_id = request.form.get('user_id')

        try:
            # 删除用户（确保删除用户前，先删除其所有登录日志）
            if action == 'delete' and user_id:
                user_id = int(user_id)
                user = User.query.get(user_id)
                if user:
                    # 先删除用户的所有登录日志
                    UserLoginLog.query.filter_by(user_id=user.id).delete()

                    # 再删除用户
                    db.session.delete(user)
                    db.session.commit()
                    flash('用户及其登录记录已删除！')
                else:
                    flash('用户不存在！')

            # 编辑用户
            elif action == 'edit' and user_id:
                user_id = int(user_id)
                user = User.query.get(user_id)
                if user:
                    new_username = request.form.get('username')
                    new_role = request.form.get('role')
                    new_employee_id = request.form.get('employee_id')
                    new_name = request.form.get('name')

                    # 确保角色只能是 'admin' 或 'user'
                    if new_role not in ['admin', 'user']:
                        flash('无效的角色类型！')
                    else:
                        user.username = new_username
                        user.role = new_role
                        user.employee_id = new_employee_id
                        user.name = new_name
                        db.session.commit()

                        # 如果修改的是当前登录用户的信息，重新登录用户，防止会话失效
                        if user.id == current_user.id:
                            login_user(user)

                        flash('用户信息已更新！')
                else:
                    flash('用户不存在！')

            # 添加用户
            elif action == 'add':
                username = request.form['username']
                password = generate_password_hash(request.form['password'])
                role = request.form['role']
                employee_id = request.form['employee_id']
                name = request.form['name']

                # 确保用户名唯一
                existing_user = User.query.filter_by(username=username).first()
                if existing_user:
                    flash('用户名已存在！')
                elif role not in ['admin', 'user']:
                    flash('无效的角色类型！')
                else:
                    new_user = User(username=username, password=password, role=role, employee_id=employee_id, name=name)
                    db.session.add(new_user)
                    db.session.commit()
                    flash('新用户已添加！')

        except ValueError:
            flash('无效的用户ID')
        except Exception as e:
            db.session.rollback()  # 发生错误时回滚事务
            flash(f'操作失败: {str(e)}')

        return redirect(url_for('admin_dashboard'))

    return render_template(
        'admin.html',
        users=users,
        login_logs=login_logs_paginated.items,  # 当前页的日志记录
        page=page,  # 传递当前页码
        has_next=login_logs_paginated.has_next  # 是否有下一页
    )


# 用户登出
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("您已成功登出！", "info")
    return redirect(url_for('login'))

# 导出用户登录历史记录
@app.route('/export_login_history', methods=['POST'])
@login_required
def export_login_history():
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    # 获取所有登录记录
    login_logs = UserLoginLog.query.order_by(UserLoginLog.login_time.desc()).all()

    # 创建 CSV 数据
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["登录时间", "用户名", "IP地址", "浏览器"])
    
    for log in login_logs:
        writer.writerow([log.login_time, log.user.username, log.ip_address, log.user_agent])

    # 解决 Excel 乱码问题：使用 utf-8-sig
    response = Response(output.getvalue().encode('utf-8-sig'), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=login_history.csv"
    return response

# 删除用户登录历史记录
@app.route('/delete_login_history', methods=['POST'])
@login_required
def delete_login_history():
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    log_ids = request.form.getlist('log_ids')
    
    if log_ids:
        UserLoginLog.query.filter(UserLoginLog.id.in_(log_ids)).delete(synchronize_session=False)
        db.session.commit()
        flash("选定的登录记录已删除！")

    return redirect(url_for('admin_dashboard'))


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

