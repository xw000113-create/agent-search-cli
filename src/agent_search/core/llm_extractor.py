"""
LLM Integration for AI-Powered Extraction

Extract structured data from web content using LLMs.
Supports multiple LLM providers via LiteLLM interface.

Usage:
    from agent_search.core.llm_extractor import LLMExtractor, LLMConfig
    from pydantic import BaseModel

    class Product(BaseModel):
        name: str
        price: float
        description: str

    config = LLMConfig(
        provider="openai/gpt-4o-mini",
        api_key="sk-..."
    )

    extractor = LLMExtractor(config)
    products = await extractor.extract(html, Product)
"""

import json
import re
from typing import Optional, Dict, Any, List, Type, Union
from dataclasses import dataclass, field

try:
    from pydantic import BaseModel, ValidationError

    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False


@dataclass
class LLMConfig:
    """Configuration for LLM extraction."""

    provider: str = "openai/gpt-4o-mini"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 2000
    top_p: float = 1.0

    # Retry settings
    max_retries: int = 3
    backoff_base_delay: float = 1.0
    backoff_max_delay: float = 60.0
    backoff_exponential_factor: float = 2.0


class LLMExtractor:
    """
    Extract structured data using LLMs.

    Supports OpenAI, Anthropic, Groq, Ollama, and more via LiteLLM.
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._client = None

    def _get_client(self):
        """Get or create LLM client."""
        if self._client is None:
            try:
                import openai

                self._client = openai.AsyncOpenAI(
                    api_key=self.config.api_key, base_url=self.config.base_url
                )
            except ImportError:
                raise ImportError("OpenAI SDK required. Install: pip install openai")
        return self._client

    async def extract(
        self,
        content: str,
        schema: Type[BaseModel],
        instruction: Optional[str] = None,
        input_format: str = "markdown",
    ) -> List[BaseModel]:
        """
        Extract structured data from content using LLM.

        Args:
            content: Content to extract from (HTML or Markdown)
            schema: Pydantic model defining the structure
            instruction: Additional instructions for extraction
            input_format: Format of input content (html, markdown, fit_markdown)

        Returns:
            List of extracted items as Pydantic model instances
        """
        if not HAS_PYDANTIC:
            raise ImportError("Pydantic required for schema extraction")

        # Prepare system prompt
        system_prompt = self._build_system_prompt(schema, instruction)

        # Truncate content if too long
        content = self._truncate_content(content, max_tokens=4000)

        # Build user prompt
        user_prompt = self._build_user_prompt(content, schema, input_format)

        # Call LLM with retry
        for attempt in range(self.config.max_retries):
            try:
                client = self._get_client()

                response = await client.chat.completions.create(
                    model=self.config.provider.replace("openai/", ""),
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    top_p=self.config.top_p,
                    response_format={"type": "json_object"},
                )

                # Parse response
                content_text = response.choices[0].message.content
                data = json.loads(content_text)

                # Handle different response structures
                if "items" in data:
                    items = data["items"]
                elif "data" in data:
                    items = data["data"]
                elif isinstance(data, list):
                    items = data
                else:
                    items = [data]

                # Validate with Pydantic
                results = []
                for item in items:
                    try:
                        results.append(schema(**item))
                    except ValidationError:
                        continue

                return results

            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    raise

                # Exponential backoff
                delay = min(
                    self.config.backoff_base_delay
                    * (self.config.backoff_exponential_factor**attempt),
                    self.config.backoff_max_delay,
                )
                import asyncio

                await asyncio.sleep(delay)

        return []

    def _build_system_prompt(
        self, schema: Type[BaseModel], instruction: Optional[str]
    ) -> str:
        """Build system prompt for extraction."""
        schema_json = json.dumps(schema.model_json_schema(), indent=2)

        prompt = f"""You are a data extraction specialist. Extract structured data from the provided content according to the JSON schema below.

Schema:
{schema_json}

Instructions:
1. Extract all items matching the schema from the content
2. Return a JSON object with an "items" array containing the extracted data
3. If no items match, return {{"items": []}}
4. Ensure all required fields are present
5. Use null for optional fields that are not present
"""

        if instruction:
            prompt += f"\n\nAdditional instructions: {instruction}"

        return prompt

    def _build_user_prompt(
        self, content: str, schema: Type[BaseModel], input_format: str
    ) -> str:
        """Build user prompt with content."""
        prompt = f"Extract data from this {input_format} content:\n\n"
        prompt += f"```{input_format}\n{content}\n```"
        return prompt

    def _truncate_content(self, content: str, max_tokens: int = 4000) -> str:
        """Truncate content to fit within token limit."""
        # Rough estimate: 1 token ≈ 4 characters
        max_chars = max_tokens * 4

        if len(content) > max_chars:
            # Try to truncate at a sentence boundary
            truncated = content[:max_chars]
            last_period = truncated.rfind(".")
            if last_period > max_chars * 0.8:
                truncated = truncated[: last_period + 1]

            return truncated + "\n\n[Content truncated...]"

        return content


class TableExtractionStrategy:
    """
    Extract tables using LLM with intelligent chunking.
    Similar to Crawl4AI's LLMTableExtraction.
    """

    def __init__(
        self,
        llm_config: Optional[LLMConfig] = None,
        enable_chunking: bool = True,
        chunk_token_threshold: int = 4000,
        overlap_threshold: int = 200,
    ):
        self.llm_config = llm_config or LLMConfig()
        self.enable_chunking = enable_chunking
        self.chunk_token_threshold = chunk_token_threshold
        self.overlap_threshold = overlap_threshold

    async def extract(
        self, content: str, instruction: str = "Extract all tables from this content"
    ) -> List[Dict[str, Any]]:
        """
        Extract tables from content.

        Args:
            content: HTML or Markdown content
            instruction: Instructions for extraction

        Returns:
            List of tables with headers and rows
        """
        from .html_to_markdown import HTMLToMarkdown

        # Convert to markdown if HTML
        if content.strip().startswith("<"):
            converter = HTMLToMarkdown()
            content = converter.convert(content)

        # Chunk if needed
        if self.enable_chunking and len(content) > self.chunk_token_threshold * 4:
            chunks = self._chunk_content(content)
            all_tables = []
            for chunk in chunks:
                tables = await self._extract_from_chunk(chunk, instruction)
                all_tables.extend(tables)
            return self._merge_tables(all_tables)
        else:
            return await self._extract_from_chunk(content, instruction)

    def _chunk_content(self, content: str) -> List[str]:
        """Split content into overlapping chunks."""
        chunks = []
        chunk_size = self.chunk_token_threshold * 4
        overlap = self.overlap_threshold * 4

        start = 0
        while start < len(content):
            end = start + chunk_size
            chunk = content[start:end]
            chunks.append(chunk)
            start = end - overlap

        return chunks

    async def _extract_from_chunk(
        self, content: str, instruction: str
    ) -> List[Dict[str, Any]]:
        """Extract tables from a single chunk."""
        extractor = LLMExtractor(self.llm_config)

        class TableSchema(BaseModel):
            headers: List[str]
            rows: List[List[str]]
            caption: Optional[str] = None

        tables = await extractor.extract(
            content, TableSchema, instruction=instruction, input_format="markdown"
        )

        return [
            {"headers": table.headers, "rows": table.rows, "caption": table.caption}
            for table in tables
        ]

    def _merge_tables(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge tables from multiple chunks."""
        # Group tables by caption or header similarity
        merged = []
        seen_headers = set()

        for table in tables:
            header_key = tuple(table.get("headers", []))
            if header_key not in seen_headers:
                seen_headers.add(header_key)
                merged.append(table)
            else:
                # Merge rows into existing table
                for existing in merged:
                    if tuple(existing.get("headers", [])) == header_key:
                        existing["rows"].extend(table.get("rows", []))
                        break

        return merged


# Support for multiple LLM providers
class LiteLLMExtractor(LLMExtractor):
    """
    LLM extractor using LiteLLM for multiple provider support.

    Supports: OpenAI, Anthropic, Groq, Cohere, Ollama, etc.
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        super().__init__(config)
        self._litellm = None

    def _get_client(self):
        """Get LiteLLM client."""
        if self._litellm is None:
            try:
                import litellm

                self._litellm = litellm
                # Set API keys from config
                if self.config.api_key:
                    if "anthropic" in self.config.provider:
                        litellm.anthropic_key = self.config.api_key
                    elif "groq" in self.config.provider:
                        litellm.groq_key = self.config.api_key
                    else:
                        litellm.openai_key = self.config.api_key
            except ImportError:
                raise ImportError("LiteLLM required. Install: pip install litellm")
        return self._litellm

    async def extract(
        self,
        content: str,
        schema: Type[BaseModel],
        instruction: Optional[str] = None,
        input_format: str = "markdown",
    ) -> List[BaseModel]:
        """Extract using LiteLLM."""
        if not HAS_PYDANTIC:
            raise ImportError("Pydantic required")

        litellm = self._get_client()

        system_prompt = self._build_system_prompt(schema, instruction)
        user_prompt = self._build_user_prompt(
            self._truncate_content(content, max_tokens=4000), schema, input_format
        )

        for attempt in range(self.config.max_retries):
            try:
                response = await litellm.acompletion(
                    model=self.config.provider,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    response_format={"type": "json_object"},
                )

                content_text = response.choices[0].message.content
                data = json.loads(content_text)

                # Extract items
                if "items" in data:
                    items = data["items"]
                elif "data" in data:
                    items = data["data"]
                elif isinstance(data, list):
                    items = data
                else:
                    items = [data]

                results = []
                for item in items:
                    try:
                        results.append(schema(**item))
                    except ValidationError:
                        continue

                return results

            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    raise

                delay = min(
                    self.config.backoff_base_delay
                    * (self.config.backoff_exponential_factor**attempt),
                    self.config.backoff_max_delay,
                )
                import asyncio

                await asyncio.sleep(delay)

        return []


# Convenience functions
async def extract_with_llm(
    content: str,
    schema: Type[BaseModel],
    provider: str = "openai/gpt-4o-mini",
    api_key: Optional[str] = None,
    instruction: Optional[str] = None,
) -> List[BaseModel]:
    """
    Quick extraction using LLM.

    Args:
        content: Content to extract from
        schema: Pydantic schema
        provider: LLM provider (e.g., openai/gpt-4o-mini, anthropic/claude-3-haiku)
        api_key: API key for provider
        instruction: Additional instructions

    Returns:
        List of extracted items
    """
    config = LLMConfig(provider=provider, api_key=api_key)
    extractor = LiteLLMExtractor(config)
    return await extractor.extract(content, schema, instruction=instruction)
