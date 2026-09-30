"""Type into a form, click, wait and take screenshots."""
import asyncio

from dotenv import load_dotenv
from maxun import Maxun

load_dotenv()


async def main():
    async with Maxun() as maxun:
        robot = await (
            maxun.extract.create("Form Fill Demo")
            .navigate("https://practice.expandtesting.com/inputs")
            .type("#input-text", "John Doe")
            .type("#input-number", "42")
            .type("#input-password", "SecurePassword123", input_type="password")
            .wait(500)
            .capture_screenshot("Full page")
            .capture_screenshot("Viewport", full_page=False)
            .build()
        )
        result = await robot.run()
        for shot in result.screenshots:
            print(shot if isinstance(shot, str) else list(shot))


asyncio.run(main())
