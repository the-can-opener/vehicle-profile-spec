def export(document):
    lines = []
    for section in ("properties", "queries", "actions"):
        lines.append(section)
        for name in sorted(document.get(section, {})):
            lines.append(f"  {name}")
    return "\n".join(lines) + "\n"
