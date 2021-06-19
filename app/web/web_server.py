import asyncio
import os.path
import ssl
import asyncpg
import time
import tornado.ioloop
import tornado.web

from configparser import ConfigParser
from app.config import Config
from app.database.setup import db_setup, first_setup, show_db_error
from app.logger import logger
from app.plugins.plugin import get_available_plugins, load_plugins
from app.web.handlers.admin.add_member import AddMemberHandler
from app.web.handlers.admin.geography import GeographyHandler
from app.web.handlers.admin.members import MembersHandler
from app.web.handlers.admin.organizations import OrganizationsHandler
from app.web.handlers.admin.add_organization import AddOrganizationHandler
from app.web.handlers.admin.edit_organization import EditOrganizationHandler
from app.web.handlers.admin.roles import RolesHandler
from app.web.handlers.api.geography.municipalities import APIMunicipalitiesHandler
from app.web.handlers.api.geography.postal_code import APIPostalCodeHandler
from app.web.handlers.api.member import APIMemberHandler
from app.web.handlers.api.membership import APIMemberShipHandler
from app.web.handlers.api.organization import APIOrganizationHandler
from app.web.handlers.authentication import RecoveryHandler, SignInHandler, SignUpHandler
from app.web.handlers.error import Error404Handler
from app.web.handlers.error_kratos import ErrorKratosHandler
from app.web.handlers.kratos import KratosHandler
from app.web.handlers.main import MainHandler
from app.web.handlers.new_member import NewMemberHandler
from app.web.handlers.profile import ProfileHandler
from app.web.handlers.verify import VerifyHandler
from tornado.platform.asyncio import AnyThreadEventLoopPolicy
from typing import Union


class WebAppOptions:
    debug: bool = False
    https: bool = False
    port: int = 8888
    xsrf: bool = True
    cookie_secret: str = ""
    cert_file: os.PathLike = ""
    private_file: os.PathLike = ""
    db_username: str = ""
    db_password: str = ""
    db_hostname: str = ""
    dbname: str = ""
    test: bool = False


def start():
    logger.info("Starting server...")
    ioloop = tornado.ioloop.IOLoop.current()

    config = Config.get_config()  # type: ConfigParser

    options = WebAppOptions()
    options.debug = config.getboolean("WebServer", "debug", fallback=False)
    options.https = config.getboolean("WebServer", "https", fallback=False)
    options.port = config.getint("WebServer", "port")
    options.cookie_secret = config.get("WebServer", "cookie_secret")
    options.cert_file = config.get("WebServer", "certs")
    options.private_file = config.get("WebServer", "private")
    options.db_username = config.get("PostgreSQL", "username")
    options.db_password = config.get("PostgreSQL", "password")
    options.db_hostname = config.get("PostgreSQL", "hostname")
    options.dbname = config.get("PostgreSQL", "dbname")

    configure_application(options)

    asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
    logger.info("Server was successfully started")

    ioloop.start()


def configure_application(options: WebAppOptions):
    ioloop = tornado.ioloop.IOLoop.current()

    available_plugins = get_available_plugins()
    plugins = load_plugins(available_plugins)

    handlers = [
        (r"/", MainHandler),
        (r"/kratos/(.*)", KratosHandler),
        (r"/admin/add-member", AddMemberHandler),
        (r"/admin/geography", GeographyHandler),
        (r"/admin/members", MembersHandler),
        (r"/admin/organizations", OrganizationsHandler),
        (r"/admin/add-organization", AddOrganizationHandler),
        (r"/admin/edit-organization", EditOrganizationHandler),
        (r"/admin/roles", RolesHandler),
        (r"/api/member", APIMemberHandler),
        (r"/api/membership", APIMemberShipHandler),
        (r"/api/membership/(?P<id>[^\/]+)", APIMemberShipHandler),
        (r"/api/geography/municipalities", APIMunicipalitiesHandler),
        (r"/api/geography/postal_code/(?P<postal_code>[^\/]+)", APIPostalCodeHandler),
        (r"/api/organization", APIOrganizationHandler),
        (r"/api/organization/(?P<id>[^\/]+)", APIOrganizationHandler),
        (r"/auth/login", SignInHandler),
        (r"/auth/registration", SignUpHandler),
        (r"/error", ErrorKratosHandler),
        (r"/login", tornado.web.RedirectHandler, dict(url=r"/auth/login")),
        (r"/new-member", NewMemberHandler),
        (r"/profile", ProfileHandler),
        (r"/recovery", RecoveryHandler),
        (r"/verify", VerifyHandler),
    ]

    for plugin in plugins:
        handlers.append(plugin.get_handler())

    db = None

    if options.test is False:
        db = try_connect_to_database(options, handlers)

    webapp = tornado.web.Application(
        handlers,
        default_handler_class=Error404Handler,
        cookie_secret=options.cookie_secret,
        template_path=os.path.join(os.path.dirname(__file__), "..", "..", "templates"),
        static_path=os.path.join(os.path.dirname(__file__), "..", "..", "static"),
        login_url="/auth/login",
        xsrf_cookies=options.xsrf,
        ioloop=ioloop,
        debug=options.debug
    )

    webapp.db = db

    if options.https is True:
        cert_file = os.path.abspath(options.cert_file)
        private_file = os.path.abspath(options.private_file)

        if os.path.isfile(cert_file) is False:
            logger.error("Path specified in config for certification points to a non-file: " + cert_file)
            raise FileNotFoundError("Given path is not a file: " + cert_file)
        if os.path.isfile(private_file) is False:
            logger.error("Path specified in config for private key points to a non-file: " + private_file)
            raise FileNotFoundError("Given path is not a file: " + private_file)

        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(cert_file, private_file)

        http_server = tornado.httpserver.HTTPServer(webapp, ssl_options=ssl_ctx)
        http_server.listen(options.port)

        return http_server
    else:
        webapp.listen(options.port)

        return webapp


def try_connect_to_database(options: WebAppOptions, handlers: list) -> Union[asyncpg.pool.Pool, None]:
    attempts = 3
    db = None

    while attempts > 0:
        try:
            pool_task = init_db(options)
            db = asyncio.get_event_loop().run_until_complete(pool_task)
            attempts = 0
        except Exception:
            logger.critical(
                """Error occured when trying to connect to database, check if host, name, username and password is correct in
                config/config.ini""",
                exc_info=1
            )

            if db is not None:
                asyncio.get_event_loop().run_until_complete(db.close())
                db = None

            attempts -= 1

            if attempts > 0:
                time.sleep(5)
                logger.critical("Retrying database connection...")

    if db is not None:
        logger.debug("Database connection initialized...")
        asyncio.get_event_loop().run_until_complete(db_setup(db, handlers))
        asyncio.get_event_loop().run_until_complete(first_setup(db, handlers))
    else:
        logger.error("Database connection failed")
        logger.warning("Running without a database")
        show_db_error(handlers)
        db = None

    return db


def init_db(options: WebAppOptions) -> asyncpg.pool.Pool:
    if options.db_hostname == "" and options.dbname == "":
        return None

    dsn = "postgres://{username}:{password}@{hostname}/{database}".format(
        username=options.db_username,
        password=options.db_password,
        hostname=options.db_hostname,
        database=options.dbname
    )

    return asyncpg.create_pool(dsn, min_size=2, max_size=20, max_inactive_connection_lifetime=1800)
