import json
from pathlib import Path

import rich_click as click

from . import __version__
from .catalog import load_catalog
from .cli_options import package_options, vehicle_options
from .errors import ProfileError
from .exporters import EXPORTERS
from .resolve import resolve as resolve_packages
from .strict import StrictOption
from .telemetry import (
    build_dictionary,
    infer_dictionary,
    inspect_telemetry,
    read_observations_jsonl,
    read_telemetry,
    write_observations_jsonl,
    write_telemetry,
)
from .vbo import export_telemetry_to_vbo


@click.group()
@click.version_option(__version__)
def cli():
    """Validate, compose and migrate Vehicle Binding format 2 packages."""


def emit(text, output=None):
    if output:
        Path(output).write_text(text, encoding="utf-8")
    else:
        click.echo(text, nl=False)


@cli.command("export")
@click.argument("format", type=click.Choice(list(EXPORTERS)))
@package_options
def export(
    format,
    package_path,
    overlay,
    vehicle,
    strict,
    strict_exceptions,
    integrity_required,
    log_file,
    output,
):
    policy = StrictOption.from_file(strict, strict_exceptions)
    try:
        document = resolve_packages(
            [package_path], vehicle_options(vehicle), policy, overlay, integrity_required
        )
        emit(EXPORTERS[format](document), output)
        validation_log(policy, log_file)
    except ProfileError as exc:
        if log_file:
            Path(log_file).write_text(str(exc) + "\n")
        raise


def validation_log(policy, log_file):
    lines = [
        f"DOC_UNKNOWN_FIELD excepted: {path}: {policy.exceptions[path]}"
        for path in sorted(policy.ignored)
    ]
    for line in lines:
        click.echo(line, err=True)
    if log_file:
        Path(log_file).write_text(
            "\n".join([*lines, "OK: structural validation passed; vehicle behavior not tested"])
            + "\n"
        )


@cli.command()
@click.option("--package", "package_path", type=click.Path(exists=True))
@click.option("--verify", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path())
def compose(package_path, verify, output):
    from .compose import compose as pack

    if verify:
        if package_path or output:
            raise click.UsageError("--verify cannot be combined with --package or -o")
        resolve_packages([verify])
    elif package_path and output:
        pack(package_path, output)
    else:
        raise click.UsageError("use --package PATH -o FILE.zip or --verify FILE.zip")
    click.echo("OK")


@cli.command("resolve")
@click.option("--packages", multiple=True, required=True, type=click.Path(exists=True))
@click.option("--vehicle", default="")
@click.option("--strict", is_flag=True)
@click.option("--strict-exceptions", type=click.Path(exists=True, dir_okay=False))
@click.option("--log-file", type=click.Path())
@click.option("--integrity-required", is_flag=True)
@click.option("-l", "--overlay", multiple=True, type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path())
def resolve_command(
    packages, vehicle, strict, strict_exceptions, log_file, integrity_required, overlay, output
):
    policy = StrictOption.from_file(strict, strict_exceptions)
    try:
        emit(
            EXPORTERS["json"](
                resolve_packages(
                    packages, vehicle_options(vehicle), policy, overlay, integrity_required
                )
            ),
            output,
        )
        validation_log(policy, log_file)
    except ProfileError as exc:
        if log_file:
            Path(log_file).write_text(str(exc) + "\n")
        raise


@cli.command()
@click.argument("old", type=click.Path(exists=True))
@click.argument("new", type=click.Path(exists=True))
def diff(old, new):
    from .diff import diff as compare

    emit(json.dumps(compare(old, new), indent=2, sort_keys=True) + "\n")


@cli.command()
@click.argument("legacy", type=click.Path(exists=True))
@click.option("-o", "--output", required=True, type=click.Path())
@click.option(
    "--framing",
    type=click.Choice(["raw", "isotp", "isotp-single-frame"]),
    help="Declare legacy request/response framing; never inferred from bytes.",
)
@click.option(
    "--responder",
    multiple=True,
    metavar="ENDPOINT=HEX",
    help="Select a responder for a legacy endpoint with multiple response IDs.",
)
@click.option(
    "--steering-side",
    type=click.Choice(["left", "right"]),
    help="Declare the steering side for physical left/right door mappings.",
)
def migrate(legacy, output, framing, responder, steering_side):
    from .migrate import migrate as convert

    try:
        responders = dict(item.split("=", 1) for item in responder)
        if len(responders) != len(responder):
            raise ValueError("duplicate endpoint")
    except ValueError as exc:
        raise click.BadParameter("use unique ENDPOINT=HEX responder selections") from exc
    report = convert(
        legacy, output, framing=framing, responders=responders, steering_side=steering_side
    )
    emit(json.dumps({"output": output, "unmapped": report}, indent=2) + "\n")


@cli.group()
def vss():
    """Search the pinned VSS catalog."""


@vss.command()
@click.argument("text")
@click.option("--role", type=click.Choice(["sensor", "actuator", "attribute"]))
def search(text, role):
    for path, entry in sorted(load_catalog().items()):
        if text.lower() in (path + " " + entry.get("description", "")).lower() and (
            not role or entry["type"] == role
        ):
            click.echo(json.dumps({"path": path, **entry}, sort_keys=True))


@vss.command()
@click.argument("path")
def show(path):
    catalog = load_catalog()
    if path not in catalog:
        raise click.ClickException(f"VSS_UNKNOWN_PATH: {path}")
    emit(json.dumps({"path": path, **catalog[path]}, indent=2, sort_keys=True) + "\n")


@cli.group()
def skills():
    """List and install the bundled agent skills."""


@skills.command("list")
def skills_list():
    from .skills import list_skills

    click.echo("\n".join(list_skills()))


@skills.command("install")
@click.option("--agent", default="cursor", type=click.Choice(["cursor", "claude", "codex", "all"]))
@click.option("--project", is_flag=True)
@click.option("--dir", "directory", type=click.Path())
def skills_install(agent, project, directory):
    from .skills import install

    click.echo("\n".join(install(agent, project, directory)))


@cli.group()
def telemetry():
    """Pack, unpack, inspect, and export compressed protobuf telemetry."""


@telemetry.command("pack")
@click.argument("input_jsonl", type=click.Path(exists=True, dir_okay=False))
@click.option("-o", "--output", required=True, type=click.Path(dir_okay=False))
@click.option("--vehicle-id", default="vehicle", show_default=True)
@click.option("--package", "package_path", type=click.Path(exists=True))
@click.option(
    "--host-sensors", is_flag=True, help="Include standard host GNSS/IMU VSS 6.1 signals."
)
@click.option(
    "--compression",
    type=click.Choice(["raw", "zlib", "zip"]),
    default="zlib",
    show_default=True,
)
@click.option("--batch-size", type=int, default=1000, show_default=True)
@click.option(
    "--emit-on-change",
    is_flag=True,
    help="Suppress consecutive unchanged samples while respecting max_age_ms heartbeats.",
)
@click.option(
    "--downgrade-invalid",
    is_flag=True,
    help="Encode out-of-range or off-grid samples as INVALID with no value instead of failing.",
)
def telemetry_pack(
    input_jsonl,
    output,
    vehicle_id,
    package_path,
    host_sensors,
    compression,
    batch_size,
    emit_on_change,
    downgrade_invalid,
):
    observations = read_observations_jsonl(input_jsonl)
    if package_path:
        document = resolve_packages([package_path])
        dictionary = build_dictionary(
            vehicle_id,
            document=document,
            include_host_sensors=host_sensors,
        )
    else:
        dictionary = infer_dictionary(vehicle_id, observations)
    written = write_telemetry(
        output,
        dictionary,
        observations,
        compression=compression,
        batch_size=batch_size,
        downgrade_invalid=downgrade_invalid,
        emit_on_change=emit_on_change,
    )
    emit(
        json.dumps(
            {
                "output": str(output),
                "compression": compression,
                "bytes": written,
                "signals": len(dictionary.signals),
                "observations": len(observations),
                "dictionary_fingerprint": dictionary.fingerprint.hex(),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


@telemetry.command("unpack")
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False))
@click.option("-o", "--output", type=click.Path(dir_okay=False))
def telemetry_unpack(input_path, output):
    _, observations = read_telemetry(input_path)
    if output:
        write_observations_jsonl(output, observations)
        click.echo(f"Wrote {len(observations)} observations to {output}")
    else:
        emit("".join(json.dumps(obs.to_dict(), sort_keys=True) + "\n" for obs in observations))


@telemetry.command("inspect")
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False))
def telemetry_inspect(input_path):
    emit(json.dumps(inspect_telemetry(input_path), indent=2, sort_keys=True) + "\n")


@telemetry.command("to-vbo")
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False))
@click.option("-o", "--output", required=True, type=click.Path(dir_okay=False))
@click.option("--gps-tolerance-ms", type=int, default=5, show_default=True)
@click.option("--max-age-ms", type=int, default=None)
def telemetry_to_vbo(input_path, output, gps_tolerance_ms, max_age_ms):
    report = export_telemetry_to_vbo(
        input_path,
        output,
        gps_pair_tolerance_ms=gps_tolerance_ms,
        max_age_ms=max_age_ms,
    )
    emit(json.dumps({"output": str(output), **report.to_dict()}, indent=2, sort_keys=True) + "\n")


def main():
    try:
        cli(standalone_mode=False)
    except click.ClickException as exc:
        exc.show()
        raise SystemExit(exc.exit_code) from exc
    except (ProfileError, ValueError, OSError) as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
