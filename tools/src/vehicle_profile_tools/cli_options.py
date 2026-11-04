import rich_click as click


def package_options(function):
    for option in reversed(
        [
            click.option("--package", "package_path", required=True, type=click.Path(exists=True)),
            click.option("-l", "--overlay", multiple=True, type=click.Path(exists=True)),
            click.option("--vehicle", default=""),
            click.option("--strict", is_flag=True),
            click.option("--strict-exceptions", type=click.Path(exists=True, dir_okay=False)),
            click.option("--integrity-required", is_flag=True),
            click.option("--log-file", type=click.Path()),
            click.option("-o", "--output", type=click.Path()),
        ]
    ):
        function = option(function)
    return function


def vehicle_options(text):
    if not text:
        return {}
    try:
        pairs = [part.split("=", 1) for part in text.split(",")]
        values = dict(pairs)
        allowed = {"make", "model", "year", "trim", "engine", "market"}
        if (
            set(values) - allowed
            or len(values) != len(pairs)
            or any(not v for v in values.values())
        ):
            raise ValueError("unknown, duplicate or empty vehicle selector")
        if "year" in values:
            values["year"] = int(values["year"])
        return values
    except ValueError as exc:
        raise click.BadParameter("expected make=Nissan,model=Versa,year=2011") from exc
