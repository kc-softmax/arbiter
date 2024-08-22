import typer
from arbiter.runner.commands.build import app as build_app
from arbiter.runner.runner import ArbiterRunner
from arbiter.app import ArbiterApp

app = typer.Typer()
app.add_typer(
    build_app,
    name="build",
    rich_help_panel="build environment",
    help="Configure build environment for deploying service")


@app.command()
def run(
    name: str = typer.Option(
        "Danimoth", "--name", help="Name of the arbiter to run."),
    reload: bool = typer.Option(
        False, "--reload", help="Enable auto-reload for code changes."),
    log_level: str = typer.Option(
        "info", "--log-level", help="Log level for arbiter.")
):
    app = ArbiterApp()
    ArbiterRunner.run(
        app=app,
        name=name,
        reload=reload,
        log_level=log_level
    )
  

if __name__ == "__main__":
    app()
