from django import template
from django.utils.safestring import mark_safe
from markdown_it import MarkdownIt

register = template.Library()

# CommonMark renderer with raw HTML disabled (html=False). Clinical notes are
# authored in Markdown but rendered safely: any embedded HTML is escaped and the
# default link validator blocks dangerous schemes (javascript:, vbscript:),
# preventing stored XSS in a clinical context. Keeping the source as Markdown
# (near plain text) also keeps the NLP engine input clean.
_renderer = MarkdownIt("commonmark", {"html": False})


@register.filter(name="markdownify")
def markdownify(value):
    """Render Markdown text to sanitized HTML for display in templates."""
    if not value:
        return ""
    return mark_safe(_renderer.render(str(value)))
