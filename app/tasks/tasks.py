import asyncio

from .celery import app, options, admin
from app.database.dao.members import MembersDao
from app.email import send_email
from app.web.web_server import init_db
from celery.exceptions import Reject
from celery.schedules import crontab


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(hour=0, minute=0),
        task_remove_expired_memberships.s(),
    )


async def remove_expired_memberships() -> int:
    db = await init_db(options)

    dao = MembersDao(db)

    count = await dao.count_expired_memberships()
    await dao.remove_expired_memberships()

    return count


@app.task(bind=True, max_retries=2)
def task_remove_expired_memberships(self):
    try:
        count = asyncio.get_event_loop().run_until_complete(remove_expired_memberships())
    except Exception as e:
        send_email(
            admin, "Critical: could not delete memberships!",
            "Task ID: {task_id}\nException message: {msg}".format(
                task_id=self.request.id,
                msg=e
            )
        )
        raise Reject(e, requeue=False)

    send_email(admin, "Memberships removed: " + count.__str__(), "More statistics may be added in the future...")
