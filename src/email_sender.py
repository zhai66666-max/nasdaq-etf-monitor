"""SMTP 邮件发送（QQ邮箱）"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header


def send_email(html_content, subject):
    """发送 HTML 邮件。凭证从环境变量读取。"""
    host = os.environ.get('EMAIL_HOST', 'smtp.qq.com')
    port = int(os.environ.get('EMAIL_PORT', '465'))
    username = os.environ.get('EMAIL_USERNAME', '')
    password = os.environ.get('EMAIL_PASSWORD', '')
    to = os.environ.get('EMAIL_TO', '')

    if not all([username, password, to]):
        raise ValueError('邮件配置不完整（EMAIL_HOST/PORT/USERNAME/PASSWORD/TO）')

    recipients = [e.strip() for e in to.split(',') if e.strip()]

    msg = MIMEMultipart('alternative')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = username
    msg['To'] = ', '.join(recipients)
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    with smtplib.SMTP_SSL(host, port, timeout=20) as server:
        server.login(username, password)
        server.sendmail(username, recipients, msg.as_string())
    return recipients
