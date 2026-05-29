import re
from typing import Optional


class OptionalDate():
    """Represents a date with optional/unknown components.

    Supports partial dates where unknown parts are represented with 'X'.
    Format: [~][<]yyyy-mm-dd where any digit can be replaced with 'X'.
    The optional prefix characters encode approximate (~, Około) and
    before-date (<, Przed) qualifiers; they are stored and round-tripped
    as part of the date string.

    Examples:
        - Full date: "2026-01-15"
        - Partial year: "19XX-12-25"
        - Unknown day: "2026-01-XX"
        - Fully unknown: "XXXX-XX-XX"
        - Approximate: "~1900-04-XX"
        - Before date: "<19XX-XX-XX"
        - Both qualifiers: "~<19XX-XX-XX"

    Attributes:
        _prefix (str): Qualifier prefix (subset of "~<", may be empty)
        _year (str): Year component (4 characters, digits or X's)
        _month (str): Month component (2 characters, digits or X's)
        _day (str): Day component (2 characters, digits or X's)
    """

    def __init__(self, year: str = "XXXX", month: str = "XX", day: str = "XX", prefix: str = "") -> None:
        """Initialize an OptionalDate with year, month, day and optional prefix.

        Args:
            year: Year string (4 characters, default "XXXX")
            month: Month string (2 characters, default "XX")
            day: Day string (2 characters, default "XX")
            prefix: Qualifier prefix composed of '~' and/or '<' (default "")
        """
        self._prefix = prefix
        self._year = year
        self._month = month
        self._day = day

    @staticmethod
    def from_string(date_str: str) -> 'OptionalDate':
        """Parse a date string in [~][<]yyyy-mm-dd format with optional X's.

        Creates an OptionalDate from a string. Accepts an optional leading
        prefix of '~' (Około) and/or '<' (Przed) followed by the date body.

        Args:
            date_str: Date string, optionally prefixed with '~' and/or '<',
                      e.g. "2026-01-XX", "~1900-04-XX", "<19XX-XX-XX",
                      "~<19XX-XX-XX"

        Returns:
            OptionalDate: Parsed date object (prefix preserved)

        Raises:
            ValueError: If date_str is empty/None or has incorrect format

        Example:
            >>> date = OptionalDate.from_string("1990-12-25")
            >>> date = OptionalDate.from_string("~<19XX-XX-15")
        """
        if not date_str:
            raise ValueError("Date string is null.")

        match = re.match(r'^([~<]*)([\dXx]{4}-[\dXx]{2}-[\dXx]{2})$', date_str)
        if not match:
            raise ValueError(f"Date string has incorrect format: {date_str}.")

        prefix = match.group(1)
        body = match.group(2)
        date_chunks = body.split("-")

        return OptionalDate(date_chunks[0], date_chunks[1], date_chunks[2], prefix)

    def to_string(self) -> str:
        """Convert the OptionalDate to a string in [~][<]yyyy-mm-dd format.

        Returns:
            str: Date string, including any qualifier prefix

        Example:
            >>> date = OptionalDate("2026", "01", "15")
            >>> date.to_string()
            '2026-01-15'
            >>> date = OptionalDate("1900", "04", "XX", "~")
            >>> date.to_string()
            '~1900-04-XX'
        """
        return f"{self._prefix}{self._year}-{self._month}-{self._day}"