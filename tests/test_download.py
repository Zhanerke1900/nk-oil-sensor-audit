import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from download import sha256_file, download_one


class DownloadChecks(unittest.TestCase):
    def test_sha256_matches_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "file.csv"
            path.write_bytes(b"well_id,value\nNK-7,3\n")
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(sha256_file(path), expected)

    def test_verified_file_is_reused_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            path = directory / "measurements.csv"
            path.write_bytes(b"small example")
            item = {"file": path.name, "repo": "unused/repo", "revision": "abc",
                    "source_file": "measurements.csv", "sha256": sha256_file(path)}
            with patch("urllib.request.urlopen") as urlopen:
                result = download_one(item, directory)
            urlopen.assert_not_called()
            self.assertEqual(result["size_bytes"], len(b"small example"))

    def test_download_creates_missing_destination_directory(self):
        from io import BytesIO
        with tempfile.TemporaryDirectory() as parent:
            directory = Path(parent) / "new" / "raw"
            payload = b"timestamp,value\n2026-01-01,3\n"
            item = {"file": "measurements.csv", "repo": "unused/repo",
                    "revision": "abc", "source_file": "measurements.csv",
                    "sha256": hashlib.sha256(payload).hexdigest()}
            with patch("urllib.request.urlopen", return_value=BytesIO(payload)):
                download_one(item, directory)
            self.assertEqual((directory / "measurements.csv").read_bytes(), payload)
            self.assertFalse((directory / "measurements.csv.part").exists())


if __name__ == "__main__":
    unittest.main()
