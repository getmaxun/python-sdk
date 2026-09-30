"""Work with files instead of web pages (PDF, DOCX, XLSX, CSV, JPG, PNG).

On self-hosted Maxun, documents.extract() and the "summary" format need an LLM:
pass llm_provider=... (and llm_api_key for anthropic/openai).
"""
import asyncio
import sys

from dotenv import load_dotenv
from maxun import Maxun

load_dotenv()


async def main(path: str):
    async with Maxun() as maxun:
        # Pull specific data out of the file
        robot = await maxun.documents.extract(path, "Invoice number, date, and total amount")
        result = await robot.run()
        print(result.document_data)

        # Convert the file to Markdown (formats default to markdown, html, links, summary)
        robot = await maxun.documents.parse(path, formats=["markdown"])
        result = await robot.run()
        print((result.markdown or "")[:1000])

        # Bytes work too; give a file name so the type is known
        with open(path, "rb") as f:
            await maxun.documents.parse(f.read(), file_name="copy-" + path.split("/")[-1], formats=["markdown"])


asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "invoice.pdf"))
