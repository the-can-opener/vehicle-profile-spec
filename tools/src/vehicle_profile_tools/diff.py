from .merge import SECTIONS
from .resolve import resolve


def diff(old, new):
    a, b = resolve([old]), resolve([new])
    changes = {}
    for section in SECTIONS:
        left, right = a.get(section, {}), b.get(section, {})
        added = sorted(right.keys() - left.keys())
        removed = sorted(left.keys() - right.keys())
        changed = sorted(k for k in left.keys() & right.keys() if left[k] != right[k])
        if added or removed or changed:
            changes[section] = {"added": added, "removed": removed, "changed": changed}
    return changes
