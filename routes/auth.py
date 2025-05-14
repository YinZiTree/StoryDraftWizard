import uuid
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from app import db
from models import User, VerificationToken, LicenseKey, AdminConfig
from utils.email import send_verification_email, send_welcome_email, send_license_key_email

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('generator.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # 验证输入
        if not all([username, email, password]):
            flash('请填写所有必填字段', 'danger')
            return redirect(url_for('auth.register'))
        
        # 检查用户名和邮箱是否已存在
        if User.query.filter_by(username=username).first():
            flash('用户名已被使用', 'danger')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash('邮箱已被注册', 'danger')
            return redirect(url_for('auth.register'))
        
        # 创建新用户
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.flush()
        
        # 创建验证令牌
        token = str(uuid.uuid4())
        verification = VerificationToken(
            user_id=user.id,
            token=token,
            purpose='register'
        )
        db.session.add(verification)
        
        # 创建试用卡密
        config = AdminConfig.query.first()
        trial_key = LicenseKey(
            key=f"TRIAL-{str(uuid.uuid4())[:8].upper()}",
            user_id=user.id,
            max_uses=config.trial_uses,
            remaining_uses=config.trial_uses
        )
        db.session.add(trial_key)
        
        db.session.commit()
        
        # 发送验证邮件
        send_verification_email(user.email, token)
        
        flash('注册成功！请查收邮件并验证您的账号', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth_bp.route('/verify/<token>')
def verify(token):
    verification = VerificationToken.query.filter_by(token=token, purpose='register').first()
    
    if not verification:
        flash('无效或已过期的验证链接', 'danger')
        return redirect(url_for('auth.login'))
    
    user = User.query.get(verification.user_id)
    if not user:
        flash('用户不存在', 'danger')
        return redirect(url_for('auth.login'))
    
    user.is_active = True
    db.session.delete(verification)  # 删除使用过的验证令牌
    db.session.commit()
    
    # 发送欢迎邮件
    send_welcome_email(user.email, user.username)
    
    flash('账号验证成功！现在您可以登录了', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('generator.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            flash('邮箱或密码错误', 'danger')
            return redirect(url_for('auth.login'))
        
        if not user.is_active:
            flash('账号尚未激活，请查收邮件并点击验证链接', 'warning')
            return redirect(url_for('auth.login'))
        
        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        login_user(user, remember=remember)
        
        # 重定向到请求的页面或者默认到仪表盘
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        
        if user.is_admin:
            return redirect(url_for('admin.index'))
        else:
            return redirect(url_for('generator.dashboard'))
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已成功登出', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/activate-key', methods=['POST'])
@login_required
def activate_key():
    key_code = request.form.get('key_code')
    
    if not key_code:
        flash('请输入卡密', 'danger')
        return redirect(url_for('generator.dashboard'))
    
    # 查找卡密
    license_key = LicenseKey.query.filter_by(key=key_code).first()
    
    if not license_key:
        flash('无效的卡密', 'danger')
        return redirect(url_for('generator.dashboard'))
    
    if not license_key.is_active:
        flash('此卡密已被禁用', 'danger')
        return redirect(url_for('generator.dashboard'))
    
    if license_key.expires_at and license_key.expires_at < datetime.utcnow():
        flash('此卡密已过期', 'danger')
        return redirect(url_for('generator.dashboard'))
    
    if license_key.remaining_uses <= 0:
        flash('此卡密已用尽次数', 'danger')
        return redirect(url_for('generator.dashboard'))
    
    if license_key.user_id and license_key.user_id != current_user.id:
        flash('此卡密已被其他用户使用', 'danger')
        return redirect(url_for('generator.dashboard'))
    
    # 绑定卡密到用户
    if not license_key.user_id:
        license_key.user_id = current_user.id
    
    # 发送卡密邮件
    send_license_key_email(current_user.email, current_user.username, license_key.key, license_key.remaining_uses)
    
    db.session.commit()
    
    flash(f'卡密激活成功！可用次数: {license_key.remaining_uses}', 'success')
    return redirect(url_for('generator.dashboard'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('generator.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash('请输入邮箱地址', 'danger')
            return redirect(url_for('auth.forgot_password'))
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            flash('未找到该邮箱对应的账号', 'danger')
            return redirect(url_for('auth.forgot_password'))
        
        # 创建重置密码令牌
        token = str(uuid.uuid4())
        reset_token = VerificationToken(
            user_id=user.id,
            token=token,
            purpose='reset_password'
        )
        db.session.add(reset_token)
        db.session.commit()
        
        # 发送重置密码邮件
        # TODO: 实现发送重置密码邮件的功能
        
        flash('重置密码链接已发送到您的邮箱', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('forgot_password.html')
