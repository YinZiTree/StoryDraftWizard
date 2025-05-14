import os
import json
import uuid
import shutil
import zipfile
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, send_file, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from models import UsageLog, LicenseKey
from utils.generator import generate_capcut_draft, allowed_file, get_available_templates
from utils.template import create_draft_zip

generator_bp = Blueprint('generator', __name__)

@generator_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('generator.dashboard'))
    return render_template('index.html')

@generator_bp.route('/dashboard')
@login_required
def dashboard():
    # 获取用户的卡密
    license_keys = LicenseKey.query.filter_by(user_id=current_user.id, is_active=True).all()
    
    # 获取用户的使用记录
    usage_logs = UsageLog.query.filter_by(user_id=current_user.id).order_by(UsageLog.timestamp.desc()).limit(10).all()
    
    # 计算总剩余次数
    total_remaining = sum(key.remaining_uses for key in license_keys if key.is_active)
    
    # 获取可用模板
    templates = get_available_templates()
    
    return render_template('dashboard.html', 
                           license_keys=license_keys, 
                           usage_logs=usage_logs,
                           total_remaining=total_remaining,
                           templates=templates)

@generator_bp.route('/generate', methods=['POST'])
@login_required
def generate():
    # 检查文件是否存在
    if 'storyboard_file' not in request.files:
        flash('没有上传文件', 'danger')
        return redirect(url_for('generator.dashboard'))
    
    file = request.files['storyboard_file']
    
    # 检查文件名
    if file.filename == '':
        flash('没有选择文件', 'danger')
        return redirect(url_for('generator.dashboard'))
    
    # 检查文件类型
    if not allowed_file(file.filename):
        flash('不支持的文件类型，请上传JSON文件', 'danger')
        return redirect(url_for('generator.dashboard'))
    
    # 检查用户是否有可用次数
    # 查找用户所有有效的卡密
    license_keys = LicenseKey.query.filter_by(user_id=current_user.id, is_active=True).all()
    
    # 如果没有可用卡密
    if not license_keys:
        flash('您没有可用的卡密，请先激活卡密', 'danger')
        return redirect(url_for('generator.dashboard'))
    
    # 检查是否有可用次数
    usable_key = next((key for key in license_keys if key.remaining_uses > 0), None)
    
    if not usable_key:
        flash('您的卡密已用尽次数，请激活新的卡密', 'danger')
        return redirect(url_for('generator.dashboard'))
    
    # 创建文件名和保存路径
    filename = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{timestamp}_{filename}")
    
    # 保存文件
    file.save(file_path)
    
    # 获取选择的模板
    template_name = request.form.get('template', '')
    
    # 处理背景图片
    background_path = None
    if 'background' in request.files and request.files['background'].filename != '':
        background_file = request.files['background']
        background_filename = secure_filename(background_file.filename)
        background_path = os.path.join(current_app.config['UPLOAD_FOLDER'], background_filename)
        background_file.save(background_path)
    
    # 获取草稿名称
    draft_name = request.form.get('draft_name', f"剪映草稿_{timestamp}")
    
    try:
        # 生成草稿
        draft_id = generate_capcut_draft(file_path, template_name, background_path, draft_name)
        
        # 创建ZIP文件
        zip_path = create_draft_zip(draft_id)
        
        # 减少使用次数
        usable_key.remaining_uses -= 1
        
        # 记录使用日志
        usage_log = UsageLog(
            user_id=current_user.id,
            license_key_id=usable_key.id,
            storyboard_file=filename,
            ip_address=request.remote_addr
        )
        
        db.session.add(usage_log)
        db.session.commit()
        
        # 读取meta_info以获取draft_name
        meta_info_path = os.path.join(current_app.config['TEMP_FOLDER'], draft_id, 'draft_meta_info.json')
        if os.path.exists(meta_info_path):
            with open(meta_info_path, 'r', encoding='utf-8') as f:
                meta_info = json.load(f)
                download_name = meta_info.get('draft_name', draft_id)
        else:
            download_name = draft_id
        
        # 返回ZIP文件下载
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=f'{download_name}.zip',
            mimetype='application/zip'
        )
    
    except Exception as e:
        # 记录错误日志
        error_message = str(e)
        usage_log = UsageLog(
            user_id=current_user.id,
            license_key_id=usable_key.id if usable_key else None,
            storyboard_file=filename,
            success=False,
            error_message=error_message,
            ip_address=request.remote_addr
        )
        
        db.session.add(usage_log)
        db.session.commit()
        
        flash(f'生成草稿文件失败: {error_message}', 'danger')
        return redirect(url_for('generator.dashboard'))

@generator_bp.route('/templates')
@login_required
def templates():
    """获取可用的模板列表"""
    templates = get_available_templates()
    return jsonify(templates)
