import hashlib
import os
from typing import List, Optional, Union

from ._naming import auto_name
from ._resource import Resource
from ._utils import load_document
from .client import DOCUMENT_PARSE_FORMATS
from .llm_options import build_llm_payload
from .robot import Robot
from .types import DocumentFormat, LLMProvider

FileInput = Union[str, os.PathLike, bytes]


class Documents(Resource):
    """Robots that read files instead of web pages: PDF, DOCX, XLSX, CSV, JPG and PNG."""

    robot_types = ("doc-extract", "doc-parse")

    async def extract(
        self,
        file: FileInput,
        prompt: str,
        name: Optional[str] = None,
        file_name: Optional[str] = None,
        llm_provider: Optional[LLMProvider] = None,
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
    ) -> Robot:
        """Create a robot that pulls the data described by ``prompt`` out of a file.

        :param file: A path, or the file's bytes (then pass ``file_name`` so the
            type can be detected, e.g. ``"invoice.pdf"``).
        :param name: Robot name. Defaults to one made from the file and prompt, so
            sending the same file and prompt again returns the same robot.
        :param llm_*: Self-hosted Maxun only (required there). Leave unset on Maxun Cloud.
        """
        if not prompt or not prompt.strip():
            raise ValueError("prompt is required")
        file_name, data, _ = load_document(file, file_name)
        llm = build_llm_payload(llm_provider, llm_model, llm_api_key, llm_base_url)
        settings = {"type": "doc-extract", "file": hashlib.sha1(data).hexdigest(), "prompt": prompt.strip(), **llm}

        async def create(robot_name: str) -> Robot:
            body = await self.client.create_document_extract_robot(
                data, prompt, robot_name=robot_name, llm_provider=llm_provider, llm_model=llm_model,
                llm_api_key=llm_api_key, llm_base_url=llm_base_url, file_name=file_name,
            )
            return Robot(self.client, body["data"])

        return await self._create_reusing(name, auto_name("Document", file_name, settings), create)

    async def parse(
        self,
        file: FileInput,
        formats: Optional[List[DocumentFormat]] = None,
        name: Optional[str] = None,
        file_name: Optional[str] = None,
        llm_provider: Optional[LLMProvider] = None,
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
    ) -> Robot:
        """Create a robot that converts a file to markdown, html, links and/or a summary.

        :param formats: Any of markdown, html, links, summary. Defaults to all four.
        :param llm_*: Self-hosted Maxun only, needed for ``summary``.
        """
        file_name, data, _ = load_document(file, file_name)
        llm = build_llm_payload(llm_provider, llm_model, llm_api_key, llm_base_url)
        settings = {
            "type": "doc-parse",
            "file": hashlib.sha1(data).hexdigest(),
            "formats": sorted(formats or DOCUMENT_PARSE_FORMATS),
            **llm,
        }

        async def create(robot_name: str) -> Robot:
            body = await self.client.create_document_parse_robot(
                data, formats, robot_name=robot_name, file_name=file_name, llm_provider=llm_provider,
                llm_model=llm_model, llm_api_key=llm_api_key, llm_base_url=llm_base_url,
            )
            return Robot(self.client, body["data"])

        return await self._create_reusing(name, auto_name("Parse", file_name, settings), create)


__all__ = ["Documents", "DOCUMENT_PARSE_FORMATS"]
