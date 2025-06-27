# -*- coding: utf-8 -*-
"""
Tests for date_validator module
"""

import unittest
from datetime import date, datetime

from core.date_validator import DateValidator, is_valid_date, parse_date, format_date


class TestDateValidator(unittest.TestCase):
    """DateValidatorのテストケース"""
    
    def test_valid_date_formats(self):
        """有効な日付フォーマットのテスト"""
        valid_dates = [
            "2024-01-01",
            "2024-12-31", 
            "2025-06-27",
            "2000-02-29"  # うるう年
        ]
        
        for date_str in valid_dates:
            with self.subTest(date_str=date_str):
                self.assertTrue(DateValidator.is_valid_date_format(date_str))
                self.assertTrue(is_valid_date(date_str))
    
    def test_invalid_date_formats(self):
        """無効な日付フォーマットのテスト"""
        invalid_dates = [
            "2024-1-1",      # ゼロパディングなし
            "24-01-01",      # 2桁年
            "2024/01/01",    # スラッシュ区切り
            "2024-01",       # 日なし
            "2024-13-01",    # 無効な月
            "2024-02-30",    # 存在しない日
            "invalid",       # 文字列
            "",              # 空文字
            None,            # None
            123,             # 数値
        ]
        
        for date_input in invalid_dates:
            with self.subTest(date_input=date_input):
                self.assertFalse(DateValidator.is_valid_date_format(str(date_input) if date_input is not None else ""))
                if isinstance(date_input, str):
                    self.assertFalse(is_valid_date(date_input))
    
    def test_parse_date_string(self):
        """日付文字列解析のテスト"""
        test_cases = [
            ("2024-06-27", date(2024, 6, 27)),
            ("2000-02-29", date(2000, 2, 29)),
            ("invalid", None),
            ("2024-13-01", None),
        ]
        
        for date_str, expected in test_cases:
            with self.subTest(date_str=date_str):
                result = DateValidator.parse_date_string(date_str)
                self.assertEqual(result, expected)
                
                # 便利関数もテスト
                result2 = parse_date(date_str)
                self.assertEqual(result2, expected)
    
    def test_format_date(self):
        """日付フォーマットのテスト"""
        test_date = date(2024, 6, 27)
        test_datetime = datetime(2024, 6, 27, 15, 30, 45)
        
        self.assertEqual(DateValidator.format_date(test_date), "2024-06-27")
        self.assertEqual(DateValidator.format_date(test_datetime), "2024-06-27")
        
        # 便利関数もテスト
        self.assertEqual(format_date(test_date), "2024-06-27")
        self.assertEqual(format_date(test_datetime), "2024-06-27")
        
        # 無効なタイプのテスト
        with self.assertRaises(TypeError):
            DateValidator.format_date("2024-06-27")
        
        with self.assertRaises(TypeError):
            format_date("2024-06-27")
    
    def test_validate_and_format(self):
        """検証とフォーマットの統合テスト"""
        test_cases = [
            ("2024-06-27", "2024-06-27"),
            (date(2024, 6, 27), "2024-06-27"),
            (datetime(2024, 6, 27, 15, 30), "2024-06-27"),
            ("invalid", None),
            ("2024-13-01", None),
            (123, None),
        ]
        
        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                result = DateValidator.validate_and_format(input_val)
                self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()