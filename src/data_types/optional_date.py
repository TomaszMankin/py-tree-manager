import re
from typing import Optional


class OptionalDate():
    """Represents a date with optional/unknown components.

    Supports partial dates where unknown parts are represented with 'X'.
    Format: yyyy-mm-dd where any digit can be replaced with 'X'.

    Examples:
        - Full date: "2026-01-15"
        - Partial year: "19XX-12-25"
        - Unknown day: "2026-01-XX"
        - Fully unknown: "XXXX-XX-XX"

    Attributes:
        _year (str): Year component (4 characters, digits or X's)
        _month (str): Month component (2 characters, digits or X's)
        _day (str): Day component (2 characters, digits or X's)
    """

    def __init__(self, year: str = "XXXX", month: str = "XX", day: str = "XX") -> None:
        """Initialize an OptionalDate with year, month, and day components.

        Args:
            year: Year string (4 characters, default "XXXX")
            month: Month string (2 characters, default "XX")
            day: Day string (2 characters, default "XX")
        """
        self._year = year
        self._month = month
        self._day = day

    @staticmethod
    def from_string(date_str: str) -> 'OptionalDate':
        """Parse a date string in yyyy-mm-dd format with optional X's.

        Creates an OptionalDate from a string. Validates that the format
        matches yyyy-mm-dd with digits or X's (case insensitive).

        Args:
            date_str: Date string in format yyyy-mm-dd (e.g., "2026-01-XX")

        Returns:
            OptionalDate: Parsed date object

        Raises:
            ValueError: If date_str is empty/None or has incorrect format

        Example:
            >>> date = OptionalDate.from_string("1990-12-25")
            >>> date = OptionalDate.from_string("19XX-XX-15")
        """
        if not date_str:
            raise ValueError("Date string is null.")

        pattern = r'^[\dXx]{4}-[\dXx]{2}-[\dXx]{2}$'
        if not bool(re.match(pattern, date_str)):
            raise ValueError(f"Date string has incorrect format: {date_str}.")

        date_chunks = date_str.split("-")

        return OptionalDate(date_chunks[0], date_chunks[1], date_chunks[2])

    def to_string(self) -> str:
        """Convert the OptionalDate to a string in yyyy-mm-dd format.

        Returns:
            str: Date string in format yyyy-mm-dd

        Example:
            >>> date = OptionalDate("2026", "01", "15")
            >>> date.to_string()
            '2026-01-15'
        """
        return f"{self._year}-{self._month}-{self._day}"