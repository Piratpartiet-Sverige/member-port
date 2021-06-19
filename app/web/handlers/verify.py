import tornado.web
import ory_kratos_client

from ory_kratos_client.api import v0alpha1_api
from ory_kratos_client.rest import ApiException
from ory_kratos_client.configuration import Configuration

from app.database.dao.users import UsersDao
from app.logger import logger
from app.web.handlers.base import BaseHandler


class VerifyHandler(BaseHandler):
    @tornado.web.authenticated
    async def get(self):
        flow = self.get_argument("flow", default="")

        if (flow == ""):
            return self.redirect("http://127.0.0.1:8888/kratos/self-service/verification/browser")

        configuration = Configuration(
            host="http://pirate-kratos:4433"
        )

        cookie = self.request.headers['Cookie']
        errors = []
        nodes = []
        action = ""
        method = ""
        state = ""

        with ory_kratos_client.ApiClient(configuration) as api_client:
            api_instance = v0alpha1_api.V0alpha1Api(api_client)
            try:
                api_response = api_instance.get_self_service_verification_flow(flow, cookie=cookie)
                logger.debug(api_response)
                errors = api_response.ui.messages.value if hasattr(api_response.ui, 'messages') else []
                nodes = api_response.ui.nodes.value
                action = api_response.ui.action
                method = api_response.ui.method
                state = api_response.state.value
            except ApiException as e:
                logger.error("Exception when calling V0alpha1Api->get_self_service_verification_flow: %s\n" % e)

                if e.status == 410:
                    return self.redirect("http://127.0.0.1:8888/kratos/self-service/verification/browser")

        dao = UsersDao(self.db)
        permissions_check = await dao.check_user_admin(self.current_user.user.id)

        await self.render(
            "verify.html",
            admin=permissions_check,
            title="Verifiera",
            user=self.current_user.user,
            action=action,
            method=method,
            errors=errors,
            nodes=nodes,
            state=state
        )
