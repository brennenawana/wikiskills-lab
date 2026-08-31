#!/usr/bin/env python3
"""Fetch the SpreadsheetBench data and checker from their original sources.

We point at the upstream work; we do not copy it. The benchmark publishes no
license file, so neither its data nor its checker is ever stored in this
repository — this script downloads both into the git-ignored `data/` folder,
at pinned versions, and verifies the dataset checksum.

  python3 fetch_data.py            # downloads ~15 MB into data/

Sources (credits in ../../CREDITS.md and REPORT.md §9):
- Dataset: SpreadsheetBench "Verified-400" (Hugging Face: KAKA22), pinned
  revision.
- Checker: RUCKBReasoning/SpreadsheetBench evaluation code, pinned commit.

Standard library only for the download; the checker itself needs
`openpyxl` and `pandas` at the upstream's pins (see adapter/README.md).
"""

import hashlib
import os
import sys
import tarfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

DATASET_REVISION = "ab0b742b0fc95b946f212d80ac7771b5531272e4"
DATASET_URL = ("https://huggingface.co/datasets/KAKA22/SpreadsheetBench/"
               "resolve/%s/spreadsheetbench_verified_400.tar.gz"
               % DATASET_REVISION)
DATASET_SHA256 = ("10ef893dd29cb13ab97143ea787e68cdc9574a13"
                  "873ab9a54e50b31dc03fc949")

UPSTREAM_COMMIT = "49b73a94775fb489063f60ca1865e3a650079a79"
UPSTREAM_FILES = ["evaluation.py", "open_spreadsheet.py"]
UPSTREAM_BASE = ("https://raw.githubusercontent.com/RUCKBReasoning/"
                 "SpreadsheetBench/%s/evaluation/" % UPSTREAM_COMMIT)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url, dest):
    print("fetching %s" % url)
    tmp = dest + ".part"
    with urllib.request.urlopen(url, timeout=600) as resp, \
            open(tmp, "wb") as fh:
        while True:
            chunk = resp.read(1 << 16)
            if not chunk:
                break
            fh.write(chunk)
    os.replace(tmp, dest)


def main():
    os.makedirs(DATA, exist_ok=True)

    tarball = os.path.join(DATA, "spreadsheetbench_verified_400.tar.gz")
    if not (os.path.exists(tarball) and sha256(tarball) == DATASET_SHA256):
        download(DATASET_URL, tarball)
        got = sha256(tarball)
        if got != DATASET_SHA256:
            print("FATAL: dataset checksum mismatch\n expected %s\n got %s"
                  % (DATASET_SHA256, got), file=sys.stderr)
            sys.exit(1)
    extracted = os.path.join(DATA, "spreadsheetbench_verified_400")
    if not os.path.isdir(extracted):
        print("extracting...")
        with tarfile.open(tarball) as tf:
            tf.extractall(DATA, filter="data")
    print("dataset OK: %s" % extracted)

    updir = os.path.join(DATA, "upstream")
    os.makedirs(updir, exist_ok=True)
    for fn in UPSTREAM_FILES:
        dest = os.path.join(updir, fn)
        if not os.path.exists(dest):
            download(UPSTREAM_BASE + fn, dest)
    with open(os.path.join(updir, "COMMIT"), "w") as fh:
        fh.write(UPSTREAM_COMMIT + "\n")
    print("checker OK: %s (commit %s)" % (updir, UPSTREAM_COMMIT[:12]))
    print()
    print("Reminder: everything under data/ is the benchmark authors' work,")
    print("cached for local research use only. It is git-ignored here and")
    print("must never be committed or redistributed.")


if __name__ == "__main__":
    main()
