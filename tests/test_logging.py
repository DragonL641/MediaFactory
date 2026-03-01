"""Tests for the unified logging system.

Simple tests to verify logging module can be imported and basic functions work.
"""

import pytest


class TestLoggingBasic:
    """基础日志功能测试。"""

    def test_logging_module_import(self):
        """测试日志模块可以导入。"""
        from mediafactory import logging as mf_logging

        assert mf_logging is not None

    def test_logging_functions_exist(self):
        """测试日志函数存在。"""
        from mediafactory.logging import (
            log_info,
            log_error,
            log_warning,
            log_debug,
        )

        assert callable(log_info)
        assert callable(log_error)
        assert callable(log_warning)
        assert callable(log_debug)

    def test_log_info_basic(self):
        """测试基本 info 日志。"""
        from mediafactory.logging import log_info

        # 不应抛出异常
        log_info("Test info message")

    def test_log_error_basic(self):
        """测试基本 error 日志。"""
        from mediafactory.logging import log_error

        # 不应抛出异常
        log_error("Test error message")

    def test_structured_logging_functions(self):
        """测试结构化日志函数存在且可调用。"""
        from mediafactory.logging import (
            log_stage,
            log_step,
            log_success,
        )

        # 不应抛出异常
        log_stage("Test Stage")
        log_step("Test step")
        log_success("Test success")
