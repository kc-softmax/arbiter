import typer
from arbiter.runner import ArbiterRunner

main = typer.Typer()

@main.command()
def dev(
    # not optional
    module: str = typer.Argument(
        ...,
        help="The module path to the arbiter service."),
    reload: bool = typer.Option(
        True, "--reload", help="Enable auto-reload for service node code changes."),
):
    ArbiterRunner.run(module, reload=reload)

if __name__ == "__main__":
    main()
