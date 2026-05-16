"""Unit tests for services/file_service.py.

TDD order followed: BOM regression test written first (red before Step 1 fix,
green after). All other tests written after the implementation.

Test classes:
  TestFileServiceJsonReading       -- BOM regression + no-BOM happy path
  TestFileServiceUniqueFolderName  -- _get_unique_folder_name duplicate numbering
  TestFileServiceCreatePersonFolder -- create_person_folder layout
  TestFileServiceRootLocation      -- is_root_location_set flag behaviour + scan
  TestFileServiceScanDrafts        -- scan_drafts_location duplicate-append regression
"""

import json
import os
import uuid
from pathlib import Path

import pytest

from src.services.file_service import FileService
from src.wrappers.person_data_wrapper import PersonDataWrapper, PersonDataProperty
from src.wrappers.settings_wrapper import SettingsWrapper, SettingsDataProperty


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"
BOM_FIXTURE = FIXTURE_DIR / "me_json_with_bom.json"
NO_BOM_FIXTURE = FIXTURE_DIR / "me_json_no_bom.json"


def _make_fs(tmp_path, monkeypatch):
    """Create an isolated FileService that stores settings in tmp_path/apptmp.

    Also monkeypatches LOCALAPPDATA so the bootstrap pointer goes to a per-test
    scratch space (never the real %LOCALAPPDATA%). This prevents cross-test
    contamination from set_root_folder() writing the pointer.
    """
    import tempfile as _tempfile

    app_tmp = tmp_path / "apptmp"
    app_tmp.mkdir(exist_ok=True)
    monkeypatch.setattr(_tempfile, "gettempdir", lambda: str(app_tmp))

    appdata = tmp_path / "appdata"
    appdata.mkdir(exist_ok=True)
    monkeypatch.setenv("LOCALAPPDATA", str(appdata))

    return FileService()


def _make_rooted_fs(tmp_path, monkeypatch):
    """Create an isolated FileService with a root already set."""
    fs = _make_fs(tmp_path, monkeypatch)
    root = tmp_path / "tree"
    root.mkdir()
    fs.set_root_folder(str(root))
    return root, fs


# ---------------------------------------------------------------------------
# JSON reading — BOM regression + happy path
# ---------------------------------------------------------------------------

class TestFileServiceJsonReading:
    """Covers the BOM encoding fix at _read_json_data (line 377).

    The BOM regression test FAILS before the encoding='utf-8' -> 'utf-8-sig'
    fix is applied and PASSES after. No-BOM test passes in both states.
    """

    def test_reads_utf8_with_bom(self, tmp_path, monkeypatch):
        """_read_json_data must successfully parse a file written with UTF-8 BOM.

        This is the regression test that pins the BOM fix. It reads the static
        fixture at tests/fixtures/me_json_with_bom.json (EF BB BF prefix).
        Without the fix (encoding='utf-8') this raises json.JSONDecodeError.
        With the fix (encoding='utf-8-sig') the BOM is stripped and JSON parses.
        """
        fs = _make_fs(tmp_path, monkeypatch)
        data = fs._read_json_data(str(BOM_FIXTURE))
        assert data["unique_identifier"] == "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb"
        assert data["person_name"] == "Jan Testowy"

    def test_reads_utf8_without_bom(self, tmp_path, monkeypatch):
        """_read_json_data reads a plain UTF-8 file (no BOM) correctly."""
        fs = _make_fs(tmp_path, monkeypatch)
        data = fs._read_json_data(str(NO_BOM_FIXTURE))
        assert data["unique_identifier"] == "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb"
        assert data["person_name"] == "Jan Testowy"

    def test_read_me_file_with_bom(self, tmp_path, monkeypatch):
        """Public read_me_file() also handles BOM (it delegates to _read_json_data)."""
        fs = _make_fs(tmp_path, monkeypatch)
        data = fs.read_me_file(str(BOM_FIXTURE))
        assert data["unique_identifier"] == "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb"

    def test_reads_bom_file_written_inline(self, tmp_path, monkeypatch):
        """BOM written programmatically (as Python bytes) is also parsed correctly."""
        fs = _make_fs(tmp_path, monkeypatch)
        bom_path = tmp_path / "inline_bom.json"
        payload = {"unique_identifier": "test-uid-inline", "person_name": "Inline"}
        bom_path.write_bytes(b"\xef\xbb\xbf" + json.dumps(payload).encode("utf-8"))

        data = fs._read_json_data(str(bom_path))
        assert data["unique_identifier"] == "test-uid-inline"


# ---------------------------------------------------------------------------
# _get_unique_folder_name — duplicate numbering
# ---------------------------------------------------------------------------

class TestFileServiceUniqueFolderName:
    """Covers _get_unique_folder_name() collision resolution."""

    def test_returns_basename_when_free(self, tmp_path, monkeypatch):
        """When no folder with that name exists the base name is returned unchanged."""
        root, fs = _make_rooted_fs(tmp_path, monkeypatch)
        result = fs._get_unique_folder_name("A Kowalski")
        assert result == "A Kowalski"

    def test_appends_2_when_basename_taken(self, tmp_path, monkeypatch):
        """When the base name folder exists the result is '<name> (2)'."""
        root, fs = _make_rooted_fs(tmp_path, monkeypatch)
        (root / "Lista osób" / "A Kowalski").mkdir()
        result = fs._get_unique_folder_name("A Kowalski")
        assert result == "A Kowalski (2)"

    def test_appends_3_when_2_also_taken(self, tmp_path, monkeypatch):
        """When both base name and (2) exist the result is '<name> (3)'."""
        root, fs = _make_rooted_fs(tmp_path, monkeypatch)
        (root / "Lista osób" / "A Kowalski").mkdir()
        (root / "Lista osób" / "A Kowalski (2)").mkdir()
        result = fs._get_unique_folder_name("A Kowalski")
        assert result == "A Kowalski (3)"


# ---------------------------------------------------------------------------
# create_person_folder
# ---------------------------------------------------------------------------

class TestFileServiceCreatePersonFolder:
    """Covers create_person_folder() directory + me.json layout."""

    def test_creates_folder_subfolders_and_me_json(self, tmp_path, monkeypatch, me_json_factory):
        """create_person_folder creates the expected tree on disk."""
        root, fs = _make_rooted_fs(tmp_path, monkeypatch)
        data = me_json_factory(name="Jan A", first_name="Jan", last_name="A")
        wrapper = PersonDataWrapper(data)

        path_str = fs.create_person_folder("Jan A", wrapper)
        folder = Path(path_str)

        assert folder.exists() and folder.is_dir()
        assert (folder / "me.json").exists()
        for sub in ("Dzieci", "Rodzice", "Małżonkowie", "Rodzeństwo"):
            assert (folder / sub).is_dir()

    def test_create_person_folder_raises_without_root(self, tmp_path, monkeypatch, me_json_factory):
        """create_person_folder raises RuntimeError when root is not set."""
        fs = _make_fs(tmp_path, monkeypatch)  # root NOT set
        wrapper = PersonDataWrapper(me_json_factory())
        with pytest.raises(RuntimeError):
            fs.create_person_folder("Jan B", wrapper)


# ---------------------------------------------------------------------------
# is_root_location_set — inverted flag
# ---------------------------------------------------------------------------

class TestFileServiceRootLocation:
    """Covers is_root_location_set() and scan_root_location().

    The flag in settings is select_root_folder:
      True  = "still needs to be selected" = root NOT set = is_root_location_set() -> False
      False = "already selected"           = root IS  set = is_root_location_set() -> True

    This inversion is the quirk documented in context.md and phases.md.
    """

    def test_is_root_set_false_before_set(self, tmp_path, monkeypatch):
        """Before set_root_folder() is called, is_root_location_set() is False.

        The settings default has select_root_folder=True (needs selection),
        so is_root_location_set() must return NOT True = False.
        """
        fs = _make_fs(tmp_path, monkeypatch)
        # Fresh FileService, no root configured yet.
        assert fs.is_root_location_set() is False

    def test_is_root_set_true_after_set(self, tmp_path, monkeypatch):
        """After set_root_folder() the flag is inverted to True.

        set_root_folder() calls _set_root_selected_flag(False), meaning
        'does NOT need to be selected (anymore)'. is_root_location_set()
        returns not False = True.
        """
        root, fs = _make_rooted_fs(tmp_path, monkeypatch)
        # Root was set in _make_rooted_fs.
        assert fs.is_root_location_set() is True

    def test_scan_root_skips_forbidden_folders(self, tmp_path, monkeypatch, me_json_factory):
        """scan_root_location only caches folders NOT in _forbidden_locations.

        Builds four folders: three valid + one forbidden ("Wspólne").
        After scan, three people should be cached, not four.
        """
        root, fs = _make_rooted_fs(tmp_path, monkeypatch)
        lista = root / "Lista osób"

        valid_names = ["A Person", "B Person", "C Person"]
        forbidden_name = "Wspólne"

        for name in valid_names:
            folder = lista / name
            folder.mkdir()
            me = me_json_factory(name=name, first_name=name.split()[0], last_name=name.split()[1])
            (folder / "me.json").write_text(
                json.dumps(me, ensure_ascii=False), encoding="utf-8"
            )

        # Create the forbidden folder with a me.json (it should be skipped by scan)
        forbidden_folder = lista / forbidden_name
        forbidden_folder.mkdir()
        me_forbidden = me_json_factory(name=forbidden_name, first_name="Wspólne", last_name="X")
        (forbidden_folder / "me.json").write_text(
            json.dumps(me_forbidden, ensure_ascii=False), encoding="utf-8"
        )

        fs.scan_root_location()

        cached = fs.get_list_of_people()
        cached_names = [v[PersonDataProperty.PERSON_NAME.value] for v in cached.values()]
        assert len(cached) == 3
        assert forbidden_name not in cached_names
        for name in valid_names:
            assert name in cached_names

    def test_scan_root_reads_bom_files(self, tmp_path, monkeypatch, me_json_factory):
        """scan_root_location successfully reads a me.json file that has a UTF-8 BOM.

        This is the integration of the BOM fix at line 222 (scan_root_location).
        """
        root, fs = _make_rooted_fs(tmp_path, monkeypatch)
        lista = root / "Lista osób"
        folder = lista / "BOM Person"
        folder.mkdir()

        me = me_json_factory(name="BOM Person", first_name="BOM", last_name="Person",
                             uid="cccccccc-1111-2222-3333-dddddddddddd")
        bom_bytes = b"\xef\xbb\xbf" + json.dumps(me, ensure_ascii=False).encode("utf-8")
        (folder / "me.json").write_bytes(bom_bytes)

        fs.scan_root_location()  # would raise JSONDecodeError before the fix

        cached = fs.get_list_of_people()
        assert "cccccccc-1111-2222-3333-dddddddddddd" in cached


# ---------------------------------------------------------------------------
# scan_drafts_location — duplicate-append regression
# ---------------------------------------------------------------------------

class TestFileServiceScanDrafts:
    """Covers the duplicate-append bug fix in scan_drafts_location().

    Before the fix: repeated calls accumulate the same file paths in
    self.saved_drafts_locations because the list was never cleared.
    After the fix: the list is reset at the start of each call.
    """

    def test_repeated_scans_do_not_accumulate_duplicates(self, tmp_root, monkeypatch):
        """Calling scan_drafts_location twice must not duplicate entries.

        Drafts live under <root>/Poczekalnia/ (not %TEMP%/PyTreeManager/).
        Uses tmp_root fixture so the root is set and Poczekalnia exists.
        """
        root, fs = tmp_root

        # Write one draft file into Poczekalnia
        draft_uid = str(uuid.uuid4())
        draft_path = root / "Poczekalnia" / f"{draft_uid}.json"
        draft_path.write_text("{}", encoding="utf-8")

        fs.scan_drafts_location()
        first_count = len(fs.saved_drafts_locations)

        fs.scan_drafts_location()
        second_count = len(fs.saved_drafts_locations)

        assert first_count == 1, "Expected 1 draft after first scan"
        assert second_count == 1, (
            "Expected 1 draft after second scan (not 2). "
            "scan_drafts_location accumulated duplicates — bug not fixed."
        )


# ---------------------------------------------------------------------------
# List-management edge cases
# ---------------------------------------------------------------------------

class TestFileServiceListEdges:
    """Covers edge cases for scan_root_location() not exercised by the base tests.

    These tests pin the current behavior as the contract; no behavior changes
    were made in this sprint.
    """

    def test_empty_lista_osob_returns_empty_people_list(self, tmp_path, monkeypatch):
        """scan_root_location() on an empty Lista osob returns zero cached people.

        The folder exists but has no person subfolders. This is the empty-root
        case the app may encounter on first use before any person is added.
        """
        root, fs = _make_rooted_fs(tmp_path, monkeypatch)
        # Lista osob exists (created by set_root_folder) but is empty.
        fs.scan_root_location()
        cached = fs.get_list_of_people()
        assert len(cached) == 0, (
            f"Expected 0 people for empty Lista osob, got {len(cached)}"
        )

    def test_only_forbidden_folders_returns_empty_people_list(self, tmp_path, monkeypatch):
        """scan_root_location() skips all four forbidden folder names.

        Even when every folder in Lista osob is forbidden, the result is zero
        cached people -- not an error, not a partial result.
        """
        root, fs = _make_rooted_fs(tmp_path, monkeypatch)
        lista = root / "Lista osob"
        # FileService uses the Polish name; construct it properly.
        lista = root / "Lista os\xf3b"

        forbidden_names = [
            "Pozostałe nieuporządkowane",
            "Rutowscy - dane ogólne",
            "Do ustalenia",
            "Wspólne",
        ]
        for name in forbidden_names:
            (lista / name).mkdir()

        fs.scan_root_location()
        cached = fs.get_list_of_people()
        assert len(cached) == 0, (
            f"Expected 0 people (all folders forbidden), got {len(cached)}: {list(cached.keys())}"
        )

    def test_scan_root_raises_when_root_not_set(self, tmp_path, monkeypatch):
        """scan_root_location() raises RuntimeError when no root folder is set.

        This is the documented contract: the caller must call set_root_folder()
        first. Testing pins this so a silent behavior change would surface.
        """
        fs = _make_fs(tmp_path, monkeypatch)  # root NOT set
        with pytest.raises(RuntimeError):
            fs.scan_root_location()

    def test_scan_root_raises_when_lista_osob_missing(self, tmp_path, monkeypatch):
        """scan_root_location() raises FileNotFoundError when Lista osob is absent.

        set_root_folder() creates Lista osob automatically, but a user who
        manually deletes that folder would hit this path. The current behavior
        is to raise (iterdir() on a non-existent dir) rather than return empty.
        """
        root, fs = _make_rooted_fs(tmp_path, monkeypatch)
        import shutil
        lista = root / "Lista os\xf3b"
        shutil.rmtree(str(lista))

        with pytest.raises((FileNotFoundError, OSError)):
            fs.scan_root_location()

    def test_scan_root_fifty_people_returns_all(self, tmp_path, monkeypatch):
        """scan_root_location() returns all 50 people from a 50-person tree.

        Sanity-checks that there is no off-by-one or O(n^2) hidden behaviour
        at scale comparable to the live 354-person tree.
        """
        root, fs = _make_rooted_fs(tmp_path, monkeypatch)
        lista = root / "Lista os\xf3b"

        uids = []
        for i in range(50):
            name = f"Person{i:03d} Testowy"
            folder = lista / name
            folder.mkdir()
            uid = str(uuid.uuid4())
            uids.append(uid)
            me = {
                "unique_identifier": uid,
                "person_name": name,
                "location": str(folder),
                "first_name": f"Person{i:03d}",
                "other_first_names": "",
                "last_name": "Testowy",
                "other_last_names": "",
                "maiden_name": "",
                "other_maiden_names": "",
                "has_maiden_name": False,
                "sex": "Mezczyzna",
                "spouse": [],
                "spouse_id": [],
                "children": [],
                "children_id": [],
                "parents": [],
                "parents_id": [],
                "siblings": [],
                "siblings_id": [],
                "notes": "",
                "dates_of_birth": "",
                "dates_of_death": "",
            }
            (folder / "me.json").write_text(
                json.dumps(me, ensure_ascii=False), encoding="utf-8"
            )

        fs.scan_root_location()
        cached = fs.get_list_of_people()
        assert len(cached) == 50, (
            f"Expected 50 cached people, got {len(cached)}"
        )
        for uid in uids:
            assert uid in cached, f"UID {uid} missing from cached people"

    def test_get_unique_folder_name_suffix_4(self, tmp_path, monkeypatch):
        """_get_unique_folder_name returns (4) when (2) and (3) are both taken."""
        root, fs = _make_rooted_fs(tmp_path, monkeypatch)
        lista = root / "Lista os\xf3b"
        (lista / "A Kowalski").mkdir()
        (lista / "A Kowalski (2)").mkdir()
        (lista / "A Kowalski (3)").mkdir()
        result = fs._get_unique_folder_name("A Kowalski")
        assert result == "A Kowalski (4)"
