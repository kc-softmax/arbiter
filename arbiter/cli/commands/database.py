import typer
from typing import Optional
from alembic.config import Config as AlembicConfig

from arbiter.cli.utils import AsyncTyper

def _get_alembic_config():
    from arbiter.cli import CONFIG_FILE
    from arbiter.cli.utils import read_config

    db_url = read_config(CONFIG_FILE).get("database", "sqlalchemy.url", fallback=None)
    alembic_cfg = AlembicConfig(CONFIG_FILE)
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    return alembic_cfg

app = AsyncTyper()
    
@app.command()
def revision(
    message: Optional[str] = typer.Option(None, "--message", "-m", help="String message to apply to the revision"),
    autogenerate: Optional[bool] = typer.Option(False, "--auto", help="Whether or not to autogenerate the script from the database"),
    sql: Optional[bool] = typer.Option(False, "--sql", help="Whether to dump the script out as a SQL string; when specified, the script is dumped to stdout."),
    head: Optional[str] = typer.Option("head", "--head", help="Head revision to build the new revision upon as a parent"),
    splice: Optional[bool] = typer.Option(False, "--splice", help="Whether or not the new revision should be made into a new head of its own; is required when the given ``head`` is not itself a head."),
    branch_label: Optional[str] = typer.Option(None, "--branch_label", help="String label to apply to the branch"),
    version_path: Optional[str] = typer.Option(None, "--version-path", help="String symbol identifying a specific version path from the configuration"),
    rev_id: Optional[str] = typer.Option(None, "--rev-id", help="Optional revision identifier to use instead of having one generated"),
    depends_on: Optional[str] = typer.Option(None, "--depends-on", help="Optional list of 'depends on' identifiers"),
):
    """
    Create new alembic revision.
    """
    from alembic import command as alembic_command

    alembic_command.revision(config=_get_alembic_config(), 
                             message=message,
                             autogenerate=autogenerate,
                             sql=sql,
                             head=head,
                             splice=splice,
                             branch_label=branch_label,
                             version_path=version_path,
                             rev_id=rev_id,
                             depends_on=depends_on)
    typer.echo(typer.style("New database revision Created.", fg=typer.colors.GREEN, bold=True))
    

@app.command()
def upgrade(
    revision: Optional[str] = typer.Option("head", "--revision", "-r", help="Revision identifier."),
    sql: Optional[bool] = typer.Option(False, "--sql", help="Whether to use ``--sql`` mode"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Arbitrary tag that can be intercepted by custom ``env.py`` scripts.")
):
    """
    Upgrade to a later version.
    """
    from alembic import command as alembic_command

    alembic_command.upgrade(_get_alembic_config(), 
                            revision,
                            sql=sql,
                            tag=tag)

@app.command()
def downgrade(
    revision: Optional[str] = typer.Option("head", "--revision", "-r", help="Revision identifier."),
    sql: Optional[bool] = typer.Option(False, "--sql", help="Whether to use ``--sql`` mode"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Arbitrary tag that can be intercepted by custom ``env.py`` scripts.")
):
    """
    Revert to a previous version.
    """
    from alembic import command as alembic_command

    alembic_command.downgrade(_get_alembic_config(),
                              revision=revision,
                              sql=sql,
                              tag=tag)
    
@app.command()
def stamp(
    revision: Optional[str] = typer.Option("head", "--revision", "-r", help="Revision identifier."),
    sql: Optional[bool] = typer.Option(False, "--sql", help="Whether to use ``--sql`` mode"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Arbitrary tag that can be intercepted by custom ``env.py`` scripts."),
    purge: Optional[bool] = typer.Option(False, "--purge", help="Delete all entries in the version table before stamping")
):
    """
    'stamp' the revision table with the given revision
    """
    from alembic import command as alembic_command

    alembic_command.stamp(_get_alembic_config(),
                          revision=revision,
                          sql=sql,
                          tag=tag,
                          purge=purge)

@app.command()
def heads(
    verbose: Optional[bool] = typer.Option(False, "--verbose", "-v", help="Output in verbose mode"),
    resolve_dependencies: Optional[bool] = typer.Option(False, "--resolve", help="Treat dependency version as down revisions")
):
    """
    Show current available heads in the script directory.
    """
    from alembic import command as alembic_command

    alembic_command.heads(_get_alembic_config(),
                          verbose=verbose,
                          resolve_dependencies=resolve_dependencies)

@app.command()
def history(
    rev_range:Optional[str] = typer.Option(None, "--rev_range", help="Revision range"),
    verbose: Optional[bool] = typer.Option(False, "--verbose", "-v", help="Output in verbose mode"),
    indicate_current: Optional[bool] = typer.Option(False, "-i", help="Indicate current revision")
):
    """
    List changeset scripts in chronological order.
    """
    from alembic import command as alembic_command

    alembic_command.history(_get_alembic_config(),
                            rev_range=rev_range,
                            verbose=verbose,
                            indicate_current=indicate_current)

@app.command()
def current(
    verbose: Optional[bool] = typer.Option(False, "--verbose", "-v", help="Output in verbose mode"),
):
    """
    Display the current revision for a database.
    """
    from alembic import command as alembic_command

    alembic_command.current(_get_alembic_config(), verbose=verbose)

@app.command()
def merge(
    message: Optional[str] = typer.Option(None, "--message", "-m", help="String message to apply to the revision"),
    branch_label: Optional[str] = typer.Option(None, "--branch_label", help="String label to apply to the branch"),
    rev_id: Optional[str] = typer.Option(None, "--id", help="Revision identifier instead of generating a new")
):
    """
    Merge two revisions together.  Creates a new migration file.
    """
    from alembic import command as alembic_command

    alembic_command.merge(_get_alembic_config())
