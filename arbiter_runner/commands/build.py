# import typer
# import sys
# import os
# import json
# from typing import Callable

# from arbiter.utils import find_python_files_in_path, find_registered_services
# from arbiter_runner.utils import AsyncTyper
# from arbiter.arbiter_runner.utils import (
#     read_config,
#     write_config,
#     refresh_output,
#     popen_command,
#     Commands,
#     Communication,
#     SupportedModules,
# )
# from arbiter.service import ArbiterServiceWorker


# app = AsyncTyper()

# filtered_plan_cmd: Callable[[str, str], str] = lambda cmd, var: cmd.format(var=var if var else '')
# filtered_apply_cmd: Callable[[str, str, str], str] = lambda cmd, var, module: cmd.format(
#     var=var if var else '', module=module)


# @app.command(help="build local kubernetes deployment enviroment")
# def local():
#     typer.echo(typer.style("not supported yet", fg=typer.colors.RED, bold=True))


# @app.command(help="build AWS cloud resource for deployment")
# def cloud():
#     # add init path because cli don't know main.tf file path
#     sys.path.insert(0, os.getcwd())
#     try:
#         # rewrite command by inputing value
#         # get available service and main app
#         python_files_in_root = find_python_files_in_path()
#         registered_services = find_registered_services(python_files_in_root, ArbiterServiceWorker)
#         service_list = json.dumps(
#             {
#                 service.__module__: service.__name__
#                 for service in registered_services
#             }
#         )
#         addtional_var = f"-var='service_list={service_list}' -var='service_name=arbiter'"
#         # Usage plan
#         _, stderr = popen_command(
#             Commands.TERRAFORM_INIT,
#             communication_err=Communication.RETURN_ERR
#         )
#         if stderr:
#             typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
#             raise typer.Abort()
#         _, stderr = popen_command(
#             filtered_plan_cmd(Commands.TERRAFORM_PLAN, addtional_var),
#             communication_err=Communication.RETURN_ERR
#         )
#         if stderr:
#             typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
#             raise typer.Abort()
#         deploy = typer.confirm("Are you sure you want to deploy it?")
#         if not deploy:
#             raise typer.Abort()

#         # 1. create network, security group
#         _, stderr = popen_command(
#             filtered_apply_cmd(Commands.TERRAFORM_APPLY, addtional_var, SupportedModules.NETWORK),
#             communication_err=Communication.RETURN_ERR
#         )
#         if stderr:
#             typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
#             raise typer.Abort()
#         _, stderr = popen_command(
#             filtered_apply_cmd(Commands.TERRAFORM_APPLY, addtional_var, SupportedModules.SG),
#             communication_err=Communication.RETURN_ERR
#         )
#         if stderr:
#             typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
#             raise typer.Abort()

#         # 2. create cache
#         _, stderr = popen_command(
#             filtered_apply_cmd(Commands.TERRAFORM_APPLY, addtional_var, SupportedModules.CACHE),
#             communication_err=Communication.RETURN_ERR
#         )
#         if stderr:
#             typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
#             raise typer.Abort()
#         refresh_output()

#         # 3. get endpoint
#         stdout, stderr = popen_command(
#             Commands.TERRAFORM_OUTPUT,
#             communication_out=Communication.RETURN_OUT,
#             communication_err=Communication.RETURN_ERR
#         )
#         if stderr:
#             typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
#             raise typer.Abort()
#         output: dict[str, str] = json.loads(stdout)
#         if output.get("redis_endpoint"):
#             config = read_config("arbiter.setting.ini")
#             config.set("cache", "redis.url", output["redis_endpoint"]["value"])
#             config.set("database", "port", "443")
#             config.set("database", "hostname", "s0.fourbarracks.io")
#             write_config(config, "arbiter.setting.ini")
#         else:
#             typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
#             raise typer.Abort()

#         # 4. docker(ECR, push image)
#         _, stderr = popen_command(
#             filtered_apply_cmd(Commands.TERRAFORM_APPLY, addtional_var, SupportedModules.IMAGES),
#             communication_err=Communication.RETURN_ERR
#         )
#         if stderr:
#             typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
#             raise typer.Abort()
#         refresh_output()
#         stdout, stderr = popen_command(
#             Commands.TERRAFORM_OUTPUT,
#             communication_out=Communication.RETURN_OUT,
#             communication_err=Communication.RETURN_ERR
#         )
#         if stderr:
#             typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
#             raise typer.Abort()
#         output: dict[str, str] = json.loads(stdout)
#         if output.get("images"):
#             repo_name = output["images"]["value"]
#             _, _ = popen_command(f"./build_and_push.sh {repo_name} ap-northeast-2 linux/amd64 ./")

#         # 5. create service(ELB, ECS, Container Instance, domain)
#         _, stderr = popen_command(
#             filtered_apply_cmd(Commands.TERRAFORM_APPLY, addtional_var, SupportedModules.LB),
#             communication_err=Communication.RETURN_ERR
#         )
#         if stderr:
#             typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
#             raise typer.Abort()
#         _, stderr = popen_command(
#             filtered_apply_cmd(Commands.TERRAFORM_APPLY, addtional_var, SupportedModules.CONTAINER),
#             communication_err=Communication.RETURN_ERR
#         )
#         if stderr:
#             typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
#             raise typer.Abort()
#         _, stderr = popen_command(
#             filtered_apply_cmd(Commands.TERRAFORM_APPLY, addtional_var, SupportedModules.COMPUTE),
#             communication_err=Communication.RETURN_ERR
#         )
#         if stderr:
#             typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
#             raise typer.Abort()
#         _, stderr = popen_command(
#             filtered_apply_cmd(Commands.TERRAFORM_APPLY, addtional_var, SupportedModules.DOMAIN),
#             communication_err=Communication.RETURN_ERR
#         )
#         if stderr:
#             typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
#             raise typer.Abort()
#         refresh_output()

#         # 6. get domain
#         stdout, stderr = popen_command(
#             Commands.TERRAFORM_OUTPUT,
#             communication_out=Communication.RETURN_OUT,
#             communication_err=Communication.RETURN_ERR
#         )
#         if stderr:
#             typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
#             raise typer.Abort()
#         output: dict[str, str] = json.loads(stdout)
#         if output.get("domain_name"):
#             domain_name = output["domain_name"]["value"]
#             print("#" * 100)
#             typer.echo(typer.style(f"Domain Name: {domain_name}", fg=typer.colors.GREEN, bold=True))
#             print("#" * 100)
#     except typer.Abort:
#         _, _ = popen_command(Commands.TERRAFORM_DESTROY)
#     except Exception:
#         _, _ = popen_command(Commands.TERRAFORM_DESTROY)
