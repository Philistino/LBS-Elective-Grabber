import functools
import logging
import smtplib
import ssl
import time
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from random import randrange

import toml
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

config = toml.load(Path(Path(__file__).parent, "config.toml"))


def get_logger(*, name: str, file_name: str, log_level):
    """creates logger instance with log file in same directory
    Args:
        name: name of logger
        file_name: name of file to log messages
        log_level: log level of logger
    Returns:
        logging object
    """
    logs_dir = Path(Path(__file__).parent, "logs")
    if not logs_dir.exists():
        logs_dir.mkdir()
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    fh = TimedRotatingFileHandler(
        Path(logs_dir, file_name), when="midnight", encoding="utf-8", backupCount=30
    )
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-5s - %(name)-15s - %(funcName)-20s - %(message)s"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


log = get_logger(
    name="lbs_elective_grabber",
    file_name="lbs_elective_log",
    log_level=logging.DEBUG,
)


class GmailEmailer:
    """Object to send emails via Gmail account. Account must allow access by less secure apps in settings"""

    def __init__(
        self, sender_email: str, sender_password: str, notification_send_to_email: str
    ):
        """creates email sending object
        Args:
            sender_email: email account that will send the email
            sender_password: password to sender_email
            notification_send_to_email: address to send messages to
        """
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.notification_send_to_email = notification_send_to_email

    def send_email(self, *, subject: str, message_content: str) -> None:
        """sends emails via gmail
        Args:
            subject: subject of email message
            message_content: body of email message
        Returns:
            None
        """
        port = 465
        smtp_server = "smtp.gmail.com"
        message = f"Subject: {subject}\n\n{message_content}."

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, self.notification_send_to_email, message)


def get_driver(*, local: bool = False, headless: bool = False) -> webdriver:
    """returns chrome webdriver to run chrome in a docker container
    Args:
        local: use locally saved webdriver executable
        headless: run webdriver headless
    Returns:
        selenium chromedriver
    """
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--window-size=1600, 2000")
    if headless:
        chrome_options.add_argument("--headless")
    if local:
        driver = webdriver.Chrome(
            config["local_path_to_webdriver"], options=chrome_options
        )
    else:
        driver = webdriver.Remote(
            config["url_to_webdriver"],
            DesiredCapabilities.CHROME,
            options=chrome_options,
        )
    driver.implicitly_wait(10)
    return driver


def retry(
    try_count: int = 3, delay: int = 5, additional_allowed_exceptions: tuple = ()
):
    """decorator for retrying functions that may fail with an exception a certain number of times
    Note that functions that use this decorator will typically return True if the function completed w/o exception, not the value returned by the function.
        If the returned value of the function is truthy, one can return the value instead of True in the try section.
    Args:
        try_count: number of times to try the function
        delay: number of seconds to delay between retries
        additional_allowed_exceptions: exceptions not accounted for in decorated function that will be ignored and will allow a retry
    Returns:
        @retry decorator"""

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            for _ in range(try_count):
                try:
                    result = f(*args, **kwargs)
                    if result:
                        return result
                except additional_allowed_exceptions:
                    log.exception("Allowable exception occurred: ")
                time.sleep(delay)

        return wrapper

    return decorator


@retry(try_count=5, delay=1)
def wait_util_shortlist_loaded(driver: webdriver) -> bool:
    """explicit wait for shortlist element to load"""
    try:
        WebDriverWait(driver, 360).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//*[@id='short-list-details-table-body']")
            )
        )
        return True
    except:
        driver.refresh()
        log.exception("Failed to load shortlist element")
        return False


@retry(try_count=3, delay=5)
def click_element(driver: webdriver, actions: ActionChains, element) -> bool:
    """tries to click element and scrolls to click element if it is covered"""
    try:
        actions.move_to_element(element).perform()
        element = WebDriverWait(driver, 10, poll_frequency=0.2).until(
            EC.visibility_of(element)
        )
        element = WebDriverWait(driver, 10, poll_frequency=0.2).until(
            EC.element_to_be_clickable(element)
        )
        element.click()
        log.info("Clicked add button successfully")
        return True
    except:
        log.exception("Exception while clicking button")
        for _ in randrange(3, 10):
            actions.send_keys(Keys.DOWN).perform()
            time.sleep(0.3)
        return False


def login(driver: webdriver, username: str, password: str) -> None:
    """logs in via microsoft single sign on"""
    try:
        email_box = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "i0116"))
        )
        email_box.send_keys(username)
        email_box.send_keys(Keys.RETURN)
        pass_box = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "i0118"))
        )
        pass_box.send_keys(password)
        pass_box.send_keys(Keys.RETURN)
    except:
        log.exception("Could not login")
    else:
        log.debug("Login successful")


def find_and_add_courses(
    driver: webdriver, actions: ActionChains, emailer: GmailEmailer, refresh_interval
) -> None:
    """scrolls to and clicks on course add buttons in shortlist if they are available"""
    wait_util_shortlist_loaded(driver)
    add_buttons = driver.find_elements(By.CLASS_NAME, "add-course-stream-button")
    for button in add_buttons:
        actions.move_to_element(button).perform()
        button = WebDriverWait(driver, 10, poll_frequency=0.2).until(
            EC.visibility_of(button)
        )
        addable = button.get_attribute("onclick")
        if addable:
            log.info(f"Found addable course: {addable}")
            emailer.send_email(
                subject="COURSE FOUND - ELECTIVES SCRAPER",
                message_content=f"Found addable course: {addable}",
            )
            result = click_element(driver, actions, button)
            if result:
                log.info(f"Added course: {addable}")
                emailer.send_email(
                    subject="COURSE ADDED - ELECTIVES SCRAPER",
                    message_content=f"Added course: {addable}",
                )
    time.sleep(refresh_interval)


def main():
    emailer = GmailEmailer(
        config["notification_sender_email"],
        config["notification_sender_password"],
        config["notification_send_to_email"],
    )
    log.info("Starting scraper")
    driver = get_driver()
    actions = ActionChains(driver)
    try:
        driver.get("https://ebs.london.edu/ShortList")
        login(driver, config["lbs_email_address"], config["lbs_password"])
        driver.maximize_window()
        while True:
            find_and_add_courses(
                driver, actions, emailer, max(10, config["page_refresh_interval"])
            )
            driver.refresh()
    except Exception as e:
        log.exception("Exception:")
        emailer.send_email(
            subject="Fatal exception - ELECTIVES SCRAPER",
            message_content=f"Scraper stopped with exception:\n{e}",
        )
    finally:
        driver.close()
        log.info("Stopping script")


if __name__ == "__main__":
    main()
