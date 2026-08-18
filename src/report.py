"""HTML 报告生成"""
import os
from jinja2 import Environment, FileSystemLoader
from datetime import date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(BASE_DIR, 'templates')


def generate_html(context):
    """渲染邮件 HTML"""
    env = Environment(loader=FileSystemLoader(TEMPLATES))
    env.filters['format'] = lambda fmt, v: fmt % v
    template = env.get_template('daily_report.html')
    return template.render(**context)


def build_context(dd_summary, ranked_etfs, signal, ndx_meta, data_status, basis_label):
    """构建模板上下文"""
    return {
        'report_date': date.today().isoformat(),
        'dd': dd_summary,
        'ranked': ranked_etfs,
        'signal': signal,
        'ndx_source': ndx_meta.get('source', '?'),
        'ndx_count': ndx_meta.get('count', 0),
        'data_status': data_status,
        'basis_label': basis_label,
    }
