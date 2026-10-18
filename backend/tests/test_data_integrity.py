
from datetime import timezone

import pytest

from app.eligibility.repository import (
    ReviewRequiredError,
    _parse_timestamp,
    _parse_uuid,
)


def test_rejects_invalid_scheme_uuid():
    with pytest.raises(ReviewRequiredError, match="valid UUID"):
        _parse_uuid("not-a-uuid", "scheme_id")


def test_rejects_missing_source_timestamp():
    with pytest.raises(ReviewRequiredError, match="missing"):
        _parse_timestamp("")


def test_rejects_timestamp_without_timezone():
    with pytest.raises(ReviewRequiredError, match="timezone"):
        _parse_timestamp("2026-10-18T12:00:00")


def test_normalizes_timestamp_to_utc():
    result = _parse_timestamp("2026-10-18T12:00:00+05:30")

    assert result.tzinfo == timezone.utc
    assert result.hour == 6
    assert result.minute == 30
