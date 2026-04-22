
"""
This module provides the command-line interface (CLI) for managing the GEMINI pipeline.

It includes commands for building, starting, stopping, cleaning, resetting, setting up, and updating the GEMINI pipeline.
"""

import click
import os, subprocess
from pathlib import Path

from gemini.config.settings import GEMINISettings
from gemini.manager import GEMINIManager, DockerUnavailableError
from gemini.cli.settings import settings as settings_group # Import the settings group


def _require(ok: bool, failure_message: str) -> None:
    """Abort the current click command cleanly if `ok` is False."""
    if not ok:
        raise click.ClickException(failure_message)

class GEMINICLIContext:
    """
    Context object for the GEMINI CLI.

    This class holds the GEMINI manager instance and paths relevant to the CLI.
    """
    def __init__(self) -> None:
        self.manager = GEMINIManager()
        self.script_dir = Path(__file__).parent
        self.pipeline_dir = self.script_dir.parent / "pipeline"


class _DockerAwareGroup(click.Group):
    """Click group that renders DockerUnavailableError as a clean CLI error."""

    def invoke(self, ctx: click.Context):
        try:
            return super().invoke(ctx)
        except DockerUnavailableError as e:
            raise click.ClickException(str(e)) from e


@click.group(cls=_DockerAwareGroup)
@click.pass_context
def cli(ctx):
    """
    GEMINI CLI for pipeline management.
    """
    ctx.obj = GEMINICLIContext()

@cli.command()
@click.pass_obj
def build(ctx: GEMINICLIContext):
    """
    Builds the GEMINI pipeline.
    """
    click.echo(click.style("Building GEMINI pipeline", fg="blue"))
    _require(ctx.manager.build(), "Build failed. See Docker output above.")
    click.echo(click.style("GEMINI pipeline built", fg="blue"))

@cli.command()
@click.pass_obj
def start(ctx: GEMINICLIContext):
    """
    Starts the GEMINI pipeline.
    """
    click.echo(click.style("Starting GEMINI pipeline", fg="blue"))
    _require(ctx.manager.start(), "Start failed. See Docker output above.")
    click.echo(click.style("GEMINI pipeline started", fg="blue"))

@cli.command()
@click.pass_obj
def stop(ctx: GEMINICLIContext):
    """
    Stops the GEMINI pipeline.
    """
    click.echo(click.style("Stopping GEMINI pipeline", fg="blue"))
    _require(ctx.manager.stop(), "Stop failed. See Docker output above.")
    click.echo(click.style("GEMINI pipeline stopped", fg="blue"))

@cli.command()
@click.pass_obj
def clean(ctx: GEMINICLIContext):
    """
    Cleans the GEMINI pipeline.
    """
    click.echo(click.style("Cleaning GEMINI pipeline", fg="blue"))
    _require(ctx.manager.clean(), "Clean failed. See Docker output above.")
    click.echo(click.style("GEMINI pipeline cleaned", fg="blue"))

@cli.command()
@click.pass_obj
def reset(ctx: GEMINICLIContext):
    """
    Resets the GEMINI pipeline.
    """
    click.echo(click.style("Resetting GEMINI pipeline", fg="blue"))
    ctx.manager.save_settings()
    _require(ctx.manager.rebuild(), "Reset failed. See Docker output above.")
    click.echo(click.style("GEMINI pipeline reset", fg="blue"))

@cli.command()
@click.option('--default', is_flag=True, help="Use default settings")
@click.pass_obj
def setup(ctx: GEMINICLIContext, default: bool = False):
    """
    Sets up the GEMINI pipeline.

    Args:
        default (bool): Use default settings.
    """
    click.echo(click.style("Setting up GEMINI pipeline", fg="blue"))
    ctx.manager.save_settings()
    _require(ctx.manager.rebuild(), "Setup failed. See Docker output above.")
    click.echo(click.style("GEMINI pipeline setup complete", fg="blue"))


@cli.command()
@click.pass_obj
def update(ctx: GEMINICLIContext):
    """
    Updates the GEMINI pipeline.
    """
    click.echo(click.style("Updating GEMINI pipeline", fg="blue"))
    _require(ctx.manager.update(), "Update script failed.")
    ctx.manager.save_settings()
    _require(ctx.manager.rebuild(), "Update failed during rebuild. See Docker output above.")
    click.echo(click.style("GEMINI pipeline updated", fg="blue"))

# Add the settings command group to the main CLI
cli.add_command(settings_group)
