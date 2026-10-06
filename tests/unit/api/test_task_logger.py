"""per-task 日志 sink 契约（真实 loguru，临时数据目录）"""

import pytest

pytestmark = [pytest.mark.unit]


@pytest.fixture
def isolated_data_root(tmp_path, monkeypatch):
    monkeypatch.setattr("mediafactory.config.get_data_root_dir", lambda: tmp_path)
    return tmp_path


class TestTaskLogSink:
    def test_log_lines_land_in_task_file_with_separator(self, isolated_data_root):
        from mediafactory.api.task_logger import (
            attach_task_log_sink,
            detach_task_log_sink,
            task_log_path,
        )
        from mediafactory.logging import log_info

        sink = attach_task_log_sink("t1", "scale=4")
        try:
            log_info("hello from engine")
        finally:
            detach_task_log_sink(sink)

        content = task_log_path("t1").read_text(encoding="utf-8")
        assert "==== attempt 1 @" in content
        assert "scale=4" in content
        assert "hello from engine" in content

    def test_repeated_attach_increments_attempt(self, isolated_data_root):
        from mediafactory.api.task_logger import (
            attach_task_log_sink,
            detach_task_log_sink,
            task_log_path,
        )
        from mediafactory.logging import log_info

        for _ in range(2):
            s = attach_task_log_sink("t2", "cfg")
            log_info("run")
            detach_task_log_sink(s)
        content = task_log_path("t2").read_text(encoding="utf-8")
        assert "==== attempt 1 @" in content and "==== attempt 2 @" in content

    def test_detach_survives_bad_sink_id(self):
        from mediafactory.api.task_logger import detach_task_log_sink

        detach_task_log_sink(999999)  # 不抛

    def test_engine_log_not_in_task_file_after_detach(self, isolated_data_root):
        from mediafactory.api.task_logger import (
            attach_task_log_sink,
            detach_task_log_sink,
            task_log_path,
        )
        from mediafactory.logging import log_info

        s = attach_task_log_sink("t3", "cfg")
        detach_task_log_sink(s)
        log_info("after detach")
        assert "after detach" not in task_log_path("t3").read_text(encoding="utf-8")

    def test_read_tail_and_cleanup(self, isolated_data_root):
        from mediafactory.api.task_logger import (
            cleanup_task_log,
            read_task_log_tail,
            task_log_path,
        )

        task_log_path("t4").write_text("l1\nl2\nl3\n", encoding="utf-8")
        assert read_task_log_tail("t4") == ["l1", "l2", "l3"]
        assert read_task_log_tail("t4", max_lines=2) == ["l2", "l3"]
        assert read_task_log_tail("nonexistent") == []
        cleanup_task_log("t4")
        assert not task_log_path("t4").exists()
        cleanup_task_log("t4")  # 幂等
