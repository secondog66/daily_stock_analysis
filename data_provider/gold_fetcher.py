# -*- coding: utf-8 -*-
"""
===================================
GoldFetcher - 黄金价格数据源 (Priority 3)
===================================

数据来源：Yahoo Finance（通过 yfinance 库获取黄金期货或现货价格）
特点：国际贵金属数据源、实时更新
定位：专门用于黄金价格分析，提供与股票相同的分析能力

关键策略：
1. 将黄金作为特殊资产代码处理（如 GC=F 或 XAUUSD=X）
2. 统一价格数据格式，支持技术指标计算
3. 遵循与股票数据相同的标准化流程
"""

import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

import pandas as pd
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from .base import BaseFetcher, DataFetchError, STANDARD_COLUMNS
from .realtime_types import UnifiedRealtimeQuote, RealtimeSource

logger = logging.getLogger(__name__)


def is_gold_code(stock_code: str) -> bool:
    """
    判断是否为黄金相关代码

    支持格式：
    - 'GOLD' - 通用黄金标识
    - 'GC=F' - COMEX黄金期货
    - 'XAUUSD=X' - XAU/USD现货黄金
    - 'XAU' - XAU黄金
    """
    code = (stock_code or "").strip().upper()
    return code in ['GOLD', 'GC=F', 'XAUUSD=X', 'XAU'] or 'GOLD' in code or 'GC=' in code or 'XAU' in code


class GoldFetcher(BaseFetcher):
    """
    黄金价格数据源实现

    优先级：3（中等，用于黄金分析）
    数据来源：Yahoo Finance黄金相关符号

    关键策略：
    - 将黄金代码转换为Yahoo Finance对应的符号
    - 提供与股票相同的数据格式和分析能力
    - 统一的实时行情和历史数据分析接口
    """

    name = "GoldFetcher"
    priority = int(os.getenv("GOLD_PRIORITY", "3"))

    def __init__(self):
        """初始化 GoldFetcher"""
        pass

    def _convert_gold_code(self, stock_code: str) -> str:
        """
        转换黄金代码为 Yahoo Finance 格式

        Args:
            stock_code: 原始黄金代码，如 'GOLD', 'GC=F', 'XAUUSD=X', 'XAU'

        Returns:
            Yahoo Finance 格式代码
        """
        code = stock_code.strip().upper()

        # 标准化黄金代码到 Yahoo Finance 符号
        if code in ['GOLD', 'GC=F']:
            return 'GC=F'  # COMEX黄金期货
        elif code in ['XAUUSD=X', 'XAU']:
            return 'XAUUSD=X'  # XAU/USD现货黄金
        else:
            # 默认使用COMEX黄金期货
            logger.warning(f"未知黄金代码 {code}，使用默认 GC=F")
            return 'GC=F'

    @retry(
        stop=stop_after_attempt(2),  # 减少重试次数以避免长时间等待
        wait=wait_exponential(multiplier=1, min=1, max=10),  # 减少等待时间
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        从 Yahoo Finance 获取黄金原始数据

        使用 yfinance.download() 获取黄金价格数据
        包括备用方案来处理API限制

        流程：
        1. 转换黄金代码格式
        2. 调用 yfinance API
        3. 处理返回数据
        """
        import yfinance as yf

        # 转换代码格式
        yf_code = self._convert_gold_code(stock_code)

        logger.debug(f"调用 yfinance.download({yf_code}, {start_date}, {end_date})")

        try:
            # 使用 yfinance 下载数据
            df = yf.download(
                tickers=yf_code,
                start=start_date,
                end=end_date,
                progress=False,  # 禁止进度条
                auto_adjust=True,  # 自动调整价格（复权）
                multi_level_index=False  # 黄金不需要多层索引
            )

            if df.empty:
                # 尝试使用不同的yf_code
                alternate_codes = []
                if 'GOLD' in stock_code.upper():
                    alternate_codes = ['GC=F', 'XAUUSD=X']
                elif 'GC=F' in yf_code:
                    alternate_codes = ['XAUUSD=X', 'GOLD']
                elif 'XAUUSD=X' in yf_code:
                    alternate_codes = ['GC=F', 'GOLD']

                for alt_code in alternate_codes:
                    logger.debug(f"原始代码失败，尝试备用代码: {alt_code}")
                    try:
                        df = yf.download(
                            tickers=alt_code,
                            start=start_date,
                            end=end_date,
                            progress=False,
                            auto_adjust=True,
                            multi_level_index=False
                        )
                        if not df.empty:
                            logger.info(f"使用备用代码 {alt_code} 成功获取黄金数据")
                            break
                    except:
                        continue

            if df.empty:
                raise DataFetchError(f"Yahoo Finance 未查询到 {stock_code} 的黄金数据")

            return df

        except Exception as e:
            if isinstance(e, DataFetchError):
                raise
            # 尝试使用备用方法
            try:
                return self._fetch_gold_data_alternative(yf_code, start_date, end_date)
            except:
                raise DataFetchError(f"Yahoo Finance 获取黄金数据失败: {e}") from e

    def _fetch_gold_data_alternative(self, yf_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        备用的黄金数据获取方法

        尝试使用不同的yfinance方法或API来获取数据
        """
        import yfinance as yf
        import warnings
        warnings.filterwarnings("ignore")

        # 尝试使用特定的黄金代码
        alt_codes = ['GC=F', 'XAUUSD=X', 'XAU=X']

        for alt_code in alt_codes:
            try:
                ticker = yf.Ticker(alt_code)
                # 尝试获取一段时间的数据
                df = ticker.history(start=start_date, end=end_date)
                if not df.empty:
                    logger.info(f"使用备用方法通过 {alt_code} 成功获取黄金数据")
                    # 重命名列以符合标准格式
                    if 'Date' not in df.columns:
                        df = df.reset_index()
                    return df
            except Exception as e:
                logger.debug(f"备用方法尝试 {alt_code} 失败: {e}")
                continue

        raise DataFetchError(f"备用方法也无法获取黄金数据")

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        标准化黄金价格数据

        yfinance 返回的列名：
        Open, High, Low, Close, Volume（索引是日期）

        需要映射到标准列名：
        date, open, high, low, close, volume, amount, pct_chg
        """
        df = df.copy()

        # 重置索引，将日期从索引变为列
        df = df.reset_index()

        # 列名映射（yfinance 使用首字母大写）
        column_mapping = {
            'Date': 'date',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
        }

        df = df.rename(columns=column_mapping)

        # 计算涨跌幅（因为 yfinance 不直接提供）
        if 'close' in df.columns:
            df['pct_chg'] = df['close'].pct_change() * 100
            df['pct_chg'] = df['pct_chg'].fillna(0).round(2)

        # 计算成交额（黄金数据可能没有实际成交额，使用估值）
        if 'volume' in df.columns and 'close' in df.columns:
            df['amount'] = df['volume'] * df['close']
        else:
            # 黄金期货可能没有真实成交量，使用估值
            df['amount'] = 0

        # 添加黄金代码列
        df['code'] = stock_code

        # 只保留需要的列
        keep_cols = ['code'] + STANDARD_COLUMNS
        existing_cols = [col for col in keep_cols if col in df.columns]
        df = df[existing_cols]

        return df

    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """
        获取黄金实时行情数据

        数据来源：yfinance Ticker.info

        Args:
            stock_code: 黄金代码，如 'GOLD', 'GC=F', 'XAUUSD=X', 'XAU'

        Returns:
            UnifiedRealtimeQuote 对象，获取失败返回 None
        """
        import yfinance as yf

        if not is_gold_code(stock_code):
            logger.debug(f"[GoldFetcher] {stock_code} 不是黄金代码，跳过")
            return None

        try:
            yf_code = self._convert_gold_code(stock_code)
            logger.debug(f"[GoldFetcher] 获取黄金 {yf_code} 实时行情")

            ticker = yf.Ticker(yf_code)

            # 尝试获取最新数据
            try:
                info = ticker.fast_info
                if info is None:
                    raise ValueError("fast_info is None")

                price = getattr(info, 'lastPrice', None) or getattr(info, 'last_price', None)
                prev_close = getattr(info, 'previousClose', None) or getattr(info, 'previous_close', None)
                open_price = getattr(info, 'open', None)
                high = getattr(info, 'dayHigh', None) or getattr(info, 'day_high', None)
                low = getattr(info, 'dayLow', None) or getattr(info, 'day_low', None)
                volume = getattr(info, 'lastVolume', None) or getattr(info, 'last_volume', None)

            except Exception:
                # 回退到 history 方法获取最新数据
                logger.debug("[GoldFetcher] fast_info 失败，尝试 history 方法")
                hist = ticker.history(period='2d')
                if hist.empty:
                    logger.warning(f"[GoldFetcher] 无法获取 {yf_code} 的数据")
                    return None

                today = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else today

                price = float(today['Close'])
                prev_close = float(prev['Close'])
                open_price = float(today['Open'])
                high = float(today['High'])
                low = float(today['Low'])
                volume = int(today['Volume'])

            # 计算涨跌幅
            change_amount = None
            change_pct = None
            if price is not None and prev_close is not None and prev_close > 0:
                change_amount = price - prev_close
                change_pct = (change_amount / prev_close) * 100

            # 计算振幅
            amplitude = None
            if high is not None and low is not None and prev_close is not None and prev_close > 0:
                amplitude = ((high - low) / prev_close) * 100

            # 确定黄金名称
            gold_name_map = {
                'GC=F': 'COMEX黄金期货',
                'XAUUSD=X': '现货黄金(XAU/USD)',
                'XAU': '黄金(XAU)'
            }
            name = gold_name_map.get(yf_code, f'黄金({stock_code})')

            quote = UnifiedRealtimeQuote(
                code=stock_code,
                name=name,
                source=RealtimeSource.GOLD,
                price=price,
                change_pct=round(change_pct, 2) if change_pct is not None else None,
                change_amount=round(change_amount, 4) if change_amount is not None else None,
                volume=volume,
                amount=volume * price if volume and price else None,  # 估算成交额
                volume_ratio=None,
                turnover_rate=None,
                amplitude=round(amplitude, 2) if amplitude is not None else None,
                open_price=open_price,
                high=high,
                low=low,
                pre_close=prev_close,
                pe_ratio=None,  # 黄金没有PE比率
                pb_ratio=None,  # 黄金没有PB比率
                total_mv=None,  # 黄金没有市值
                circ_mv=None,  # 黄金没有流通市值
            )

            logger.info(f"[GoldFetcher] 获取黄金 {stock_code} 实时行情成功: 价格={price}")
            return quote

        except Exception as e:
            logger.warning(f"[GoldFetcher] 获取黄金 {stock_code} 实时行情失败: {e}")
            return None

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        """
        获取黄金名称

        Args:
            stock_code: 黄金代码

        Returns:
            黄金名称
        """
        if not is_gold_code(stock_code):
            return None

        gold_name_map = {
            'GOLD': '黄金',
            'GC=F': 'COMEX黄金期货',
            'XAUUSD=X': '现货黄金(XAU/USD)',
            'XAU': '黄金(XAU)'
        }
        return gold_name_map.get(stock_code.upper(), f'黄金({stock_code})')


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)

    fetcher = GoldFetcher()

    try:
        df = fetcher.get_daily_data('GOLD')  # 黄金
        print(f"获取黄金数据成功，共 {len(df)} 条数据")
        print(df.tail())
    except Exception as e:
        print(f"获取黄金数据失败: {e}")
