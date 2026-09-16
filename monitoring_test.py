import asyncio
import os

from dotenv import load_dotenv
from maxun import Config, Scrape

load_dotenv()


async def main():
    api_key = os.environ.get("MAXUN_API_KEY")
    base_url = os.environ.get(
        "MAXUN_BASE_URL",
        "http://localhost:8080/api/sdk",
    )

    if not api_key:
        raise RuntimeError("MAXUN_API_KEY is required")

    scrape = Scrape(
        Config(
            api_key=api_key,
            base_url=base_url,
        )
    )

    try:
        robot = await scrape.create(
            name="Python SDK Monitoring Test",
            url="https://www.worldometers.info/world-population/",
            formats=["text", "markdown", "html"],
            monitor=True,
        )

        print(f"Robot created: {robot.id}")

        print("\nRunning baseline capture...")
        baseline = await robot.run()

        print(
            {
                "runId": baseline.get("runId"),
                "hasChanges": baseline.get("hasChanges"),
                "changedFormats": baseline.get("changedFormats"),
            }
        )

        print("\nRunning comparison capture...")
        current = await robot.run()

        print(
            {
                "runId": current.get("runId"),
                "hasChanges": current.get("hasChanges"),
                "changedFormats": current.get("changedFormats"),
            }
        )

        comparison = await robot.get_run_diff(current["runId"])

        print(
            "\nComparison:",
            {
                "previousRunId": comparison.get("previousRunId"),
                "currentRunId": comparison.get("runId"),
                "hasChanges": comparison.get("hasChanges"),
                "changedFormats": comparison.get("changedFormats"),
            },
        )

        for format_diff in comparison.get("diffs", []):
            print(f"\n--- {format_diff['format']} ---")

            printed = 0

            for change in format_diff.get("changes", []):
                if not change.get("added") and not change.get("removed"):
                    continue

                prefix = "+" if change.get("added") else "-"
                value = change.get("value", "")

                # Keep terminal output manageable, especially for HTML.
                print(f"{prefix} {value[:1000]}")
                printed += 1

                if printed >= 20:
                    print("... remaining changes omitted")
                    break

    finally:
        await scrape.client.client.aclose()


if __name__ == "__main__":
    asyncio.run(main())