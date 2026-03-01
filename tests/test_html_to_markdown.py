"""
Tests for HTML to Markdown conversion.
"""

import unittest
from agent_search.html_to_markdown import (
    HTMLToMarkdown,
    MarkdownCleaner,
    ConversionOptions,
    html_to_markdown,
)


class TestHTMLToMarkdown(unittest.TestCase):
    """Test HTML to Markdown conversion."""

    def setUp(self):
        """Set up test fixtures."""
        self.converter = HTMLToMarkdown()

    def test_simple_paragraph(self):
        """Test converting a simple paragraph."""
        html = "<p>This is a paragraph.</p>"
        markdown = self.converter.convert(html)

        self.assertIn("This is a paragraph.", markdown)

    def test_headings(self):
        """Test converting headings."""
        html = """
        <h1>Heading 1</h1>
        <h2>Heading 2</h2>
        <h3>Heading 3</h3>
        """
        markdown = self.converter.convert(html)

        self.assertIn("# Heading 1", markdown)
        self.assertIn("## Heading 2", markdown)
        self.assertIn("### Heading 3", markdown)

    def test_links(self):
        """Test converting links."""
        html = '<a href="https://example.com">Link text</a>'
        markdown = self.converter.convert(html)

        self.assertIn("[Link text](https://example.com)", markdown)

    def test_images(self):
        """Test converting images."""
        html = '<img src="https://example.com/image.jpg" alt="Alt text">'
        markdown = self.converter.convert(html)

        self.assertIn("![Alt text](https://example.com/image.jpg)", markdown)

    def test_lists(self):
        """Test converting lists."""
        html = """
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        <ol>
            <li>First</li>
            <li>Second</li>
        </ol>
        """
        markdown = self.converter.convert(html)

        self.assertIn("- Item 1", markdown)
        self.assertIn("- Item 2", markdown)
        self.assertIn("1. First", markdown)
        self.assertIn("2. Second", markdown)

    def test_code_blocks(self):
        """Test converting code blocks."""
        html = """
        <pre><code class="language-python">
        def hello():
            print("Hello")
        </code></pre>
        """
        markdown = self.converter.convert(html)

        self.assertIn("```python", markdown)
        self.assertIn("```", markdown)

    def test_tables(self):
        """Test converting tables."""
        html = """
        <table>
            <thead>
                <tr><th>Name</th><th>Age</th></tr>
            </thead>
            <tbody>
                <tr><td>Alice</td><td>30</td></tr>
                <tr><td>Bob</td><td>25</td></tr>
            </tbody>
        </table>
        """
        markdown = self.converter.convert(html)

        self.assertIn("| Name | Age |", markdown)
        self.assertIn("| Alice | 30 |", markdown)

    def test_script_removal(self):
        """Test that scripts are removed."""
        html = """
        <p>Text</p>
        <script>alert('test');</script>
        <p>More text</p>
        """
        markdown = self.converter.convert(html)

        self.assertNotIn("<script>", markdown)
        self.assertNotIn("alert", markdown)

    def test_style_removal(self):
        """Test that style tags are removed."""
        html = """
        <p>Text</p>
        <style>body { color: red; }</style>
        <p>More text</p>
        """
        markdown = self.converter.convert(html)

        self.assertNotIn("<style>", markdown)
        self.assertNotIn("color: red", markdown)

    def test_base_url_resolution(self):
        """Test resolving relative URLs."""
        html = '<a href="/page">Link</a>'
        markdown = self.converter.convert(html, base_url="https://example.com")

        self.assertIn("(https://example.com/page)", markdown)

    def test_empty_html(self):
        """Test handling empty HTML."""
        markdown = self.converter.convert("")
        self.assertEqual(markdown, "")

    def test_blockquote(self):
        """Test converting blockquotes."""
        html = "<blockquote>This is a quote</blockquote>"
        markdown = self.converter.convert(html)

        self.assertIn("> This is a quote", markdown)

    def test_inline_code(self):
        """Test converting inline code."""
        html = "<p>Use <code>print()</code> to output</p>"
        markdown = self.converter.convert(html)

        self.assertIn("`print()`", markdown)


class TestMarkdownCleaner(unittest.TestCase):
    """Test Markdown cleaning."""

    def setUp(self):
        """Set up test fixtures."""
        self.cleaner = MarkdownCleaner()

    def test_remove_excessive_whitespace(self):
        """Test removing excessive blank lines."""
        markdown = "Line 1\n\n\n\n\nLine 2"
        cleaned = self.cleaner.clean(markdown)

        self.assertNotIn("\n\n\n\n", cleaned)

    def test_remove_empty_links(self):
        """Test removing empty links."""
        markdown = "[ ](https://example.com)"
        cleaned = self.cleaner.clean(markdown)

        self.assertNotIn("[ ](", cleaned)

    def test_extract_fit_markdown_no_query(self):
        """Test extracting fit markdown without query."""
        markdown = "A\n\nB\n\nC\n\nD"
        fit = self.cleaner.extract_fit_markdown(markdown, max_length=10)

        # Should truncate to 10 chars
        self.assertLessEqual(len(fit), 13)  # + "..."

    def test_extract_fit_markdown_with_query(self):
        """Test extracting relevant parts based on query."""
        markdown = """
        This is about cats.
        
        This is about dogs.
        
        More about cats here.
        """
        fit = self.cleaner.extract_fit_markdown(markdown, query="cats")

        self.assertIn("cats", fit.lower())


class TestConversionOptions(unittest.TestCase):
    """Test ConversionOptions."""

    def test_default_options(self):
        """Test default option values."""
        options = ConversionOptions()

        self.assertTrue(options.include_images)
        self.assertTrue(options.include_links)
        self.assertTrue(options.include_tables)
        self.assertEqual(options.heading_style, "atx")

    def test_custom_options(self):
        """Test custom option values."""
        options = ConversionOptions(include_images=False, heading_style="setext")

        self.assertFalse(options.include_images)
        self.assertEqual(options.heading_style, "setext")


class TestHtmlToMarkdownFunction(unittest.TestCase):
    """Test the convenience function."""

    def test_quick_conversion(self):
        """Test quick conversion function."""
        html = "<p>Hello World</p>"
        markdown = html_to_markdown(html)

        self.assertIn("Hello World", markdown)

    def test_with_options(self):
        """Test conversion with options."""
        html = '<img src="test.jpg" alt="Test">'
        markdown = html_to_markdown(html, include_images=False)

        self.assertNotIn("![", markdown)


if __name__ == "__main__":
    unittest.main()
