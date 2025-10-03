"""Command-line interface for regex-vault."""

import json
import sys
import logging
from pathlib import Path
from typing import Optional

import click
import yaml

from regexvault import __version__
from regexvault.engine import Engine
from regexvault.registry import load_registry
from regexvault.models import RedactionStrategy


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


@click.group()
@click.version_option(version=__version__)
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging")
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """regex-vault: Detect and mask personal information."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    setup_logging(verbose)


@main.command()
@click.option(
    "--text",
    "-t",
    help="Text to search (use --file for file input)",
)
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True, path_type=Path),
    help="File to search",
)
@click.option(
    "--ns",
    "--namespace",
    "namespaces",
    multiple=True,
    help="Namespaces to search (can be used multiple times)",
)
@click.option(
    "--patterns",
    "-p",
    type=click.Path(exists=True, path_type=Path),
    multiple=True,
    help="Pattern files to load (uses defaults if not specified)",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format",
)
@click.option(
    "--include-text",
    is_flag=True,
    help="Include matched text in output (respects privacy policy)",
)
@click.pass_context
def find(
    ctx: click.Context,
    text: Optional[str],
    file: Optional[Path],
    namespaces: tuple[str, ...],
    patterns: tuple[Path, ...],
    output: str,
    include_text: bool,
) -> None:
    """Find PII in text or file."""
    # Load text
    if text is None and file is None:
        click.echo("Error: Must provide --text or --file", err=True)
        sys.exit(1)

    if file:
        text = file.read_text(encoding="utf-8")
    assert text is not None

    # Load patterns
    pattern_paths = [str(p) for p in patterns] if patterns else None
    registry = load_registry(paths=pattern_paths)

    # Create engine and find
    engine = Engine(registry)
    ns_list = list(namespaces) if namespaces else None
    result = engine.find(text, namespaces=ns_list, include_matched_text=include_text)

    # Output results
    if output == "json":
        matches_data = [
            {
                "ns_id": m.ns_id,
                "namespace": m.namespace,
                "pattern_id": m.pattern_id,
                "category": m.category.value,
                "start": m.start,
                "end": m.end,
                "matched_text": m.matched_text,
                "severity": m.severity.value,
            }
            for m in result.matches
        ]
        click.echo(
            json.dumps(
                {
                    "match_count": result.match_count,
                    "namespaces_searched": result.namespaces_searched,
                    "matches": matches_data,
                },
                indent=2,
            )
        )
    else:
        click.echo(f"Found {result.match_count} matches")
        for match in result.matches:
            text_preview = f" [{match.matched_text}]" if match.matched_text else ""
            click.echo(
                f"  {match.ns_id} ({match.category.value}) at {match.start}-{match.end}"
                f" [severity: {match.severity.value}]{text_preview}"
            )


@main.command()
@click.option(
    "--text",
    "-t",
    required=True,
    help="Text to validate",
)
@click.option(
    "--ns-id",
    required=True,
    help="Pattern namespace/id (e.g., kr/mobile)",
)
@click.option(
    "--patterns",
    "-p",
    type=click.Path(exists=True, path_type=Path),
    multiple=True,
    help="Pattern files to load",
)
@click.pass_context
def validate(
    ctx: click.Context,
    text: str,
    ns_id: str,
    patterns: tuple[Path, ...],
) -> None:
    """Validate text against a specific pattern."""
    # Load patterns
    pattern_paths = [str(p) for p in patterns] if patterns else None
    registry = load_registry(paths=pattern_paths)

    # Create engine and validate
    engine = Engine(registry)

    try:
        result = engine.validate(text, ns_id)
        if result.is_valid:
            click.echo(f"✓ Valid {ns_id}")
            sys.exit(0)
        else:
            click.echo(f"✗ Invalid {ns_id}")
            sys.exit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(2)


@main.command()
@click.option(
    "--text",
    "-t",
    help="Text to redact (use --in for file input)",
)
@click.option(
    "--in",
    "input_file",
    type=click.Path(exists=True, path_type=Path),
    help="Input file to redact",
)
@click.option(
    "--out",
    "output_file",
    type=click.Path(path_type=Path),
    help="Output file (prints to stdout if not specified)",
)
@click.option(
    "--ns",
    "--namespace",
    "namespaces",
    multiple=True,
    help="Namespaces to search",
)
@click.option(
    "--patterns",
    "-p",
    type=click.Path(exists=True, path_type=Path),
    multiple=True,
    help="Pattern files to load",
)
@click.option(
    "--strategy",
    type=click.Choice(["mask", "hash", "tokenize"]),
    default="mask",
    help="Redaction strategy",
)
@click.option(
    "--stats",
    is_flag=True,
    help="Print redaction statistics",
)
@click.pass_context
def redact(
    ctx: click.Context,
    text: Optional[str],
    input_file: Optional[Path],
    output_file: Optional[Path],
    namespaces: tuple[str, ...],
    patterns: tuple[Path, ...],
    strategy: str,
    stats: bool,
) -> None:
    """Redact PII from text or file."""
    # Load text
    if text is None and input_file is None:
        click.echo("Error: Must provide --text or --in", err=True)
        sys.exit(1)

    if input_file:
        text = input_file.read_text(encoding="utf-8")
    assert text is not None

    # Load patterns
    pattern_paths = [str(p) for p in patterns] if patterns else None
    registry = load_registry(paths=pattern_paths)

    # Create engine and redact
    engine = Engine(registry)
    ns_list = list(namespaces) if namespaces else None
    redaction_strategy = RedactionStrategy(strategy)
    result = engine.redact(text, namespaces=ns_list, strategy=redaction_strategy)

    # Output redacted text
    if output_file:
        output_file.write_text(result.redacted_text, encoding="utf-8")
        if stats:
            click.echo(f"Redacted {result.redaction_count} items to {output_file}")
    else:
        click.echo(result.redacted_text)
        if stats:
            click.echo(f"\n[Redacted {result.redaction_count} items]", err=True)


@main.command()
@click.option(
    "--port",
    "-p",
    type=int,
    default=8080,
    help="Port to listen on",
)
@click.option(
    "--host",
    "-h",
    default="0.0.0.0",
    help="Host to bind to",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Configuration file",
)
@click.option(
    "--reload",
    is_flag=True,
    help="Enable auto-reload (development only)",
)
@click.pass_context
def serve(
    ctx: click.Context,
    port: int,
    host: str,
    config: Optional[Path],
    reload: bool,
) -> None:
    """Start HTTP/gRPC server."""
    try:
        import uvicorn
        from regexvault.server import create_app
    except ImportError:
        click.echo(
            "Error: Server dependencies not installed. Install with: pip install regex-vault[server]",
            err=True,
        )
        sys.exit(1)

    # Load config
    config_data = {}
    if config:
        with open(config, "r") as f:
            config_data = yaml.safe_load(f)

    # Override with CLI options
    server_config = config_data.get("server", {})
    port = port or server_config.get("port", 8080)
    host = host or server_config.get("host", "0.0.0.0")

    click.echo(f"Starting server on {host}:{port}")

    # Create app
    app = create_app(config_data)

    # Run server
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level="info" if ctx.obj.get("verbose") else "warning",
    )


@main.command()
@click.option(
    "--patterns",
    "-p",
    type=click.Path(exists=True, path_type=Path),
    multiple=True,
    help="Pattern files to list",
)
def list_patterns(patterns: tuple[Path, ...]) -> None:
    """List available patterns."""
    pattern_paths = [str(p) for p in patterns] if patterns else None
    registry = load_registry(paths=pattern_paths)

    click.echo(f"Loaded {len(registry)} patterns from {len(registry.namespaces)} namespaces\n")

    for namespace in sorted(registry.namespaces.keys()):
        click.echo(f"Namespace: {namespace}")
        for pattern in registry.get_namespace_patterns(namespace):
            click.echo(
                f"  {pattern.id:<20} {pattern.category.value:<15} {pattern.description}"
            )
        click.echo()


if __name__ == "__main__":
    main()
