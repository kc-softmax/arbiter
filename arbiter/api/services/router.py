import arbiter.api.services.schemas as schemas
import arbiter.api.services.exceptions as exceptions

from prisma.errors import UniqueViolationError
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from http import HTTPStatus
from arbiter.database import get_db, Prisma
from arbiter.api.services.constants import ServicesRouterTag


router = APIRouter(
    prefix="/services",
)


@router.post(
    "/messages/send",
    tags=[ServicesRouterTag.MANAGE],
    status_code=HTTPStatus.ACCEPTED,
    response_model=bool
)
async def send_message_to_service(
    data: schemas.MessageSchema,
    db: Prisma = Depends(get_db)
):
    # 하나의 쿼리로 만들 수 있을텐데
    service = await db.service.find_unique(where={"id": data.service_id})
    if data.target_registry_ids:
        targets = await db.serviceregistry.find_many(where={"id": {"in": data.target_registry_ids}})
    else:
        targets = service.registered_services
    if targets:
        # send messages
        # TODO
        pass
    return True


@router.post(
    "/manage/list",
    tags=[ServicesRouterTag.MANAGE],
    status_code=HTTPStatus.ACCEPTED,
    response_model=list[schemas.ServiceSchema]
)
async def fetch_service_list(
    data: schemas.FetchServiceListSchema,
    db: Prisma = Depends(get_db)
):
    if data.service_id:
        return await db.service.find_many(where={"id": data.service_id})
    else:
        return await db.service.find_many()


@router.post(
    "/manage/start",
    tags=[ServicesRouterTag.MANAGE],
    status_code=HTTPStatus.ACCEPTED,
    response_model=schemas.ServiceRegistrySchema
)
async def service_start(
    data: schemas.StartServiceSchema,
    db: Prisma = Depends(get_db)
):
    service = await db.service.find_unique(where={"id": data.service_id})
    if not service:
        raise exceptions.ServiceNotFound

    # TODO start service and check is actually started
    #

    registry = await db.serviceregistry.create(
        data={"service": {"connect": {"id": service.id}}}
    )

    return registry


@router.post(
    "/manage/restart",
    tags=[ServicesRouterTag.MANAGE],
    status_code=HTTPStatus.ACCEPTED,
    response_model=bool
)
async def service_restart(
    data: schemas.MessageSchema,
    db: Prisma = Depends(get_db)
):

    return True


@router.post(
    "/manage/pause",
    tags=[ServicesRouterTag.MANAGE],
    status_code=HTTPStatus.ACCEPTED,
    response_model=bool
)
async def service_pause(
    data: schemas.MessageSchema,
    db: Prisma = Depends(get_db)
):

    return True


@router.post(
    "/manage/resume",
    tags=[ServicesRouterTag.MANAGE],
    status_code=HTTPStatus.ACCEPTED,
    response_model=bool
)
async def service_resume(
    data: schemas.MessageSchema,
    db: Prisma = Depends(get_db)
):

    return True


@router.post(
    "/manage/stop",
    tags=[ServicesRouterTag.MANAGE],
    status_code=HTTPStatus.ACCEPTED,
    response_model=bool
)
async def service_stop(
    data: schemas.MessageSchema,
    db: Prisma = Depends(get_db)
):

    return True
