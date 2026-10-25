from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.core.calendar import diary_calendar_authority
from app.services import diary


@pytest.mark.parametrize("offset", [0, 7, 8, -3650, 30])
def test_new_entry_date_limit_uses_server_date(monkeypatch, offset):
    today = date(2026, 10, 25)
    session = Mock()
    authority = Mock(return_value=today)
    monkeypatch.setattr(diary, "database_calendar_date", authority)
    requested = today + timedelta(days=offset)
    if offset > 7:
        with pytest.raises(HTTPException) as error:
            diary.validate_new_entry_date(session, requested)
        assert error.value.status_code == 422
        assert error.value.detail == {
            "code": "DIARY_ENTRY_DATE_TOO_FAR",
            "message_ar": "يمكن إضافة الأطعمة حتى 7 أيام قادمة فقط.",
        }
    else:
        diary.validate_new_entry_date(session, requested)
    authority.assert_called_once_with(session)


@pytest.mark.parametrize("hour, allowed", [(20, False), (21, True)])
def test_new_entry_limit_changes_at_riyadh_midnight(monkeypatch, hour, allowed):
    today = diary_calendar_authority(datetime(2026, 10, 25, hour, 59 if hour == 20 else 0, 59 if hour == 20 else 0, tzinfo=timezone.utc)).current_diary_date
    monkeypatch.setattr(diary, "database_calendar_date", lambda session: today)
    requested = date(2026, 11, 2)
    if allowed:
        diary.validate_new_entry_date(Mock(), requested)
    else:
        with pytest.raises(HTTPException):
            diary.validate_new_entry_date(Mock(), requested)
