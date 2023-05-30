import time
from typing import Literal

import selenium
import undetected_chromedriver as uc
from selenium.common import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from auth_handler import save_access_token, save_cookies, get_cookies, LLM_PROVIDER, save_next_data
from config import EMAIL, PASSWORD
from exceptions import HandleCloudflareFailException, UseSeleniumFailedException
from log_handler import logger
from utils import download_file, SingletonMeta

# hook fetch_package to fix a download error
uc.Patcher.fetch_package = download_file


def _fetch_access_token(name: LLM_PROVIDER, driver: selenium.webdriver):
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
    response = driver.execute_async_script(script)
    save_access_token(name, response)


def _fetch_cookies(name: LLM_PROVIDER, cookies: str):
    save_cookies(name, cookies)


class SeleniumRequests(metaclass=SingletonMeta):

    def __init__(self):
        self._options = uc.ChromeOptions()
        # 初始登录不需要请求头包含 bearer
        self._options.add_argument("--window-size=1920x1080")
        # self.options.add_argument('--headless=new')
        self.driver = uc.Chrome(options=self._options)
        self._wait10 = WebDriverWait(self.driver, 10)
        self._wait15 = WebDriverWait(self.driver, 15)
        self._wait20 = WebDriverWait(self.driver, 20)
        self._wait25 = WebDriverWait(self.driver, 25)
        self._wait35 = WebDriverWait(self.driver, 35)

    def _handle_cloudflare_click(self) -> Literal["login", "prompt-textarea"]:
        self._wait25.until(EC.any_of(
            EC.frame_to_be_available_and_switch_to_it((By.XPATH, '//iframe[@allow="cross-origin-isolated"]')),
            EC.element_to_be_clickable((By.XPATH, '//button/div[text()="Log in"]'))
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
        self._wait25.until(EC.any_of(EC.presence_of_element_located((By.XPATH, "//button/div[text()=\"Next\"]")),
                                     EC.presence_of_element_located((By.XPATH, '//textarea[@id="prompt-textarea"]'))
                                     ))
        if self.driver.find_elements(By.XPATH, "//button/div[text()=\"Next\"]"):
            self.driver.find_element(By.XPATH, "//button/div[text()=\"Next\"]").click()
            self.driver.find_element(By.XPATH, "//button/div[text()=\"Next\"]").click()
            self.driver.find_element(By.XPATH, "//button/div[text()=\"Done\"]").click()
            return True

        if self.driver.find_elements(By.XPATH, '//textarea[@id="prompt-textarea"]'):
            return True

    def _handle_login(self, mail: str, password: str):
        # 处理 Login
        el_button = self._wait10.until(
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

    # receive commands handler
    def _quit_drive(self):
        self.driver.quit()

    def _driver_get_index(self):
        self.driver.get("https://chat.openai.com")

    def _drive_save_cookies(self, url: str = "https://chat.openai.com"):
        self.driver.get(url)
        cookies = self.driver.get_cookies()
        _fetch_cookies("chatgpt", cookies)

    def _driver_refresh(self):
        self.driver.refresh()

    def _driver_get_conversation(self, conversation_id: str):
        self.driver.get(f"https://chat.openai.com/c/{conversation_id}")

    _send_command_mappings = {
        "get_index": _driver_get_index,
        "save_cookies": _drive_save_cookies,
        "refresh": _driver_refresh,
        "get_conversation": _driver_get_conversation,
        "quit_driver": _quit_drive
    }

    def chatgpt_login(self):
        self.driver.get('https://chat.openai.com/auth/login')

        for i in range(2):
            try:
                if self._handle_cloudflare_click() == "login":
                    break
            except (TimeoutException, NoSuchElementException, HandleCloudflareFailException) as e:
                logger.warning(f"warning a error occurred {i}", e)
        # 处理登录
        self._handle_login(EMAIL, PASSWORD)

        # 处理登录时的弹窗
        if self._handle_welcome_click():
            cookies = self.driver.get_cookies()
            _fetch_cookies("chatgpt", cookies)
            self._get_next_data()
            _fetch_access_token("chatgpt", self.driver)
        while True:
            receive = yield
            self._send_command_mappings[receive.key](**receive.args)

    def chatgpt_log_with_cookies(self):
        cookies_ = get_cookies("chatgpt")

        self.driver.get('https://chat.openai.com')
        for cookie in cookies_:
            try:
                self.driver.add_cookie(cookie)
            except Exception as e:
                logger.warning(f"failed load this cookie {cookie}\n", e)
        self.driver.get('https://chat.openai.com')
        time.sleep(3)

        # battle cloudflare
        is_get_to = False
        try:
            is_get_to = self._handle_welcome_click()
        except (TimeoutException, NoSuchElementException) as e:
            logger.warning(f"warning use cookies to login didn't handle_welcome_click", e)
            try:
                r = self._handle_cloudflare_click()
                if r == "login":
                    self._handle_login(EMAIL, PASSWORD)
                    is_get_to = self._handle_welcome_click()
                if r == "prompt-textarea":
                    is_get_to = self._handle_welcome_click()
            except (TimeoutException, NoSuchElementException) as e:
                logger.warning("error", e)
        if is_get_to:
            cookies = self.driver.get_cookies()
            _fetch_cookies("chatgpt", cookies)
            self._get_next_data()
            _fetch_access_token("chatgpt", self.driver)
            self.driver.close()
        else:
            raise UseSeleniumFailedException
        # result = None
        # while True:
        #     try:
        #         receive = yield result
        #         result = self._send_command_mappings[receive.key](**receive.args)
        #     except GeneratorExit:
        #         self.driver.close()
        #         return
