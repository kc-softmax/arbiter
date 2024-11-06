import sys
import typer
from arbiter.runner import ArbiterRunner

main = typer.Typer()

@main.command()
def dev(
    # not optional
    module: str = typer.Argument(
        default="arbiter:ArbiterNode",
        help="The module path to the arbiter service."),
    reload: bool = typer.Option(
        True, "--reload", help="Enable auto-reload for service node code changes."),
    app_dir: str = typer.Option(
        "", "--app-dir", help="Arbiter need to know app path"),
):
    if app_dir is not None:
        sys.path.insert(0, app_dir)

    ArbiterRunner.run(module, reload=reload)

@main.command()
def repl():
    pass

if __name__ == "__main__":
    main()
