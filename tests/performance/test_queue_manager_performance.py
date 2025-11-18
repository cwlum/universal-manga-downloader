from __future__ import annotations

import time

import pytest

from core.queue_manager import QueueManager


@pytest.mark.performance
def test_queue_manager_throughput_is_fast() -> None:
    manager = QueueManager()
    iterations = 1000

    start = time.perf_counter()
    for queue_id in range(iterations):
        manager.add_item(queue_id, f"https://example.com/{queue_id}", None)
    for queue_id in range(iterations):
        manager.start_item(queue_id)
        manager.update_progress(queue_id, 1, maximum=1)
        manager.complete_item(queue_id)
    runtime = time.perf_counter() - start

    stats = manager.get_stats()
    assert stats.total == iterations
    assert stats.completed == iterations
    assert stats.pending == 0
    assert stats.active == 0
    assert runtime < 1.0, f"Queue operations took {runtime:.3f}s for {iterations} items"
