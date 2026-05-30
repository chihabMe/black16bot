from background_task import background

from broadcasts.services import send_broadcast


@background(schedule=0)
def send_broadcast_task(broadcast_id: int) -> None:
    send_broadcast(broadcast_id=broadcast_id)
