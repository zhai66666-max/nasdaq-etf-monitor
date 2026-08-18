#!/usr/bin/env python3
"""
纳斯达克100 ETF 溢价率 + 历史回撤监控系统
每天北京时间 07:00 由 GitHub Actions 运行。
"""
import sys
import os
import traceback
from datetime import datetime, timedelta, timezone

# 允许直接 python main.py 运行
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import data_fetcher, drawdown, etf, ranking, database, report, email_sender
from src import config_loader

BEIJING_TZ = timezone(timedelta(hours=8))


def beijing_today():
    """北京时间日期（GitHub Actions 服务器是 UTC）"""
    return datetime.now(BEIJING_TZ).date()


def main(send=True):
    run_date = beijing_today().isoformat()
    logs = []

    # ===== 1. 纳斯达克100 历史数据 =====
    logs.append('获取纳斯达克100历史数据...')
    ndx_df, ndx_source = data_fetcher.fetch_nasdaq_history()
    ndx_meta = {'source': ndx_source, 'count': len(ndx_df)}
    logs.append(f'  数据源: {ndx_source}, {len(ndx_df)} 条日线')

    # ===== 2. 历史回撤计算 =====
    strategy = config_loader.load_strategy()
    dd = drawdown.summary(
        ndx_df,
        levels=strategy['drawdown_levels'],
        thresholds=strategy['event_thresholds'],
    )
    logs.append(f'  当前回撤: {dd["current_drawdown"]:.2f}% '
                f'(百分位 {dd["percentile"]:.0f}%, 等级 {dd["level"]["label"]})')

    # ===== 3. ETF 数据 =====
    etf_configs = config_loader.load_etfs()['etfs']
    logs.append(f'获取 {len(etf_configs)} 只 ETF 数据...')
    etf_results, ok_etfs, failed_etfs = etf.get_all_etfs(etf_configs)
    logs.append(f'  成功: {len(ok_etfs)}, 失败: {len(failed_etfs)}')
    for f in failed_etfs:
        logs.append(f'    ⚠️ {f["code"]} {f["name"]}: {f["error"]}')

    # ===== 4. 排序与判断 =====
    liquidity = config_loader.load_etfs()['liquidity']
    ranked = etf.rank_etfs(ok_etfs, strategy['premium_levels'], liquidity)
    signal = ranking.build_signal(dd, ranked, strategy['premium_accept_max'])
    recs = ranking.build_recommendations(ranked, liquidity)

    if signal['best_etf']:
        best = signal['best_etf']
        logs.append(f'  最低溢价: {best["code"]} {best["name"]} {best["premium"]:.2f}%')
    logs.append(f'  综合信号: {"满足加仓条件 ✅" if signal["satisfied"] else "未满足 ⚪"}')

    # ===== 5. 数据状态说明 =====
    basis_set = set(e['premium_basis'] for e in ok_etfs if e.get('premium_basis'))
    basis_label = '、'.join(sorted(basis_set)) if basis_set else '未知'
    data_status = f'{len(ok_etfs)}/{len(etf_configs)} ETF成功'
    if failed_etfs:
        data_status += f'，{len(failed_etfs)}只异常'

    # ===== 6. 保存数据库 =====
    logs.append('保存 DuckDB 数据库...')
    conn = database.get_connection()
    database.init_db(conn)
    database.save_nasdaq(conn, dd['series'])
    database.save_etfs(conn, etf_results, run_date)
    database.save_drawdown_events(conn, dd['events'], run_date)
    conn.close()

    # ===== 7. 生成报告 =====
    context = report.build_context(dd, ranked, signal, ndx_meta, data_status, basis_label)
    html = report.generate_html(context)

    # 保存 HTML 供存档
    os.makedirs('data', exist_ok=True)
    with open(f'data/report_{run_date}.html', 'w', encoding='utf-8') as f:
        f.write(html)

    # ===== 8. 发送邮件 =====
    email_status = '跳过'
    if send:
        subject = (f'[纳指监控] {run_date} 历史回撤 {dd["current_drawdown"]:.2f}% '
                   f'({dd["level"]["label"]}) | 最低溢价 '
                   f'{signal["best_etf"]["premium"]:.2f}%' if signal['best_etf']
                   else f'[纳指监控] {run_date} 历史回撤 {dd["current_drawdown"]:.2f}%')
        try:
            recipients = email_sender.send_email(html, subject)
            email_status = f'成功 → {", ".join(recipients)}'
        except Exception as e:
            email_status = f'失败: {e}'
    logs.append(f'邮件: {email_status}')

    return {
        'date': run_date,
        'drawdown': dd['current_drawdown'],
        'percentile': dd['percentile'],
        'level': dd['level']['label'],
        'etfs_ok': len(ok_etfs),
        'etfs_failed': len(failed_etfs),
        'best_etf': signal['best_etf']['code'] if signal['best_etf'] else None,
        'best_premium': signal['best_etf']['premium'] if signal['best_etf'] else None,
        'signal_satisfied': signal['satisfied'],
        'email': email_status,
        'logs': logs,
    }


if __name__ == '__main__':
    dry = '--no-send' in sys.argv
    try:
        result = main(send=not dry)
        print('\n===== 运行完成 =====')
        for line in result['logs']:
            print(line)
        print(f"\n结果: 回撤 {result['drawdown']:.2f}% | "
              f"最佳ETF {result['best_etf']} 溢价 {result['best_premium']}% | "
              f"信号 {'✅满足' if result['signal_satisfied'] else '⚪未满足'}")
    except Exception as e:
        print(f'\n❌ 运行失败: {e}')
        traceback.print_exc()
        sys.exit(1)
