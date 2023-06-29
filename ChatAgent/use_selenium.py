from pathlib import Path
from typing import Literal

import time
import undetected_chromedriver as uc
from selenium.common import TimeoutException, NoSuchElementException, UnableToSetCookieException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from .auth_handler import save_access_token, save_cookies, get_cookies, LLM_PROVIDER, save_next_data
from .config import config
from .exceptions import HandleCloudflareFailException, UseSeleniumFailedException
from .log_handler import logger
from .utils import SingletonMeta
# hook fetch_package to fix a download error
from .utils import download_file

uc.Patcher.fetch_package = download_file


def _fetch_cookies(name: LLM_PROVIDER, cookies: list[dict]):
    save_cookies(name, cookies)


class SeleniumRequests(metaclass=SingletonMeta):

    def __init__(self):
        self.driver = uc.Chrome(headless=True)
        # self.driver = uc.Chrome()
        self._wait15 = WebDriverWait(self.driver, 15)
        self._wait25 = WebDriverWait(self.driver, 25)
        self._wait35 = WebDriverWait(self.driver, 35)

    @property
    def get_driver(self):
        return self.driver

    def _get_user_agent_ua(self):
        sec_ch_ua = self.driver.execute_script("return navigator.userAgentData.toJSON();")
        user_agent = self.driver.execute_script("return navigator.userAgent;")
        logger.info(f"success in getting sec_ch_ua and user_agent")
        user_agent_ua = {
            "version_main": self.driver.patcher.version_main,
            "Sec-Ch-Ua": ", ".join(
                f'"{sec_ch_ua["brands"][i]["brand"]}";v="{sec_ch_ua["brands"][i]["version"]}"' for i in
                range(len(sec_ch_ua["brands"]))),
            "User-Agent": user_agent}
        path = Path(__file__).parent / "user_agent_ua.in"
        with open(path, "w") as f:
            f.write(str(user_agent_ua["version_main"]) + "\n")
            f.write(user_agent_ua["User-Agent"] + "\n")
            f.write(user_agent_ua["Sec-Ch-Ua"])
        return user_agent_ua

    def _handle_cloudflare_click(self) -> Literal["login", "prompt-textarea"]:
        self._wait25.until(EC.any_of(
            EC.element_to_be_clickable((By.XPATH, '//button/div[text()="Log in"]')),
            EC.frame_to_be_available_and_switch_to_it((By.XPATH, '//iframe[@allow="cross-origin-isolated"]'))
        ))
        if self.driver.find_elements(By.XPATH, '//button/div[text()="Log in"]'):
            return "login"
        cloudflare_click = self._wait25.until(
            EC.presence_of_element_located((By.XPATH, '//input[@type="checkbox"]'))
        )
        cloudflare_click.click()
        time.sleep(3)
        self.driver.switch_to.default_content()

        if self.driver.find_elements(By.XPATH, '//button/div[text()="Log in"]'):
            return "login"
        if self.driver.find_elements(By.XPATH, '//textarea[@id="prompt-textarea"]'):
            return "prompt-textarea"
        else:
            raise HandleCloudflareFailException

    def _handle_welcome_click(self):
        self._wait25.until(EC.any_of(EC.element_to_be_clickable((By.XPATH, '//button/div[text()="Log in"]')),
                                     EC.presence_of_element_located((By.XPATH, "//button/div[text()=\"Next\"]")),
                                     EC.presence_of_element_located((By.XPATH, '//textarea[@id="prompt-textarea"]'))
                                     ))
        if self.driver.find_elements(By.XPATH, "//button/div[text()=\"Next\"]"):
            self.driver.find_element(By.XPATH, "//button/div[text()=\"Next\"]").click()
            self.driver.find_element(By.XPATH, "//button/div[text()=\"Next\"]").click()
            self.driver.find_element(By.XPATH, "//button/div[text()=\"Done\"]").click()
            return True

        if self.driver.find_elements(By.XPATH, '//textarea[@id="prompt-textarea"]'):
            return True
        if self.driver.find_elements(By.XPATH, '//button/div[text()="Log in"]'):
            return False

    def _handle_login(self, mail: str, password: str):
        # 处理 Login
        el_button = self._wait15.until(
            EC.element_to_be_clickable((By.XPATH, '//button/div[text()="Log in"]'))
        )
        el_button.click()

        # 输入Email
        el_email_input = self._wait25.until(
            EC.presence_of_element_located((By.XPATH, '//input[@inputmode="email"]'))
        )
        el_email_input.send_keys(mail)
        continue_click = self._wait25.until(
            EC.presence_of_element_located((By.XPATH, '//button[@type="submit"]'))
        )
        continue_click.click()
        # 输入password
        input_password = self.driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')
        input_password.send_keys(password)
        self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

    def _get_next_data(self):
        next_data = self.driver.find_elements(By.XPATH, '//script[@id="__NEXT_DATA__"]')
        if next_data:
            next_data = next_data[0].get_attribute("textContent")
            logger.info(f"get __NEXT_DATA__ {next_data}")
            save_next_data("chatgpt", next_data)

    def _fetch_access_token(self):
        url = "https://chat.openai.com/api/auth/session"
        script = f"""
                var callback = arguments[arguments.length - 1];
                var xhr = new XMLHttpRequest();
                xhr.open("GET", "{url}", true);
                xhr.onreadystatechange = function() {{
                  if (xhr.readyState === 4 && xhr.status === 200) {{
                    var responseData = JSON.parse(xhr.responseText);
                    callback(responseData);
                  }}
                }};
                xhr.send();
                """
        response = self.driver.execute_async_script(script)
        logger.info(f"start fetch {url}/n get {response}...")
        save_access_token("chatgpt", response)

    def from_session_cookies(self) -> list[dict]:
        self.driver.get(f"https://chat.openai.com/api/auth/session")
        time.sleep(1)
        cookies = self.driver.get_cookies()
        return cookies

    def chatgpt_login(self):
        self.driver.get('https://chat.openai.com/auth/login')
        if not config["USER_AGENT_UA"] and self.driver.patcher.version_main != config["USER_AGENT_UA"]["version_main"]:
            config.setdefault("USER_AGENT_UA", self._get_user_agent_ua())
        try:
            if not self._handle_cloudflare_click() == "login":
                # retry once again
                self._handle_cloudflare_click()
        except (TimeoutException, NoSuchElementException, HandleCloudflareFailException) as e:
            logger.warning(f"warning a error occurred {e.msg}")
        # 处理登录
        self._handle_login(config["EMAIL"], config["PASSWORD"])

        # 处理登录时的弹窗
        if self._handle_welcome_click():
            self.driver.get("https://chat.openai.com/api/auth/session")

            cookies = self.driver.get_cookies()
            response = self.driver.page_source
            logger.info(f"start fetch https://chat.openai.com/api/auth/session \n get {response}...")
            save_access_token("chatgpt", response)
            _fetch_cookies("chatgpt", cookies)
            return self.driver
        else:
            raise UseSeleniumFailedException()

    def chatgpt_log_with_cookies(self):
        cookies_ = get_cookies("chatgpt")
        if not cookies_:
            self.chatgpt_login()
            return
        self.driver.get('https://chat.openai.com')
        if not config["USER_AGENT_UA"] and self.driver.patcher.version_main != config["USER_AGENT_UA"]["version_main"]:
            config.setdefault("USER_AGENT_UA", self._get_user_agent_ua())
        for cookie in cookies_:
            try:
                if cookie["name"] == "__Secure-next-auth.session-token" and cookie["expiry"] < int(time.time()):
                    self.chatgpt_login()
                    return
                if cookie["name"] == "__Host-next-auth.csrf-token":
                    continue
                self.driver.add_cookie(cookie)
            except UnableToSetCookieException as e:
                logger.warning(f"{e.msg} {cookie['name']}")
        self.driver.get('https://chat.openai.com')
        time.sleep(3)

        # battle cloudflare
        is_get_to = False
        try:
            is_get_to = self._handle_welcome_click()
        except (TimeoutException, NoSuchElementException) as e:
            logger.warning(f"warning use cookies to login didn't handle_welcome_click {e.msg}")
            try:
                r = self._handle_cloudflare_click()
                if r == "login":
                    self._handle_login(config["EMAIL"], config["PASSWORD"])
                    is_get_to = self._handle_welcome_click()
                if r == "prompt-textarea":
                    is_get_to = self._handle_welcome_click()
            except (TimeoutException, NoSuchElementException) as e:
                logger.warning("error", e.msg)
        if not is_get_to:
            self._handle_login(config["EMAIL"], config["PASSWORD"])
            is_get_to = self._handle_welcome_click()
        if is_get_to:
            cookies = self.driver.get_cookies()
            _fetch_cookies("chatgpt", cookies)
            # self.driver.close()
            return self.driver
        else:
            raise UseSeleniumFailedException()
