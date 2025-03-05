import io
import os
import re
import tempfile
import zipfile
from pathlib import Path

import pytest
import requests

from app.frontend_management import (
    FrontEndProvider,
    download_release_asset_zip,
    FrontendManager,
    DEFAULT_VERSION_STRING,
)

class DummyResponse:
    """Dummy response to simulate requests responses."""
    def __init__(self, json_data, content=None, links=None):
        self._json_data = json_data
        self.content = content
        self.links = links or {}

    def json(self):
        return self._json_data

    def raise_for_status(self):
        pass

def test_parse_version_string_valid():
    """Test that a valid version string is parsed into owner, repo, version."""
    valid_str = "owner/repo@v1.2.3"
    owner, repo, version = FrontendManager.parse_version_string(valid_str)
    assert owner == "owner"
    assert repo == "repo"
    assert version == "v1.2.3"

    valid_str2 = "owner/repo@latest"
    owner, repo, version = FrontendManager.parse_version_string(valid_str2)
    assert version == "latest"

def test_parse_version_string_invalid():
    """Test that an invalid version string raises an error."""
    with pytest.raises(Exception):
        FrontendManager.parse_version_string("invalid_string")

def test_frontend_provider_properties():
    """Test that FrontEndProvider returns correct folder and release URL."""
    provider = FrontEndProvider("testowner", "testrepo")
    assert provider.folder_name == "testowner_testrepo"
    expected_url = "https://api.github.com/repos/testowner/testrepo/releases"
    assert provider.release_url == expected_url

def test_get_latest_release(monkeypatch):
    """Test get_release with 'latest' by monkeypatching requests.get for /latest endpoint."""
    dummy_latest = {
        'id': 100,
        'tag_name': 'v2.0.0',
        'name': 'Release 2.0.0',
        'prerelease': False,
        'created_at': '',
        'published_at': '',
        'body': '',
        'assets': []
    }

    def dummy_get(url, timeout):
        if url.endswith("/latest"):
            return DummyResponse(dummy_latest)
        else:
            return DummyResponse([])

    monkeypatch.setattr(requests, "get", dummy_get)
    provider = FrontEndProvider("owner", "repo")
    latest = provider.get_release("latest")
    assert latest['tag_name'] == 'v2.0.0'

def test_get_specific_release(monkeypatch):
    """Test get_release with a specific version from the list of releases."""
    dummy_releases = [
        {
            'id': 1,
            'tag_name': 'v1.2.3',
            'name': 'R1',
            'prerelease': False,
            'created_at': '',
            'published_at': '',
            'body': '',
            'assets': []
        },
        {
            'id': 2,
            'tag_name': 'v2.0.0',
            'name': 'R2',
            'prerelease': False,
            'created_at': '',
            'published_at': '',
            'body': '',
            'assets': []
        },
    ]

    def dummy_get(url, timeout):
        # For simplicity, always return the dummy_releases list.
        return DummyResponse(dummy_releases)

    monkeypatch.setattr(requests, "get", dummy_get)
    provider = FrontEndProvider("owner", "repo")
    release = provider.get_release("1.2.3")
    assert release['tag_name'] == 'v1.2.3'

def test_download_release_asset_zip(monkeypatch, tmp_path):
    """Test downloading and extracting a zip file asset from a release."""
    # Create a dummy zip archive in memory.
    dummy_zip_data = io.BytesIO()
    with zipfile.ZipFile(dummy_zip_data, "w") as zf:
        zf.writestr("test.txt", "hello")
    dummy_zip_data.seek(0)

    class DummyAssetResponse:
        def __init__(self, content):
            self.content = content

        def raise_for_status(self):
            pass

    def dummy_get(url, headers, allow_redirects, timeout):
        return DummyAssetResponse(dummy_zip_data.getvalue())

    monkeypatch.setattr(requests, "get", dummy_get)

    release = {'assets': [{'name': 'dist.zip', 'url': 'http://dummy'}]}
    dest = tmp_path / "extracted"
    dest.mkdir()
    download_release_asset_zip(release, str(dest))
    extracted_file = dest / "test.txt"
    assert extracted_file.exists()
    with extracted_file.open() as f:
        assert f.read() == "hello"

def test_init_frontend_default():
    """Test that init_frontend_unsafe returns default frontend path when given DEFAULT_VERSION_STRING."""
    result = FrontendManager.init_frontend_unsafe(DEFAULT_VERSION_STRING)
    assert result == FrontendManager.DEFAULT_FRONTEND_PATH

def test_init_frontend_existing(monkeypatch, tmp_path):
    """Test that init_frontend_unsafe returns the already existing folder without downloading."""
    fake_root = tmp_path / "web_custom_versions"
    fake_root.mkdir()
    expected_path = fake_root / "testowner_testrepo" / "1.0.0"
    expected_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(FrontendManager, "CUSTOM_FRONTENDS_ROOT", str(fake_root))
    version_string = "testowner/testrepo@v1.0.0"
    result = FrontendManager.init_frontend_unsafe(version_string)
    assert result == str(expected_path)

def test_init_frontend_download(monkeypatch, tmp_path):
    """Test that init_frontend_unsafe downloads and extracts the frontend when needed."""
    fake_root = tmp_path / "web_custom_versions"
    fake_root.mkdir()
    monkeypatch.setattr(FrontendManager, "CUSTOM_FRONTENDS_ROOT", str(fake_root))

    # Create a dummy release with tag 'v1.0.0' and an asset zip file.
    dummy_release = {
        'id': 1,
        'tag_name': 'v1.0.0',
        'name': 'dummy',
        'prerelease': False,
        'created_at': '',
        'published_at': '',
        'body': '',
        'assets': [{'name': 'dist.zip', 'url': 'http://dummyzip'}]
    }

    def dummy_get_release(self, version):
        return dummy_release

    monkeypatch.setattr(FrontEndProvider, "get_release", dummy_get_release)

    dummy_zip_data = io.BytesIO()
    with zipfile.ZipFile(dummy_zip_data, "w") as zf:
        zf.writestr("front.txt", "frontend content")
    dummy_zip_data.seek(0)

    class DummyAssetResponse:
        def __init__(self, content):
            self.content = content

        def raise_for_status(self):
            pass

    def dummy_get(url, headers, allow_redirects, timeout):
        return DummyAssetResponse(dummy_zip_data.getvalue())

    monkeypatch.setattr(requests, "get", dummy_get)

    version_string = "testowner/testrepo@1.0.0"
    result = FrontendManager.init_frontend_unsafe(version_string)
    expected_path = fake_root / "testowner_testrepo" / "1.0.0"
    assert result == str(expected_path)
    extracted = expected_path / "front.txt"
    assert extracted.exists()
    with extracted.open() as f:
        assert f.read() == "frontend content"

def test_init_frontend_fallback(monkeypatch):
    """Test that init_frontend falls back to the default frontend path when an error occurs."""
    def dummy_init_frontend_unsafe(version_string, provider=None):
        raise Exception("Simulated failure")
    monkeypatch.setattr(FrontendManager, "init_frontend_unsafe", dummy_init_frontend_unsafe)
    result = FrontendManager.init_frontend("any_version")
    assert result == FrontendManager.DEFAULT_FRONTEND_PATH
def test_all_releases_pagination(monkeypatch):
    """Test that all_releases follows GitHub pagination links and aggregates releases."""
    dummy_page1 = [{
        'id': 1,
        'tag_name': 'v1.0.0',
        'name': 'First Release',
        'prerelease': False,
        'created_at': '',
        'published_at': '',
        'body': '',
        'assets': []
    }]
    dummy_page2 = [{
        'id': 2,
        'tag_name': 'v2.0.0',
        'name': 'Second Release',
        'prerelease': False,
        'created_at': '',
        'published_at': '',
        'body': '',
        'assets': []
    }]
    call_count = []
    def dummy_get(url, timeout):
        call_count.append(url)
        if url == "https://api.github.com/repos/owner/repo/releases":
            return DummyResponse(dummy_page1, links={'next': {'url': 'http://dummy_url_page2'}})
        elif url == "http://dummy_url_page2":
            return DummyResponse(dummy_page2, links={})
        return DummyResponse([])
    monkeypatch.setattr(requests, "get", dummy_get)
    provider = FrontEndProvider("owner", "repo")
    releases = provider.all_releases
    assert len(releases) == 2
    # Assert that the two pages were requested in order.
    assert call_count == ["https://api.github.com/repos/owner/repo/releases", "http://dummy_url_page2"]

def test_cached_latest_release(monkeypatch):
    """Test that the latest_release property is cached and only requests once."""
    call_count = [0]
    dummy_latest = {
        'id': 100,
        'tag_name': 'v3.0.0',
        'name': 'Latest Release',
        'prerelease': False,
        'created_at': '',
        'published_at': '',
        'body': '',
        'assets': []
    }
    def dummy_get(url, timeout):
        call_count[0] += 1
        return DummyResponse(dummy_latest)
    monkeypatch.setattr(requests, "get", dummy_get)
    provider = FrontEndProvider("owner", "repo")
    # Call latest_release twice: the underlying get method should only be called once.
    latest_first = provider.latest_release
    latest_second = provider.latest_release
    assert call_count[0] == 1
    assert latest_first['tag_name'] == 'v3.0.0'
    assert latest_second['tag_name'] == 'v3.0.0'

def test_get_release_not_found(monkeypatch):
    """Test that get_release raises a ValueError when the version is not found."""
    dummy_releases = [{
        'id': 1,
        'tag_name': 'v1.0.0',
        'name': 'Release1',
        'prerelease': False,
        'created_at': '',
        'published_at': '',
        'body': '',
        'assets': []
    }]
    def dummy_get(url, timeout):
        return DummyResponse(dummy_releases)
    monkeypatch.setattr(requests, "get", dummy_get)
    provider = FrontEndProvider("owner", "repo")
    with pytest.raises(ValueError, match="Version 2.0.0 not found in releases"):
        provider.get_release("2.0.0")

def test_parse_version_string_edge():
    """Test that a version string with dashes and underscores is correctly parsed."""
    version_str = "owner-name/repo_name@v10.20.30"
    owner, repo, version = FrontendManager.parse_version_string(version_str)
    assert owner == "owner-name"
    assert repo == "repo_name"
    assert version == "v10.20.30"

def test_init_frontend_cleanup_failure(monkeypatch, tmp_path):
    """Test that init_frontend_unsafe cleans up the directory if zip extraction fails."""
    fake_root = tmp_path / "web_custom_versions"
    fake_root.mkdir()
    monkeypatch.setattr(FrontendManager, "CUSTOM_FRONTENDS_ROOT", str(fake_root))
    version_string = "testowner/testrepo@v1.0.0"
    dummy_release = {
        'id': 1,
        'tag_name': 'v1.0.0',
        'name': 'dummy',
        'prerelease': False,
        'created_at': '',
        'published_at': '',
        'body': '',
        'assets': [{'name': 'dist.zip', 'url': 'http://dummyzip'}]
    }
    def dummy_get_release(self, version):
        return dummy_release
    monkeypatch.setattr(FrontEndProvider, "get_release", dummy_get_release)
    def dummy_download_failure(release, destination_path):
        raise Exception("Extraction failure")
    monkeypatch.setattr("app.frontend_management.download_release_asset_zip", dummy_download_failure)
    with pytest.raises(Exception, match="Extraction failure"):
        FrontendManager.init_frontend_unsafe(version_string)
    expected_path = fake_root / "testowner_testrepo" / "1.0.0"
    # The folder should be removed if it's empty (after a failed download)
    assert not expected_path.exists()

def test_download_release_asset_zip_asset_not_found():
    """Test that an error is raised when 'dist.zip' asset is not found in the release."""
    # Prepare a release dict without the correct asset name.
    release = {'assets': [{'name': 'not_dist.zip', 'url': 'http://dummy'}]}
    import pytest
    from app.frontend_management import download_release_asset_zip
    with pytest.raises(ValueError, match="dist.zip not found in the release assets"):
        download_release_asset_zip(release, "dummy_destination")

def test_download_release_asset_zip_http_error(monkeypatch, tmp_path):
    """Test that download_release_asset_zip propagates HTTPError when requests.get fails."""
    import requests
    from app.frontend_management import download_release_asset_zip
    # Define a dummy requests.get that always raises HTTPError.
    def dummy_get(url, headers, allow_redirects, timeout):
        raise requests.HTTPError("HTTP Error triggered")
    monkeypatch.setattr(requests, "get", dummy_get)
    release = {'assets': [{'name': 'dist.zip', 'url': 'http://dummy'}]}
    dest = tmp_path / "extracted"
    dest.mkdir()
    import pytest
    with pytest.raises(requests.HTTPError, match="HTTP Error triggered"):
        download_release_asset_zip(release, str(dest))

def test_parse_version_string_without_v():
    """Test that a version string without the 'v' prefix in version is correctly parsed."""
    from app.frontend_management import FrontendManager
    version_str = "owner/repo@1.2.3"
    owner, repo, version = FrontendManager.parse_version_string(version_str)
    assert owner == "owner"
    assert repo == "repo"
    assert version == "1.2.3"
def test_download_release_asset_zip_invalid_zip(monkeypatch, tmp_path):
    """Test that download_release_asset_zip raises a BadZipFile error when zip extraction fails due to invalid zip data."""
    from zipfile import BadZipFile

    # Dummy requests.get simulating invalid zip content.
    def dummy_get(url, headers, allow_redirects, timeout):
        class DummyAssetResponse:
            def __init__(self):
                self.content = b"this is not a valid zip file"
            def raise_for_status(self):
                pass
        return DummyAssetResponse()

    monkeypatch.setattr(requests, "get", dummy_get)

    release = {'assets': [{'name': 'dist.zip', 'url': 'http://dummy'}]}
    dest = tmp_path / "extracted_invalid"
    dest.mkdir()

    import pytest
    with pytest.raises(BadZipFile):
        download_release_asset_zip(release, str(dest))

def test_init_frontend_custom_provider(monkeypatch, tmp_path):
    """Test that init_frontend_unsafe uses the provided custom provider and downloads the frontend correctly."""
    fake_root = tmp_path / "web_custom_versions"
    fake_root.mkdir()

    dummy_release = {
        'id': 100,
        'tag_name': 'v1.1.1',
        'name': 'Custom Release',
        'prerelease': False,
        'created_at': '',
        'published_at': '',
        'body': '',
        'assets': [{'name': 'dist.zip', 'url': 'http://dummyzip'}]
    }

    # Create a dummy provider that simply returns our dummy_release.
    class DummyProvider(FrontEndProvider):
        def get_release(self, version: str):
            return dummy_release

    # Override the CUSTOM_FRONTENDS_ROOT of FrontendManager.
    monkeypatch.setattr(FrontendManager, "CUSTOM_FRONTENDS_ROOT", str(fake_root))

    # Prepare a dummy zip archive in memory.
    import io
    dummy_zip_data = io.BytesIO()
    with zipfile.ZipFile(dummy_zip_data, "w") as zf:
        zf.writestr("custom.txt", "custom content")
    dummy_zip_data.seek(0)

    class DummyAssetResponse:
        def __init__(self, content):
            self.content = content
        def raise_for_status(self):
            pass

    def dummy_get(url, headers, allow_redirects, timeout):
        return DummyAssetResponse(dummy_zip_data.getvalue())

    monkeypatch.setattr(requests, "get", dummy_get)

    version_string = "customowner/customrepo@v1.1.1"
    result = FrontendManager.init_frontend_unsafe(version_string, provider=DummyProvider("customowner", "customrepo"))

    expected_path = fake_root / "customowner_customrepo" / "1.1.1"
    assert result == str(expected_path)

    extracted = expected_path / "custom.txt"
    assert extracted.exists()
    with extracted.open() as f:
        assert f.read() == "custom content"