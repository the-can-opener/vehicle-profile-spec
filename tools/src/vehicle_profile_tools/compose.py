import zipfile

from .container import Package
from .resolve import resolve


def compose(source, output):
    resolve([source])
    pkg = Package(source)
    # Store rather than compress: deterministic output and bounded reader ratio.
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(pkg.assets):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            archive.writestr(info, pkg.read(name))
    return resolve([output])
