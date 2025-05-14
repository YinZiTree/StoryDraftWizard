from flask import current_app, url_for
from flask_mail import Message
from app import mail

def send_email(subject, recipient, template):
    """
    发送邮件的通用函数
    """
    try:
        msg = Message(
            subject,
            recipients=[recipient],
            html=template,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"邮件发送失败: {str(e)}")
        return False

def send_verification_email(recipient, token):
    """
    发送账号验证邮件
    """
    verify_url = url_for('auth.verify', token=token, _external=True)
    subject = "【剪映草稿生成器】请验证您的账号"
    
    template = f"""
    <html>
      <head>
        <style>
          body {{ font-family: Arial, sans-serif; color: #333; }}
          .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
          .header {{ background-color: #4a76a8; color: white; padding: 15px; text-align: center; }}
          .content {{ padding: 20px; }}
          .button {{ display: inline-block; background-color: #4a76a8; color: white; padding: 10px 20px; 
                    text-decoration: none; border-radius: 4px; margin-top: 15px; }}
          .footer {{ font-size: 12px; color: #999; margin-top: 30px; text-align: center; }}
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h2>验证您的账号</h2>
          </div>
          <div class="content">
            <p>感谢您注册剪映草稿生成器！</p>
            <p>请点击下面的按钮验证您的账号：</p>
            <p><a href="{verify_url}" class="button">验证账号</a></p>
            <p>或者复制以下链接到浏览器：</p>
            <p>{verify_url}</p>
            <p>如果您没有注册此账号，请忽略此邮件。</p>
          </div>
          <div class="footer">
            <p>此邮件为系统自动发送，请勿回复。</p>
          </div>
        </div>
      </body>
    </html>
    """
    
    return send_email(subject, recipient, template)

def send_welcome_email(recipient, username):
    """
    发送欢迎邮件
    """
    subject = "【剪映草稿生成器】欢迎使用我们的服务"
    
    template = f"""
    <html>
      <head>
        <style>
          body {{ font-family: Arial, sans-serif; color: #333; }}
          .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
          .header {{ background-color: #4a76a8; color: white; padding: 15px; text-align: center; }}
          .content {{ padding: 20px; }}
          .button {{ display: inline-block; background-color: #4a76a8; color: white; padding: 10px 20px; 
                    text-decoration: none; border-radius: 4px; margin-top: 15px; }}
          .footer {{ font-size: 12px; color: #999; margin-top: 30px; text-align: center; }}
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h2>欢迎加入，{username}！</h2>
          </div>
          <div class="content">
            <p>感谢您完成账号验证！</p>
            <p>现在您可以开始使用剪映草稿生成器了。我们的服务可以帮助您快速生成剪映草稿模板，提高视频创作效率。</p>
            <p>如果您有任何问题或需要帮助，请随时联系我们。</p>
            <p><a href="{url_for('generator.dashboard', _external=True)}" class="button">开始使用</a></p>
          </div>
          <div class="footer">
            <p>此邮件为系统自动发送，请勿回复。</p>
          </div>
        </div>
      </body>
    </html>
    """
    
    return send_email(subject, recipient, template)

def send_license_key_email(recipient, username, key, remaining_uses):
    """
    发送卡密邮件
    """
    subject = "【剪映草稿生成器】您的卡密信息"
    
    template = f"""
    <html>
      <head>
        <style>
          body {{ font-family: Arial, sans-serif; color: #333; }}
          .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
          .header {{ background-color: #4a76a8; color: white; padding: 15px; text-align: center; }}
          .content {{ padding: 20px; }}
          .key-box {{ background-color: #f5f5f5; padding: 15px; margin: 15px 0; border-radius: 4px; text-align: center; }}
          .key {{ font-size: 18px; font-weight: bold; color: #4a76a8; }}
          .button {{ display: inline-block; background-color: #4a76a8; color: white; padding: 10px 20px; 
                    text-decoration: none; border-radius: 4px; margin-top: 15px; }}
          .footer {{ font-size: 12px; color: #999; margin-top: 30px; text-align: center; }}
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h2>您的卡密信息</h2>
          </div>
          <div class="content">
            <p>尊敬的{username}，</p>
            <p>您的剪映草稿生成器卡密信息如下：</p>
            <div class="key-box">
              <p>卡密：<span class="key">{key}</span></p>
              <p>剩余使用次数：{remaining_uses}</p>
            </div>
            <p>您可以在我们的网站上使用此卡密生成剪映草稿模板。</p>
            <p><a href="{url_for('generator.dashboard', _external=True)}" class="button">前往使用</a></p>
          </div>
          <div class="footer">
            <p>此邮件为系统自动发送，请勿回复。</p>
          </div>
        </div>
      </body>
    </html>
    """
    
    return send_email(subject, recipient, template)

def send_reset_password_email(recipient, token):
    """
    发送重置密码邮件
    """
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    subject = "【剪映草稿生成器】重置您的密码"
    
    template = f"""
    <html>
      <head>
        <style>
          body {{ font-family: Arial, sans-serif; color: #333; }}
          .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
          .header {{ background-color: #4a76a8; color: white; padding: 15px; text-align: center; }}
          .content {{ padding: 20px; }}
          .button {{ display: inline-block; background-color: #4a76a8; color: white; padding: 10px 20px; 
                    text-decoration: none; border-radius: 4px; margin-top: 15px; }}
          .footer {{ font-size: 12px; color: #999; margin-top: 30px; text-align: center; }}
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h2>重置您的密码</h2>
          </div>
          <div class="content">
            <p>您最近请求重置剪映草稿生成器的账号密码。</p>
            <p>请点击下面的按钮设置新密码：</p>
            <p><a href="{reset_url}" class="button">重置密码</a></p>
            <p>或者复制以下链接到浏览器：</p>
            <p>{reset_url}</p>
            <p>如果您没有请求重置密码，请忽略此邮件并保持密码不变。</p>
          </div>
          <div class="footer">
            <p>此邮件为系统自动发送，请勿回复。</p>
          </div>
        </div>
      </body>
    </html>
    """
    
    return send_email(subject, recipient, template)
