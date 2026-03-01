"""
Structured Data Extraction

Extract structured data from HTML using CSS/XPath selectors or LLMs.
Supports Pydantic schemas for type-safe extraction.

Usage:
    from agent_search.core.data_extraction import StructuredExtractor, CSSExtractionStrategy
    from pydantic import BaseModel, Field

    # Using Pydantic schema
    class Product(BaseModel):
        name: str = Field(description="Product name")
        price: str = Field(description="Product price")
        description: Optional[str] = Field(default=None)

    extractor = StructuredExtractor()
    products = extractor.extract_with_schema(html, Product)

    # Using CSS selectors
    strategy = CSSExtractionStrategy({
        "base_selector": ".product",
        "fields": {
            "name": {"selector": "h2", "type": "text"},
            "price": {"selector": ".price", "type": "text"},
            "image": {"selector": "img", "type": "attribute", "attribute": "src"}
        }
    })

    data = extractor.extract_with_css(html, strategy)
"""

import json
import re
from typing import Optional, Dict, Any, List, Type, Union, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod

try:
    from bs4 import BeautifulSoup, Tag

    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    from pydantic import BaseModel, Field, ValidationError

    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False


class ExtractionStrategy(ABC):
    """Base class for extraction strategies."""

    @abstractmethod
    def extract(
        self, html: str, base_url: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Extract data from HTML."""
        pass


@dataclass
class CSSFieldConfig:
    """Configuration for a CSS extraction field."""

    selector: str
    type: str = "text"  # text, html, attribute, number
    attribute: Optional[str] = None
    transform: Optional[Callable[[str], Any]] = None
    default: Any = None


@dataclass
class CSSExtractionStrategy:
    """Strategy for extracting data using CSS selectors."""

    base_selector: str
    fields: Dict[str, Union[str, Dict[str, Any], CSSFieldConfig]]
    multiple: bool = True

    def __post_init__(self):
        # Normalize field configs
        normalized = {}
        for name, config in self.fields.items():
            if isinstance(config, str):
                # Simple selector string
                normalized[name] = CSSFieldConfig(selector=config, type="text")
            elif isinstance(config, dict):
                # Dict config
                normalized[name] = CSSFieldConfig(**config)
            elif isinstance(config, CSSFieldConfig):
                normalized[name] = config
        self.fields = normalized

    def extract(
        self, html: str, base_url: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Extract data using CSS selectors."""
        if not HAS_BS4:
            raise ImportError("BeautifulSoup4 required")

        soup = BeautifulSoup(html, "html.parser")
        results = []

        # Find base elements
        if self.multiple:
            elements = soup.select(self.base_selector)
        else:
            element = soup.select_one(self.base_selector)
            elements = [element] if element else []

        for element in elements:
            if not element:
                continue

            item = {}
            for field_name, config in self.fields.items():
                try:
                    # Find the field element
                    if config.selector.startswith("@"):
                        # Use current element
                        field_el = element
                    else:
                        field_el = element.select_one(config.selector)

                    if not field_el:
                        item[field_name] = config.default
                        continue

                    # Extract value based on type
                    if config.type == "text":
                        value = field_el.get_text(strip=True)
                    elif config.type == "html":
                        value = str(field_el)
                    elif config.type == "attribute":
                        value = field_el.get(config.attribute, config.default)
                    elif config.type == "number":
                        text = field_el.get_text(strip=True)
                        # Extract number from text
                        numbers = re.findall(r"[\d,]+\.?\d*", text)
                        value = (
                            float(numbers[0].replace(",", ""))
                            if numbers
                            else config.default
                        )
                    else:
                        value = field_el.get_text(strip=True)

                    # Apply transform if provided
                    if config.transform and value:
                        value = config.transform(value)

                    item[field_name] = value

                except Exception:
                    item[field_name] = config.default

            if item:
                results.append(item)

        return results


@dataclass
class XPathExtractionStrategy:
    """Strategy for extracting data using XPath selectors."""

    base_xpath: str
    fields: Dict[str, Union[str, Dict[str, Any]]]
    namespaces: Optional[Dict[str, str]] = None

    def extract(
        self, html: str, base_url: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Extract data using XPath selectors."""
        try:
            from lxml import etree, html as lhtml
        except ImportError:
            raise ImportError(
                "lxml is required for XPath extraction. Install: pip install lxml"
            )

        tree = lhtml.fromstring(html)
        results = []

        # Find base elements
        base_elements = tree.xpath(self.base_xpath, namespaces=self.namespaces)

        for element in base_elements:
            item = {}
            for field_name, config in self.fields.items():
                try:
                    if isinstance(config, str):
                        # Simple XPath
                        xpath = config
                        attr = None
                    else:
                        xpath = config.get("xpath", config.get("selector", "."))
                        attr = config.get("attribute")

                    # Evaluate XPath
                    values = element.xpath(xpath, namespaces=self.namespaces)

                    if values:
                        if attr:
                            # Get attribute
                            if isinstance(values[0], etree._Element):
                                value = values[0].get(attr)
                            else:
                                value = str(values[0])
                        else:
                            # Get text
                            if isinstance(values[0], etree._Element):
                                value = values[0].text_content().strip()
                            else:
                                value = str(values[0]).strip()
                    else:
                        value = (
                            config.get("default") if isinstance(config, dict) else None
                        )

                    item[field_name] = value

                except Exception:
                    item[field_name] = None

            if item:
                results.append(item)

        return results


class StructuredExtractor:
    """
    Extract structured data from HTML.

    Supports multiple extraction strategies:
    - CSS selectors (BeautifulSoup)
    - XPath selectors (lxml)
    - Pydantic schemas with LLM extraction
    """

    def __init__(self):
        if not HAS_BS4:
            raise ImportError("BeautifulSoup4 required")

    def extract_with_css(
        self, html: str, strategy: CSSExtractionStrategy, base_url: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract data using CSS selectors.

        Args:
            html: HTML content
            strategy: CSS extraction strategy
            base_url: Base URL for resolving relative links

        Returns:
            List of extracted items
        """
        return strategy.extract(html, base_url)

    def extract_with_xpath(
        self,
        html: str,
        strategy: XPathExtractionStrategy,
        base_url: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract data using XPath selectors.

        Args:
            html: HTML content
            strategy: XPath extraction strategy
            base_url: Base URL for resolving relative links

        Returns:
            List of extracted items
        """
        return strategy.extract(html, base_url)

    def extract_with_schema(
        self,
        html: str,
        schema: Type[BaseModel],
        instructions: Optional[str] = None,
        llm_client=None,
    ) -> List[BaseModel]:
        """
        Extract data using LLM with Pydantic schema.

        Similar to Firecrawl's JSON extraction.

        Args:
            html: HTML content (will be converted to markdown)
            schema: Pydantic model class
            instructions: Additional instructions for the LLM
            llm_client: LLM client for extraction (optional)

        Returns:
            List of validated Pydantic model instances
        """
        if not HAS_PYDANTIC:
            raise ImportError("Pydantic is required for schema extraction")

        # Convert HTML to markdown first
        from .html_to_markdown import html_to_markdown

        markdown = html_to_markdown(html)

        if llm_client:
            # Use provided LLM client
            return self._extract_with_llm(markdown, schema, instructions, llm_client)
        else:
            # Use pattern matching for simple schemas
            return self._extract_with_patterns(html, schema)

    def _extract_with_patterns(
        self, html: str, schema: Type[BaseModel]
    ) -> List[BaseModel]:
        """
        Extract using regex patterns (fallback when no LLM available).
        """
        # Get schema fields
        fields = (
            schema.model_fields
            if hasattr(schema, "model_fields")
            else schema.__fields__
        )

        items = []
        soup = BeautifulSoup(html, "html.parser")

        # Try to find repeating patterns
        # This is a simple heuristic - find elements with similar structure
        candidates = soup.find_all(["div", "article", "section", "li"])

        for element in candidates:
            item_data = {}

            for field_name, field_info in fields.items():
                # Try to find text that matches field name
                field_text = element.find(string=re.compile(field_name, re.I))
                if field_text:
                    # Get the next sibling or parent's text
                    parent = field_text.parent
                    if parent and parent.next_sibling:
                        value = parent.next_sibling.get_text(strip=True)
                    else:
                        value = field_text.strip()

                    # Try to cast to expected type
                    try:
                        field_type = (
                            field_info.annotation
                            if hasattr(field_info, "annotation")
                            else field_info.outer_type_
                        )
                        if field_type == str:
                            item_data[field_name] = value
                        elif field_type in (int, float):
                            # Extract number
                            numbers = re.findall(r"[\d,]+\.?\d*", value)
                            if numbers:
                                num_str = numbers[0].replace(",", "")
                                item_data[field_name] = field_type(num_str)
                    except:
                        item_data[field_name] = value

            if item_data:
                try:
                    items.append(schema(**item_data))
                except ValidationError:
                    pass

        return items

    def _extract_with_llm(
        self,
        markdown: str,
        schema: Type[BaseModel],
        instructions: Optional[str],
        llm_client,
    ) -> List[BaseModel]:
        """Extract using LLM."""
        # This is a placeholder - actual implementation would use the LLM
        # to parse the markdown and extract structured data
        raise NotImplementedError("LLM extraction requires an LLM client")

    def extract_tables(
        self, html: str, convert_numbers: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Extract all tables from HTML as structured data.

        Args:
            html: HTML content
            convert_numbers: Try to convert numeric strings to numbers

        Returns:
            List of tables, each with 'headers' and 'rows'
        """
        soup = BeautifulSoup(html, "html.parser")
        tables = []

        for table in soup.find_all("table"):
            table_data = {"headers": [], "rows": []}

            # Extract headers
            thead = table.find("thead")
            if thead:
                headers = thead.find_all("th")
            else:
                # Try first row
                first_row = table.find("tr")
                headers = first_row.find_all(["th", "td"]) if first_row else []

            table_data["headers"] = [h.get_text(strip=True) for h in headers]

            # Extract rows
            tbody = table.find("tbody") or table
            for row in tbody.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if cells:
                    row_data = []
                    for cell in cells:
                        value = cell.get_text(strip=True)

                        # Try to convert to number
                        if convert_numbers:
                            try:
                                if "." in value:
                                    value = float(value.replace(",", ""))
                                else:
                                    value = int(value.replace(",", ""))
                            except ValueError:
                                pass

                        row_data.append(value)

                    if row_data:
                        table_data["rows"].append(row_data)

            if table_data["headers"] or table_data["rows"]:
                tables.append(table_data)

        return tables

    def extract_links(
        self, html: str, base_url: Optional[str] = None, same_domain_only: bool = False
    ) -> List[Dict[str, str]]:
        """
        Extract all links from HTML.

        Args:
            html: HTML content
            base_url: Base URL for resolving relative links
            same_domain_only: Only return links from the same domain

        Returns:
            List of link dicts with 'url', 'text', 'title'
        """
        from urllib.parse import urljoin, urlparse

        soup = BeautifulSoup(html, "html.parser")
        links = []

        base_domain = urlparse(base_url).netloc if base_url else None

        for a in soup.find_all("a", href=True):
            href = a["href"]

            # Skip anchors and javascript
            if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            # Resolve relative URLs
            if base_url and not href.startswith(("http://", "https://")):
                href = urljoin(base_url, href)

            # Check domain
            if same_domain_only and base_domain:
                link_domain = urlparse(href).netloc
                if link_domain != base_domain:
                    continue

            links.append(
                {
                    "url": href,
                    "text": a.get_text(strip=True),
                    "title": a.get("title", ""),
                    "is_external": urlparse(href).netloc != base_domain
                    if base_domain
                    else True,
                }
            )

        return links

    def extract_images(
        self, html: str, base_url: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Extract all images from HTML.

        Args:
            html: HTML content
            base_url: Base URL for resolving relative URLs

        Returns:
            List of image dicts with 'url', 'alt', 'title'
        """
        from urllib.parse import urljoin

        soup = BeautifulSoup(html, "html.parser")
        images = []

        for img in soup.find_all("img"):
            src = img.get("src", "")
            if not src:
                continue

            # Resolve relative URLs
            if base_url and not src.startswith(("http://", "https://", "data:")):
                src = urljoin(base_url, src)

            images.append(
                {
                    "url": src,
                    "alt": img.get("alt", ""),
                    "title": img.get("title", ""),
                    "width": img.get("width"),
                    "height": img.get("height"),
                }
            )

        return images

    def extract_metadata(self, html: str) -> Dict[str, Any]:
        """
        Extract metadata from HTML head.

        Returns:
            Dict with title, description, keywords, etc.
        """
        soup = BeautifulSoup(html, "html.parser")
        metadata = {
            "title": "",
            "description": "",
            "keywords": [],
            "author": "",
            "og": {},
            "twitter": {},
        }

        # Title
        title = soup.find("title")
        if title:
            metadata["title"] = title.get_text(strip=True)

        # Standard meta tags
        meta_mapping = {
            "description": ["description", "og:description", "twitter:description"],
            "author": ["author", "og:author"],
        }

        for key, names in meta_mapping.items():
            for name in names:
                meta = soup.find("meta", attrs={"name": name}) or soup.find(
                    "meta", attrs={"property": name}
                )
                if meta and meta.get("content"):
                    metadata[key] = meta["content"]
                    break

        # Keywords
        keywords_meta = soup.find("meta", attrs={"name": "keywords"})
        if keywords_meta:
            metadata["keywords"] = [
                k.strip() for k in keywords_meta.get("content", "").split(",")
            ]

        # Open Graph
        for meta in soup.find_all("meta", property=re.compile("^og:")):
            prop = meta.get("property", "").replace("og:", "")
            if prop:
                metadata["og"][prop] = meta.get("content", "")

        # Twitter Card
        for meta in soup.find_all("meta", attrs={"name": re.compile("^twitter:")}):
            name = meta.get("name", "").replace("twitter:", "")
            if name:
                metadata["twitter"][name] = meta.get("content", "")

        return metadata


# Convenience function
def extract_with_css(
    html: str, base_selector: str, fields: Dict[str, Any], **kwargs
) -> List[Dict[str, Any]]:
    """
    Quick extraction using CSS selectors.

    Args:
        html: HTML content
        base_selector: CSS selector for base elements
        fields: Field definitions
        **kwargs: Additional strategy options

    Returns:
        List of extracted items
    """
    strategy = CSSExtractionStrategy(
        base_selector=base_selector, fields=fields, **kwargs
    )
    extractor = StructuredExtractor()
    return extractor.extract_with_css(html, strategy)
