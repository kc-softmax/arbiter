import json
import sys
import uuid
import typer
from rich import print

from auth.service import UserService, ConsoleUserService
from auth.models import User
from database import create_db_and_tables


app = typer.Typer()


@app.command('register_user_by_device_id')
def register_user_by_device_id(device_id: str = typer.Argument(uuid.uuid4())):
    if user := UserService().register_user_by_device_id(
        device_id=device_id
    ):
        print("[green]{0} Success! Device ID: {1}".format(get_current_function(), device_id))
    else:
        print("[red]{0} Failed!".format(get_current_function()))


@app.command('login_by_device_id')
def login_by_device_id(device_id: str = typer.Argument('')):
    if user := UserService().login_by_device_id(device_id=device_id):
        print("[green]{0} Success! Device ID: {1}".format(get_current_function(), device_id))
    else:
        print("[red]{0} Failed!".format(get_current_function()))


@app.command('register_user_by_email')
def register_user_by_email(
    email: str = typer.Argument('test@test.com'),
    password: str = typer.Argument('password')
):
    if user := UserService().register_user_by_email(
        email=email,
        password=password
    ):
        print("[green]{0} Success! Email: {1}".format(get_current_function(), email))
    else:
        print("[red]{0} Failed!".format(get_current_function()))


@app.command('login_by_email')
def login_by_email(
    email: str = typer.Argument('test@test.com'),
    password: str = typer.Argument('password')
):
    if user := UserService().login_by_email(
        email=email,
        password=password
    ):
        print("[green]{0} Success! Email: {1}".format(get_current_function(), email))
    else:
        print("[red]{0} Failed!".format(get_current_function()))


@app.command('check_user_by_email')
def check_user_by_email(email: str = typer.Argument('test@test.com')):
    if user := UserService().check_user_by_email(
        email=email
    ):
        print("[green]{0} Success! Email: {1}".format(get_current_function(), email))
    else:
        print("[red]{0} Failed!".format(get_current_function()))


@app.command('delete_user')
def delete_user(user_id: int = typer.Argument(1)):
    if is_success := UserService().delete_user(user_id=user_id):
        print("[green]{0} Success! User ID: {1}".format(get_current_function(), user_id))
    else:
        print("[red]{0} Failed!".format(get_current_function()))


@app.command('get_user')
def get_user(user_id: int = typer.Argument(1)):
    if user := UserService().get_user(user_id=user_id):
        print("[green]{0} Success! User ID: {1}".format(get_current_function(), dict(user)))
    else:
        print("[red]{0} Failed!".format(get_current_function()))


@app.command('update_user')
def update_user(
    user_id: int = typer.Argument(1),
    user: str = typer.Argument('{"display_name": "test1234", "verified": true}')
):
    if user := UserService().update_user(
        user_id=user_id,
        user=User(**json.loads(user))
    ):
        print("[green]{0} Success! User: {1}".format(get_current_function(), dict(user)))
    else:
        print("[red]{0} Failed!".format(get_current_function()))


@app.command('register_console_user')
def register_console_user(
    email: str = typer.Argument('tesst@test.com'),
    password: str = typer.Argument('password'),
    user_name: str = typer.Argument('test_user'),
    role: str = typer.Argument('owner')
):
    if console_user := ConsoleUserService().register_console_user(
        email=email,
        password=password,
        user_name=user_name,
        role=role
    ):
        print("[green]{0} Success! User: {1}".format(get_current_function(), dict(console_user)))
    else:
        print("[red]{0} Failed!".format(get_current_function()))


@app.command('get_console_user_all')
def get_console_user_all():
    if console_users := ConsoleUserService().get_console_user_all():
        print("[green]{0} Success! User: {1}".format(get_current_function(), console_users))
    else:
        print("[red]{0} Failed!".format(get_current_function()))


@app.command('get_console_by_role')
def get_console_by_role(role: str = typer.Argument('owner')):
    if console_users := ConsoleUserService().get_console_by_role(role=role):
        print("[green]{0} Success! User: {1}".format(get_current_function(), console_users))
    else:
        print("[red]{0} Failed!".format(get_current_function()))


@app.command('get_console_user_by_id')
def get_console_user_by_id(user_id: int = typer.Argument(1)):
    if console_user := ConsoleUserService().get_console_user_by_id(user_id=user_id):
        print("[green]{0} Success! User: {1}".format(get_current_function(), dict(console_user)))
    else:
        print("[red]{0} Failed!".format(get_current_function()))


@app.command('update_console_user')
def update_console_user(
    user_id: int = typer.Argument(1),
    console_user: str = typer.Argument('{"user_name": "test_user"}')
):
    if console_user := ConsoleUserService().update_console_user(
        user_id=user_id,
        console_user=User(**json.loads(console_user))
    ):
        print("[green]{0} Success! User: {1}".format(get_current_function(), dict(console_user)))
    else:
        print("[red]{0} Failed!".format(get_current_function()))


@app.command('delete_console_user')
def delete_console_user(user_id: int = typer.Argument(1)):
    if is_success := ConsoleUserService().delete_console_user(user_id=user_id):
        print("[green]{0} Success! User ID: {1}".format(get_current_function(), user_id))
    else:
        print("[red]{0} Failed!".format(get_current_function()))


def get_current_function():
    return sys._getframe(1).f_code.co_name


if __name__ == "__main__":
    create_db_and_tables()
    app()
