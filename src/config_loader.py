"""配置加载：YAML 配置文件统一入口"""
import os
import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_yaml(filename):
    path = os.path.join(BASE_DIR, 'config', filename)
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_etfs():
    """ETF 监控名单"""
    return load_yaml('etfs.yaml')


def load_strategy():
    """策略配置"""
    return load_yaml('strategy.yaml')
