"""JSON Schema counterparts of model validators (cross-reference rules remain semantic)."""


def exclusive(*forms):
    return {
        "oneOf": [
            {
                "required": list(required),
                "not": {
                    "anyOf": [
                        {"required": [key]} for other in forms if other != required for key in other
                    ]
                },
            }
            for required in forms
        ]
    }


def augment(name, schema):
    rules = []
    if name in ("Body", "DirectWrite", "Action"):
        rules += [
            {
                "oneOf": [
                    {
                        "required": ["request"],
                        "not": {"anyOf": [{"required": ["steps"]}, {"required": ["repeat"]}]},
                    },
                    {"required": ["steps"], "not": {"required": ["request"]}},
                    {
                        "required": ["repeat"],
                        "not": {"anyOf": [{"required": ["request"]}, {"required": ["steps"]}]},
                    },
                ]
            },
            {"if": {"required": ["expect"]}, "then": {"required": ["request"]}},
            {"not": {"required": ["duration", "repeat"]}},
            {"not": {"required": ["release", "repeat"]}},
        ]
    elif name == "Property":
        rules += [
            {"anyOf": [{"required": [key]} for key in ("read", "write", "value")]},
            {"not": {"required": ["read", "value"]}},
        ]
    elif name == "Read":
        rules += [{"anyOf": [{"required": ["signal"]}, {"required": ["query"]}]}]
    elif name == "Decoder":
        rules += [
            exclusive(("byte", "bytes"), ("start_bit", "bits", "bit_order")),
            {
                "if": {"required": ["enum"]},
                "then": {"not": {"anyOf": [{"required": ["scale"]}, {"required": ["offset"]}]}},
            },
            {
                "if": {"required": ["bits"]},
                "then": {"properties": {"type": {"enum": ["int", "uint"]}}},
            },
        ]
    elif name in ("DbcSignal", "SourceRef"):
        rules += [{"not": {"required": ["enum", "decode_as"]}}]
    elif name == "NamedQuery":
        rules += [exclusive(("decode", "datatype"), ("outputs",))]
        schema["properties"]["outputs"]["anyOf"][0]["additionalProperties"] = {
            "allOf": [{"$ref": "#/$defs/Decoder"}, {"required": ["datatype"]}]
        }
    elif name == "Channel":
        rules += [
            {"not": {"required": ["bitrate", "configuration"]}},
            {
                "if": {"properties": {"protocol": {"const": "can"}}},
                "then": {"not": {"anyOf": [{"required": ["data_bitrate"]}, {"required": ["fd"]}]}},
            },
        ]
    elif name == "FixtureCase":
        rules += [
            exclusive(("path",), ("name",)),
            {
                "if": {"properties": {"kind": {"enum": ["signal", "write"]}}},
                "then": {"required": ["path"]},
            },
            {"if": {"properties": {"kind": {"const": "action"}}}, "then": {"required": ["name"]}},
            {"if": {"properties": {"kind": {"const": "write"}}}, "then": {"required": ["target"]}},
        ]
    elif name == "Endpoint":
        rules += [
            {
                "if": {"properties": {"rx": {"minItems": 1}}, "required": ["rx"]},
                "then": {"required": ["timeout_ms"]},
            },
            {
                "if": {"required": ["addressing"]},
                "then": {"properties": {"protocol": {"const": "isotp"}}},
            },
        ]
    if rules:
        schema.setdefault("allOf", []).extend(rules)
    # Optional fields may be absent; explicit null is not an alternative binding.
    if name in ("Property", "Read", "Body", "DirectWrite", "Action", "NamedQuery"):
        for key, value in schema.get("properties", {}).items():
            if "anyOf" in value and key != "value":
                value["anyOf"] = [item for item in value["anyOf"] if item != {"type": "null"}]
    if name == "Property":
        schema["properties"]["value"]["not"] = {"type": "null"}
    return schema
