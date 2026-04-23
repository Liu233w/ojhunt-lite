import pytest
from playwright.sync_api import Page, expect

from e2e.helpers import BASE_URL

DISCORD_INVITE_URL = "https://discord.gg/9BsnDaHpTU"
DISCORD_SERVER_NAME = "OJ Analyzer Development"


@pytest.mark.playwright
def test_about_page_loads(page: Page):
    page.goto(f"{BASE_URL}/about")
    expect(page).to_have_title("About - OJHunt Lite")


@pytest.mark.playwright
def test_about_discord_link(page: Page):
    page.goto(f"{BASE_URL}/about")
    discord_link = page.locator('a[href*="discord.gg"]')
    expect(discord_link).to_be_visible()
    assert discord_link.get_attribute("href") == DISCORD_INVITE_URL


@pytest.mark.playwright
def test_about_discord_link_resolves(page: Page):
    page.goto(DISCORD_INVITE_URL)
    expect(page.locator("h1", has_text=DISCORD_SERVER_NAME)).to_be_visible()
