"""
Download the real system-identification datasets used by notebook 04.

These are third-party research datasets, not redistributed in this repo -- run this
script once to fetch them into data/real/.

    python scripts/download_data.py

Sources & attribution
----------------------
* Hair dryer -- DaISy (Database for the Identification of Systems), KU Leuven ESAT/SISTA.
    B. De Moor (ed.), DaISy, dataset 96-006.
    https://homes.esat.kuleuven.be/~smc/daisy/
* Cascaded tanks -- Nonlinear System Identification Benchmark, 4TU.ResearchData.
    M. Schoukens & J.P. Noel, "Cascaded tanks benchmark ...", doi:10.4121/12960104.
    https://www.nonlinearbenchmark.org/
"""

import gzip
import io
import socket
import urllib.request
import zipfile
from pathlib import Path

socket.setdefaulttimeout(90)
OUT = Path(__file__).resolve().parents[1] / "data" / "real"

DRYER = "https://ftp.esat.kuleuven.be/pub/SISTA/data/mechanical/"
TANKS_ZIP = ("https://data.4tu.nl/file/"
             "d4810b78-6cdd-48fe-8950-9bd601e5f47f/"
             "3b697e42-01a4-4979-a370-813a456c36f5")


def _get(url: str) -> bytes:
    print("  downloading", url)
    return urllib.request.urlopen(url).read()


def download_dryer() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("[hair dryer] DaISy 96-006")
    (OUT / "dryer_description.txt").write_bytes(_get(DRYER + "dryer.txt"))
    data = gzip.decompress(_get(DRYER + "dryer.dat.gz"))
    (OUT / "dryer.dat").write_bytes(data)
    print("  -> data/real/dryer.dat")


def download_cascaded_tanks() -> None:
    dest = OUT / "cascaded_tanks"
    dest.mkdir(parents=True, exist_ok=True)
    print("[cascaded tanks] 4TU doi:10.4121/12960104")
    z = zipfile.ZipFile(io.BytesIO(_get(TANKS_ZIP)))
    # Extract only the small CSV data file (skip the bundled photos/video).
    for name in z.namelist():
        if name.lower().endswith("databenchmark.csv"):
            with z.open(name) as src:
                (dest / "dataBenchmark.csv").write_bytes(src.read())
            print("  -> data/real/cascaded_tanks/dataBenchmark.csv")
            return
    raise RuntimeError("dataBenchmark.csv not found in the archive")


def main() -> None:
    download_dryer()
    download_cascaded_tanks()
    print("done.")


if __name__ == "__main__":
    main()
