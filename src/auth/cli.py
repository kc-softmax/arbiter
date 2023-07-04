import json
import sys
import uuid
import typer
from rich import print
from auth import service
from auth.models import User
from database import create_db_and_tables


app = typer.Typer()


@app.command('register_user_by_device_id')
def register_user_by_device_id(device_id: str = typer.Argument(uuid.uuid4())):
    if user := service.register_user_by_device_id(
        device_id=device_id
    ):
        print("[green]{0} Success! Device ID: {1}".format(get_current_function(), device_id))
    else:
        print("[red]{0} Failed!".format(get_current_function()))


@app.command('login_by_device_id')
def login_by_device_id(device_id: str = typer.Argument('')):
    if user := service.login_by_device_id(device_id=device_id):
        print("[green]{0} Success! Device ID: {1}".format(get_current_function(), device_id))
    else:
        print("[red]{0} Failed!".format(get_current_function()))


@app.command('resister_user_by_email')
def resister_user_by_email(
    email: str = typer.Argument('test@test.com'),
    password: str = typer.Argument('password')
):
    if user := service.resister_user_by_email(
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
    if user := service.login_by_email(
        email=email,
        password=password
    ):
        print("[green]{0} Success! Email: {1}".format(get_current_function(), email))
    else:
        print("[red]{0} Failed!".format(get_current_function()))


@app.command('check_user_by_email')
def check_user_by_email(email: str = typer.Argument('test@test.com')):
    if user := service.check_user_by_email(
        email=email
    ):
        print("[green]{0} Success! Email: {1}".format(get_current_function(), email))
    else:
        print("[red]{0} Failed!".format(get_current_function()))


@app.command('delete_user')
def delete_user(user_id: int = typer.Argument(1)):
    if is_success := service.delete_user(user_id=user_id):
        print("[green]{0} Success! User ID: {1}".format(get_current_function(), user_id))
    else:
        print("[red]{0} Failed!".format(get_current_function()))


@app.command('get_user')
def get_user(user_id: int = typer.Argument(1)):
    if user := service.get_user(user_id=user_id):
        print("[green]{0} Success! User ID: {1}".format(sys._getframe(0).f_code.co_name, dict(user)))
    else:
        print("[red]{0} Failed!".format(sys._getframe(0).f_code.co_name))


@app.command('update_user')
def update_user(
    user_id: int = typer.Argument(1),
    user: str = typer.Argument('{"display_name": "test1234", "verified": true}')
):
    if user := service.update_user(
        user_id=user_id,
        user=User(**json.loads(user))
    ):
        print("[green]{0} Success! User ID: {1}".format(get_current_function(), dict(user)))
    else:
        print("[red]{0} Failed!".format(sys._getframe(0).f_code.co_name))


def get_current_function():
    return sys._getframe(1).f_code.co_name


if __name__ == "__main__":
    create_db_and_tables()
    app()
