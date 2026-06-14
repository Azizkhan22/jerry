import os
from typing import Literal

from langchain_core.tools import tool
from playwright.sync_api import sync_playwright

import config

# ======================================================================
# CUSTOMIZE THESE SELECTORS for your specific attendance portal.
#
# How to find them: open the portal in Chrome -> right-click the
# username field / password field / login button / check-in / check-out
# buttons -> "Inspect" -> copy a usable selector (id, name, or text).
#
# Quick tips:
#   - input[name='username']        -> matches <input name="username">
#   - input[id='loginUser']         -> matches <input id="loginUser">
#   - text=Check In                 -> matches a button/link whose text
#                                       is exactly "Check In"
#
# Set DEBUG_HEADFUL = True the first time and run mark_attendance once -
# a real browser window will open so you can watch it and confirm the
# selectors are correct.
# ======================================================================

LOGIN_USERNAME_SELECTOR = "input[name='username']"
LOGIN_PASSWORD_SELECTOR = "input[name='password']"
LOGIN_SUBMIT_SELECTOR = "button[type='submit']"

# If attendance controls live on a different page after login, set its
# full URL here. Leave empty if they're on the page you land on after login.
ATTENDANCE_PAGE_URL = ""

CHECK_IN_SELECTOR = "text=Check In"
CHECK_OUT_SELECTOR = "text=Check Out"

DEBUG_HEADFUL = False


@tool
def mark_attendance(action: Literal["in", "out"]) -> str:
    """Mark attendance on the internship portal. Use action='in' to check
    in (mark arrival) or action='out' to check out (mark departure). Only
    call this when the user explicitly asks to mark attendance right now -
    never on your own initiative."""
    if not all([config.ATTENDANCE_PORTAL_URL, config.ATTENDANCE_USERNAME, config.ATTENDANCE_PASSWORD]):
        return "Error: attendance portal credentials are not set in .env"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not DEBUG_HEADFUL)
        page = browser.new_page()
        try:
            page.goto(config.ATTENDANCE_PORTAL_URL, wait_until="networkidle")

            page.fill(LOGIN_USERNAME_SELECTOR, config.ATTENDANCE_USERNAME)
            page.fill(LOGIN_PASSWORD_SELECTOR, config.ATTENDANCE_PASSWORD)
            page.click(LOGIN_SUBMIT_SELECTOR)
            page.wait_for_load_state("networkidle")

            if ATTENDANCE_PAGE_URL:
                page.goto(ATTENDANCE_PAGE_URL, wait_until="networkidle")

            selector = CHECK_IN_SELECTOR if action == "in" else CHECK_OUT_SELECTOR
            page.click(selector)
            page.wait_for_load_state("networkidle")

            return f"Attendance marked as '{action}' successfully."

        except Exception as e:
            os.makedirs(config.DATA_DIR, exist_ok=True)
            screenshot_path = os.path.join(config.DATA_DIR, "attendance_error.png")
            page.screenshot(path=screenshot_path)
            return (
                f"Failed to mark attendance ('{action}'): {e}\n"
                f"A screenshot was saved to {screenshot_path} - use it to fix "
                f"the selectors at the top of tools/attendance_tools.py."
            )
        finally:
            browser.close()
