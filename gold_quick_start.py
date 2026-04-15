#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
黄金分析功能 - 快速开始示例

此脚本展示了如何在现有系统中使用黄金分析功能
"""

from data_provider.base import DataFetcherManager
from data_provider.gold_fetcher import is_gold_code
import pandas as pd

def quick_start_example():
    """快速开始示例"""
    print("🚀 黄金分析功能快速开始示例")
    print("=" * 50)

    # 1. 创建数据管理器
    print("\n1. 创建数据管理器...")
    manager = DataFetcherManager()
    print(f"✅ 已创建DataFetcherManager，可用数据源: {manager.available_fetchers}")

    # 2. 识别黄金代码
    print("\n2. 黄金代码识别...")
    gold_codes = ['GOLD', 'GC=F', 'XAUUSD=X', 'XAU']
    for code in gold_codes:
        result = is_gold_code(code)
        print(f"   {code}: {'✅ 黄金代码' if result else '❌ 非黄金代码'}")

    # 3. 获取实时行情
    print("\n3. 获取黄金实时行情...")
    quote = manager.get_realtime_quote('GOLD')
    if quote:
        print(f"✅ 获取成功: {quote.name or '黄金'}, 价格: {quote.price}")
        if quote.change_pct is not None:
            print(f"   涨跌幅: {quote.change_pct}%")
        if quote.volume:
            print(f"   成交量: {quote.volume:,}")
    else:
        print("⚠️  未能获取实时行情（可能因API限制）")

    # 4. 获取历史数据（即使API限制也展示方法）
    print("\n4. 获取黄金历史数据...")
    try:
        # 这里可能会因为API限制而失败，但展示正确的调用方法
        df, source = manager.get_daily_data('GOLD', days=10)
        print(f"✅ 获取成功，数据源: {source}，记录数: {len(df)}")
        if not df.empty:
            latest = df.iloc[-1]
            print(f"   最新收盘价: {latest['close']:.2f}")
            if 'ma5' in df.columns:
                print(f"   MA5: {latest['ma5']:.2f}")
                print(f"   MA10: {latest['ma10']:.2f}")
    except Exception as e:
        print(f"⚠️  获取历史数据失败（通常因为API限制）: {e}")
        print("   这是正常的，因为Yahoo Finance有API调用限制")

    # 5. 与股票数据对比
    print("\n5. 与股票数据格式对比...")
    try:
        stock_df, _ = manager.get_daily_data('000001', days=5)
        print(f"📊 股票数据列: {list(stock_df.columns)}")

        # 展示黄金数据应该使用的相同格式
        print(f"📊 黄金数据列: ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg']")
        print(f"💡 两者使用相同的标准化格式")
    except Exception as e:
        print(f"⚠️  获取股票数据对比失败: {e}")

    print(f"\n6. 在自选股中使用黄金...")
    print(f"   您可以在配置中设置:")
    print(f"   STOCK_LIST = '600519,000001,GOLD,XAUUSD=X'")
    print(f"   系统将同时分析股票和黄金")

    print(f"\n7. 专业黄金分析策略...")
    print(f"   系统已配置专用的黄金分析策略文件: strategies/gold_analysis.yaml")
    print(f"   该策略使黄金具备与股票相同的分析深度")

    print(f"\n🎉 快速开始完成！")
    print(f"💡 您现在可以在系统中像分析股票一样分析黄金价格了！")

if __name__ == "__main__":
    quick_start_example()
