# 剪映草稿生成器 API 使用指南

本文档提供了剪映草稿生成器API的详细使用说明，包括接口介绍、参数说明和返回值格式等信息。

## 目录

- [认证方式](#认证方式)
- [接口列表](#接口列表)
  - [草稿生成接口](#草稿生成接口)
  - [卡密验证接口](#卡密验证接口)
  - [订单通知接口](#订单通知接口)
- [错误码说明](#错误码说明)
- [示例代码](#示例代码)

## 认证方式

API接口使用卡密（License Key）进行认证。卡密支持多种计算方式：

- fixed（固定次数）：每次调用消耗固定次数
- by_size（按大小计算）：每10MB消耗1次
- by_duration（按时长计算）：每10分钟消耗1次
- by_count（按素材数量计算）：每5个素材消耗1次

## 接口列表

### 草稿生成接口

生成剪映草稿文件。

- **URL**: `http://127.0.0.1:5000/api/generate`
- **方法**: POST
- **请求头**:
  - Content-Type: application/json
  - Authorization: Bearer {卡密}

- **请求参数**:

```json
{
    "storyboard": {
        "scenes": [
            {
                "text": "场景文本",
                "content": "场景描述",
                "prompt": "AI提示词",
                "image_paths": ["图片路径1", "图片路径2"],
                "audio_info": {
                    "path": "音频路径",
                    "duration": 6464 // 单位毫秒
                },
                "background_image": "背景图片路径"//可为空
            }
        ]
    },
    "template_name": "标准",  // 可选
    "draft_name": "草稿名称" // 可选
}
```

- **返回示例**:

```json
{
    "code": 200,
    "message": "草稿生成成功",
    "data": {
        "draft_id": "draft_1234567890",
        "download_url": "http://your-domain.com/download/draft_1234567890.zip"
    }
}
```

### 卡密验证接口

验证卡密有效性和剩余次数。

- **URL**: `/api/verify_key`
- **方法**: GET
- **参数**: 
  - key: 卡密字符串

- **返回示例**:

```json
{
    "code": 200,
    "message": "卡密有效",
    "data": {
        "key": "F-ABC123DEF456",
        "type": "fixed",
        "max_uses": 50,
        "remaining_uses": 45,
        "expires_at": "2025-12-31 23:59:59"
    }
}
```

### 订单通知接口

接收支付成功通知，自动生成卡密。

- **URL**: `http://127.0.0.1:5000///api/order_notify`
- **方法**: POST
- **参数**:

```json
{
    "order_id": "ORDER_123456789",
    "amount": 10.00,
    "payment_time": "2025-04-26 12:00:00"
}
```

- **返回示例**:

```json
{
    "code": 200,
    "message": "订单处理成功",
    "data": {
        "key": "F-ABC123DEF456",
        "max_uses": 50
    }
}
```

## 错误码说明

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 卡密无效或已过期 |
| 403 | 无权限或次数不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 示例代码

### Python

```python
import requests
import json

def generate_draft(api_key, storyboard_data):
    url = "http://your-domain.com/api/generate"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "storyboard": storyboard_data,
        "template_name": "标准"
    }

    response = requests.post(url, headers=headers, json=data)
    return response.json()

def verify_key(api_key):
    url = f"http://your-domain.com/api/verify_key?key={api_key}"
    response = requests.get(url)
    return response.json()

# 使用示例
if __name__ == "__main__":
    api_key = "F-ABC123DEF456"

    # 验证卡密
    key_info = verify_key(api_key)
    print("卡密信息:", json.dumps(key_info, indent=2, ensure_ascii=False))

    # 生成草稿
    storyboard = {
        "scenes": [
            {
                "text": "测试场景",
                "content": "测试描述",
                "image_paths": ["test.jpg"],
                "audio_info": {
                    "path": "test.mp3",
                    "duration": "0分10秒"
                }
            }
        ]
    }

    result = generate_draft(api_key, storyboard)
    print("生成结果:", json.dumps(result, indent=2, ensure_ascii=False))
```

### JavaScript

```javascript
async function generateDraft(apiKey, storyboardData) {
    const url = "http://your-domain.com/api/generate";
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify({
            storyboard: storyboardData,
            template_name: "标准"
        })
    });
    return await response.json();
}

async function verifyKey(apiKey) {
    const url = `http://your-domain.com/api/verify_key?key=${apiKey}`;
    const response = await fetch(url);
    return await response.json();
}

// 使用示例
async function example() {
    const apiKey = "F-ABC123DEF456";

    // 验证卡密
    const keyInfo = await verifyKey(apiKey);
    console.log("卡密信息:", keyInfo);

    // 生成草稿
    const storyboard = {
        scenes: [
            {
                text: "测试场景",
                content: "测试描述",
                image_paths: ["test.jpg"],
                audio_info: {
                    path: "test.mp3",
                    duration: "0分10秒"
                }
            }
        ]
    };

    const result = await generateDraft(apiKey, storyboard);
    console.log("生成结果:", result);
}

example().catch(console.error);