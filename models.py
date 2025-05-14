from datetime import datetime
from flask_login import UserMixin
from app import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # 关联
    keys = db.relationship('LicenseKey', backref='user', lazy='dynamic')
    usage_logs = db.relationship('UsageLog', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'

class VerificationToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    purpose = db.Column(db.String(20), nullable=False)  # 'register', 'reset_password'
    
    def __repr__(self):
        return f'<VerificationToken {self.token}>'

class LicenseKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    max_uses = db.Column(db.Integer, nullable=False)
    remaining_uses = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    calculation_type = db.Column(db.String(20), default='fixed')  # fixed, by_size, by_duration, by_count
    calculation_value = db.Column(db.Float, default=1.0)  # 计算数值，根据calculation_type有不同含义
    meta_info = db.Column(db.Text, nullable=True)  # 存储JSON格式的其他元数据
    
    # 关联
    usage_logs = db.relationship('UsageLog', backref='license_key', lazy='dynamic')
    
    def __repr__(self):
        return f'<LicenseKey {self.key}>'
        
    def get_calculation_type(self):
        """从卡密前缀或存储的计算类型中获取计算方式"""
        if self.calculation_type:
            return self.calculation_type
            
        # 从前缀推断
        prefix_map = {
            'F-': 'fixed',
            'S-': 'by_size',
            'D-': 'by_duration',
            'C-': 'by_count',
        }
        
        for prefix, calc_type in prefix_map.items():
            if self.key.startswith(prefix):
                return calc_type
                
        return 'fixed'  # 默认固定计算方式

class UsageLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    license_key_id = db.Column(db.Integer, db.ForeignKey('license_key.id'), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    storyboard_file = db.Column(db.String(256), nullable=True)
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    
    def __repr__(self):
        return f'<UsageLog {self.id}>'

class AdminConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trial_uses = db.Column(db.Integer, default=3)  # 试用用户可用次数
    license_key_uses = db.Column(db.Integer, default=50)  # 默认卡密可用次数
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<AdminConfig {self.id}>'
