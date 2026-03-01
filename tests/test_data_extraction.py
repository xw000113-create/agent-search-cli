"""
Tests for data extraction modules.
"""

import unittest
from unittest.mock import Mock, patch
from agent_search.data_extraction import (
    StructuredExtractor,
    CSSExtractionStrategy,
    CSSFieldConfig,
    extract_with_css,
)


class TestStructuredExtractor(unittest.TestCase):
    """Test structured data extraction."""

    def setUp(self):
        """Set up test fixtures."""
        self.extractor = StructuredExtractor()

    def test_extract_tables(self):
        """Test extracting tables from HTML."""
        html = """
        <table>
            <thead>
                <tr><th>Name</th><th>Value</th></tr>
            </thead>
            <tbody>
                <tr><td>Test</td><td>123</td></tr>
            </tbody>
        </table>
        """

        tables = self.extractor.extract_tables(html)

        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0]["headers"], ["Name", "Value"])
        self.assertEqual(tables[0]["rows"][0], ["Test", 123])

    def test_extract_links(self):
        """Test extracting links."""
        html = """
        <a href="https://example.com">Example</a>
        <a href="/internal">Internal</a>
        <a href="#anchor">Anchor</a>
        """

        links = self.extractor.extract_links(html, base_url="https://test.com")

        # Should have 2 links (anchor excluded)
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0]["url"], "https://example.com")
        self.assertEqual(links[1]["url"], "https://test.com/internal")

    def test_extract_images(self):
        """Test extracting images."""
        html = """
        <img src="image.jpg" alt="Test" title="Test Image">
        <img src="/other.png" alt="Other">
        """

        images = self.extractor.extract_images(html, base_url="https://test.com")

        self.assertEqual(len(images), 2)
        self.assertEqual(images[0]["url"], "https://test.com/image.jpg")
        self.assertEqual(images[0]["alt"], "Test")

    def test_extract_metadata(self):
        """Test extracting metadata."""
        html = """
        <html>
        <head>
            <title>Test Page</title>
            <meta name="description" content="Test description">
            <meta name="author" content="Test Author">
            <meta name="keywords" content="test, example, python">
        </head>
        </html>
        """

        metadata = self.extractor.extract_metadata(html)

        self.assertEqual(metadata["title"], "Test Page")
        self.assertEqual(metadata["description"], "Test description")
        self.assertEqual(metadata["author"], "Test Author")
        self.assertEqual(metadata["keywords"], ["test", "example", "python"])

    def test_extract_metadata_og(self):
        """Test extracting Open Graph metadata."""
        html = """
        <html>
        <head>
            <meta property="og:title" content="OG Title">
            <meta property="og:description" content="OG Description">
            <meta property="og:url" content="https://example.com">
        </head>
        </html>
        """

        metadata = self.extractor.extract_metadata(html)

        self.assertEqual(metadata["og"]["title"], "OG Title")
        self.assertEqual(metadata["og"]["description"], "OG Description")


class TestCSSExtractionStrategy(unittest.TestCase):
    """Test CSS extraction strategy."""

    def test_simple_extraction(self):
        """Test simple CSS selector extraction."""
        html = """
        <div class="product">
            <h2>Product Name</h2>
            <span class="price">$19.99</span>
        </div>
        <div class="product">
            <h2>Another Product</h2>
            <span class="price">$29.99</span>
        </div>
        """

        strategy = CSSExtractionStrategy(
            base_selector=".product", fields={"name": "h2", "price": ".price"}
        )

        extractor = StructuredExtractor()
        results = extractor.extract_with_css(html, strategy)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["name"], "Product Name")
        self.assertEqual(results[0]["price"], "$19.99")

    def test_attribute_extraction(self):
        """Test extracting attributes."""
        html = """
        <div class="item">
            <a href="https://example.com" class="link">Link</a>
            <img src="image.jpg" alt="Image">
        </div>
        """

        strategy = CSSExtractionStrategy(
            base_selector=".item",
            fields={
                "link_url": {"selector": "a", "type": "attribute", "attribute": "href"},
                "image_src": {
                    "selector": "img",
                    "type": "attribute",
                    "attribute": "src",
                },
            },
        )

        extractor = StructuredExtractor()
        results = extractor.extract_with_css(html, strategy)

        self.assertEqual(results[0]["link_url"], "https://example.com")
        self.assertEqual(results[0]["image_src"], "image.jpg")

    def test_number_extraction(self):
        """Test extracting numbers."""
        html = """
        <div class="stats">
            <span class="count">1,234</span>
            <span class="price">$19.99</span>
        </div>
        """

        strategy = CSSExtractionStrategy(
            base_selector=".stats",
            fields={
                "count": {"selector": ".count", "type": "number"},
                "price": {"selector": ".price", "type": "number"},
            },
            multiple=False,
        )

        extractor = StructuredExtractor()
        results = extractor.extract_with_css(html, strategy)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["count"], 1234)
        self.assertEqual(results[0]["price"], 19.99)

    def test_default_values(self):
        """Test default values."""
        html = """
        <div class="product">
            <h2>Name</h2>
        </div>
        """

        strategy = CSSExtractionStrategy(
            base_selector=".product",
            fields={
                "name": "h2",
                "price": {"selector": ".nonexistent", "type": "text", "default": "N/A"},
            },
        )

        extractor = StructuredExtractor()
        results = extractor.extract_with_css(html, strategy)

        self.assertEqual(results[0]["price"], "N/A")


class TestCSSFieldConfig(unittest.TestCase):
    """Test CSSFieldConfig."""

    def test_default_config(self):
        """Test default field config."""
        config = CSSFieldConfig(selector=".test")

        self.assertEqual(config.selector, ".test")
        self.assertEqual(config.type, "text")
        self.assertIsNone(config.attribute)
        self.assertIsNone(config.default)

    def test_custom_config(self):
        """Test custom field config."""
        config = CSSFieldConfig(selector=".price", type="number", default=0.0)

        self.assertEqual(config.type, "number")
        self.assertEqual(config.default, 0.0)


class TestExtractWithCSS(unittest.TestCase):
    """Test extract_with_css convenience function."""

    def test_quick_extraction(self):
        """Test quick extraction."""
        html = """
        <div class="item">
            <h2>Title</h2>
        </div>
        """

        results = extract_with_css(html, ".item", {"title": "h2"})

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Title")


if __name__ == "__main__":
    unittest.main()
