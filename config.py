import os

class Config:
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_secret_key')
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # 邮件配置
    MAIL_SERVER = 'smtp.qq.com'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USE_TLS = False
    MAIL_USERNAME = '1576129288@qq.com'
    MAIL_PASSWORD = 'lajylchugszobaej'
    MAIL_DEFAULT_SENDER = '1576129288@qq.com'
    
    # 应用配置
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'json'}
    
    # 临时目录
    TEMP_FOLDER = os.path.join(os.getcwd(), 'temp')
    
    # 确保目录存在
    for folder in [UPLOAD_FOLDER, TEMP_FOLDER]:
        if not os.path.exists(folder):
            os.makedirs(folder)
