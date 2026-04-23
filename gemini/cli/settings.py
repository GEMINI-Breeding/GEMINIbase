"""
This module provides CLI commands for managing GEMINIbase configuration settings.
"""

import click
import os
from pathlib import Path

from gemini.config.settings import GEMINISettings
from gemini.manager import GEMINIManager

class GEMINISettingsContext:
    """
    Context object for the GEMINIbase settings CLI.

    This class holds the GEMINIbase manager instance and paths relevant to the settings CLI.
    """
    def __init__(self) -> None:
        self.manager = GEMINIManager()
        self.script_dir = Path(__file__).parent
        self.pipeline_dir = self.script_dir.parent / "pipeline"
        self.env_file_path = self.pipeline_dir / ".env"

@click.group()
@click.pass_context
def settings(ctx):
    """Manage GEMINIbase configuration settings."""
    ctx.obj = GEMINISettingsContext()

@settings.command("set-local")
@click.option('--enable/--disable', default=None, help="Enable or disable local mode.")
@click.pass_obj
def set_local(ctx: GEMINISettingsContext, enable: bool):
    """
    Enables or disables local mode for the GEMINIbase pipeline.

    Args:
        enable (bool): True to enable local mode, False to disable.
    """
    settings = ctx.manager.get_settings()
    if enable is None:
        click.echo(click.style("Please specify --enable or --disable.", fg="red"))
        return
    if settings.GEMINI_TYPE == "local" and enable:
        click.echo(click.style("Local mode is already enabled.", fg="yellow"))
        return
    if settings.GEMINI_TYPE == "local" and not enable:
        click.echo(click.style("Local mode is already disabled.", fg="yellow"))
        return
    ctx.manager.set_setting("GEMINI_TYPE", "local" if enable else "internal")
    click.echo(click.style(f"Local mode set to: {'enabled' if enable else 'disabled'}", fg="green"))

@settings.command("set-debug")
@click.option('--enable/--disable', default=None, help="Enable or disable debug mode.")
@click.pass_obj
def set_debug(ctx: GEMINISettingsContext, enable: bool):
    """Sets the GEMINI_DEBUG flag in the .env file."""
    if enable is None:
        click.echo(click.style("Please specify --enable or --disable.", fg="red"))
        return
    current_settings = ctx.manager.get_settings()
    if current_settings.GEMINI_DEBUG == enable:
        click.echo(click.style(f"Debug mode is already {'enabled' if enable else 'disabled'}.", fg="yellow"))
        return
    ctx.manager.set_setting("GEMINI_DEBUG", enable)
    click.echo(click.style(f"Debug mode set to: {enable}", fg="green"))


@settings.command("set-public-domain")
@click.option('--domain', default=None, help="Set the domain for the GEMINIbase pipeline.")
@click.pass_obj
def set_domain(ctx: GEMINISettingsContext, domain: str):
    """Sets the GEMINI_PUBLIC_DOMAIN in the .env file."""
    if domain is None:
        click.echo(click.style("Please specify a domain.", fg="red"))
        return
    current_settings = ctx.manager.get_settings()
    if current_settings.GEMINI_PUBLIC_DOMAIN == domain and current_settings.GEMINI_TYPE == "public":
        click.echo(click.style(f"Domain is already set to {domain}.", fg="yellow"))
        return
    ctx.manager.set_setting("GEMINI_PUBLIC_DOMAIN", domain)
    ctx.manager.set_setting("GEMINI_TYPE", "public")
    click.echo(click.style(f"Domain set to: {domain}", fg="green"))

@settings.command("set-public-ip")
@click.option('--ip', default=None, help="Set the public IP for the GEMINIbase pipeline.")
@click.pass_obj
def set_ip(ctx: GEMINISettingsContext, ip: str):
    """Sets the GEMINI_PUBLIC_IP in the .env file."""
    if ip is None:
        click.echo(click.style("Please specify an IP address.", fg="red"))
        return
    current_settings = ctx.manager.get_settings()
    if current_settings.GEMINI_PUBLIC_IP == ip and current_settings.GEMINI_TYPE == "public":
        click.echo(click.style(f"IP is already set to {ip}.", fg="yellow"))
        return
    ctx.manager.set_setting("GEMINI_PUBLIC_IP", ip)
    ctx.manager.set_setting("GEMINI_TYPE", "public")
    click.echo(click.style(f"IP set to: {ip}", fg="green"))
