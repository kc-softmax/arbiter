import asyncio
import json
import sys
import uuid
import typer
from rich import print
import inspect
import uvloop
from functools import wraps

from server.database import create_db_and_tables, make_async_session
from server.auth.service import UserService, ConsoleUserService
from server.auth.models import User


# typer command 비동기 실행
class UTyper(typer.Typer):
    def __init__(self, *args, loop_factory=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.loop_factory = loop_factory

    def command(self, *args, **kwargs):
        decorator = super().command(*args, **kwargs)

        def add_runner(f):

            @wraps(f)
            def runner(*args, **kwargs):
                if sys.version_info >= (3, 11) and self.loop_factory:
                    with asyncio.Runner(loop_factory=self.loop_factory) as runner:
                        runner.run(f(*args, **kwargs))
                else:
                    asyncio.run(f(*args, **kwargs))

            if inspect.iscoroutinefunction(f):
                return decorator(runner)
            return decorator(f)
        return add_runner


app = UTyper(loop_factory=uvloop.new_event_loop)


@app.command('register_user_by_device_id')
async def register_user_by_device_id(device_id: str = typer.Argument(uuid.uuid4())):
    async with make_async_session() as session:
        if user := await UserService(session).register_user_by_device_id(
            device_id=device_id
        ):
            print("[green]{0} Success! Device ID: {1}".format(get_current_function(), device_id))
        else:
            print("[red]{0} Failed!".format(get_current_function()))


@app.command('login_by_device_id')
async def login_by_device_id(device_id: str = typer.Argument('')):
    async with make_async_session() as session:
        if user := await UserService(session).login_by_device_id(device_id=device_id):
            print("[green]{0} Success! Device ID: {1}".format(get_current_function(), device_id))
        else:
            print("[red]{0} Failed!".format(get_current_function()))


@app.command('register_user_by_email')
async def register_user_by_email(
    email: str = typer.Argument('test@test.com'),
    password: str = typer.Argument('password')
):
    async with make_async_session() as session:
        if user := await UserService(session).register_user_by_email(
            email=email,
            password=password
        ):
            print("[green]{0} Success! Email: {1}".format(get_current_function(), email))
        else:
            print("[red]{0} Failed!".format(get_current_function()))


@app.command('login_by_email')
async def login_by_email(
    email: str = typer.Argument('test@test.com'),
    password: str = typer.Argument('password')
):
    async with make_async_session() as session:
        if user := await UserService(session).login_by_email(
            email=email,
            password=password
        ):
            print("[green]{0} Success! Email: {1}".format(get_current_function(), email))
        else:
            print("[red]{0} Failed!".format(get_current_function()))


@app.command('check_user_by_email')
async def check_user_by_email(email: str = typer.Argument('test@test.com')):
    async with make_async_session() as session:
        if user := await UserService(session).check_user_by_email(
            email=email
        ):
            print("[green]{0} Success! Email: {1}".format(get_current_function(), email))
        else:
            print("[red]{0} Failed!".format(get_current_function()))


@app.command('delete_user')
async def delete_user(user_id: int = typer.Argument(1)):
    async with make_async_session() as session:
        if is_success := await UserService(session).delete_user(user_id=user_id):
            print("[green]{0} Success! User ID: {1}".format(get_current_function(), user_id))
        else:
            print("[red]{0} Failed!".format(get_current_function()))


@app.command('get_user')
async def get_user(user_id: int = typer.Argument(1)):
    async with make_async_session() as session:
        if user := await UserService(session).get_user(user_id=user_id):
            print("[green]{0} Success! User ID: {1}".format(get_current_function(), dict(user)))
        else:
            print("[red]{0} Failed!".format(get_current_function()))


@app.command('update_user')
async def update_user(
    user_id: int = typer.Argument(1),
    user: str = typer.Argument('{"display_name": "test1234", "verified": true}')
):
    async with make_async_session() as session:
        if user := await UserService(session).update_user(
            user_id=user_id,
            user=User(**json.loads(user))
        ):
            print("[green]{0} Success! User: {1}".format(get_current_function(), dict(user)))
        else:
            print("[red]{0} Failed!".format(get_current_function()))


@app.command('register_console_user')
async def register_console_user(
    email: str = typer.Argument('t11e22sst@test.com'),
    password: str = typer.Argument('password'),
    user_name: str = typer.Argument('test_user'),
    role: str = typer.Argument('owner')
):
    async with make_async_session() as session:
        if console_user := await ConsoleUserService(session).register_console_user(
            email=email,
            password=password,
            user_name=user_name,
            role=role
        ):
            print("[green]{0} Success! User: {1}".format(get_current_function(), dict(console_user)))
        else:
            print("[red]{0} Failed!".format(get_current_function()))


@app.command('get_console_user_all')
async def get_console_user_all():
    async with make_async_session() as session:
        if console_users := await ConsoleUserService(session).get_console_user_all():
            print("[green]{0} Success! User: {1}".format(get_current_function(), console_users))
        else:
            print("[red]{0} Failed!".format(get_current_function()))


@app.command('get_console_by_role')
async def get_console_by_role(role: str = typer.Argument('owner')):
    async with make_async_session() as session:
        if console_users := await ConsoleUserService(session).get_console_by_role(role=role):
            print("[green]{0} Success! User: {1}".format(get_current_function(), console_users))
        else:
            print("[red]{0} Failed!".format(get_current_function()))


@app.command('get_console_user_by_id')
async def get_console_user_by_id(console_user_id: int = typer.Argument(1)):
    async with make_async_session() as session:
        if console_user := await ConsoleUserService(session).get_console_user_by_id(
            console_user_id=console_user_id
        ):
            print("[green]{0} Success! User: {1}".format(get_current_function(), dict(console_user)))
        else:
            print("[red]{0} Failed!".format(get_current_function()))


@app.command('update_console_user')
async def update_console_user(
    user_id: int = typer.Argument(1),
    console_user: str = typer.Argument('{"user_name": "test_user"}')
):
    async with make_async_session() as session:
        if console_user := ConsoleUserService(session).update_console_user(
            user_id=user_id,
            console_user=User(**json.loads(console_user))
        ):
            print("[green]{0} Success! User: {1}".format(get_current_function(), dict(console_user)))
        else:
            print("[red]{0} Failed!".format(get_current_function()))


@app.command('delete_console_user')
async def delete_console_user(console_user_id: int = typer.Argument(1)):
    async with make_async_session() as session:
        if is_success := await ConsoleUserService(session).delete_console_user(console_user_id=console_user_id):
            print("[green]{0} Success! User ID: {1}".format(get_current_function(), console_user_id))
        else:
            print("[red]{0} Failed!".format(get_current_function()))


def get_current_function():
    return sys._getframe(1).f_code.co_name


async def main():
    await create_db_and_tables()


if __name__ == "__main__":
    asyncio.run(main())
    app()
