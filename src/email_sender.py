"""SMTP 邮件发送（QQ邮箱）"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header


# 收件人黑名单：命中的地址永不接收邮件（2026-09-17 起停发 1741534484@qq.com）
# 如需调整，用环境变量 EMAIL_BLOCKLIST 覆盖（英文逗号分隔）
BLOCKED_RECIPIENTS = frozenset(
    e.strip().lower()
    for e in os.environ.get('EMAIL_BLOCKLIST', '1741534484@qq.com').split(',')
    if e.strip()
)


def send_email(html_content, subject):
    """发送 HTML 邮件。凭证从环境变量读取。"""
    host = os.environ.get('EMAIL_HOST', 'smtp.qq.com')
    port = int(os.environ.get('EMAIL_PORT', '465'))
    username = os.environ.get('EMAIL_USERNAME', '')
    password = os.environ.get('EMAIL_PASSWORD', '')
    to = os.environ.get('EMAIL_TO', '')

    if not all([username, password, to]):
        raise ValueError('邮件配置不完整（EMAIL_HOST/PORT/USERNAME/PASSWORD/TO）')

    configured = [e.strip() for e in to.split(',') if e.strip()]
    recipients = [e for e in configured if e.lower() not in BLOCKED_RECIPIENTS]
    skipped = len(configured) - len(recipients)
    if skipped:
        print(f'黑名单已过滤 {skipped} 个收件人')
    if not recipients:
        raise ValueError('收件人全部位于黑名单，邮件未发送')

    msg = MIMEMultipart('alternative')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = username
    msg['To'] = ', '.join(recipients)
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    with smtplib.SMTP_SSL(host, port, timeout=20) as server:
        server.login(username, password)
        server.sendmail(username, recipients, msg.as_string())
    return recipients
