"""Shared pytest fixtures for py-tree-manager tests.

Fixtures:
  tmp_root        -- creates a minimal tree under tmp_path, configures FileService to
                     use that tree as its root, returns (root_path, file_service).
  me_json_factory -- callable factory for valid me.json dicts.

Shortcut stub strategy: patch ShortcutHelper.create_shortcut directly rather than
faking the pythoncom.CoCreateInstance + IShellLink + IPersistFile chain, which
requires more ceremony and is fragile against pywin32 version changes.
"""

import json
import sys
import uuid
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Shortcut stub — patches ShortcutHelper.create_shortcut with a no-op-that-
# touches-the-file.  Must be called before any project test runs so the
# service-layer tests (which call TreeService.save_person_and_add_to_tree)
# get a stub instead of real COM.
# ---------------------------------------------------------------------------

def _install_shortcut_stub():
    """Replace ShortcutHelper.create_shortcut with a no-op stub.

    The stub creates an empty file at shortcut_path so that downstream code
    that checks Path(shortcut_path).exists() still works, without invoking
    real COM.

    Called at module-import time so all test collection happens after the
    stub is in place.  The integration conftest restores the real method for
    integration tests, then calls this again on teardown.
    """
    from src.helpers import shortcut_helper as _sh

    def _fake_create_shortcut(target_path: str, shortcut_path: str) -> None:
        Path(shortcut_path).touch()

    _sh.ShortcutHelper.create_shortcut = staticmethod(_fake_create_shortcut)


# Install before any test collection imports project code that exercises shortcuts.
_install_shortcut_stub()


@pytest.fixture(scope="session", autouse=True)
def shortcut_stub():
    """Session-scoped fixture that confirms the stub is in place.

    Exists for documentation and to provide a named hook for any future
    fixture that needs to depend on the stub being installed.
    """
    yield


# ---------------------------------------------------------------------------
# tmp_root
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_root(tmp_path, monkeypatch):
    """Provision a test tree root and return a configured FileService.

    Steps:
      1. Redirect tempfile.gettempdir() to tmp_path/apptmp so the legacy
         %TEMP% migration path goes to a scratch space.
      2. Redirect LOCALAPPDATA env var to tmp_path/appdata so the bootstrap
         pointer file goes to a per-test scratch space (never the real
         %LOCALAPPDATA%).
      3. Instantiate FileService (pointer absent + no legacy = fresh install).
      4. Create tmp_path/tree as the root; call set_root_folder() which
         creates Lista osob/, Drzewo/, Poczekalnia/, Rody/, .PyTreeManager/,
         .PyTreeManager/logs/, writes settings.json there, and writes pointer.

    Returns:
        tuple[Path, FileService]: (root_path, file_service)

    The root_path is tmp_path/tree. FileService has root set and
    is_root_location_set() returns True.
    """
    import tempfile as _tempfile
    from src.services.file_service import FileService

    app_tmp = tmp_path / "apptmp"
    app_tmp.mkdir()
    monkeypatch.setattr(_tempfile, "gettempdir", lambda: str(app_tmp))

    appdata = tmp_path / "appdata"
    appdata.mkdir()
    monkeypatch.setenv("LOCALAPPDATA", str(appdata))

    tree_root = tmp_path / "tree"
    tree_root.mkdir()

    fs = FileService()
    fs.set_root_folder(str(tree_root))

    return tree_root, fs


# ---------------------------------------------------------------------------
# me_json_factory
# ---------------------------------------------------------------------------

@pytest.fixture
def me_json_factory():
    """Return a callable that builds a complete, valid me.json dict.

    All relationship arrays default to empty lists so the result always passes
    TreeService._validate_person_data(). Override any field by keyword.

    Usage:
        data = me_json_factory(name="Jan Kowalski", uid="<uuid>")
    """

    def _make(
        uid=None,
        name="Jan Testowy",
        first_name="Jan",
        last_name="Testowy",
        parents=None,
        parents_id=None,
        children=None,
        children_id=None,
        spouses=None,
        spouse_id=None,
        siblings=None,
        siblings_id=None,
        notes="",
        date_of_birth=None,
        date_of_death=None,
        location="",
        sex="Mezczyzna",
    ):
        return {
            "unique_identifier": uid or str(uuid.uuid4()),
            "person_name": name,
            "location": location,
            "first_name": first_name,
            "other_first_names": "",
            "last_name": last_name,
            "other_last_names": "",
            "maiden_name": "",
            "other_maiden_names": "",
            "has_maiden_name": False,
            "sex": sex,
            "spouse": spouses or [],
            "spouse_id": spouse_id or [],
            "children": children or [],
            "children_id": children_id or [],
            "parents": parents or [],
            "parents_id": parents_id or [],
            "siblings": siblings or [],
            "siblings_id": siblings_id or [],
            "notes": notes,
            "dates_of_birth": date_of_birth or "",
            "dates_of_death": date_of_death or "",
        }

    return _make


# ---------------------------------------------------------------------------
# Session-scoped no-real-emails guard.
#
# Two defensive layers prevent any test from sending a real email:
#   1. PYTREEMANAGER_EMAIL_* env vars are removed for the entire session.
#      With them gone, is_email_configured() returns False and the email
#      enqueue path short-circuits before reaching _attempt_send.
#   2. smtplib.SMTP_SSL is replaced with a MagicMock. Even if a code path
#      reaches the network layer (e.g., a test sets the env vars locally
#      via monkeypatch.setenv), the SMTP_SSL call returns a mock instead
#      of opening a real socket.
#
# Individual tests that need specific SMTP behaviour use per-test
# monkeypatch.setattr(smtplib, "SMTP_SSL", ...) — pytest's monkeypatch
# undoes after each test, restoring the session-wide mock.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True, scope="session")
def _no_real_emails_during_tests():
    import os
    import smtplib
    from unittest.mock import MagicMock

    original_smtp_ssl = smtplib.SMTP_SSL
    original_password = os.environ.pop("PYTREEMANAGER_EMAIL_PASSWORD", None)
    original_recipient = os.environ.pop("PYTREEMANAGER_EMAIL_RECIPIENT", None)

    smtplib.SMTP_SSL = MagicMock(return_value=MagicMock())

    yield

    smtplib.SMTP_SSL = original_smtp_ssl
    if original_password is not None:
        os.environ["PYTREEMANAGER_EMAIL_PASSWORD"] = original_password
    if original_recipient is not None:
        os.environ["PYTREEMANAGER_EMAIL_RECIPIENT"] = original_recipient
