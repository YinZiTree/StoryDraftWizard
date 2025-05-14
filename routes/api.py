import os
import json
import uuid
import random
import string
import tempfile
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from models import db, LicenseKey, User, AdminConfig, UsageLog
from flask_login import current_user

api_bp = Blueprint('api', __name__, url_prefix='/api')

def generate_license_key(length=16):
    """生成随机卡密"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

@api_bp.route('/orders/notify', methods=['POST'])
def order_notify():
    """
    订单通知接口
    
    接收参数:
    {
        "orderHistory": [
            {
                "out_trade_no": "ORDER_1745664119095_pd9l82",
                "total": 1,  // 金额，用于计算卡密使用次数
                "updateTime": 1745666553045,
                "payer_total": 1
            }
        ]
    }
    
    或者简单格式:
    {
        "out_trade_no": "ORDER_1745664119095_pd9l82",
        "total": 1,  // 金额，用于计算卡密使用次数
        "updateTime": 1745666553045,
        "payer_total": 1
    }
    """
    try:
        data = request.json
        results = []
        
        # 处理orderHistory格式
        if data and 'orderHistory' in data and isinstance(data['orderHistory'], list):
            orders = data['orderHistory']
        else:
            # 处理单个订单格式
            orders = [data] if data else []
        
        # 校验订单信息
        if not orders:
            return jsonify({'code': 400, 'message': '缺少订单信息'}), 400
        
        # 获取管理员配置，确定卡密使用次数计算方式
        admin_config = AdminConfig.query.first()
        if not admin_config:
            # 如果没有配置，创建默认配置
            admin_config = AdminConfig(
                trial_uses=3,              # 试用用户可用次数
                license_key_uses=50        # 默认卡密可用次数
            )
            db.session.add(admin_config)
            db.session.commit()
        
        # 遍历处理每个订单
        for order_data in orders:
            # 校验必要参数
            if not order_data or 'out_trade_no' not in order_data or 'total' not in order_data:
                results.append({
                    'code': 400, 
                    'message': '订单缺少必要参数',
                    'order_data': order_data
                })
                continue
            
            # 获取订单信息
            order_id = order_data.get('out_trade_no')
            total_amount = float(order_data.get('total', 0))
            
            # 检查订单是否已处理
            existing_usage_log = UsageLog.query.filter_by(storyboard_file=f"order_{order_id}").first()
            if existing_usage_log:
                # 订单已处理，跳过
                results.append({
                    'code': 200,
                    'message': '订单已处理',
                    'order_id': order_id,
                    'data': {
                        'license_key': None,
                        'max_uses': 0,
                        'remaining_uses': 0
                    }
                })
                continue
            
            # 根据订单金额设置不同的使用次数
            # 根据管理员配置和总金额计算使用次数
            calculation_config = {
                1: 10,      # 1元 = 10次
                5: 60,      # 5元 = 60次
                10: 130,    # 10元 = 130次
                20: 280,    # 20元 = 280次
                50: 750,    # 50元 = 750次
                100: 1600,  # 100元 = 1600次
                200: 3600,  # 200元 = 3600次
                500: 10000  # 500元 = 10000次
            }
            
            # 根据金额阶梯找到最接近的配置
            key_uses = admin_config.license_key_uses  # 默认值
            for amount, uses in sorted(calculation_config.items()):
                if total_amount >= amount:
                    key_uses = uses
                else:
                    break
            
            # 如果金额不在预设范围内，使用比例计算
            if total_amount > 0 and key_uses == admin_config.license_key_uses:
                key_uses = int(total_amount * admin_config.license_key_uses)
            
            # 确保最小使用次数
            if key_uses < 1:
                key_uses = 1
            
            # 生成卡密
            license_key = generate_license_key()
            
            # 创建卡密记录
            new_key = LicenseKey(
                key=license_key,
                max_uses=key_uses,
                remaining_uses=key_uses,
                is_active=True,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=365)  # 默认一年有效期
            )
            
            # 记录订单处理日志
            usage_log = UsageLog(
                user_id=1,  # 系统用户ID
                license_key_id=None,  # 先不关联卡密，等卡密创建后再更新
                timestamp=datetime.utcnow(),
                storyboard_file=f"order_{order_id}",  # 用订单ID标记
                success=True,
                error_message=None,
                ip_address=request.remote_addr
            )
            
            db.session.add(new_key)
            db.session.add(usage_log)
            db.session.commit()
            
            # 更新使用记录关联的卡密ID
            usage_log.license_key_id = new_key.id
            db.session.commit()
            
            results.append({
                'code': 200,
                'message': '卡密创建成功',
                'order_id': order_id,
                'data': {
                    'license_key': license_key,
                    'max_uses': key_uses,
                    'remaining_uses': key_uses
                }
            })
        
        # 返回所有订单处理结果
        return jsonify({
            'code': 200,
            'message': f'已处理 {len(results)} 个订单',
            'results': results
        })
    
    except Exception as e:
        return jsonify({
            'code': 500, 
            'message': f'服务器错误: {str(e)}'
        }), 500

@api_bp.route('/license/create', methods=['POST'])
def create_license():
    """
    创建卡密接口（管理员专用）
    
    接收参数:
    {
        "count": 1,           // 创建数量
        "max_uses": 50,       // 最大使用次数
        "expires_days": 365,  // 有效期天数
        "email": "",          // 可选，指定用户邮箱，将自动绑定
        "calculation_type": "fixed",  // 计算方式: fixed(固定), by_size(按大小), by_duration(按时长), by_count(按数量)
        "calculation_value": 50       // 计算数值，根据不同计算方式有不同含义
    }
    """
    try:
        # 验证管理员权限
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'code': 403, 'message': '无权限访问'}), 403
        
        data = request.json
        
        # 参数校验
        count = int(data.get('count', 1))
        max_uses = int(data.get('max_uses', 50))
        expires_days = int(data.get('expires_days', 365))
        email = data.get('email', '')
        calculation_type = data.get('calculation_type', 'fixed')
        calculation_value = float(data.get('calculation_value', 50))
        
        if count < 1:
            count = 1
        
        if max_uses < 1:
            max_uses = 1
        
        if expires_days < 1:
            expires_days = 1
        
        # 根据计算方式确定使用次数
        admin_config = AdminConfig.query.first()
        if not admin_config:
            admin_config = AdminConfig(
                trial_uses=3,              # 试用用户可用次数
                license_key_uses=50        # 默认卡密可用次数
            )
            db.session.add(admin_config)
            db.session.commit()
        
        # 找到指定用户（如果有）
        user_id = None
        if email:
            user = User.query.filter_by(email=email).first()
            if user:
                user_id = user.id
        
        # 验证计算方式
        valid_calculation_types = ['fixed', 'by_size', 'by_duration', 'by_count']
        if calculation_type not in valid_calculation_types:
            calculation_type = 'fixed'  # 默认使用固定方式
        
        # 生成卡密
        license_keys = []
        for _ in range(count):
            license_key = generate_license_key()
            
            # 根据计算类型添加前缀，方便识别
            prefix_map = {
                'fixed': 'F',      # 固定次数
                'by_size': 'S',    # 按大小
                'by_duration': 'D', # 按时长
                'by_count': 'C'    # 按数量
            }
            prefixed_key = f"{prefix_map.get(calculation_type, 'X')}-{license_key}"
            
            # 创建卡密记录，包含额外字段
            meta_info = {
                'calculation_type': calculation_type,
                'calculation_value': calculation_value
            }
            
            # 序列化元数据
            meta_json = json.dumps(meta_info)
            
            # 创建卡密记录
            new_key = LicenseKey(
                key=prefixed_key,
                user_id=user_id,  # 如果找到用户，则直接绑定
                max_uses=max_uses,
                remaining_uses=max_uses,
                is_active=True,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=expires_days),
                calculation_type=calculation_type,
                calculation_value=calculation_value,
                meta_info=meta_json
            )
            
            db.session.add(new_key)
            license_keys.append({
                'license_key': prefixed_key,
                'max_uses': max_uses,
                'remaining_uses': max_uses,
                'user_email': email if user_id else None,
                'calculation_type': calculation_type,
                'calculation_value': calculation_value,
                'expires_at': (datetime.utcnow() + timedelta(days=expires_days)).strftime('%Y-%m-%d %H:%M:%S')
            })
        
        db.session.commit()
        
        # 如果有用户邮箱，发送卡密邮件
        if email:
            try:
                from flask_mail import Message
                from app import mail
                
                html = f"<h2>【剪映草稿生成器】您的卡密信息</h2>"
                html += f"<p>以下是为您生成的{count}个卡密：</p><ul>"
                
                for key_info in license_keys:
                    html += f"<li>卡密: {key_info['license_key']} (可用次数: {key_info['remaining_uses']})</li>"
                
                html += "</ul>"
                html += f"<p>计算方式: {calculation_type}</p>"
                html += f"<p>过期时间: {license_keys[0]['expires_at']}</p>"
                
                msg = Message(
                    "【剪映草稿生成器】您的卡密信息",
                    recipients=[email],
                    html=html,
                    sender=current_app.config['MAIL_DEFAULT_SENDER']
                )
                
                mail.send(msg)
            except Exception as e:
                # 邮件发送失败不影响卡密创建
                pass
        
        return jsonify({
            'code': 200,
            'message': '卡密创建成功',
            'data': {
                'count': count,
                'calculation_type': calculation_type,
                'calculation_value': calculation_value,
                'license_keys': license_keys
            }
        })
    
    except Exception as e:
        return jsonify({'code': 500, 'message': f'服务器错误: {str(e)}'}), 500

@api_bp.route('/license/check', methods=['GET'])
def check_license():
    """
    检查卡密有效性和剩余次数
    
    参数:
    - key: 卡密
    """
    try:
        key = request.args.get('key', '')
        
        if not key:
            return jsonify({'code': 400, 'message': '缺少必要参数'}), 400
        
        # 查询卡密
        license_key = LicenseKey.query.filter_by(key=key).first()
        
        if not license_key:
            return jsonify({'code': 404, 'message': '卡密不存在'}), 404
        
        # 检查是否已过期
        if license_key.expires_at and license_key.expires_at < datetime.utcnow():
            return jsonify({'code': 400, 'message': '卡密已过期', 'data': {'is_valid': False}}), 400
        
        # 检查是否还有剩余次数
        if license_key.remaining_uses <= 0:
            return jsonify({'code': 400, 'message': '卡密已用尽', 'data': {'is_valid': False}}), 400
        
        # 检查是否已被禁用
        if not license_key.is_active:
            return jsonify({'code': 400, 'message': '卡密已被禁用', 'data': {'is_valid': False}}), 400
        
        # 获取计算类型，优先使用存储的计算类型，否则从前缀推断
        calc_type = license_key.calculation_type if license_key.calculation_type else license_key.get_calculation_type()
        
        # 尝试获取元数据
        meta_info = {}
        if license_key.meta_info:
            try:
                meta_info = json.loads(license_key.meta_info)
            except:
                pass
        
        # 返回卡密信息
        return jsonify({
            'code': 200,
            'message': '卡密有效',
            'data': {
                'is_valid': True,
                'key': license_key.key,
                'max_uses': license_key.max_uses,
                'remaining_uses': license_key.remaining_uses,
                'is_active': license_key.is_active,
                'created_at': license_key.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'expires_at': license_key.expires_at.strftime('%Y-%m-%d %H:%M:%S') if license_key.expires_at else None,
                'calculation_type': calc_type,
                'calculation_value': license_key.calculation_value,
                'meta_info': meta_info
            }
        })
    
    except Exception as e:
        return jsonify({'code': 500, 'message': f'服务器错误: {str(e)}'}), 500

@api_bp.route('/license/use', methods=['POST'])
def use_license():
    """
    使用卡密（减少剩余次数）
    
    参数:
    {
        "key": "卡密",
        "size": 0,       // 可选，数据包大小（字节）
        "duration": 0,   // 可选，音频总时长（秒或毫秒）
        "count": 0       // 可选，素材数量
        "calculation_type": "fixed" // 可选，计算方式: fixed(固定), by_size(按大小), by_duration(按时长), by_count(按数量)
    }
    """
    try:
        data = request.json
        
        # 参数校验
        if not data or 'key' not in data:
            return jsonify({'code': 400, 'message': '缺少必要参数'}), 400
        
        key = data.get('key', '')
        size_bytes = int(data.get('size', 0))
        duration = float(data.get('duration', 0))
        material_count = int(data.get('count', 0))
        calculation_type = data.get('calculation_type', 'fixed')
        
        # 获取管理员配置
        admin_config = AdminConfig.query.first()
        if not admin_config:
            admin_config = AdminConfig(
                trial_uses=3,
                license_key_uses=50
            )
            db.session.add(admin_config)
            db.session.commit()
        
        # 查询卡密
        license_key = LicenseKey.query.filter_by(key=key).first()
        
        if not license_key:
            return jsonify({'code': 404, 'message': '卡密不存在'}), 404
        
        # 检查是否已过期
        if license_key.expires_at and license_key.expires_at < datetime.utcnow():
            return jsonify({'code': 400, 'message': '卡密已过期'}), 400
        
        # 检查是否还有剩余次数
        if license_key.remaining_uses <= 0:
            return jsonify({'code': 400, 'message': '卡密已用尽'}), 400
        
        # 检查是否已被禁用
        if not license_key.is_active:
            return jsonify({'code': 400, 'message': '卡密已被禁用'}), 400
        
        # 根据计算方式确定扣除的次数
        uses_to_deduct = 1  # 默认扣除1次
        
        if calculation_type == 'by_size':
            # 按数据包大小计算（每10MB扣除1次）
            if size_bytes > 0:
                # 转换为MB
                size_mb = size_bytes / (1024 * 1024)
                uses_to_deduct = max(1, int(size_mb / 10))
        
        elif calculation_type == 'by_duration':
            # 按音频时长计算（每10分钟扣除1次）
            if duration > 0:
                # 处理毫秒格式
                if duration > 10000:  # 判断为毫秒格式
                    duration = duration / 1000  # 转换为秒
                
                # 转换为分钟
                duration_min = duration / 60
                uses_to_deduct = max(1, int(duration_min / 10))
        
        elif calculation_type == 'by_count':
            # 按素材数量计算（每5个素材扣除1次）
            if material_count > 0:
                uses_to_deduct = max(1, int(material_count / 5))
        
        # 确保不超过剩余使用次数
        uses_to_deduct = min(uses_to_deduct, license_key.remaining_uses)
        
        # 更新剩余次数
        license_key.remaining_uses -= uses_to_deduct
        
        # 记录使用日志
        user_id = license_key.user_id if license_key.user_id else 1  # 系统用户ID
        usage_log = UsageLog(
            user_id=user_id,
            license_key_id=license_key.id,
            timestamp=datetime.utcnow(),
            storyboard_file=f"api_use_{calculation_type}",
            success=True,
            error_message=None,
            ip_address=request.remote_addr
        )
        
        db.session.add(usage_log)
        db.session.commit()
        
        # 返回更新后的卡密信息
        return jsonify({
            'code': 200,
            'message': '卡密使用成功',
            'data': {
                'key': license_key.key,
                'max_uses': license_key.max_uses,
                'remaining_uses': license_key.remaining_uses,
                'used': uses_to_deduct,
                'calculation_type': calculation_type
            }
        })
    
    except Exception as e:
        return jsonify({'code': 500, 'message': f'服务器错误: {str(e)}'}), 500

@api_bp.route('/generator/draft', methods=['POST'])
def generate_draft():
    """
    通过API生成草稿文件
    
    参数:
    {
        "key": "卡密",
        "storyboard": {},     // storyboard.json的内容
        "template": "标准",    // 可选，模板名称
        "draft_name": "草稿名称" // 可选，草稿名称
    }
    """
    try:
        from utils.generator import generate_capcut_draft
        from utils.template import create_draft_zip
        import tempfile
        
        data = request.json
        
        # 参数校验
        if not data or 'key' not in data or 'storyboard' not in data:
            return jsonify({'code': 400, 'message': '缺少必要参数'}), 400
        
        key = data.get('key', '')
        storyboard_data = data.get('storyboard', {})
        template_name = data.get('template', '')
        draft_name = data.get('draft_name', '')
        
        # 校验卡密
        license_key = LicenseKey.query.filter_by(key=key).first()
        
        if not license_key:
            return jsonify({'code': 404, 'message': '卡密不存在'}), 404
        
        # 检查是否已过期
        if license_key.expires_at and license_key.expires_at < datetime.utcnow():
            return jsonify({'code': 400, 'message': '卡密已过期'}), 400
        
        # 检查是否还有剩余次数
        if license_key.remaining_uses <= 0:
            return jsonify({'code': 400, 'message': '卡密已用尽'}), 400
        
        # 检查是否已被禁用
        if not license_key.is_active:
            return jsonify({'code': 400, 'message': '卡密已被禁用'}), 400
        
        # 将storyboard数据写入临时文件
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        temp_file.close()
        
        with open(temp_file.name, 'w', encoding='utf-8') as f:
            json.dump(storyboard_data, f, ensure_ascii=False, indent=2)
        
        try:
            # 生成草稿
            draft_id = generate_capcut_draft(temp_file.name, template_name, None, draft_name)
            
            # 创建ZIP文件
            zip_path = create_draft_zip(draft_id)
            
            # 获取卡密的计算类型
            calculation_type = license_key.calculation_type if license_key.calculation_type else license_key.get_calculation_type()
            
            # 根据卡密类型计算使用次数
            uses_to_deduct = 1  # 默认扣除1次
            
            if calculation_type == 'by_size':
                # 尝试获取storyboard的大小
                storyboard_size = len(json.dumps(storyboard_data).encode('utf-8'))
                size_mb = storyboard_size / (1024 * 1024)
                uses_to_deduct = max(1, int(size_mb / 10))  # 每10MB扣1次
                
            elif calculation_type == 'by_duration':
                # 尝试从storyboard中提取总时长
                try:
                    from utils.generator import extract_audio_duration
                    duration_sec = extract_audio_duration(storyboard_data)
                    if duration_sec > 0:
                        duration_min = duration_sec / 60
                        uses_to_deduct = max(1, int(duration_min / 10))  # 每10分钟扣1次
                except:
                    pass
                    
            elif calculation_type == 'by_count':
                # 尝试从storyboard中获取素材数量
                try:
                    material_count = 0
                    if 'scenes' in storyboard_data:
                        scenes = storyboard_data['scenes']
                        for scene in scenes:
                            if 'elements' in scene:
                                material_count += len(scene['elements'])
                    if material_count > 0:
                        uses_to_deduct = max(1, int(material_count / 5))  # 每5个素材扣1次
                except:
                    pass
            
            # 确保不超过剩余使用次数
            uses_to_deduct = min(uses_to_deduct, license_key.remaining_uses)
            
            # 减少卡密使用次数
            license_key.remaining_uses -= uses_to_deduct
            
            # 记录使用日志
            user_id = license_key.user_id if license_key.user_id else 1
            usage_log = UsageLog(
                user_id=user_id,
                license_key_id=license_key.id,
                timestamp=datetime.utcnow(),
                storyboard_file=f"draft_{draft_id}",
                success=True,
                error_message=None,
                ip_address=request.remote_addr
            )
            
            db.session.add(usage_log)
            db.session.commit()
            
            # 返回下载链接
            download_url = request.host_url.rstrip('/') + f'/temp/{os.path.basename(zip_path)}'
            
            return jsonify({
                'code': 200,
                'message': '草稿生成成功',
                'data': {
                    'draft_id': draft_id,
                    'download_url': download_url
                }
            })
        
        finally:
            # 清理临时文件
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
    except Exception as e:
        return jsonify({'code': 500, 'message': f'服务器错误: {str(e)}'}), 500