import uuid
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, and_, desc, case
from flask_mail import Message

from app import db, mail
from models import User, LicenseKey, UsageLog, AdminConfig
from utils.email import send_license_key_email

admin_bp = Blueprint('admin', __name__)

# 管理员权限检查装饰器
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('您没有权限访问此页面', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return login_required(decorated_function)

@admin_bp.route('/')
@admin_required
def index():
    # 获取基本统计数据
    user_count = User.query.count()
    key_count = LicenseKey.query.count()
    usage_count = UsageLog.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    
    # 最近注册的用户
    recent_users = User.query.order_by(desc(User.registration_date)).limit(5).all()
    
    # 最近的使用记录
    recent_usages = UsageLog.query.order_by(desc(UsageLog.timestamp)).limit(5).all()
    
    return render_template('admin/index.html', 
                           user_count=user_count,
                           key_count=key_count,
                           usage_count=usage_count,
                           active_users=active_users,
                           recent_users=recent_users,
                           recent_usages=recent_usages)

@admin_bp.route('/users')
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    users = User.query.order_by(User.registration_date.desc()).paginate(page=page, per_page=per_page)
    
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:user_id>')
@admin_required
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    
    # 用户的卡密
    license_keys = LicenseKey.query.filter_by(user_id=user.id).all()
    
    # 用户的使用记录
    usage_logs = UsageLog.query.filter_by(user_id=user.id).order_by(UsageLog.timestamp.desc()).all()
    
    return render_template('admin/user_detail.html', user=user, license_keys=license_keys, usage_logs=usage_logs)

@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # 不允许停用管理员账号
    if user.is_admin:
        flash('不能停用管理员账号', 'danger')
        return redirect(url_for('admin.users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = '启用' if user.is_active else '停用'
    flash(f'用户 {user.username} 已{status}', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/keys')
@admin_required
def keys():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    license_keys = LicenseKey.query.order_by(LicenseKey.created_at.desc()).paginate(page=page, per_page=per_page)
    
    return render_template('admin/keys.html', license_keys=license_keys)

@admin_bp.route('/keys/create', methods=['GET', 'POST'])
@admin_required
def create_key():
    if request.method == 'POST':
        count = int(request.form.get('count', 1))
        max_uses = int(request.form.get('max_uses', 50))
        expires_days = int(request.form.get('expires_days', 0))
        
        # 检查输入
        if count <= 0 or max_uses <= 0:
            flash('生成数量和使用次数必须大于0', 'danger')
            return redirect(url_for('admin.create_key'))
        
        # 设置过期时间
        expires_at = None
        if expires_days > 0:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        # 生成卡密
        for _ in range(count):
            key = f"LK-{str(uuid.uuid4())[:12].upper()}"
            license_key = LicenseKey(
                key=key,
                max_uses=max_uses,
                remaining_uses=max_uses,
                expires_at=expires_at
            )
            db.session.add(license_key)
        
        db.session.commit()
        
        flash(f'成功生成 {count} 个卡密', 'success')
        return redirect(url_for('admin.keys'))
    
    return render_template('admin/create_key.html')

@admin_bp.route('/keys/<int:key_id>/recharge', methods=['POST'])
@admin_required
def recharge_key(key_id):
    license_key = LicenseKey.query.get_or_404(key_id)
    amount = int(request.form.get('amount', 0))
    
    if amount <= 0:
        flash('充值次数必须大于0', 'danger')
        return redirect(url_for('admin.keys'))
    
    license_key.remaining_uses += amount
    license_key.max_uses += amount
    db.session.commit()
    
    if license_key.user:
        send_license_key_email(license_key.user.email, license_key.user.username, 
                             license_key.key, license_key.remaining_uses)
    
    flash(f'已为卡密 {license_key.key} 充值 {amount} 次', 'success')
    return redirect(url_for('admin.keys'))

@admin_bp.route('/keys/<int:key_id>/toggle', methods=['POST'])
@admin_required
def toggle_key(key_id):
    license_key = LicenseKey.query.get_or_404(key_id)
    
    license_key.is_active = not license_key.is_active
    db.session.commit()
    
    status = '启用' if license_key.is_active else '禁用'
    flash(f'卡密 {license_key.key} 已{status}', 'success')
    return redirect(url_for('admin.keys'))

@admin_bp.route('/keys/send-batch', methods=['POST'])
@admin_required
def send_keys_batch():
    email = request.form.get('email')
    key_ids = request.form.getlist('key_ids[]')
    
    if not email:
        return jsonify({'status': 'error', 'message': '请提供接收卡密的邮箱'})
    
    if not key_ids:
        return jsonify({'status': 'error', 'message': '请选择要发送的卡密'})
        
    keys_info = []
    for key_id in key_ids:
        license_key = LicenseKey.query.get(key_id)
        if license_key:
            keys_info.append({
                'key': license_key.key,
                'remaining_uses': license_key.remaining_uses
            })
    
    if keys_info:
        # 批量发送邮件
        html = "<h2>您的卡密信息</h2><ul>"
        for info in keys_info:
            html += f"<li>卡密: {info['key']} (剩余次数: {info['remaining_uses']})</li>"
        html += "</ul>"
        
        msg = Message(
            "【剪映草稿生成器】您的卡密信息",
            recipients=[email],
            html=html,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        try:
            mail.send(msg)
            return jsonify({'status': 'success', 'message': f'已成功发送 {len(keys_info)} 个卡密至 {email}'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'邮件发送失败: {str(e)}'})
    
    return jsonify({'status': 'error', 'message': '未找到有效的卡密'})

@admin_bp.route('/keys/<int:key_id>/send', methods=['POST'])
@admin_required
def send_key(key_id):
    license_key = LicenseKey.query.get_or_404(key_id)
    email = request.form.get('email')
    
    if not email and not license_key.user_id:
        flash('请提供接收卡密的邮箱', 'danger')
        return redirect(url_for('admin.keys'))
    
    try:
        if license_key.user_id:
            user = User.query.get(license_key.user_id)
            if user:
                send_license_key_email(user.email, user.username, license_key.key, license_key.remaining_uses)
                flash(f'卡密已发送至用户 {user.email}', 'success')
            else:
                flash('用户不存在', 'danger')
        else:
            send_license_key_email(email, '用户', license_key.key, license_key.remaining_uses)
            flash(f'卡密已发送至 {email}', 'success')
    except Exception as e:
        flash(f'邮件发送失败: {str(e)}', 'danger')
    
    return redirect(url_for('admin.keys'))

@admin_bp.route('/statistics')
@admin_required
def statistics():
    # 获取时间范围
    time_range = request.args.get('range', 'day')
    
    today = datetime.utcnow().date()
    
    # 导入数据库工具
    from utils.database import get_database_type
    
    # 检测数据库类型
    db_type = get_database_type(db)
    
    if time_range == 'day':
        start_date = today
        date_format = '%H:00'  # 小时
        
        # 根据数据库类型使用不同的分组函数
        if db_type == 'postgresql':
            group_by = func.date_trunc('hour', UsageLog.timestamp)
        else:
            # SQLite或其他数据库使用strftime
            group_by = func.strftime('%Y-%m-%d %H', UsageLog.timestamp)
            
    elif time_range == 'week':
        start_date = today - timedelta(days=7)
        date_format = '%Y-%m-%d'  # 天
        
        if db_type == 'postgresql':
            group_by = func.date_trunc('day', UsageLog.timestamp)
        else:
            group_by = func.strftime('%Y-%m-%d', UsageLog.timestamp)
            
    elif time_range == 'month':
        start_date = today.replace(day=1)
        date_format = '%Y-%m-%d'  # 天
        
        if db_type == 'postgresql':
            group_by = func.date_trunc('day', UsageLog.timestamp)
        else:
            group_by = func.strftime('%Y-%m-%d', UsageLog.timestamp)
            
    else:  # year
        start_date = today.replace(month=1, day=1)
        date_format = '%Y-%m'  # 月
        
        if db_type == 'postgresql':
            group_by = func.date_trunc('month', UsageLog.timestamp)
        else:
            group_by = func.strftime('%Y-%m', UsageLog.timestamp)
    
    # 将start_date转换为datetime
    start_datetime = datetime.combine(start_date, datetime.min.time())
    
    # 查询指定时间范围内的使用记录数量（按时间分组）
    usage_stats = db.session.query(
        group_by.label('date'),
        func.count(UsageLog.id).label('count')
    ).filter(
        UsageLog.timestamp >= start_datetime
    ).group_by('date').all()
    
    # 查询指定时间范围内的用户注册数量（按时间分组）
    # 使用数据库兼容性适配器
    from utils.database import format_date
    
    if time_range == 'day':
        reg_group_by = format_date(db, User.registration_date, '%H')
    elif time_range == 'week' or time_range == 'month':
        reg_group_by = format_date(db, User.registration_date, '%Y-%m-%d')
    else:  # year
        reg_group_by = format_date(db, User.registration_date, '%Y-%m')
    
    registration_stats = db.session.query(
        reg_group_by.label('date'),
        func.count(User.id).label('count')
    ).filter(
        User.registration_date >= start_datetime
    ).group_by('date').all()
    
    # 将结果转换为JSON格式
    usage_data = {item.date: item.count for item in usage_stats}
    registration_data = {item.date: item.count for item in registration_stats}
    
    return render_template('admin/statistics.html', 
                           time_range=time_range,
                           usage_data=usage_data,
                           registration_data=registration_data)

@admin_bp.route('/api/statistics', methods=['GET'])
@admin_required
def api_statistics():
    """获取统计数据API（增强版）"""
    try:
        # 获取时间范围和分组类型
        time_range = request.args.get('range', 'day')
        group_by = request.args.get('group', 'hour')  # 可选值: minute, hour, day, month
        
        # 今天的日期
        now = datetime.utcnow()
        today = now.date()
        
        # 根据时间范围计算开始时间
        if time_range == 'day':
            start_date = today
            if group_by == 'minute':
                filter_format = '%H:%M'
                label_format = '%H:%M'
            else:  # hour
                filter_format = '%H'  
                label_format = '%H:00'
        elif time_range == 'week':
            start_date = today - timedelta(days=7)
            if group_by == 'hour':
                filter_format = '%Y-%m-%d %H'
                label_format = '%m-%d %H:00'
            else:  # day
                filter_format = '%Y-%m-%d'
                label_format = '%m-%d'
        elif time_range == 'month':
            start_date = today.replace(day=1)
            if group_by == 'hour':
                filter_format = '%Y-%m-%d %H'
                label_format = '%m-%d %H:00'
            else:  # day
                filter_format = '%Y-%m-%d'
                label_format = '%m-%d'
        else:  # year
            start_date = today.replace(month=1, day=1)
            if group_by == 'day':
                filter_format = '%Y-%m-%d'
                label_format = '%m-%d'
            else:  # month
                filter_format = '%Y-%m'
                label_format = '%Y-%m'
        
        # 将start_date转换为datetime
        start_datetime = datetime.combine(start_date, datetime.min.time())
        
        # 查询指定时间范围内的使用记录
        usage_logs = UsageLog.query.filter(UsageLog.timestamp >= start_datetime).all()
        
        # 查询指定时间范围内的用户注册
        registrations = User.query.filter(User.registration_date >= start_datetime).all()
        
        # 统计数据
        usage_data = {}
        success_data = {}
        failed_data = {}
        registration_data = {}
        
        # 处理使用记录
        for log in usage_logs:
            if group_by == 'minute':
                date_key = log.timestamp.strftime('%Y-%m-%d %H:%M')
            elif group_by == 'hour':
                date_key = log.timestamp.strftime('%Y-%m-%d %H')
            elif group_by == 'month':
                date_key = log.timestamp.strftime('%Y-%m')
            else:  # day
                date_key = log.timestamp.strftime('%Y-%m-%d')
                
            label = log.timestamp.strftime(label_format)
            
            # 初始化数据结构
            if date_key not in usage_data:
                usage_data[date_key] = {'label': label, 'value': 0}
                success_data[date_key] = {'label': label, 'value': 0}
                failed_data[date_key] = {'label': label, 'value': 0}
            
            # 累加计数
            usage_data[date_key]['value'] += 1
            
            # 区分成功和失败
            if log.success:
                success_data[date_key]['value'] += 1
            else:
                failed_data[date_key]['value'] += 1
        
        # 处理注册记录
        for user in registrations:
            if group_by == 'minute':
                date_key = user.registration_date.strftime('%Y-%m-%d %H:%M')
            elif group_by == 'hour':
                date_key = user.registration_date.strftime('%Y-%m-%d %H')
            elif group_by == 'month':
                date_key = user.registration_date.strftime('%Y-%m')
            else:  # day
                date_key = user.registration_date.strftime('%Y-%m-%d')
                
            label = user.registration_date.strftime(label_format)
            
            if date_key not in registration_data:
                registration_data[date_key] = {'label': label, 'value': 0}
            registration_data[date_key]['value'] += 1
        
        # 转换为列表并排序
        usage_list = sorted(usage_data.values(), key=lambda x: x['label'])
        success_list = sorted(success_data.values(), key=lambda x: x['label'])
        failed_list = sorted(failed_data.values(), key=lambda x: x['label'])
        registration_list = sorted(registration_data.values(), key=lambda x: x['label'])
        
        # 统计用户使用情况
        user_stats = db.session.query(
            User.username,
            func.count(UsageLog.id).label('usage_count')
        ).join(
            UsageLog, User.id == UsageLog.user_id
        ).filter(
            UsageLog.timestamp >= start_datetime
        ).group_by(
            User.username
        ).order_by(
            func.count(UsageLog.id).desc()
        ).limit(10).all()
        
        # 统计卡密使用情况
        key_stats = db.session.query(
            LicenseKey.key,
            func.count(UsageLog.id).label('usage_count')
        ).join(
            UsageLog, LicenseKey.id == UsageLog.license_key_id
        ).filter(
            UsageLog.timestamp >= start_datetime
        ).group_by(
            LicenseKey.key
        ).order_by(
            func.count(UsageLog.id).desc()
        ).limit(10).all()
        
        # 返回增强的统计数据
        return jsonify({
            'success': True,
            'data': {
                'total_usage': len(usage_logs),
                'total_success': sum(1 for log in usage_logs if log.success),
                'total_failed': sum(1 for log in usage_logs if not log.success),
                'total_registrations': len(registrations),
                'usage': usage_list,
                'success': success_list,
                'failed': failed_list,
                'registrations': registration_list,
                'top_users': [{'username': stat.username, 'count': stat.usage_count} for stat in user_stats],
                'top_keys': [{'key': stat.key, 'count': stat.usage_count} for stat in key_stats],
                'time_range': time_range,
                'group_by': group_by
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取统计数据出错: {str(e)}'})

@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    config = AdminConfig.query.first()
    
    if request.method == 'POST':
        trial_uses = int(request.form.get('trial_uses', 3))
        license_key_uses = int(request.form.get('license_key_uses', 50))
        
        if trial_uses <= 0 or license_key_uses <= 0:
            flash('使用次数必须大于0', 'danger')
            return redirect(url_for('admin.settings'))
        
        config.trial_uses = trial_uses
        config.license_key_uses = license_key_uses
        db.session.commit()
        
        flash('设置已更新', 'success')
        return redirect(url_for('admin.settings'))
    
    return render_template('admin/settings.html', config=config)
