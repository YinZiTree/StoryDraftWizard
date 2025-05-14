
# 项目结构文档

## 项目概述
这是一个基于Flask的剪映草稿生成器Web应用，用于将分镜文件转换为剪映可用的草稿文件。

## 核心文件结构
```
.
├── app.py                 # 应用主入口，包含Flask应用初始化和配置
├── config.py             # 配置文件，包含数据库、邮件等配置项
├── main.py              # 服务器启动脚本
├── models.py            # 数据库模型定义
└── pyproject.toml       # Python项目依赖配置
```

## 主要模块说明

### 1. 核心应用模块
- `app.py`: 应用核心配置和初始化
  - 初始化Flask应用
  - 配置数据库连接
  - 设置登录管理器
  - 注册蓝图路由
  - 配置邮件服务

### 2. 路由模块 (/routes)
- `auth.py`: 用户认证相关路由
  - 用户注册
  - 用户登录
  - 密码重置
  
- `admin.py`: 管理员功能路由
  - 用户管理
  - 卡密管理
  - 系统设置
  
- `generator.py`: 草稿生成相关路由
  - 文件上传处理
  - 草稿生成
  - 下载服务

### 3. 工具模块 (/utils)
- `generator.py`: 草稿生成核心逻辑
  - 分镜文件解析
  - 素材处理（图片、音频）
  - 草稿JSON生成
  
- `template.py`: 模板处理工具
  - 草稿文件夹创建
  - 模板加载与处理
  
- `email.py`: 邮件服务工具
  - 邮件模板
  - 发送服务

### 4. 模板与静态文件
- `/templates`: HTML模板文件
  - 主页面模板
  - 管理面板模板
  - 用户界面模板
  
- `/static`: 静态资源文件
  - CSS样式文件
  - JavaScript脚本
  - 图片资源

### 5. 数据目录
- `/uploads`: 用户上传文件临时存储
- `/temp`: 生成的草稿文件临时存储

## 模块关联关系

### 数据流向
1. 用户上传分镜文件 → `routes/generator.py`
2. 解析和处理 → `utils/generator.py`
3. 生成草稿文件 → `utils/template.py`
4. 返回下载链接 → `routes/generator.py`

### 认证流程
1. 用户注册/登录 → `routes/auth.py`
2. 用户认证 → `flask_login`
3. 数据存储 → `models.py`

### 管理流程
1. 管理员操作 → `routes/admin.py`
2. 数据处理 → `models.py`
3. 邮件通知 → `utils/email.py`

## 依赖关系
- Flask: Web框架
- SQLAlchemy: 数据库ORM
- Flask-Login: 用户认证
- Flask-Mail: 邮件服务
- Pillow: 图片处理
- Mutagen: 音频文件处理
- Requests: HTTP请求

## 部署说明
应用使用Gunicorn作为WSGI服务器，在端口5000上运行。主要通过main.py启动，支持自动重载和多工作进程。
