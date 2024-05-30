from prisma import Prisma
from typing import Optional


class PrismaClientWrapper:
    _instance: Optional[Prisma] = None

    @classmethod
    def get_instance(cls) -> Prisma:
        if cls._instance is None:
            cls._instance = Prisma(auto_register=True)
        return cls._instance

    @classmethod
    async def connect(cls):
        instance = cls.get_instance()
        await instance.connect()

    @classmethod
    async def disconnect(cls):
        instance = cls.get_instance()
        await instance.disconnect()


def get_db() -> Prisma:
    return PrismaClientWrapper.get_instance()
