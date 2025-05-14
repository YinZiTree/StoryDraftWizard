import os
import json
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from models import User
from utils.generator import get_available_templates

templates_bp = Blueprint('templates', __name__, url_prefix='/templates')

def allowed_template_file(filename):
    """检查文件类型是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['json']

@templates_bp.route('/')
@login_required
def index():
    """模板管理页面"""
    templates = get_available_templates()
    return render_template('templates/index.html', templates=templates)

@templates_bp.route('/upload', methods=['POST'])
@login_required
def upload():
    """上传模板文件"""
    # 检查用户权限（只允许管理员上传模板）
    if not current_user.is_admin:
        flash('您没有权限上传模板', 'danger')
        return redirect(url_for('templates.index'))
    
    # 检查文件是否存在
    if 'template_file' not in request.files:
        flash('没有上传文件', 'danger')
        return redirect(url_for('templates.index'))
    
    file = request.files['template_file']
    
    # 检查文件名
    if file.filename == '':
        flash('没有选择文件', 'danger')
        return redirect(url_for('templates.index'))
    
    # 检查文件类型
    if not allowed_template_file(file.filename):
        flash('不支持的文件类型，请上传JSON文件', 'danger')
        return redirect(url_for('templates.index'))
    
    # 创建文件名和保存路径
    template_name = request.form.get('template_name', '')
    effect_type = request.form.get('effect_type', '标准')
    font_type = request.form.get('font_type', '默认')
    
    # 如果没有提供模板名称，使用原始文件名
    if not template_name:
        template_name = os.path.splitext(file.filename)[0]
    
    # 文件名添加时间戳，避免重名
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"{secure_filename(template_name)}_{timestamp}.json"
    
    # 确保模板目录存在
    template_folder = os.path.join(current_app.config['TEMP_FOLDER'], 'templates')
    os.makedirs(template_folder, exist_ok=True)
    
    file_path = os.path.join(template_folder, filename)
    
    try:
        # 先保存原始文件
        file.save(file_path)
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        
        # 如果是有效的JSON，但不是模板格式，添加模板信息
        if isinstance(template_data, dict) and 'template' not in template_data:
            template_data['name'] = template_name
            template_data['template'] = {
                'effect_type': effect_type,
                'font_type': font_type
            }
            
            # 保存更新后的文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, ensure_ascii=False, indent=2)
        
        flash(f'模板 {template_name} 上传成功', 'success')
    except Exception as e:
        flash(f'模板上传失败: {str(e)}', 'danger')
    
    return redirect(url_for('templates.index'))

@templates_bp.route('/delete/<filename>', methods=['POST'])
@login_required
def delete(filename):
    """删除模板文件"""
    # 检查用户权限（只允许管理员删除模板）
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': '您没有权限删除模板'})
    
    template_folder = os.path.join(current_app.config['TEMP_FOLDER'], 'templates')
    file_path = os.path.join(template_folder, filename)
    
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({'success': True, 'message': '模板删除成功'})
        else:
            return jsonify({'success': False, 'message': '模板文件不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除模板失败: {str(e)}'})

@templates_bp.route('/api/list')
def api_list():
    """获取可用模板列表（API）"""
    templates = get_available_templates()
    return jsonify(templates)

@templates_bp.route('/example')
def example():
    """获取模板示例说明"""
    return render_template('templates/example.html')