# from __future__ import annotations
# import inspect
# from typing import  Any, Callable
# from arbiter.enums import ModelState
# from arbiter.task.task_runner import ProcessRunner

# class ServiceMeta(type):

#     def __new__(cls, name: str, bases: tuple, class_dict: dict[str, Any]):
#         new_cls = super().__new__(cls, name, bases, class_dict)

#         task_functions: list[Callable] = []

#         combined_attrs = set(class_dict.keys())
#         for base in bases:
#             combined_attrs.update(dir(base))
#             # 부모 클래스에서 decorator 수집
#             for attr_name in dir(base):
#                 if (
#                     callable(getattr(base, attr_name)) and
#                     getattr(
#                         getattr(base, attr_name),
#                         'is_task_function', False)
#                 ):
#                     task_functions.append(getattr(base, attr_name))

#         # 현재 클래스에서 decorator 수집
#         for attr_name, attr_value in class_dict.items():
#             if (
#                 callable(attr_value) and getattr(
#                     attr_value, 'is_task_function', False)
#             ):
#                 task_functions.append(attr_value)


#         for task_function in task_functions:
#             signature = inspect.signature(task_function)
    
#             # Print the parameters of the function
#             for index, param in enumerate(signature.parameters.values()):
#                 if index == 0 and param.name != 'self':
#                     # Ensure the first parameter is Arbiter instance
#                     raise ValueError(
#                         f"in local task First parameter of task function must be Arbiter instance"
#                     )
#                 if param.name == 'self':
#                     continue
#                 param_type = param.annotation
#                 # Ensure the parameter has a type hint
#                 if param_type is inspect._empty:
#                     raise TypeError(
#                         "No type hint provided, Task function must have a type hint")
#                 else:
#                     # Example check if the first argument is User instance
#                     # if task.auth and index == 1:
#                     #     if param_type is not User:
#                     #         raise TypeError(
#                     #             f"if auth is True,\n{
#                     #                 name} - {rpc_func.__name__} function must have a User instance as the second argument"
#                     #         )
#                     pass
#         setattr(new_cls, 'async_task_functions', task_functions)
#         return new_cls
      
# class ArbiterService(ProcessRunner, metaclass=ServiceMeta):
    
#     # # create async task로 생성되어 진다
#     # """ use create async task """
#     async_task_functions: list[Callable] = []
    
#     # """ use mutiprocesing """
#     parallel_task_functions: list[Callable] = []
    
#     def __init__(
#         self,
#         *,
#         name: str,
#     ):
#         super().__init__()
#         self.name = name
#         self.node = ArbiterServiceNode(
#             name=self.name,
#             state=ModelState.INACTIVE,
#         )
        
#     async def setup(self):
#         ##############################
#         # task 생성 및 실행
#         # async_task_functions
#         # parallel_task_functions
        
#         ##############################
#         pass
#     # for task_function in self.task_functions:
#     #     queue = getattr(task_function, 'queue', None)
#     #     num_of_tasks = getattr(task_function, 'num_of_tasks', 1)
#     #     if not queue:
#     #         queue = get_task_queue_name(
#     #             self.__class__.__name__, 
#     #             task_function.__name__)
#     #     task_model = await self.arbiter.get_data(ArbiterTaskModel, queue)
#     #     if not task_model:
#     #         raise ValueError(f"Task model {queue} not found")
#     #     for _ in range(num_of_tasks):
#     #         params = [self.arbiter, queue, self]
#     #         task_node = ArbiterTaskNode(
#     #             service_node_id=self.service_node_id,
#     #             parent_model_id=task_model.id,
#     #             state=ModelState.INACTIVE,
#     #         )
#     #         await self.arbiter.save_data(task_node)
#     #         params.append(task_node)
#     #         self.tasks[task_node] = asyncio.create_task(task_function(*params))