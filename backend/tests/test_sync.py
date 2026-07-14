import pytest


pytestmark = pytest.mark.skip(reason="Sync push/pull is Future Scope and disabled for online-only v1.")


def test_sync_api_is_future_scope() -> None:
    """Historical sync acceptance coverage is intentionally disabled for v1."""
