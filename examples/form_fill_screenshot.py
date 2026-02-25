"""
Form Filling and Screenshots Example

This example demonstrates:
- Filling form inputs with type() action
- Automatic input type detection
- Taking full-page and viewport screenshots
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from maxun import Extract, Config


async def main():
    extractor = Extract(Config(
        api_key=os.environ["MAXUN_API_KEY"],
        base_url=os.environ.get("MAXUN_BASE_URL", "https://app.maxun.dev/"),
    ))

    robot = await (
        extractor
        .create("Form Fill Demo")
        .navigate("https://practice.expandtesting.com/inputs")
        .type("#input-text", "John Doe")
        .type("#input-number", "42")
        .type("#input-password", "SecurePassword123")
        .type("#input-date", "15-08-2024")
        .capture_screenshot("Full Page", {"fullPage": True})
        .capture_screenshot("Viewport", {"fullPage": False})
    )

    print(f"Robot created: {robot.id}")

    result = await robot.run()

    binary_output = result.get("data", {}).get("binaryOutput") or {}
    print("\nForm filling completed")
    print(f"Screenshots captured: {len(binary_output)}")


load_dotenv()

if not os.environ.get("MAXUN_API_KEY"):
    print("Error: MAXUN_API_KEY environment variable is required", file=sys.stderr)
    sys.exit(1)

asyncio.run(main())
