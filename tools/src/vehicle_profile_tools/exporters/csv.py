import csv
import io


def export(document):
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["kind", "name", "signal", "query", "write"])
    for path, prop in sorted(document.get("properties", {}).items()):
        read = prop.get("read", {})
        writer.writerow(["property", path, "signal" in read, "query" in read, "write" in prop])
    for section in ("queries", "actions"):
        for name in sorted(document.get(section, {})):
            writer.writerow([section, name, "", "", ""])
    return out.getvalue()
