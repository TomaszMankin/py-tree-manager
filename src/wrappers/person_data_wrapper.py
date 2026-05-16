
from typing import Any, Dict, List, Optional
from enum import Enum
import uuid

class PersonDataProperty(Enum):
    UNIQUE_IDENTIFIER = "unique_identifier"
    PERSON_NAME = "person_name"
    LOCATION = "location"
    SPOUSES = "spouse"
    SPOUSE_ID = "spouse_id"
    CHILDREN = "children"
    CHILDREN_ID = "children_id"
    PARENTS = "parents"
    PARENTS_ID = "parents_id"
    SIBLINGS = "siblings"
    SIBLINGS_ID = "siblings_id"
    NOTES = "notes"
    DATE_OF_BIRTH = "dates_of_birth"
    DATE_OF_DEATH = "dates_of_death"
    FIRST_NAME = "first_name"
    OTHER_FIRST_NAMES = "other_first_names"
    LAST_NAME = "last_name"
    OTHER_LAST_NAMES = "other_last_names"
    MAIDEN_NAME = "maiden_name"
    OTHER_MAIDEN_NAMES = "other_maiden_names"
    SEX = "sex"
    HAS_MAIDEN_NAME = "has_maiden_name"

class PersonDataWrapper():
    """
    Wrapper for person data dictionary providing type-safe property access.

    Uses PersonDataProperty enum to ensure consistent property names.
    Provides both a generic get/set interface and typed convenience methods
    for each property.
    """

    def __init__(self, person_data: Dict[str, Any] | None = None):
        self.person_data = {} if person_data is None else person_data

    # -------------------------------------------------------------------------
    # Generic interface
    # -------------------------------------------------------------------------

    def get(self, property: PersonDataProperty) -> Any | None:
        """Get property value, returns None if not found."""
        return self.person_data.get(property.value)

    def set(self, property: PersonDataProperty, value: Any) -> None:
        """Set property value."""
        self.person_data[property.value] = value

    def to_dict(self) -> Dict[str, Any]:
        """Return underlying dictionary."""
        return self.person_data

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    def get_unique_identifier(self) -> str | None:
        return self.person_data.get(PersonDataProperty.UNIQUE_IDENTIFIER.value, "")

    def set_unique_identifier(self, value: str) -> None:
        self.person_data[PersonDataProperty.UNIQUE_IDENTIFIER.value] = value

    def get_person_name(self) -> str | None:
        return self.person_data.get(PersonDataProperty.PERSON_NAME.value, "")

    def set_person_name(self, value: str) -> None:
        self.person_data[PersonDataProperty.PERSON_NAME.value] = value

    def get_location(self) -> str | None:
        return self.person_data.get(PersonDataProperty.LOCATION.value, "")

    def set_location(self, value: str) -> None:
        self.person_data[PersonDataProperty.LOCATION.value] = value

    # -------------------------------------------------------------------------
    # Name components
    # -------------------------------------------------------------------------

    def get_first_name(self) -> str | None:
        return self.person_data.get(PersonDataProperty.FIRST_NAME.value, "")

    def set_first_name(self, value: str) -> None:
        self.person_data[PersonDataProperty.FIRST_NAME.value] = value

    def get_other_first_names(self) -> str | None:
        return self.person_data.get(PersonDataProperty.OTHER_FIRST_NAMES.value, "")

    def set_other_first_names(self, value: str) -> None:
        self.person_data[PersonDataProperty.OTHER_FIRST_NAMES.value] = value

    def get_last_name(self) -> str | None:
        return self.person_data.get(PersonDataProperty.LAST_NAME.value, "")

    def set_last_name(self, value: str) -> None:
        self.person_data[PersonDataProperty.LAST_NAME.value] = value

    def get_other_last_names(self) -> str | None:
        return self.person_data.get(PersonDataProperty.OTHER_LAST_NAMES.value, "")

    def set_other_last_names(self, value: str) -> None:
        self.person_data[PersonDataProperty.OTHER_LAST_NAMES.value] = value

    def get_maiden_name(self) -> str | None:
        return self.person_data.get(PersonDataProperty.MAIDEN_NAME.value, "")

    def set_maiden_name(self, value: str) -> None:
        self.person_data[PersonDataProperty.MAIDEN_NAME.value] = value

    def get_other_maiden_names(self) -> str | None:
        return self.person_data.get(PersonDataProperty.OTHER_MAIDEN_NAMES.value, "")

    def set_other_maiden_names(self, value: str) -> None:
        self.person_data[PersonDataProperty.OTHER_MAIDEN_NAMES.value] = value

    def get_sex(self) -> str | None:
        return self.person_data.get(PersonDataProperty.SEX.value, "")

    def set_sex(self, value: str) -> None:
        self.person_data[PersonDataProperty.SEX.value] = value

    def get_has_maiden_name(self) -> bool | None:
        return self.person_data.get(PersonDataProperty.HAS_MAIDEN_NAME.value, False)

    def set_has_maiden_name(self, value: bool) -> None:
        self.person_data[PersonDataProperty.HAS_MAIDEN_NAME.value] = value

    # -------------------------------------------------------------------------
    # Relationships — paths
    # -------------------------------------------------------------------------

    def get_spouses(self) -> List[str]:
        return self.person_data.get(PersonDataProperty.SPOUSES.value, [])

    def set_spouses(self, value: List[str]) -> None:
        self.person_data[PersonDataProperty.SPOUSES.value] = value

    def get_children(self) -> List[str]:
        return self.person_data.get(PersonDataProperty.CHILDREN.value, [])

    def set_children(self, value: List[str]) -> None:
        self.person_data[PersonDataProperty.CHILDREN.value] = value

    def get_parents(self) -> List[str]:
        return self.person_data.get(PersonDataProperty.PARENTS.value, [])

    def set_parents(self, value: List[str]) -> None:
        self.person_data[PersonDataProperty.PARENTS.value] = value

    def get_siblings(self) -> List[str]:
        return self.person_data.get(PersonDataProperty.SIBLINGS.value, [])

    def set_siblings(self, value: List[str]) -> None:
        self.person_data[PersonDataProperty.SIBLINGS.value] = value

    # -------------------------------------------------------------------------
    # Relationships — UUIDs
    # -------------------------------------------------------------------------

    def get_spouse_ids(self) -> List[str]:
        return self.person_data.get(PersonDataProperty.SPOUSE_ID.value, [])

    def set_spouse_ids(self, value: List[str]) -> None:
        self.person_data[PersonDataProperty.SPOUSE_ID.value] = value

    def get_children_ids(self) -> List[str]:
        return self.person_data.get(PersonDataProperty.CHILDREN_ID.value, [])

    def set_children_ids(self, value: List[str]) -> None:
        self.person_data[PersonDataProperty.CHILDREN_ID.value] = value

    def get_parent_ids(self) -> List[str]:
        return self.person_data.get(PersonDataProperty.PARENTS_ID.value, [])

    def set_parent_ids(self, value: List[str]) -> None:
        self.person_data[PersonDataProperty.PARENTS_ID.value] = value

    def get_sibling_ids(self) -> List[str]:
        return self.person_data.get(PersonDataProperty.SIBLINGS_ID.value, [])

    def set_sibling_ids(self, value: List[str]) -> None:
        self.person_data[PersonDataProperty.SIBLINGS_ID.value] = value

    # -------------------------------------------------------------------------
    # Dates and notes
    # -------------------------------------------------------------------------

    def get_date_of_birth(self) -> str | None:
        return self.person_data.get(PersonDataProperty.DATE_OF_BIRTH.value) or None

    def set_date_of_birth(self, value: str | None) -> None:
        self.person_data[PersonDataProperty.DATE_OF_BIRTH.value] = value or ""

    def get_date_of_death(self) -> str | None:
        return self.person_data.get(PersonDataProperty.DATE_OF_DEATH.value) or None

    def set_date_of_death(self, value: str | None) -> None:
        self.person_data[PersonDataProperty.DATE_OF_DEATH.value] = value or ""

    def get_notes(self) -> str | None:
        return self.person_data.get(PersonDataProperty.NOTES.value, "")

    def set_notes(self, value: str) -> None:
        self.person_data[PersonDataProperty.NOTES.value] = value

    # -------------------------------------------------------------------------
    # Computed
    # -------------------------------------------------------------------------

    UNKNOWN = "(nieznane)"

    def get_full_name(self) -> str:
        """Returns full name of the person."""
        full_name = self.get_first_name() or self.UNKNOWN

        other_first = self.get_other_first_names()
        if other_first:
            full_name += " " + other_first

        full_name += " " + (self.get_last_name() or self.UNKNOWN)

        other_last = self.get_other_last_names()
        if other_last:
            full_name += ";" + other_last

        if self.get_has_maiden_name():
            full_name += " zd. " + self.get_maiden_name()

            other_maiden = self.get_other_maiden_names()
            if other_maiden:
                full_name += ";" + other_maiden

        return full_name
