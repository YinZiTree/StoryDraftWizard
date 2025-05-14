import os
import logging
import sys
from datetime import datetime, timedelta

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# 设置日志
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

# 初始化扩展
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
mail = Mail()

# 创建应用
app = Flask(__name__)
app.config.from_object('config.Config')
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# 初始化扩展
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录以访问此页面'
mail.init_app(app)

# 导入路由
with app.app_context():
    # 导入模型
    from models import User, LicenseKey, UsageLog, AdminConfig
    
    # 执行数据库迁移
    try:
        logger.info("正在检查并执行数据库迁移...")
        from utils.database import perform_database_migrations, get_database_type
        
        db_type = get_database_type(db)
        logger.info(f"数据库类型: {db_type}")
        
        # 执行自动迁移
        perform_database_migrations(db)
    except Exception as e:
        logger.error(f"数据库迁移失败: {str(e)}")
    
    # 创建数据库表
    db.create_all()
    
    # 检查是否有管理员，如果没有则创建默认管理员
    admin = User.query.filter_by(is_admin=True).first()
    if not admin:
        from werkzeug.security import generate_password_hash
        default_admin = User(
            username='admin',
            email=app.config['MAIL_DEFAULT_SENDER'],
            password_hash=generate_password_hash('admin123'),
            is_active=True,
            is_admin=True
        )
        db.session.add(default_admin)
        
        # 创建默认配置
        default_config = AdminConfig(
            trial_uses=3,
            license_key_uses=50
        )
        db.session.add(default_config)
        db.session.commit()
        
        logger.info("Created default admin user and configuration")

    # 注册蓝图
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.generator import generator_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(generator_bp)

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}
