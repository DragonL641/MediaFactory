"""config/defaults.py 路径工具函数测试"""

import sys

from mediafactory.config import get_app_root_dir, get_data_root_dir


class TestDataRootDir:
    """get_data_root_dir：frozen 迁平台用户目录，dev 与 app root 一致"""

    def test_dev_mode_equals_app_root(self):
        # 非 frozen（开发环境）：数据根与应用根相同（项目根）
        assert get_data_root_dir() == get_app_root_dir()

    def test_frozen_darwin_uses_application_support(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "platform", "darwin")
        monkeypatch.setenv("HOME", str(tmp_path))
        assert get_data_root_dir() == (
            tmp_path / "Library" / "Application Support" / "MediaFactory"
        )

    def test_frozen_win32_uses_appdata(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "platform", "win32")
        monkeyappdata = tmp_path / "AppData" / "Roaming"
        monkeypatch.setenv("APPDATA", str(monkeyappdata))
        assert get_data_root_dir() == monkeyappdata / "MediaFactory"

    def test_frozen_win32_appdata_missing_falls_back(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.delenv("APPDATA", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        assert get_data_root_dir() == (
            tmp_path / "AppData" / "Roaming" / "MediaFactory"
        )

    def test_webui_still_resolves_from_app_root(self, monkeypatch, tmp_path):
        # 只读资产（webui/）仍跟随 app root，不随数据根迁移
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "platform", "darwin")
        monkeypatch.setenv("HOME", str(tmp_path))
        from mediafactory.api.main import _webui_dir

        assert _webui_dir().name == "webui"
        assert "Application Support" not in str(_webui_dir())

    def test_frozen_config_path_follows_data_root(self, monkeypatch, tmp_path):
        # config.toml 是可变数据：frozen 下必须落数据根（用户目录），不落 exe 旁
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "platform", "darwin")
        monkeypatch.setenv("HOME", str(tmp_path))
        from mediafactory.config import get_config_path

        assert get_config_path() == (
            tmp_path / "Library" / "Application Support" / "MediaFactory" / "config.toml"
        )
