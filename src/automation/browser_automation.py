#!/usr/bin/env python3
"""
ALPHA OMEGA - BROWSER AUTOMATION SUITE
Full Puppeteer/Playwright-style browser automation
Version: 2.0.0
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import re


class BrowserAction(Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    EXTRACT = "extract"
    FILL = "fill"
    SELECT = "select"
    HOVER = "hover"
    PRESS = "press"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    EVALUATE = "evaluate"
    COOKIE = "cookie"
    TAB = "tab"
    CLOSE = "close"


@dataclass
class BrowserConfig:
    headless: bool = True
    timeout: int = 30000
    wait_after_load: int = 1000
    user_agent: str = ""
    viewport: Dict[str, int] = field(
        default_factory=lambda: {"width": 1920, "height": 1080}
    )
    cookies: List[Dict[str, Any]] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    proxy: str = ""
    disable_images: bool = False
    disable_css: bool = False


@dataclass
class ElementSelector:
    css: str = ""
    xpath: str = ""
    text: str = ""
    role: str = ""
    placeholder: str = ""
    name: str = ""
    id: str = ""
    class_name: str = ""
    tag: str = ""
    href: str = ""
    aria_label: str = ""
    data_attributes: Dict[str, str] = field(default_factory=dict)

    def to_playwright_selector(self) -> str:
        if self.css:
            return self.css
        elif self.xpath:
            return f"xpath={self.xpath}"
        elif self.text:
            return f"text={self.text}"
        elif self.role:
            return f"role={self.role}"
        elif self.placeholder:
            return f"[placeholder='{self.placeholder}']"
        elif self.name:
            return f"[name='{self.name}']"
        elif self.id:
            return f"#{self.id}"
        elif self.class_name:
            return f".{self.class_name}"
        elif self.href:
            return f"[href='{self.href}']"
        elif self.aria_label:
            return f"[aria-label='{self.aria_label}']"
        return "*"

    def to_selenium_selector(self) -> tuple:
        if self.css:
            return ("css selector", self.css)
        elif self.xpath:
            return ("xpath", self.xpath)
        elif self.id:
            return ("id", self.id)
        elif self.class_name:
            return ("class name", self.class_name)
        elif self.name:
            return ("name", self.name)
        elif self.tag:
            return ("tag name", self.tag)
        elif self.href:
            return ("css selector", f"[href='{self.href}']")
        elif self.placeholder:
            return ("css selector", f"[placeholder='{self.placeholder}']")
        return ("css selector", "*")


@dataclass
class BrowserResult:
    success: bool
    action: str
    data: Any = None
    error: str = ""
    screenshot: bytes = b""
    url: str = ""
    title: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class WebForm:
    url: str
    fields: Dict[str, str]
    submit_selector: str = ""
    wait_for: str = ""


@dataclass
class ScrapedData:
    url: str
    title: str
    text: str
    html: str
    links: List[str]
    images: List[str]
    structured_data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


class BrowserAutomation:
    """Browser automation with multiple backend support"""

    def __init__(self, config: BrowserConfig = None):
        self.config = config or BrowserConfig()
        self.logger = logging.getLogger("BrowserAutomation")

        self._browser = None
        self._page = None
        self._context = None
        self._backend = "none"
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize browser backend"""
        self.logger.info("Initializing Browser Automation...")

        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.config.headless
            )
            self._context = await self._browser.new_context(
                viewport=self.config.viewport,
                user_agent=self.config.user_agent or None,
            )
            self._page = await self._context.new_page()
            self._backend = "playwright"
            self._initialized = True
            self.logger.info("Playwright browser initialized")
            return True
        except ImportError:
            self.logger.debug("Playwright not available")

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options

            options = Options()
            if self.config.headless:
                options.add_argument("--headless")
            options.add_argument(
                f"--window-size={self.config.viewport['width']},{self.config.viewport['height']}"
            )

            self._browser = webdriver.Chrome(options=options)
            self._backend = "selenium"
            self._initialized = True
            self.logger.info("Selenium browser initialized")
            return True
        except ImportError:
            self.logger.debug("Selenium not available")

        self._backend = "requests"
        self._initialized = True
        self.logger.info("Using requests fallback")
        return True

    async def close(self):
        """Close browser"""
        if self._backend == "playwright" and self._browser:
            await self._browser.close()
            await self._playwright.stop()
        elif self._backend == "selenium" and self._browser:
            self._browser.quit()

        self._initialized = False
        self.logger.info("Browser closed")

    async def navigate(self, url: str, wait_until: str = "load") -> BrowserResult:
        """Navigate to URL"""
        if not self._initialized:
            await self.initialize()

        try:
            if self._backend == "playwright":
                await self._page.goto(
                    url, wait_until=wait_until, timeout=self.config.timeout
                )
                await self._page.wait_for_timeout(self.config.wait_after_load)
                return BrowserResult(
                    success=True,
                    action="navigate",
                    url=self._page.url,
                    title=await self._page.title(),
                )

            elif self._backend == "selenium":
                self._browser.get(url)
                time.sleep(self.config.wait_after_load / 1000)
                return BrowserResult(
                    success=True,
                    action="navigate",
                    url=self._browser.current_url,
                    title=self._browser.title,
                )

            elif self._backend == "requests":
                import requests

                response = requests.get(url, timeout=self.config.timeout / 1000)
                return BrowserResult(
                    success=response.status_code == 200,
                    action="navigate",
                    url=url,
                    data=response.text,
                )

        except Exception as e:
            return BrowserResult(success=False, action="navigate", error=str(e))

    async def click(
        self, selector: ElementSelector, timeout: int = 5000
    ) -> BrowserResult:
        """Click element"""
        try:
            if self._backend == "playwright":
                sel = selector.to_playwright_selector()
                await self._page.click(sel, timeout=timeout)
                return BrowserResult(success=True, action="click")

            elif self._backend == "selenium":
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC

                by, value = selector.to_selenium_selector()
                element = WebDriverWait(self._browser, timeout / 1000).until(
                    EC.element_to_be_clickable((by, value))
                )
                element.click()
                return BrowserResult(success=True, action="click")

        except Exception as e:
            return BrowserResult(success=False, action="click", error=str(e))

    async def type_text(
        self,
        selector: ElementSelector,
        text: str,
        delay: int = 50,
        clear_first: bool = True,
    ) -> BrowserResult:
        """Type text into element"""
        try:
            if self._backend == "playwright":
                sel = selector.to_playwright_selector()
                if clear_first:
                    await self._page.fill(sel, "")
                await self._page.type(sel, text, delay=delay)
                return BrowserResult(success=True, action="type")

            elif self._backend == "selenium":
                from selenium.webdriver.common.by import By
                from selenium.webdriver.common.keys import Keys

                by, value = selector.to_selenium_selector()
                element = self._browser.find_element(by, value)
                if clear_first:
                    element.clear()
                element.send_keys(text)
                return BrowserResult(success=True, action="type")

        except Exception as e:
            return BrowserResult(success=False, action="type", error=str(e))

    async def fill_form(self, form: WebForm) -> BrowserResult:
        """Fill a web form"""
        results = []

        for field_name, field_value in form.fields.items():
            selector = ElementSelector(name=field_name)
            result = await self.type_text(selector, field_value)
            results.append((field_name, result.success))

        if form.submit_selector:
            submit_sel = ElementSelector(css=form.submit_selector)
            await self.click(submit_sel)

        if form.wait_for:
            await self.wait_for_selector(ElementSelector(css=form.wait_for))

        success = all(r[1] for r in results)
        return BrowserResult(
            success=success,
            action="fill_form",
            data={"fields": results},
        )

    async def wait_for_selector(
        self,
        selector: ElementSelector,
        timeout: int = 30000,
    ) -> BrowserResult:
        """Wait for element to appear"""
        try:
            if self._backend == "playwright":
                sel = selector.to_playwright_selector()
                await self._page.wait_for_selector(sel, timeout=timeout)
                return BrowserResult(success=True, action="wait")

            elif self._backend == "selenium":
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC

                by, value = selector.to_selenium_selector()
                WebDriverWait(self._browser, timeout / 1000).until(
                    EC.presence_of_element_located((by, value))
                )
                return BrowserResult(success=True, action="wait")

        except Exception as e:
            return BrowserResult(success=False, action="wait", error=str(e))

    async def wait_for_navigation(self, timeout: int = 30000) -> BrowserResult:
        """Wait for page navigation"""
        try:
            if self._backend == "playwright":
                await self._page.wait_for_load_state("networkidle", timeout=timeout)
                return BrowserResult(success=True, action="wait_navigation")

            elif self._backend == "selenium":
                time.sleep(2)
                return BrowserResult(success=True, action="wait_navigation")

        except Exception as e:
            return BrowserResult(success=False, action="wait_navigation", error=str(e))

    async def extract_text(self, selector: ElementSelector = None) -> BrowserResult:
        """Extract text from page or element"""
        try:
            if self._backend == "playwright":
                if selector:
                    sel = selector.to_playwright_selector()
                    text = await self._page.locator(sel).text_content()
                else:
                    text = await self._page.content()
                return BrowserResult(success=True, action="extract", data=text)

            elif self._backend == "selenium":
                from selenium.webdriver.common.by import By

                if selector:
                    by, value = selector.to_selenium_selector()
                    element = self._browser.find_element(by, value)
                    text = element.text
                else:
                    text = self._browser.page_source
                return BrowserResult(success=True, action="extract", data=text)

        except Exception as e:
            return BrowserResult(success=False, action="extract", error=str(e))

    async def extract_links(self, base_url: str = "") -> BrowserResult:
        """Extract all links from page"""
        try:
            if self._backend == "playwright":
                links = await self._page.evaluate("""
                    Array.from(document.querySelectorAll('a[href]')).map(a => ({
                        href: a.href,
                        text: a.textContent.trim()
                    }))
                """)
                return BrowserResult(success=True, action="extract_links", data=links)

            elif self._backend == "selenium":
                from selenium.webdriver.common.by import By

                elements = self._browser.find_elements(By.TAG_NAME, "a")
                links = [
                    {"href": e.get_attribute("href"), "text": e.text} for e in elements
                ]
                return BrowserResult(success=True, action="extract_links", data=links)

        except Exception as e:
            return BrowserResult(success=False, action="extract_links", error=str(e))

    async def scrape_page(self, url: str = None) -> ScrapedData:
        """Scrape full page data"""
        if url:
            await self.navigate(url)

        title = ""
        text = ""
        html = ""
        links = []
        images = []

        try:
            if self._backend == "playwright":
                title = await self._page.title()
                html = await self._page.content()

                text = await self._page.evaluate("""
                    document.body.innerText
                """)

                links = await self._page.evaluate("""
                    Array.from(document.querySelectorAll('a[href]')).map(a => a.href)
                """)

                images = await self._page.evaluate("""
                    Array.from(document.querySelectorAll('img[src]')).map(img => img.src)
                """)

        except Exception as e:
            self.logger.error(f"Scrape error: {e}")

        return ScrapedData(
            url=self._page.url if self._backend == "playwright" else url or "",
            title=title,
            text=text,
            html=html,
            links=links,
            images=images,
            structured_data={},
        )

    async def screenshot(self, full_page: bool = False) -> BrowserResult:
        """Take screenshot"""
        try:
            if self._backend == "playwright":
                screenshot_bytes = await self._page.screenshot(full_page=full_page)
                return BrowserResult(
                    success=True,
                    action="screenshot",
                    screenshot=screenshot_bytes,
                )

            elif self._backend == "selenium":
                screenshot_bytes = self._browser.get_screenshot_as_png()
                return BrowserResult(
                    success=True,
                    action="screenshot",
                    screenshot=screenshot_bytes,
                )

        except Exception as e:
            return BrowserResult(success=False, action="screenshot", error=str(e))

    async def execute_script(self, script: str) -> BrowserResult:
        """Execute JavaScript"""
        try:
            if self._backend == "playwright":
                result = await self._page.evaluate(script)
                return BrowserResult(success=True, action="execute", data=result)

            elif self._backend == "selenium":
                result = self._browser.execute_script(script)
                return BrowserResult(success=True, action="execute", data=result)

        except Exception as e:
            return BrowserResult(success=False, action="execute", error=str(e))

    async def set_cookies(self, cookies: List[Dict[str, Any]]):
        """Set cookies"""
        if self._backend == "playwright" and self._context:
            await self._context.add_cookies(cookies)

    async def get_cookies(self) -> List[Dict[str, Any]]:
        """Get all cookies"""
        if self._backend == "playwright" and self._context:
            return await self._context.cookies()
        return []

    async def new_tab(self, url: str = "") -> BrowserResult:
        """Open new tab"""
        try:
            if self._backend == "playwright":
                page = await self._context.new_page()
                if url:
                    await page.goto(url)
                return BrowserResult(success=True, action="tab")
        except Exception as e:
            return BrowserResult(success=False, action="tab", error=str(e))

    async def scroll(self, direction: str = "down", amount: int = 500) -> BrowserResult:
        """Scroll page"""
        try:
            if self._backend == "playwright":
                if direction == "down":
                    await self._page.mouse.wheel(0, amount)
                else:
                    await self._page.mouse.wheel(0, -amount)
                return BrowserResult(success=True, action="scroll")

            elif self._backend == "selenium":
                self._browser.execute_script(
                    f"window.scrollBy(0, {amount if direction == 'down' else -amount});"
                )
                return BrowserResult(success=True, action="scroll")

        except Exception as e:
            return BrowserResult(success=False, action="scroll", error=str(e))

    async def auto_login(
        self,
        login_url: str,
        username: str,
        password: str,
        username_selector: str = "input[name='username'], input[type='email'], #email",
        password_selector: str = "input[name='password'], input[type='password'], #password",
        submit_selector: str = "button[type='submit'], input[type='submit']",
    ) -> BrowserResult:
        """Automated login"""
        result = await self.navigate(login_url)
        if not result.success:
            return result

        await self.type_text(ElementSelector(css=username_selector), username)
        await self.type_text(ElementSelector(css=password_selector), password)
        await self.click(ElementSelector(css=submit_selector))

        await self.wait_for_navigation()

        return BrowserResult(
            success=True,
            action="login",
            url=self._page.url if self._backend == "playwright" else "",
        )

    def get_info(self) -> Dict[str, Any]:
        """Get browser info"""
        return {
            "backend": self._backend,
            "initialized": self._initialized,
            "headless": self.config.headless,
        }
