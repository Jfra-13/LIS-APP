from django.test import SimpleTestCase

from consulta.templatetags.markdown_extras import markdownify


class MarkdownifyFilterTests(SimpleTestCase):
    def test_renders_basic_markdown(self):
        html = markdownify("# Titulo\n\n**negrita** y *cursiva*")
        self.assertIn("<h1>Titulo</h1>", html)
        self.assertIn("<strong>negrita</strong>", html)
        self.assertIn("<em>cursiva</em>", html)

    def test_renders_lists(self):
        html = markdownify("- uno\n- dos")
        self.assertIn("<ul>", html)
        self.assertIn("<li>uno</li>", html)

    def test_escapes_raw_html_script(self):
        html = markdownify("texto <script>alert(1)</script>")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_escapes_event_handler_html(self):
        html = markdownify("<img src=x onerror=alert(1)>")
        self.assertNotIn("<img", html)
        self.assertIn("&lt;img", html)

    def test_neutralizes_javascript_scheme_link(self):
        # The dangerous scheme is rejected by the link validator: no anchor is
        # produced, so the markup stays as harmless literal text (no href).
        html = markdownify("[click](javascript:alert(1))")
        self.assertNotIn('href="javascript:', html)
        self.assertNotIn("<a ", html)

    def test_keeps_safe_https_link(self):
        html = markdownify("[ok](https://example.com)")
        self.assertIn('href="https://example.com"', html)

    def test_empty_returns_empty_string(self):
        self.assertEqual(markdownify(""), "")
        self.assertEqual(markdownify(None), "")
