from arbiter.api import arbiterApp
from arbiter.api.live.service import LiveService
from .engine import MyLiveEngine

live_service = LiveService(MyLiveEngine())


# Can add the handler for LiveConnectionEvent
# from arbiter.api.live.const import LiveConnectionEvent
# @live_service.on_event(LiveConnectionEvent.VALIDATE)
# def on_validate(user_id):
#   pass

arbiterApp.add_live_service('/ws', live_service)

# Can add the your route.
# @arbiterApp.post('/my_route')
# def post_my_route(
#   user: GameUser = Depends(get_current_user),
#   session: AsyncSession = Depends(unit_of_work)):
#   pass