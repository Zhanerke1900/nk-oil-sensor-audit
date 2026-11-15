"""Download the three original files at fixed Hugging Face revisions.

Run once with ``python download.py``. Existing files are reused only when their
SHA-256 matches. No login or API token is needed for these public files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
FILES = [
    {
        "file": "v2_train.csv",
        "repo": "Arailym-tleubayeva/NK-Oil-Well-Sensor-Monitoring-v2",
        "revision": "4004bb78ca8811a87c2892a89e457c59d22ace2b",
        "source_file": "train.csv",
        "sha256": "8bf92fd97ac9b0d7ec2e7aa61be90f335c7f3b6ab2a84634fb8758b057efe26a",
    },
    {
        "file": "v2_test.csv",
        "repo": "Arailym-tleubayeva/NK-Oil-Well-Sensor-Monitoring-v2",
        "revision": "4004bb78ca8811a87c2892a89e457c59d22ace2b",
        "source_file": "test.csv",
        "sha256": "8029113613ea2965cb94fc7bea50eee6f4c327b673ecc856d88d25dfb652c7d6",
    },
    {
        "file": "v1_full.csv",
        "repo": "Arailym-tleubayeva/NK-Oil-Well-Sensor-Monitoring",
        "revision": "84e5103cef58c85dc924e4b47aaed8ef2c5cb3dd",
        "source_file": "wells_dataset.csv",
        "sha256": "7a31fca2a4709a3bf9513bdc5fe7ed8f66a543a8d4e0c6855282ee8dde5f70b2",
    },
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_one(item: dict, directory: Path, force: bool = False) -> dict:
    destination = directory / item["file"]
    url = (f"https://huggingface.co/datasets/{item['repo']}/resolve/"
           f"{item['revision']}/{item['source_file']}")
    if destination.exists() and not force:
        if sha256_file(destination) == item["sha256"]:
            print(f"Verified: {destination.name}")
            return {**item, "url": url, "size_bytes": destination.stat().st_size}
        raise ValueError(f"Checksum mismatch for {destination}. "
                         "Move your changed file aside or use --force.")

    temporary = destination.with_suffix(".csv.part")
    request = urllib.request.Request(url, headers={"User-Agent": "NK-Well-Audit-Student-Project/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as stream:
            while block := response.read(1024 * 1024):
                stream.write(block)
        if sha256_file(temporary) != item["sha256"]:
            raise ValueError(f"Downloaded bytes failed checksum: {destination.name}")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Downloaded: {destination.name}")
    return {**item, "url": url, "size_bytes": destination.stat().st_size}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Replace local input files with the pinned originals")
    args = parser.parse_args()
    directory = ROOT / "data" / "raw"
    directory.mkdir(parents=True, exist_ok=True)
    try:
        manifest = [download_one(item, directory, args.force) for item in FILES]
        (directory / "download_manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
    except (OSError, ValueError, urllib.error.URLError) as error:
        parser.exit(1, f"Download stopped: {error}\nCheck your connection and run again.\n")


if __name__ == "__main__":
    main()
