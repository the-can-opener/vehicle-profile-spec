import json


def export(document):
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
