import pytest
from src.data_types.optional_date import OptionalDate


class TestOptionalDateFromString:
    def test_from_string_bare_date_unchanged(self):
        date = OptionalDate.from_string("1942-03-24")
        assert date.to_string() == "1942-03-24"

    def test_from_string_accepts_przed_prefix(self):
        date = OptionalDate.from_string("<19XX-XX-XX")
        assert date.to_string() == "<19XX-XX-XX"

    def test_from_string_accepts_okolo_prefix(self):
        date = OptionalDate.from_string("~1900-04-XX")
        assert date.to_string() == "~1900-04-XX"

    def test_from_string_accepts_both_prefixes(self):
        date = OptionalDate.from_string("~<19XX-XX-XX")
        assert date.to_string() == "~<19XX-XX-XX"

    def test_from_string_rejects_invalid_prefix(self):
        with pytest.raises(ValueError):
            OptionalDate.from_string("?19XX-XX-XX")

    def test_from_string_rejects_empty(self):
        with pytest.raises(ValueError):
            OptionalDate.from_string("")

    def test_from_string_rejects_none(self):
        with pytest.raises(ValueError):
            OptionalDate.from_string(None)
