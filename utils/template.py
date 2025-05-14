
import os
import json
import uuid
import zipfile
import time
from datetime import datetime
from flask import current_app

def create_draft_folder(draft_json, project_id):
    """
    创建剪映草稿文件夹结构
    """
    # 创建草稿文件夹
    draft_folder = os.path.join(current_app.config['TEMP_FOLDER'], project_id)
    os.makedirs(draft_folder, exist_ok=True)
    
    # 创建素材文件夹
    material_id = str(uuid.uuid4())
    material_folder = os.path.join(draft_folder, material_id)
    os.makedirs(material_folder, exist_ok=True)
    
    # 保存草稿文件
    save_draft_files(draft_json, draft_folder, project_id, material_id, project_id)
    
    return draft_folder

def save_draft_files(draft_template, draft_folder, draft_id, materials_folder_name, draft_name):
    """保存草稿文件"""
    # 保存draft_content.json
    with open(os.path.join(draft_folder, 'draft_content.json'), 'w', encoding='utf-8') as f:
        json.dump(draft_template, f, ensure_ascii=False, indent=2)

    # 保存draft_info.json - 与content相同的内容
    with open(os.path.join(draft_folder, 'draft_info.json'), 'w', encoding='utf-8') as f:
        json.dump(draft_template, f, ensure_ascii=False, indent=2)

    # 保存素材文件夹的元数据文件
    with open(os.path.join(draft_folder, f'{materials_folder_name}.json'), 'w', encoding='utf-8') as f:
        json.dump(draft_template, f, ensure_ascii=False, indent=2)

    # 创建meta_info文件
    create_draft_meta_info(draft_folder, draft_id, draft_name)
    
    return draft_folder

def create_draft_meta_info(draft_folder, draft_id, draft_name):
    """创建草稿元信息文件"""
    # 当前时间戳（微秒级）
    current_time = int(time.time() * 1000000)
    
    # 默认根路径
    draft_root_path = "H:\\缓存\\剪映草稿\\JianyingPro Drafts"
    draft_removable_storage_device = "H:"
    
    # 构建完整的草稿路径
    draft_fold_path = f"{draft_removable_storage_device}/缓存/剪映草稿/JianyingPro Drafts/{draft_name}"
    
    meta_info = {
        "cloud_package_completed_time": "",
        "draft_cloud_capcut_purchase_info": "",
        "draft_cloud_last_action_download": False,
        "draft_cloud_package_type": "",
        "draft_cloud_purchase_info": "",
        "draft_cloud_template_id": "",
        "draft_cloud_tutorial_info": "",
        "draft_cloud_videocut_purchase_info": "",
        "draft_cover": "draft_cover.jpg",
        "draft_deeplink_url": "",
        "draft_enterprise_info": {
            "draft_enterprise_extra": "",
            "draft_enterprise_id": "",
            "draft_enterprise_name": "",
            "enterprise_material": []
        },
        "draft_fold_path": draft_fold_path,
        "draft_id": draft_id.upper(),
        "draft_is_ae_produce": False,
        "draft_is_ai_packaging_used": False,
        "draft_is_ai_shorts": False,
        "draft_is_ai_translate": False,
        "draft_is_article_video_draft": False,
        "draft_is_from_deeplink": "false",
        "draft_is_invisible": False,
        "draft_materials": [
            {"type": 0, "value": []},
            {"type": 1, "value": []},
            {"type": 2, "value": []},
            {"type": 3, "value": []},
            {"type": 6, "value": []},
            {"type": 7, "value": []},
            {"type": 8, "value": []}
        ],
        "draft_materials_copied_info": [],
        "draft_name": draft_name,
        "draft_need_rename_folder": False,
        "draft_new_version": "",
        "draft_removable_storage_device": draft_removable_storage_device,
        "draft_root_path": draft_root_path,
        "draft_segment_extra_info": [],
        "draft_timeline_materials_size_": 2075,
        "draft_type": "",
        "tm_draft_cloud_completed": "",
        "tm_draft_cloud_modified": 0,
        "tm_draft_cloud_space_id": -1,
        "tm_draft_create": current_time,
        "tm_draft_modified": current_time + 3000000,
        "tm_draft_removed": 0
    }
    
    with open(os.path.join(draft_folder, 'draft_meta_info.json'), 'w', encoding='utf-8') as f:
        json.dump(meta_info, f, ensure_ascii=False, indent=2)

def create_draft_zip(draft_id):
    """创建草稿ZIP文件"""
    draft_folder = os.path.join(current_app.config['TEMP_FOLDER'], draft_id)
    
    # 从draft_meta_info.json中获取draft_name
    meta_info_path = os.path.join(draft_folder, 'draft_meta_info.json')
    if os.path.exists(meta_info_path):
        with open(meta_info_path, 'r', encoding='utf-8') as f:
            meta_info = json.load(f)
            draft_name = meta_info.get('draft_name', draft_id)
    else:
        draft_name = draft_id
    
    zip_path = os.path.join(current_app.config['TEMP_FOLDER'], f'{draft_name}.zip')
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(draft_folder):
            for file in files:
                file_path = os.path.join(root, file)
                # 修复：直接使用文件名作为ZIP中的路径，不包含父文件夹
                if root == draft_folder:
                    # 根目录文件直接添加
                    arcname = file
                else:
                    # 子目录文件保留子目录结构
                    arcname = os.path.relpath(file_path, draft_folder)
                zipf.write(file_path, arcname)
    
    return zip_path
