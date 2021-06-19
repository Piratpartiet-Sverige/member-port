import tornado.web

from tornado.web import RequestHandler
from app.logger import logger


class KratosHandler(RequestHandler):
    async def prepare(self):
        """
        Do not call manually. This runs on every request before get/post/etc.
        """
        pass

    def check_xsrf_cookie(_xsrf):
        pass

    @tornado.gen.coroutine
    def get(self, url: str = ""):
        url = "http://pirate-kratos:4433/" + url + "?" + self.request.query

        logger.debug("GET to Kratos: " + url)

        req = tornado.httpclient.HTTPRequest(url, follow_redirects=False, headers=self.request.headers)
        client = tornado.httpclient.AsyncHTTPClient()
        response = yield client.fetch(req, raise_error=False)

        self.set_status(response.code)

        for header in response.headers:
            if header.lower() == 'content-length':
                self.set_header(header, str(max(len(response.body), int(response.headers.get(header)))))
            else:
                if header.lower() == 'set-cookie':
                    cookie_strings = response.headers.get(header)
                    cookies = []
                    for cookie in cookie_strings.split(","):
                        if (cookie[0] == ' '):
                            cookies[-1] = cookies[-1] + cookie
                        else:
                            cookies.append(cookie)
                    logger.debug(cookies)
                    for cookie in cookies:
                        self.add_header(header, cookie)
                elif header.lower() != 'transfer-encoding':
                    self.set_header(header, response.headers.get(header))

        self.write(response.body)
        self.finish()

    @tornado.gen.coroutine
    def post(self, url: str = ""):
        url = "http://pirate-kratos:4433/" + url + "?" + self.request.query

        logger.debug("POST to Kratos: " + url)

        req = tornado.httpclient.HTTPRequest(url, method="POST", body=self.request.body,
                                             follow_redirects=False, headers=self.request.headers)

        logger.debug(self.request.body)
        logger.debug(self.request.headers)

        client = tornado.httpclient.AsyncHTTPClient()
        response = yield client.fetch(req, raise_error=False)

        self.set_status(response.code)

        for header in response.headers:
            if header.lower() == 'content-length':
                self.set_header(header, str(max(len(response.body), int(response.headers.get(header)))))
            else:
                if header.lower() == 'set-cookie':
                    cookie_strings = response.headers.get(header)
                    cookie_strings = cookie_strings.replace("Domain=pirate-kratos;", "")  # Domain=http://127.0.0.1:8888
                    cookies = []
                    for cookie in cookie_strings.split(","):
                        if cookie[0] == ' ':
                            cookies[-1] = cookies[-1] + cookie
                        else:
                            cookies.append(cookie)

                    for cookie in cookies:
                        self.add_header(header, cookie)
                elif header.lower() != 'transfer-encoding':
                    self.set_header(header, response.headers.get(header))

        if url.endswith("/logout"):
            self.clear_session_cookie()

        self.write(response.body)
        self.finish()
