# -*- coding: utf-8 -*-
"""
Date Validation Module - 日付フォーマット検証モジュール
統一された日付検証とフォーマット処理
"""

import re
from datetime import datetime, date
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)

# 標準日付フォーマット
STANDARD_DATE_FORMAT = "%Y-%m-%d"
STANDARD_DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')

class DateValidator:
    """日付検証クラス"""
    
    @staticmethod
    def is_valid_date_format(date_string: str) -> bool:
        """
        日付文字列がYYYY-MM-DD形式かを検証
        
        Args:
            date_string: 検証する日付文字列
            
        Returns:
            bool: 有効なフォーマットの場合True
        """
        if not isinstance(date_string, str):
            return False
            
        # パターンマッチング
        if not STANDARD_DATE_PATTERN.match(date_string):
            return False
        
        # 実際の日付として有効かチェック
        try:
            datetime.strptime(date_string, STANDARD_DATE_FORMAT)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def parse_date_string(date_string: str) -> Optional[date]:
        """
        日付文字列をdateオブジェクトに変換
        
        Args:
            date_string: 変換する日付文字列
            
        Returns:
            date: 成功時はdateオブジェクト、失敗時はNone
        """
        if not DateValidator.is_valid_date_format(date_string):
            return None
        
        try:
            dt = datetime.strptime(date_string, STANDARD_DATE_FORMAT)
            return dt.date()
        except ValueError as e:
            logger.warning(f"Failed to parse date string '{date_string}': {e}")
            return None
    
    @staticmethod
    def format_date(date_obj: Union[date, datetime]) -> str:
        """
        dateまたはdatetimeオブジェクトを標準フォーマットに変換
        
        Args:
            date_obj: 変換するdateまたはdatetimeオブジェクト
            
        Returns:
            str: YYYY-MM-DD形式の日付文字列
        """
        if isinstance(date_obj, datetime):
            return date_obj.strftime(STANDARD_DATE_FORMAT)
        elif isinstance(date_obj, date):
            return date_obj.strftime(STANDARD_DATE_FORMAT)
        else:
            raise TypeError(f"Expected date or datetime object, got {type(date_obj)}")
    
    @staticmethod
    def validate_and_format(date_input: Union[str, date, datetime]) -> Optional[str]:
        """
        入力を検証し、標準フォーマットに変換
        
        Args:
            date_input: 検証・変換する日付入力
            
        Returns:
            str: 成功時は標準フォーマットの日付文字列、失敗時はNone
        """
        try:
            if isinstance(date_input, str):
                if DateValidator.is_valid_date_format(date_input):
                    return date_input
                else:
                    return None
            elif isinstance(date_input, (date, datetime)):
                return DateValidator.format_date(date_input)
            else:
                return None
        except Exception as e:
            logger.error(f"Date validation failed for {date_input}: {e}")
            return None

# 便利関数
def is_valid_date(date_string: str) -> bool:
    """日付文字列の有効性チェック（便利関数）"""
    return DateValidator.is_valid_date_format(date_string)

def parse_date(date_string: str) -> Optional[date]:
    """日付文字列の解析（便利関数）"""
    return DateValidator.parse_date_string(date_string)

def format_date(date_obj: Union[date, datetime]) -> str:
    """日付オブジェクトのフォーマット（便利関数）"""
    return DateValidator.format_date(date_obj)