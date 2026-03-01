"""Tests for unified cancellation mechanism.

This module tests the CancellationToken implementation which provides
thread-safe cancellation across the application.
"""

import pytest
import threading
import time
from mediafactory.core.tool import CancellationToken


class TestCancellationToken:
    """Test CancellationToken functionality."""

    def test_initialization(self):
        """Test that CancellationToken initializes correctly."""
        token = CancellationToken()
        assert not token.is_cancelled()
        assert token.get_reason() == ""

    def test_cancel_with_reason(self):
        """Test cancelling with a reason."""
        token = CancellationToken()
        token.cancel("User requested cancellation")
        
        assert token.is_cancelled()
        assert token.get_reason() == "User requested cancellation"

    def test_cancel_without_reason(self):
        """Test cancelling without a reason."""
        token = CancellationToken()
        token.cancel()
        
        assert token.is_cancelled()
        assert token.get_reason() == ""

    def test_reset(self):
        """Test resetting a cancelled token."""
        token = CancellationToken()
        token.cancel("Some reason")
        assert token.is_cancelled()
        
        token.reset()
        assert not token.is_cancelled()
        assert token.get_reason() == ""

    def test_thread_safety(self):
        """Test that CancellationToken is thread-safe."""
        token = CancellationToken()
        results = []
        
        def worker():
            # Each thread tries to check and cancel
            for _ in range(100):
                if not token.is_cancelled():
                    token.cancel("Worker thread")
                results.append(token.is_cancelled())
        
        # Create multiple threads
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All results should be True after first cancel
        assert token.is_cancelled()
        assert all(results[100:])  # After first 100, all should be True

    def test_threading_event_compatibility_set(self):
        """Test threading.Event-compatible set() method."""
        token = CancellationToken()
        token.set()
        
        assert token.is_set()
        assert token.is_cancelled()

    def test_threading_event_compatibility_clear(self):
        """Test threading.Event-compatible clear() method."""
        token = CancellationToken()
        token.set()
        assert token.is_set()
        
        token.clear()
        assert not token.is_set()
        assert not token.is_cancelled()

    def test_threading_event_compatibility_is_set(self):
        """Test threading.Event-compatible is_set() method."""
        token = CancellationToken()
        assert not token.is_set()
        
        token.cancel()
        assert token.is_set()

    def test_multiple_cancellations(self):
        """Test that multiple cancel calls don't cause issues."""
        token = CancellationToken()
        
        token.cancel("First reason")
        assert token.get_reason() == "First reason"
        
        token.cancel("Second reason")
        # Second cancel should update the reason
        assert token.get_reason() == "Second reason"
        assert token.is_cancelled()

    def test_concurrent_reset_and_cancel(self):
        """Test concurrent reset and cancel operations."""
        token = CancellationToken()
        stop_event = threading.Event()
        
        def canceller():
            while not stop_event.is_set():
                token.cancel("Canceller")
                time.sleep(0.001)
        
        def resetter():
            while not stop_event.is_set():
                token.reset()
                time.sleep(0.001)
        
        # Run for a short time
        t1 = threading.Thread(target=canceller)
        t2 = threading.Thread(target=resetter)
        t1.start()
        t2.start()
        
        time.sleep(0.1)
        stop_event.set()
        
        t1.join()
        t2.join()
        
        # No assertion about final state, just ensure no crashes
        # The token should be in a valid state
        _ = token.is_cancelled()

    def test_usage_in_worker_pattern(self):
        """Test typical usage pattern in worker threads."""
        token = CancellationToken()
        work_done = []
        
        def worker():
            for i in range(10):
                if token.is_cancelled():
                    break
                work_done.append(i)
                time.sleep(0.01)
        
        # Start worker
        thread = threading.Thread(target=worker)
        thread.start()
        
        # Cancel after a short time
        time.sleep(0.05)
        token.cancel("Stop work")
        
        thread.join()
        
        # Worker should have stopped early
        assert len(work_done) < 10
        assert token.is_cancelled()

    def test_lambda_compatibility(self):
        """Test CancellationToken works in lambda expressions (common in GUI code)."""
        token = CancellationToken()
        
        # Common pattern in GUI observers
        is_cancelled_func = lambda: token.is_set()
        
        assert not is_cancelled_func()
        token.set()
        assert is_cancelled_func()


class TestCancellationTokenIntegration:
    """Integration tests for CancellationToken with other components."""

    def test_gui_observer_pattern(self):
        """Test typical GUI observer pattern with CancellationToken."""
        token = CancellationToken()
        progress_updates = []
        
        def process_with_progress(observers):
            for i in range(100):
                if observers["cancelled"]():
                    return False
                progress_updates.append(i)
                time.sleep(0.001)
            return True
        
        observers = {
            "cancelled": lambda: token.is_set(),
            "progress_func": lambda p, m: progress_updates.append(f"Progress: {p}")
        }
        
        # Run in thread
        result = []
        def worker():
            result.append(process_with_progress(observers))
        
        thread = threading.Thread(target=worker)
        thread.start()
        
        # Cancel after short time
        time.sleep(0.05)
        token.set()
        
        thread.join()
        
        # Should have cancelled
        assert result[0] is False
        assert len(progress_updates) < 100

    def test_batch_cancellation_pattern(self):
        """Test batch processing cancellation pattern."""
        batch_token = CancellationToken()
        file_tokens = [CancellationToken() for _ in range(3)]
        
        processed = []
        
        def process_file(file_id, file_token):
            for i in range(10):
                # Check both batch and file token
                if batch_token.is_set() or file_token.is_set():
                    return False
                processed.append((file_id, i))
                time.sleep(0.01)
            return True
        
        # Process files
        threads = []
        for i, file_token in enumerate(file_tokens):
            t = threading.Thread(target=process_file, args=(i, file_token))
            threads.append(t)
            t.start()
        
        # Cancel batch after short time
        time.sleep(0.05)
        batch_token.set()
        
        for t in threads:
            t.join()
        
        # All files should have stopped early
        file_0_count = len([p for p in processed if p[0] == 0])
        file_1_count = len([p for p in processed if p[0] == 1])
        file_2_count = len([p for p in processed if p[0] == 2])
        
        assert file_0_count < 10
        assert file_1_count < 10
        assert file_2_count < 10
