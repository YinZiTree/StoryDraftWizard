import os
import json
import uuid
import shutil
import time
import zipfile
from datetime import datetime
from flask import current_app
import requests
from PIL import Image
from io import BytesIO
from mutagen import File as MutagenFile
from mutagen.wave import WAVE  # For WAV files
from mutagen.mp3 import MP3    # For MP3 files

def allowed_file(filename):
    """检查文件类型是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def extract_audio_duration(storyboard_data):
    """从storyboard.json提取音频时长"""
    total_duration = 0
    scenes = storyboard_data.get('data', [])
    for scene in scenes:
        # 默认场景时长为3秒
        scene_duration = 3 * 1000000  # 默认值，单位微秒
        
        # 检查是否有音频信息
        if 'audio_info' in scene:
            # 优先从duration字段获取时长（毫秒单位）
            if 'duration' in scene['audio_info']:
                duration_ms = scene['audio_info']['duration']
                scene_duration = int(duration_ms * 1000)  # 转换为微秒
                print(f"从duration字段获取时长: {duration_ms} 毫秒 ({scene_duration} 微秒)")
            # 其次尝试从音频文件获取时长
            elif 'path' in scene['audio_info']:
                audio_path = scene['audio_info']['path']
                try:
                    if os.path.exists(audio_path):
                        audio = MutagenFile(audio_path)
                        if audio and audio.info:
                            duration_seconds = audio.info.length
                            scene_duration = int(duration_seconds * 1000000)
                except Exception:
                    pass  # 使用默认时长
        
        total_duration += scene_duration
    return total_duration

def create_default_image(path, width, height):
    """创建默认图片"""
    img = Image.new('RGB', (width, height), color=(240, 240, 240))
    img.save(path)

def create_empty_audio(path):
    """创建空音频文件"""
    # 创建一个空的MP3文件
    with open(path, 'wb') as f:
        # 写入一个最小的MP3头
        f.write(b'\xFF\xFB\x90\x44\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

def create_track(track_type):
    """创建轨道"""
    return {
        "attribute": 0,
        "flag": 3,
        "id": str(uuid.uuid4()),
        "segments": [],
        "type": track_type
    }

def get_available_templates():
    """获取所有可用的模板"""
    templates = []
    template_folder = os.path.join(current_app.config['TEMP_FOLDER'], 'templates')
    os.makedirs(template_folder, exist_ok=True)

    template_files = []
    for root, _, files in os.walk(template_folder):
        for file in files:
            if file.endswith('.json'):
                template_files.append(os.path.join(root, file))

    for template_file in template_files:
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
                templates.append({
                    'name': template_data.get('name', os.path.basename(template_file)),
                    'file': os.path.basename(template_file),
                    'effect_type': template_data.get('template', {}).get('effect_type', '标准'),
                    'font_type': template_data.get('template', {}).get('font_type', '默认')
                })
        except Exception as e:
            print(f"读取模板文件 {template_file} 时出错: {str(e)}")

    # 如果没有模板，添加默认模板
    if not templates:
        templates.append({
            'name': '标准模板',
            'file': 'standard.json',
            'effect_type': '标准',
            'font_type': '默认'
        })

    return templates

def load_template(template_name):
    """加载指定的模板"""
    template_path = os.path.join(current_app.config['TEMP_FOLDER'], 'templates', template_name)

    # 如果没有扩展名，添加.json
    if not template_path.endswith('.json'):
        template_path += '.json'

    # 如果文件不存在，使用默认模板
    if not os.path.exists(template_path):
        template_path = os.path.join(os.path.dirname(__file__), 'draft_template.json')

    if not os.path.exists(template_path):
        return None

    with open(template_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def add_image_material(draft_template, image_id, image_filename, materials_folder_name, draft_id):
    """添加图片素材"""
    image_data = {
        "aigc_type": "none",
        "audio_fade": None,
        "cartoon_path": "",
        "category_id": "",
        "category_name": "",
        "check_flag": 63487,
        "crop": {
            "lower_left_x": 0,
            "lower_left_y": 1,
            "lower_right_x": 1,
            "lower_right_y": 1,
            "upper_left_x": 0,
            "upper_left_y": 0,
            "upper_right_x": 1,
            "upper_right_y": 0
        },
        "crop_ratio": "free",
        "crop_scale": 1,
        "duration": 5000000,
        "extra_type_option": 0,
        "formula_id": "",
        "freeze": None,
        "has_audio": False,
        "height": 1024,
        "id": image_id,
        "intensifies_audio_path": "",
        "intensifies_path": "",
        "is_ai_generate_content": False,
        "is_copyright": False,
        "is_text_edit_overdub": False,
        "is_unified_beauty_mode": False,
        "local_id": "",
        "local_material_id": "",
        "material_id": "",
        "material_name": str(uuid.uuid4()),
        "material_url": "",
        "matting": {
            "flag": 0,
            "has_use_quick_brush": False,
            "has_use_quick_eraser": False,
            "interactiveTime": [],
            "path": "",
            "strokes": []
        },
        "media_path": "",
        "object_locked": None,
        "origin_material_id": "",
        "path": f"##_draftpath_placeholder_0E685133-18CE-45ED-8CB8-2904A212EC80_##\\{materials_folder_name}\\{image_filename}",
        "picture_from": "none",
        "picture_set_category_id": "",
        "picture_set_category_name": "",
        "request_id": "",
        "reverse_intensifies_path": "",
        "reverse_path": "",
        "smart_motion": None,
        "source": 0,
        "source_platform": 0,
        "stable": {
            "matrix_path": "",
            "stable_level": 0,
            "time_range": {
                "duration": 5000000,
                "start": 0
            }
        },
        "team_id": "",
        "type": "photo",
        "video_algorithm": {
            "algorithms": [],
            "complement_frame_config": None,
            "deflicker": None,
            "gameplay_configs": [],
            "motion_blur_config": None,
            "noise_reduction": None,
            "path": "",
            "quality_enhance": None,
            "time_range": None
        },
        "width": 1024
    }

    draft_template["materials"]["videos"].append(image_data)
    return image_id

def add_audio_material(draft_template, audio_id, audio_filename, materials_folder_name, draft_id):
    """添加音频素材"""
    audio_data = {
        "app_id": 0,
        "category_id": "",
        "category_name": "local",
        "check_flag": 1,
        "copyright_limit_type": "none",
        "effect_id": "",
        "formula_id": "",
        "id": audio_id,
        "intensifies_path": "",
        "is_ai_clone_tone": False,
        "is_text_edit_overdub": False,
        "is_ugc": False,
        "local_material_id": "",
        "music_id": "",
        "name": str(uuid.uuid4()),
        "path": f"##_draftpath_placeholder_0E685133-18CE-45ED-8CB8-2904A212EC80_##\\{materials_folder_name}\\{audio_filename}",
        "query": "",
        "request_id": "",
        "resource_id": "",
        "search_id": "",
        "source_from": "",
        "source_platform": 0,
        "team_id": "",
        "text_id": "",
        "tone_category_id": "",
        "tone_category_name": "",
        "tone_effect_id": "",
        "tone_effect_name": "",
        "tone_platform": "",
        "tone_second_category_id": "",
        "tone_second_category_name": "",
        "tone_speaker": "",
        "tone_type": "",
        "type": "extract_music",
        "video_id": "",
        "wave_points": []
    }

    draft_template["materials"]["audios"].append(audio_data)
    return audio_id

def add_text_material(draft_template, text_id, text_content, font_style=None):
    """添加文本素材"""
    # 使用指定的字体样式或默认样式
    if not font_style:
        font_style = {
            'id': '7244518590332801592',
            'path': '抖音美好体.ttf',
            'size': 8,
            'color': [1, 1, 1]  # 默认白色
        }

    font_id = font_style.get('id', '7244518590332801592')
    font_path = font_style.get('path', '抖音美好体.ttf')
    font_size = font_style.get('size', 8)
    font_color = font_style.get('color', [1, 1, 1])  # 默认白色

    text_data = {
        "add_type": 0,
        "alignment": 1,
        "background_alpha": 1,
        "background_color": "",
        "background_height": 0.14,
        "background_horizontal_offset": 0,
        "background_round_radius": 0,
        "background_style": 0,
        "background_vertical_offset": 0,
        "background_width": 0.14,
        "base_content": "",
        "bold_width": 0,
        "border_alpha": 1,
        "border_color": "",
        "border_width": 0.08,
        "caption_template_info": {
            "category_id": "",
            "category_name": "",
            "effect_id": "",
            "is_new": False,
            "path": "",
            "request_id": "",
            "resource_id": "",
            "resource_name": "",
            "source_platform": 0
        },
        "check_flag": 7,
        "combo_info": {
            "text_templates": []
        },
        "content": json.dumps({
            "styles": [{
                "fill": {
                    "content": {
                        "solid": {
                            "color": font_color
                        }
                    }
                },
                "range": [0, len(text_content)],
                "size": font_size,
                "font": {
                    "id": font_id,
                    "path": font_path
                }
            }],
            "text": text_content
        }, ensure_ascii=False),
        "fixed_height": -1,
        "fixed_width": -1,
        "font_category_id": "",
        "font_category_name": "",
        "font_id": font_id,
        "font_name": font_path.replace('.ttf', ''),
        "font_path": "/Applications/VideoFusion-macOS.app/Contents/Resources/Font/SystemFont/zh-hans.ttf",
        "font_resource_id": "",
        "font_size": 15,
        "font_source_platform": 0,
        "font_team_id": "",
        "font_title": "none",
        "font_url": "",
        "fonts": [{
            "effect_id": font_id,
            "id": font_id,
            "path": font_path,
            "resource_id": font_id,
            "title": font_path.replace('.ttf', '')
        }],
        "force_apply_line_max_width": False,
        "global_alpha": 1,
        "group_id": "",
        "has_shadow": False,
        "id": text_id,
        "initial_scale": 1,
        "inner_padding": -1,
        "is_rich_text": True,
        "italic_degree": 0,
        "ktv_color": "",
        "language": "",
        "layer_weight": 1,
        "letter_spacing": 0.1,
        "line_feed": 1,
        "line_max_width": 0.82,
        "line_spacing": 0.1,
        "multi_language_current": "none",
        "name": "",
        "original_size": [],
        "preset_category": "",
        "preset_category_id": "",
        "preset_has_set_alignment": False,
        "preset_id": "",
        "preset_index": 0,
        "preset_name": "",
        "recognize_task_id": "",
        "recognize_type": 0,
        "relevance_segment": [],
        "shadow_alpha": 0.9,
        "shadow_angle": -45,
        "shadow_color": "",
        "shadow_distance": 5,
        "shadow_point": {
            "x": 0.6363961030678928,
            "y": -0.6363961030678927
        },
        "shadow_smoothing": 0.45,
        "shape_clip_x": False,
        "shape_clip_y": False,
        "source_from": "",
        "style_name": "",
        "sub_type": 0,
        "subtitle_keywords": None,
        "subtitle_template_original_fontsize": 0,
        "text_alpha": 1,
        "text_color": "#ffffff",
        "text_curve": None,
        "text_preset_resource_id": "",
        "text_size": 30,
        "text_to_audio_ids": [],
        "tts_auto_update": False,
        "type": "subtitle",
        "typesetting": 0,
        "underline": False,
        "underline_offset": 0.22,
        "underline_width": 0.05,
        "use_effect_default_color": False,
        "words": {
            "end_time": [],
            "start_time": [],
            "text": []
        },
        "path": font_path
    }

    draft_template["materials"]["texts"].append(text_data)
    return text_id

def add_image_segment(track, image_id, start_time, duration, keyframes=None):
    """添加图片片段到轨道"""
    segment = {
        "caption_info": None,
        "cartoon": False,
        "clip": {
            "alpha": 1,
            "flip": {
                "horizontal": False,
                "vertical": False
            },
            "rotation": 0,
            "scale": {
                "x": 1,
                "y": 1
            },
            "transform": {
                "x": -2,
                "y": 0
            }
        },
        "common_keyframes": [],
        "enable_adjust": True,
        "enable_color_correct_adjust": False,
        "enable_color_curves": True,
        "enable_color_match_adjust": False,
        "enable_color_wheels": True,
        "enable_lut": True,
        "enable_smart_color_adjust": False,
        "extra_material_refs": [],
        "group_id": "",
        "hdr_settings": {
            "intensity": 1,
            "mode": 1,
            "nits": 1000
        },
        "id": str(uuid.uuid4()),
        "intensifies_audio": False,
        "is_placeholder": False,
        "is_tone_modify": False,
        "keyframe_refs": [],
        "last_nonzero_volume": 1,
        "material_id": image_id,
        "render_index": 1,
        "responsive_layout": {
            "enable": False,
            "horizontal_pos_layout": 0,
            "size_layout": 0,
            "target_follow": "",
            "vertical_pos_layout": 0
        },
        "reverse": False,
        "source_timerange": {
            "duration": duration,
            "start": 0
        },
        "speed": 1,
        "target_timerange": {
            "duration": duration,
            "start": start_time
        },
        "template_id": "",
        "template_scene": "default",
        "track_attribute": 0,
        "track_render_index": 3,
        "uniform_scale": {
            "on": True,
            "value": 1
        },
        "visible": True,
        "volume": 1
    }

    # 添加关键帧
    if keyframes:
        for keyframe in keyframes:
            # 为每个片段创建新的关键帧ID
            new_keyframe = {
                "id": str(uuid.uuid4()),
                "keyframe_list": [],
                "material_id": "",
                "property_type": keyframe.get("property_type", "KFTypePositionX")
            }

            # 为每个关键帧点创建新的ID
            for kf_point in keyframe.get("keyframe_list", []):
                new_point = {
                    "curveType": kf_point.get("curveType", "Line"),
                    "graphID": "",
                    "left_control": kf_point.get("left_control", []),
                    "right_control": kf_point.get("right_control", []),
                    "id": str(uuid.uuid4()),
                    "time_offset": kf_point.get("time_offset", 0),
                    "values": kf_point.get("values", [0])
                }
                new_keyframe["keyframe_list"].append(new_point)

            segment["common_keyframes"].append(new_keyframe)

    track["segments"].append(segment)
    return segment["id"]

def add_audio_segment(track, audio_id, start_time, duration):
    """添加音频片段到轨道"""
    segment = {
        "caption_info": None,
        "cartoon": False,
        "clip": {
            "alpha": 1,
            "flip": {
                "horizontal": False,
                "vertical": False
            },
            "rotation": 0,
            "scale": {
                "x": 1,
                "y": 1
            },
            "transform": {
                "x": 0,
                "y": 0
            }
        },
        "common_keyframes": [],
        "enable_adjust": True,
        "enable_color_correct_adjust": False,
        "enable_color_curves": True,
        "enable_color_match_adjust": False,
        "enable_color_wheels": True,
        "enable_lut": True,
        "enable_smart_color_adjust": False,
        "extra_material_refs": [],
        "group_id": "",
        "hdr_settings": {
            "intensity": 1,
            "mode": 1,
            "nits": 1000
        },
        "id": str(uuid.uuid4()),
        "intensifies_audio": False,
        "is_placeholder": False,
        "is_tone_modify": False,
        "keyframe_refs": [],
        "last_nonzero_volume": 1,
        "material_id": audio_id,
        "render_index": 1,
        "responsive_layout": {
            "enable": False,
            "horizontal_pos_layout": 0,
            "size_layout": 0,
            "target_follow": "",
            "vertical_pos_layout": 0
        },
        "reverse": False,
        "source_timerange": {
            "duration": duration,
            "start": 0
        },
        "speed": 1,
        "target_timerange": {
            "duration": duration,
            "start": start_time
        },
        "template_id": "",
        "template_scene": "default",
        "track_attribute": 0,
        "track_render_index": 3,
        "uniform_scale": {
            "on": True,
            "value": 1
        },
        "visible": True,
        "volume": 1
    }

    track["segments"].append(segment)
    return segment["id"]

def add_text_segment(track, text_id, start_time, duration):
    """添加文本片段到轨道"""
    segment = {
        "caption_info": None,
        "cartoon": False,
        "clip": {
            "alpha": 1,
            "flip": {
                "horizontal": False,
                "vertical": False
            },
            "rotation": 0,
            "scale": {
                "x": 1,
                "y": 1
            },
            "transform": {
                "x": 0,
                "y": -0.8854166666666666
            }
        },
        "common_keyframes": [],
        "enable_adjust": True,
        "enable_color_correct_adjust": False,
        "enable_color_curves": True,
        "enable_color_match_adjust": False,
        "enable_color_wheels": True,
        "enable_lut": True,
        "enable_smart_color_adjust": False,
        "extra_material_refs": [],
        "group_id": "",
        "hdr_settings": {
            "intensity": 1,
            "mode": 1,
            "nits": 1000
        },
        "id": str(uuid.uuid4()),
        "intensifies_audio": False,
        "is_placeholder": False,
        "is_tone_modify": False,
        "keyframe_refs": [],
        "last_nonzero_volume": 1,
        "material_id": text_id,
        "render_index": 1,
        "responsive_layout": {
            "enable": False,
            "horizontal_pos_layout": 0,
            "size_layout": 0,
            "target_follow": "",
            "vertical_pos_layout": 0
        },
        "reverse": False,
        "source_timerange": {
            "duration": duration,
            "start": 0
        },
        "speed": 1,
        "target_timerange": {
            "duration": duration,
            "start": start_time
        },
        "template_id": "",
        "template_scene": "default",
        "track_attribute": 0,
        "track_render_index": 3,
        "uniform_scale": {
            "on": True,
            "value": 1
        },
        "visible": True,
        "volume": 1
    }

    track["segments"].append(segment)
    return segment["id"]

def create_base_draft_template(draft_id):
    """创建基础草稿模板"""
    return {
        "canvas_config": {
            "height": 1920,
            "ratio": "original",
            "width": 1080
        },
        "color_space": -1,
        "config": {
            "adjust_max_index": 1,
            "attachment_info": [],
            "combination_max_index": 1,
            "export_range": None,
            "extract_audio_last_index": 1,
            "lyrics_recognition_id": "",
            "lyrics_sync": True,
            "lyrics_taskinfo": [],
            "maintrack_adsorb": True,
            "material_save_mode": 0,
            "multi_language_current": "none",
            "multi_language_list": [],
            "multi_language_main": "none",
            "multi_language_mode": "none",
            "original_sound_last_index": 1,
            "record_audio_last_index": 1,
            "sticker_max_index": 1,
            "subtitle_keywords_config": None,
            "subtitle_recognition_id": "",
            "subtitle_sync": True,
            "subtitle_taskinfo": [],
            "system_font_list": [],
            "video_mute": False,
            "zoom_info_params": None
        },
        "cover": None,
        "create_time": 0,
        "duration": 10000000,
        "extra_info": None,
        "fps": 30,
        "free_render_index_mode_on": False,
        "group_container": None,
        "id": draft_id,
        "is_drop_frame_timecode": False,
        "keyframe_graph_list": [],
        "keyframes": {
            "adjusts": [],
            "audios": [],
            "effects": [],
            "filters": [],
            "handwrites": [],
            "stickers": [],
            "texts": [],
            "videos": []
        },
        "lyrics_effects": [],
        "materials": {
            "ai_translates": [],
            "audio_balances": [],
            "audio_effects": [],
            "audio_fades": [],
            "audio_track_indexes": [],
            "audios": [],
            "beats": [],
            "canvases": [],
            "chromas": [],
            "color_curves": [],
            "masks": [],
            "digital_humans": [],
            "drafts": [],
            "effects": [],
            "flowers": [],
            "green_screens": [],
            "handwrites": [],
            "hsl": [],
            "images": [],
            "log_color_wheels": [],
            "loudnesses": [],
            "manual_deformations": [],
            "material_animations": [],
            "material_colors": [],
            "multi_language_refs": [],
            "placeholder_infos": [],
            "placeholders": [],
            "plugin_effects": [],
            "primary_color_wheels": [],
            "realtime_denoises": [],
            "shapes": [],
            "smart_crops": [],
            "smart_relights": [],
            "sound_channel_mappings": [],
            "speeds": [],
            "stickers": [],
            "tail_leaders": [],
            "text_templates": [],
            "texts": [],
            "time_marks": [],
            "transitions": [],
            "video_effects": [],
            "video_trackings": [],
            "videos": [],
            "vocal_beautifys": [],
            "vocal_separations": []
        },
        "mutable_config": None,
        "name": "",
        "new_version": "110.0.0",
        "path": "",
        "relationships": [],
        "render_index_track_mode_on": True,
        "retouch_cover": None,
        "source": "default",
        "static_cover_image_path": "",
        "time_marks": None,
        "tracks": [{
            "attribute": 0,
            "flag": 0,
            "id": "2D0629D7-BC55-4A90-867A-C078CFEEE0D2",
            "segments": [],
            "type": "video"
        }],
        "update_time": 0,
        "version": 360000,
        "platform": {
            "app_id": 3704,
            "app_source": "lv",
            "app_version": "5.9.0",
            "device_id": str(uuid.uuid4()).replace("-", ""),
            "hard_disk_id": str(uuid.uuid4()).replace("-", ""),
            "mac_address": str(uuid.uuid4()).replace("-", ""),
            "os": "mac",
            "os_version": "14.5"
        },
        "last_modified_platform": {
            "app_id": 3704,
            "app_source": "cc",
            "app_version": "5.9.0",
            "device_id": str(uuid.uuid4()).replace("-", ""),
            "hard_disk_id": str(uuid.uuid4()).replace("-", ""),
            "mac_address": str(uuid.uuid4()).replace("-", ""),
            "os": "mac",
            "os_version": "14.5"
        }
    }

def process_scenes(draft_template, scenes, materials_folder, materials_folder_name, draft_id, keyframes=None, font_style=None):
    """处理场景数据，添加到草稿中"""
    # 创建轨道
    video_track = create_track("video")
    image_track = create_track("video")
    audio_track = create_track("audio")
    text_track = create_track("text")

    # 添加轨道到草稿
    draft_template["tracks"].append(video_track)
    draft_template["tracks"].append(image_track)
    draft_template["tracks"].append(audio_track)
    draft_template["tracks"].append(text_track)

    # 处理场景
    current_time = 0
    for i, scene in enumerate(scenes):
        # 默认场景时长为3秒
        scene_duration = 3 * 1000000  # 默认值，单位微秒
        
        # 检查是否有音频信息
        if 'audio_info' in scene:
            # 优先从duration字段获取时长（毫秒单位）
            if 'duration' in scene['audio_info']:
                duration_ms = scene['audio_info']['duration']
                scene_duration = int(duration_ms * 1000)  # 转换为微秒
                print(f"场景 {i}: 从duration字段获取时长: {duration_ms} 毫秒 ({scene_duration} 微秒)")
            # 其次尝试从音频文件获取时长
            elif 'path' in scene['audio_info']:
                audio_path = scene['audio_info']['path']
                try:
                    # 检查文件是否存在
                    if os.path.exists(audio_path):
                        # 使用 mutagen 读取音频时长
                        audio = MutagenFile(audio_path)
                        if audio and audio.info:
                            duration_seconds = audio.info.length
                            scene_duration = int(duration_seconds * 1000000)
                            print(f"场景 {i}: 从音频文件 {os.path.basename(audio_path)} 获取时长: {duration_seconds:.2f} 秒")
                        else:
                            print(f"警告: 无法读取音频文件 {os.path.basename(audio_path)} 的时长信息，使用默认值 3 秒。")
                    else:
                        print(f"警告: 音频文件不存在: {audio_path}，使用默认值 3 秒。")
                except Exception as e:
                    print(f"警告: 读取音频文件 {audio_path} 时长出错: {str(e)}，使用默认值 3 秒。")
            else:
                print(f"警告: 场景 {i} 音频信息中未找到时长和路径，使用默认值 3 秒。")
        else:
            print(f"警告: 场景 {i} 未找到音频信息，使用默认值 3 秒。")

        # 处理图片
        if 'image_paths' in scene and scene['image_paths']:
            # 为简化示例，假设每个场景只有一个图片
            image_path = scene['image_paths'][0] if isinstance(scene['image_paths'], list) else scene['image_paths']
            image_filename = f"image_{i}_{str(uuid.uuid4())[:8]}.png"
            image_dest_path = os.path.join(materials_folder, image_filename)

            # 复制图片到素材文件夹
            try:
                # 检查是否是URL
                if image_path.startswith(('http://', 'https://')):
                    # 下载图片
                    response = requests.get(image_path)
                    if response.status_code == 200:
                        img = Image.open(BytesIO(response.content))
                        img.save(image_dest_path)
                    else:
                        # 如果下载失败，使用默认图片
                        create_default_image(image_dest_path, 1080, 1920)
                else:
                    # 本地文件路径
                    if os.path.exists(image_path):
                        shutil.copy(image_path, image_dest_path)
                    else:
                        # 如果文件不存在，使用默认图片
                        create_default_image(image_dest_path, 1080, 1920)
            except Exception as e:
                print(f"处理图片时出错: {str(e)}")
                # 创建默认图片
                create_default_image(image_dest_path, 1080, 1920)

            # 添加图片素材
            image_id = str(uuid.uuid4())
            add_image_material(draft_template, image_id, image_filename, materials_folder_name, draft_id)

            # 添加图片到轨道
            add_image_segment(image_track, image_id, current_time, scene_duration, keyframes)

        # 处理音频
        if 'audio_info' in scene and 'path' in scene['audio_info']:
            audio_path = scene['audio_info']['path']
            audio_filename = f"audio_{i}_{str(uuid.uuid4())[:8]}.mp3"
            audio_dest_path = os.path.join(materials_folder, audio_filename)

            # 复制音频到素材文件夹
            try:
                # 检查是否是URL
                if audio_path.startswith(('http://', 'https://')):
                    # 下载音频
                    response = requests.get(audio_path)
                    if response.status_code == 200:
                        with open(audio_dest_path, 'wb') as f:
                            f.write(response.content)
                    else:
                        # 如果下载失败，创建空音频文件
                        create_empty_audio(audio_dest_path)
                else:
                    # 本地文件路径
                    if os.path.exists(audio_path):
                        shutil.copy(audio_path, audio_dest_path)
                    else:
                        # 如果文件不存在，创建空音频文件
                        create_empty_audio(audio_dest_path)
            except Exception as e:
                print(f"处理音频时出错: {str(e)}")
                # 创建空音频文件
                create_empty_audio(audio_dest_path)

            # 添加音频素材
            audio_id = str(uuid.uuid4())
            add_audio_material(draft_template, audio_id, audio_filename, materials_folder_name, draft_id)

            # 添加音频到轨道
            add_audio_segment(audio_track, audio_id, current_time, scene_duration)

        # 处理文本
        if 'text' in scene:
            # 添加文本素材
            text_id = str(uuid.uuid4())
            add_text_material(draft_template, text_id, scene['text'], font_style)

            # 添加文本到轨道
            add_text_segment(text_track, text_id, current_time, scene_duration)

        # 更新时间
        current_time += scene_duration

def generate_draft_json(storyboard_path, template_name=None, background_path=None):
    """根据storyboard.json生成剪映草稿JSON"""
    # 读取storyboard数据
    with open(storyboard_path, 'r', encoding='utf-8') as f:
        storyboard_data = json.load(f)

    # 生成项目ID
    draft_id = str(uuid.uuid4())

    # 加载模板
    template_data = None
    keyframes = None
    font_style = None

    if template_name:
        template_data = load_template(template_name)
        if template_data:
            keyframes = template_data.get('keyframes', [])
            font_style = template_data.get('font_style', {})

    # 创建基础草稿模板
    draft_template = create_base_draft_template(draft_id)

    # 计算总时长
    total_duration = extract_audio_duration(storyboard_data)
    if total_duration > 0:
        draft_template["duration"] = total_duration

    return draft_template, storyboard_data

def create_draft_file(draft_json, output_path):
    """保存草稿文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(draft_json, f, ensure_ascii=False, indent=2)
    return output_path

def generate_capcut_draft(storyboard_path, template_name=None, background_path=None, draft_name=None):
    """
    根据分镜文件和选择的模板生成剪映草稿

    Args:
        storyboard_path: 分镜文件路径
        template_name: 模板名称
        background_path: 背景图片路径（可选）
        draft_name: 草稿名称（可选）

    Returns:
        draft_id: 草稿ID
    """
    # 生成唯一的草稿ID
    draft_id = str(uuid.uuid4())

    # 如果没有提供草稿名称，使用UUID
    if not draft_name:
        draft_name = f"{draft_id}"

    draft_folder = os.path.join(current_app.config['TEMP_FOLDER'], draft_id)
    os.makedirs(draft_folder, exist_ok=True)

    # 创建素材文件夹
    materials_folder_name = str(uuid.uuid4())
    materials_folder = os.path.join(draft_folder, materials_folder_name)
    os.makedirs(materials_folder, exist_ok=True)

    # 第一步：解析分镜文件
    with open(storyboard_path, 'r', encoding='utf-8') as f:
        storyboard_data = json.load(f)

    # 解析分镜数据，获取音频和图片信息
    scenes = storyboard_data.get('data', [])

    # 计算总时长
    total_duration = 0
    for scene in scenes:
        # 默认场景时长为3秒
        scene_duration = 3 * 1000000  # 默认值，单位微秒
        
        # 检查是否有音频信息
        if 'audio_info' in scene:
            # 优先从duration字段获取时长（毫秒单位）
            if 'duration' in scene['audio_info']:
                try:
                    duration_ms = scene['audio_info']['duration']
                    # 检查duration是否是数字类型 
                    if isinstance(duration_ms, (int, float)):
                        scene_duration = int(duration_ms * 1000)  # 转换为微秒
                        print(f"从duration字段获取时长: {duration_ms} 毫秒")
                    # 如果是字符串，尝试解析类似 "0分9秒" 的格式
                    elif isinstance(duration_ms, str):
                        minutes = 0
                        seconds = 0
                        if '分' in duration_ms:
                            minutes = int(duration_ms.split('分')[0])
                            seconds_part = duration_ms.split('分')[1]
                            if '秒' in seconds_part:
                                seconds = int(seconds_part.replace('秒', ''))
                        elif '秒' in duration_ms:
                            seconds = int(duration_ms.replace('秒', ''))
                        
                        scene_duration = (minutes * 60 + seconds) * 1000000  # 转换为微秒
                        print(f"从分镜数据中获取到时长: {minutes}分{seconds}秒")
                    
                    scene['duration'] = scene_duration
                    total_duration += scene_duration
                    continue
                except Exception as e:
                    print(f"解析duration字段出错: {str(e)}")
            
            # 如果没有duration字段或解析失败，尝试从音频文件获取时长
            if 'path' in scene['audio_info']:
                audio_path = scene['audio_info']['path']
                try:
                    if os.path.exists(audio_path):
                        audio = MutagenFile(audio_path)
                        if audio and audio.info:
                            duration_seconds = audio.info.length
                            scene_duration = int(duration_seconds * 1000000)
                            scene['duration'] = scene_duration
                            total_duration += scene_duration
                            print(f"从音频文件获取到时长: {duration_seconds:.2f}秒")
                            continue
                except Exception as e:
                    print(f"读取音频文件时长出错: {str(e)}")
        
        # 如果以上方法都失败，使用默认时长
        scene['duration'] = scene_duration  # 默认3秒
        total_duration += scene_duration
        print("使用默认时长: 3秒")

    # 加载选择的模板
    template_data = load_template(template_name)
    keyframes = None
    font_style = None

    if template_data:
        keyframes = template_data.get('keyframes', [])
        font_style = template_data.get('font_style', {})

    # 创建基础草稿模板
    draft_template = create_base_draft_template(draft_id)
    draft_template['duration'] = total_duration

    # 处理背景图片
    if background_path and os.path.exists(background_path):
        background_filename = f"background_{str(uuid.uuid4())[:8]}.png"
        background_dest_path = os.path.join(materials_folder, background_filename)
        shutil.copy(background_path, background_dest_path)

        # 添加背景图片素材
        background_id = str(uuid.uuid4())
        add_image_material(draft_template, background_id, background_filename, materials_folder_name, draft_id)

        # 创建背景轨道并添加背景图片
        background_track = create_track("video")
        draft_template["tracks"].insert(0, background_track)  # 将背景轨道插入到最底层
        add_image_segment(background_track, background_id, 0, total_duration)

    # 处理场景数据
    process_scenes(draft_template, scenes, materials_folder, materials_folder_name, draft_id, keyframes, font_style)

    # 保存草稿文件
    save_draft_files(draft_template, draft_folder, draft_id, materials_folder_name, draft_name)

    return draft_id

def save_draft_files(draft_template, draft_folder, draft_id, materials_folder_name, draft_name):
    """保存草稿文件"""
    # 保存draft_content.json
    with open(os.path.join(draft_folder, 'draft_content.json'), 'w', encoding='utf-8') as f:
        json.dump(draft_template, f, ensure_ascii=False, indent=2)

    # 保存draft_info.json - 修复：使用相同的内容
    with open(os.path.join(draft_folder, 'draft_info.json'), 'w', encoding='utf-8') as f:
        json.dump(draft_template, f, ensure_ascii=False, indent=2)

    # 保存素材文件夹的元数据文件 - 修复：使用相同的内容
    with open(os.path.join(draft_folder, f'{materials_folder_name}.json'), 'w', encoding='utf-8') as f:
        json.dump(draft_template, f, ensure_ascii=False, indent=2)

    # 创建meta_info文件
    create_draft_meta_info(draft_folder, draft_id, draft_name)

def create_draft_meta_info(draft_folder, draft_id, draft_name):
    """创建草稿元信息文件"""
    # 默认根路径
    draft_root_path = "H:\\缓存\\剪映草稿\\JianyingPro Drafts"
    draft_removable_storage_device = "H:"

    # 构建完整的草稿路径
    draft_fold_path = f"{draft_removable_storage_device}/缓存/剪映草稿/JianyingPro Drafts/{draft_name}"

    # 当前时间戳（微秒级）
    current_time = int(time.time() * 1000000)

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