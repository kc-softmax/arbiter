import os
import typer
import subprocess
import configparser
from typing import Optional
from typing_extensions import Annotated
from arbiter.command.template import (CONFIG_FILE, 
                                      PROJECT_NAME,
                                      create_project_structure, 
                                      create_default_config_file)

def read_config():
    """
    Reads configuration from an INI file.
    """
    file_path = os.path.join(CONFIG_FILE)
    if os.path.exists(file_path):
        config = configparser.ConfigParser()
        config.read(file_path)
        return config
    return None

app = typer.Typer()

@app.command()
def init(
    base_path: Optional[str] = typer.Option(".", "--path", "-p", help="The base path where to create the project.")
):
    """
    Creates a basic project structure with predefined files and directories.
    """    
    project_path = os.path.join(base_path, PROJECT_NAME)
    create_project_structure(project_path)
    create_default_config_file(".")
    
    typer.echo(f"Project created successfully.")

@app.command()
def start(
    app_path: Annotated[Optional[str], typer.Argument(..., help="The path to the FastAPI app, e.g., 'myapp.main:app'")] = f"{PROJECT_NAME}.main:arbiterApp",
    host: str = typer.Option(None, "--host", "-h", help="The host of the Arbiter FastAPI app."),
    port: int = typer.Option(None, "--port", "-p", help="The port of the Arbiter FastAPI app."),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for code changes.")
):
    """
    Read the config file.
    """
    config = read_config()
    if (config is None):
        typer.echo("No config file path found. Please run 'init' first.")
        return

    """
    Get the "host" and "port" from config file.
    """
    host = host or config.get("fastapi", "host", fallback=None)
    port = port or config.get("fastapi", "port", fallback=None)
    if (host is None or port is None):
        typer.echo("Set the port and host in 'arbiter.settings.ini' or give them as options.")
        return
        
    """
    Starts the Arbiter FastAPI app using Uvicorn.
    """
    typer.echo("Starting FastAPI app...")
    # Command to run Uvicorn with the FastAPI app
    uvicorn_command = f"uvicorn {app_path} --host {host} --port {port}"
    
    # Add reload option if specified
    if reload:
        uvicorn_command += " --reload"

    # Use subprocess to execute the command
    subprocess.run(uvicorn_command, shell=True)

if __name__ == "__main__":
    app()
