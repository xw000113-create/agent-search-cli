"""
HTML to Markdown Converter

Converts HTML content to clean, LLM-ready Markdown.
Handles various HTML elements and produces structured output.

Usage:
    from agent_search.core.html_to_markdown import HTMLToMarkdown

    converter = HTMLToMarkdown()
    markdown = converter.convert(html_content)

    # With options
    markdown = converter.convert(html_content,
                                 base_url="https://example.com",
                                 include_images=True,
                                 include_links=True)
"""

import re
import html
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass

try:
    from bs4 import BeautifulSoup, Tag

    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


@dataclass
class ConversionOptions:
    """Options for HTML to Markdown conversion."""

    include_images: bool = True
    include_links: bool = True
    include_tables: bool = True
    include_code_blocks: bool = True
    heading_style: str = "atx"  # "atx" (#) or "setext" (underlines)
    wrap_width: Optional[int] = None  # None = no wrapping
    strip_scripts: bool = True
    strip_styles: bool = True
    base_url: Optional[str] = None


class HTMLToMarkdown:
    """
    Convert HTML to clean Markdown.

    Produces LLM-ready output similar to Firecrawl and Crawl4AI.
    """

    def __init__(self):
        if not HAS_BS4:
            raise ImportError(
                "BeautifulSoup4 is required. Install: pip install beautifulsoup4"
            )
        self.options = ConversionOptions()
        self._current_list_level = 0

    def convert(
        self,
        html: str,
        base_url: Optional[str] = None,
        options: Optional[ConversionOptions] = None,
    ) -> str:
        """
        Convert HTML to Markdown.

        Args:
            html: HTML content to convert
            base_url: Base URL for resolving relative links
            options: Conversion options

        Returns:
            Clean Markdown string
        """
        if options:
            self.options = options
        if base_url:
            self.options.base_url = base_url

        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted elements
        self._clean_soup(soup)

        # Convert to markdown
        markdown = self._convert_element(soup)

        # Post-process
        markdown = self._post_process(markdown)

        return markdown

    def convert_batch(
        self, pages: List[Dict[str, str]], options: Optional[ConversionOptions] = None
    ) -> List[Dict[str, Any]]:
        """
        Convert multiple HTML pages to Markdown.

        Args:
            pages: List of dicts with 'url' and 'html' keys
            options: Conversion options

        Returns:
            List of dicts with 'url', 'markdown', 'title', 'metadata'
        """
        results = []
        for page in pages:
            try:
                markdown = self.convert(
                    page["html"], base_url=page.get("url"), options=options
                )
                soup = BeautifulSoup(page["html"], "html.parser")
                title_tag = soup.find("title")
                title = title_tag.get_text(strip=True) if title_tag else None

                results.append(
                    {
                        "url": page.get("url"),
                        "markdown": markdown,
                        "title": title,
                        "metadata": self._extract_metadata(soup, page.get("url")),
                    }
                )
            except Exception as e:
                results.append(
                    {"url": page.get("url"), "error": str(e), "markdown": ""}
                )
        return results

    def _clean_soup(self, soup: BeautifulSoup):
        """Remove script, style, and other unwanted elements."""
        # Remove scripts
        if self.options.strip_scripts:
            for script in soup.find_all("script"):
                script.decompose()

        # Remove styles
        if self.options.strip_styles:
            for style in soup.find_all("style"):
                style.decompose()

        # Remove noscript, iframe, embed, object
        for tag in soup.find_all(["noscript", "iframe", "embed", "object"]):
            tag.decompose()

        # Remove hidden elements
        for tag in soup.find_all(attrs={"aria-hidden": "true"}):
            tag.decompose()

        # Remove elements with display:none or visibility:hidden
        for tag in soup.find_all(attrs={"style": True}):
            style = tag["style"].lower()
            if "display:none" in style or "visibility:hidden" in style:
                tag.decompose()

    def _convert_element(self, element: Tag, level: int = 0) -> str:
        """Convert a BeautifulSoup element to Markdown."""
        if isinstance(element, str):
            return self._escape_text(element)

        if element.name is None:
            return self._escape_text(element.string or "")

        # Handle different element types
        handlers = {
            "h1": lambda e: self._heading(e, 1),
            "h2": lambda e: self._heading(e, 2),
            "h3": lambda e: self._heading(e, 3),
            "h4": lambda e: self._heading(e, 4),
            "h5": lambda e: self._heading(e, 5),
            "h6": lambda e: self._heading(e, 6),
            "p": self._paragraph,
            "br": lambda e: "\n",
            "hr": lambda e: "\n---\n",
            "a": self._link,
            "img": self._image,
            "strong": lambda e: f"**{self._convert_children(e)}**",
            "b": lambda e: f"**{self._convert_children(e)}**",
            "em": lambda e: f"*{self._convert_children(e)}*",
            "i": lambda e: f"*{self._convert_children(e)}*",
            "code": self._inline_code,
            "pre": self._code_block,
            "blockquote": self._blockquote,
            "ul": self._unordered_list,
            "ol": self._ordered_list,
            "li": self._list_item,
            "table": self._table,
            "thead": lambda e: self._convert_children(e),
            "tbody": lambda e: self._convert_children(e),
            "tr": self._table_row,
            "th": lambda e: f"| {self._convert_children(e).strip()} ",
            "td": lambda e: f"| {self._convert_children(e).strip()} ",
            "div": self._div,
            "span": lambda e: self._convert_children(e),
        }

        handler = handlers.get(element.name)
        if handler:
            return handler(element)

        # Default: just convert children
        return self._convert_children(element)

    def _convert_children(self, element: Tag) -> str:
        """Convert all children of an element."""
        text = ""
        for child in element.children:
            text += self._convert_element(child)
        return text

    def _heading(self, element: Tag, level: int) -> str:
        """Convert heading to Markdown."""
        text = self._convert_children(element).strip()
        if self.options.heading_style == "atx":
            return f"\n{'#' * level} {text}\n\n"
        else:
            # Setext style
            underline = "=" if level == 1 else "-"
            return f"\n{text}\n{underline * len(text)}\n\n"

    def _paragraph(self, element: Tag) -> str:
        """Convert paragraph to Markdown."""
        text = self._convert_children(element).strip()
        if text:
            return f"\n{text}\n\n"
        return ""

    def _link(self, element: Tag) -> str:
        """Convert anchor to Markdown link."""
        if not self.options.include_links:
            return self._convert_children(element)

        text = self._convert_children(element).strip()
        href = element.get("href", "")

        if not href:
            return text

        # Resolve relative URLs
        if self.options.base_url and not href.startswith(("http://", "https://", "#")):
            href = urljoin(self.options.base_url, href)

        # Skip anchor-only links
        if href.startswith("#"):
            return text

        return f"[{text}]({href})"

    def _image(self, element: Tag) -> str:
        """Convert image to Markdown."""
        if not self.options.include_images:
            return ""

        src = element.get("src", "")
        alt = element.get("alt", "")
        title = element.get("title", "")

        if not src:
            return ""

        # Resolve relative URLs
        if self.options.base_url and not src.startswith(
            ("http://", "https://", "data:")
        ):
            src = urljoin(self.options.base_url, src)

        if title:
            return f'![{alt}]({src} "{title}")\n\n'
        return f"![{alt}]({src})\n\n"

    def _inline_code(self, element: Tag) -> str:
        """Convert inline code."""
        text = element.get_text(strip=True)
        return f"`{text}`"

    def _code_block(self, element: Tag) -> str:
        """Convert code block."""
        if not self.options.include_code_blocks:
            return ""

        # Check for language class
        language = ""
        code = element.find("code")
        if code:
            classes = code.get("class", [])
            for cls in classes:
                if cls.startswith("language-") or cls.startswith("lang-"):
                    language = cls.replace("language-", "").replace("lang-", "")
                    break
            text = code.get_text()
        else:
            text = element.get_text()

        # Clean up the code
        lines = text.strip().split("\n")
        lines = [line.rstrip() for line in lines]
        text = "\n".join(lines)

        return f"\n```{language}\n{text}\n```\n\n"

    def _blockquote(self, element: Tag) -> str:
        """Convert blockquote."""
        text = self._convert_children(element).strip()
        lines = text.split("\n")
        quoted = "\n".join(f"> {line}" for line in lines if line.strip())
        return f"\n{quoted}\n\n"

    def _unordered_list(self, element: Tag) -> str:
        """Convert unordered list."""
        self._current_list_level += 1
        items = []
        for li in element.find_all("li", recursive=False):
            items.append(self._list_item(li, ordered=False))
        self._current_list_level -= 1
        return "\n" + "\n".join(items) + "\n\n"

    def _ordered_list(self, element: Tag) -> str:
        """Convert ordered list."""
        self._current_list_level += 1
        items = []
        for i, li in enumerate(element.find_all("li", recursive=False), 1):
            items.append(self._list_item(li, ordered=True, number=i))
        self._current_list_level -= 1
        return "\n" + "\n".join(items) + "\n\n"

    def _list_item(self, element: Tag, ordered: bool = False, number: int = 1) -> str:
        """Convert list item."""
        text = self._convert_children(element).strip()
        indent = "  " * (self._current_list_level - 1)

        if ordered:
            return f"{indent}{number}. {text}"
        else:
            return f"{indent}- {text}"

    def _table(self, element: Tag) -> str:
        """Convert table to Markdown."""
        if not self.options.include_tables:
            return self._convert_children(element)

        rows = []
        headers = []

        # Extract headers
        thead = element.find("thead")
        if thead:
            for th in thead.find_all("th"):
                headers.append(self._convert_children(th).strip())
        else:
            # Try first row as headers
            first_row = element.find("tr")
            if first_row:
                for th in first_row.find_all(["th", "td"]):
                    headers.append(self._convert_children(th).strip())

        # Extract rows
        tbody = element.find("tbody") or element
        for tr in tbody.find_all("tr"):
            if tr.find("th"):  # Skip header row
                continue
            row = []
            for td in tr.find_all(["td", "th"]):
                row.append(self._convert_children(td).strip())
            if row:
                rows.append(row)

        if not headers and not rows:
            return ""

        # Build markdown table
        md = "\n"
        if headers:
            md += "| " + " | ".join(headers) + " |\n"
            md += "|" + "|".join([" --- " for _ in headers]) + "|\n"

        for row in rows:
            md += "| " + " | ".join(row) + " |\n"

        md += "\n"
        return md

    def _table_row(self, element: Tag) -> str:
        """Convert table row."""
        return self._convert_children(element) + "|\n"

    def _div(self, element: Tag) -> str:
        """Convert div - treat as block if it looks like one."""
        text = self._convert_children(element).strip()
        if text:
            return f"\n{text}\n\n"
        return ""

    def _escape_text(self, text: str) -> str:
        """Escape special Markdown characters."""
        if not text:
            return ""

        # Unescape HTML entities first
        text = html.unescape(text)

        # Escape Markdown special characters
        # But be careful not to escape inside code
        chars_to_escape = [
            ("\\", "\\\\"),  # Must be first
            ("*", "\\*"),
            ("_", "\\_"),
            ("[", "\\["),
            ("]", "\\]"),
            ("`", "\\`"),
        ]

        for char, escaped in chars_to_escape:
            text = text.replace(char, escaped)

        return text

    def _post_process(self, markdown: str) -> str:
        """Clean up the Markdown output."""
        # Remove excessive blank lines
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)

        # Remove leading/trailing whitespace
        markdown = markdown.strip()

        # Fix list spacing
        markdown = re.sub(r"\n- ", "\n- ", markdown)
        markdown = re.sub(r"\n\d+\. ", "\n\\g<0>", markdown)

        return markdown

    def _extract_metadata(
        self, soup: BeautifulSoup, url: Optional[str]
    ) -> Dict[str, Any]:
        """Extract metadata from HTML."""
        metadata = {
            "source_url": url,
            "title": None,
            "description": None,
            "author": None,
            "published_date": None,
            "keywords": [],
        }

        # Title
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.get_text(strip=True)

        # Meta tags
        meta_attrs = {
            "description": ["description", "og:description", "twitter:description"],
            "author": ["author", "og:author"],
            "published_date": [
                "published_date",
                "article:published_time",
                "datePublished",
            ],
        }

        for key, attr_names in meta_attrs.items():
            for name in attr_names:
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

        return metadata


class MarkdownCleaner:
    """Clean and optimize Markdown for LLM consumption."""

    def clean(self, markdown: str) -> str:
        """Clean Markdown for better LLM processing."""
        # Remove excessive whitespace
        text = re.sub(r"\n{4,}", "\n\n\n", markdown)

        # Remove multiple spaces
        text = re.sub(r" +", " ", text)

        # Remove trailing whitespace
        lines = [line.rstrip() for line in text.split("\n")]
        text = "\n".join(lines)

        # Remove empty links
        text = re.sub(r"\[\s*\]\([^)]*\)", "", text)

        # Remove image-only paragraphs
        text = re.sub(r"^\s*!\[.*?\]\(.*?\)\s*$", "", text, flags=re.MULTILINE)

        return text.strip()

    def extract_fit_markdown(
        self,
        markdown: str,
        query: Optional[str] = None,
        max_length: Optional[int] = None,
    ) -> str:
        """
        Extract relevant parts of markdown based on query.

        Similar to Crawl4AI's "fit markdown" feature.
        """
        if not query:
            # Just truncate if too long
            if max_length and len(markdown) > max_length:
                return markdown[:max_length] + "..."
            return markdown

        # Simple relevance scoring
        query_words = set(query.lower().split())
        paragraphs = markdown.split("\n\n")

        scored_paragraphs = []
        for para in paragraphs:
            score = sum(1 for word in query_words if word in para.lower())
            scored_paragraphs.append((score, para))

        # Sort by score descending
        scored_paragraphs.sort(key=lambda x: x[0], reverse=True)

        # Take top paragraphs
        if max_length:
            result = []
            current_length = 0
            for score, para in scored_paragraphs:
                if current_length + len(para) > max_length:
                    break
                result.append(para)
                current_length += len(para) + 2
            return "\n\n".join(result)

        return "\n\n".join(para for _, para in scored_paragraphs[:10])


# Convenience function
def html_to_markdown(html: str, base_url: Optional[str] = None, **kwargs) -> str:
    """
    Quick HTML to Markdown conversion.

    Args:
        html: HTML content
        base_url: Base URL for resolving links
        **kwargs: Additional options for ConversionOptions

    Returns:
        Markdown string
    """
    options = ConversionOptions(**kwargs)
    converter = HTMLToMarkdown()
    return converter.convert(html, base_url=base_url, options=options)
