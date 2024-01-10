import json
import time
from pathlib import Path

import undetected_chromedriver as uc
from selenium.common import UnableToSetCookieException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from .auth_handler import save_access_token, save_cookies, get_cookies
from .config import config
from .log_handler import logger


# To delete
# hook fetch_package to fix a download error, you may not need this
# if config["ACCOUNTS"][0]["EMAIL"][:3] == "wit":
#     from .utils import download_file
#
#     uc.Patcher.fetch_package = download_file


def _get_driver_executable_path():
    driver_executable_path = Path(config["DRIVER_EXECUTABLE_PATH"])
    return driver_executable_path if driver_executable_path.exists() else None


class SeleniumRequests:

    def __init__(self, user: dict, headless: bool = not config["DEBUG"]):
        self.driver = uc.Chrome(
            driver_executable_path=_get_driver_executable_path(),
            headless=headless)
        self.user = user
        self._wait15 = WebDriverWait(self.driver, 15)
        self._wait25 = WebDriverWait(self.driver, 25)
        self._wait35 = WebDriverWait(self.driver, 35)

    @property
    def get_driver(self):
        return self.driver

    def _get_user_agent_ua(self):
        sec_ch_ua = self.driver.execute_script("return navigator.userAgentData.toJSON();")
        user_agent = self.driver.execute_script("return navigator.userAgent;")
        user_agent_ua = {
            "version_main": self.driver.capabilities['browserVersion'].split(".")[0],
            "Sec-Ch-Ua": ", ".join(
                f'"{sec_ch_ua["brands"][i]["brand"]}";v="{sec_ch_ua["brands"][i]["version"]}"' for i in
                range(len(sec_ch_ua["brands"]))),
            "User-Agent": user_agent}
        logger.info(f"success in getting user_agent_ua\n{user_agent_ua}")
        path = Path(__file__).parent / "user_agent_ua.in"
        with open(path, "w") as f:
            f.write(user_agent_ua["version_main"] + "\n")
            f.write(user_agent_ua["User-Agent"] + "\n")
            f.write(user_agent_ua["Sec-Ch-Ua"])
        return user_agent_ua

    def fetch_access_token_cookies(self, auth_again: bool) -> tuple[list[dict], str] | list[dict]:
        self.driver.get(f"https://chat.openai.com/api/auth/session")
        time.sleep(1)
        cookies = self.driver.get_cookies()
        save_cookies("chatgpt", self.user, cookies)
        if auth_again:
            json_text = self.driver.find_element(By.TAG_NAME, 'pre').text
            logger.info(f"Fetch https://chat.openai.com/api/auth/session ACCESS_TOKEN\n... {json_text[-140:]}")
            save_access_token("chatgpt", self.user, json_text)
            return cookies, json.loads(json_text)["accessToken"]
        else:
            return cookies

    def chatgpt_login_with_cookies(self) -> tuple[list[dict], str] | list[dict]:
        cookies_ = get_cookies("chatgpt", self.user)
        self.driver.get('https://chat.openai.com')
        for cookie in cookies_:
            try:
                if cookie["sameSite"] == "no_restriction":
                    cookie["sameSite"] = "None"
                elif cookie["sameSite"] == "strict":
                    cookie["sameSite"] = "Strict"
                else:
                    cookie["sameSite"] = "Lax"
                self.driver.add_cookie(cookie)
            except (UnableToSetCookieException, AssertionError) as e:
                logger.warning(f"{e.msg if type(e) == UnableToSetCookieException else str(e)} {cookie['name']}")
        self.driver.get('https://chat.openai.com')
        time.sleep(2)
        if self.driver.find_elements(By.XPATH, "//button/div[text()=\"Okay, let’s go\"]"):
            self.driver.find_element(By.XPATH, "//button/div[text()=\"Okay, let’s go\"]").click()
        if self.driver.find_elements(By.XPATH, '//textarea[@id="prompt-textarea"]'):
            return self.fetch_access_token_cookies(True)
