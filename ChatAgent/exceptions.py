class NoSuchCookiesException(Exception):
    def __init__(self, message="No Such Cookies"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"NoSuchCookiesException: {self.message}"


class HandleCloudflareFailException(Exception):
    def __init__(self, message="Handle Cloudflare Failed"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"HandleCloudflareFailException: {self.message}"


class AccessTokenExpiredException(Exception):
    def __init__(self, message="AccessToken Expired"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"AccessTokenExpiredException: {self.message}"


class AuthenticationTokenExpired(Exception):
    def __init__(self, message="Authentication Token Expired"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"AuthenticationTokenExpired: {self.message}"


class UseSeleniumFailedException(Exception):
    def __init__(self, message="Use Selenium Failed"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"UseSeleniumFailedException: {self.message}"


class Requests403Error(Exception):
    def __init__(self, message="Request 403"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"Requests403Error: {self.message}"


class Requests500Error(Exception):
    def __init__(self, message="Request 500"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"Requests500Error: {self.message}"


class RequestsError(Exception):
    def __init__(self, message="Request Error"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"RequestError: {self.message}"


class RetryFailed(Exception):
    def __init__(self, message="Retry Failed"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"RetryFailed: {self.message}"
