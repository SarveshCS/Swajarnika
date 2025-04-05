from django import template
import os
import markdown
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def filename(value):
    return os.path.basename(value)

@register.filter
def markdown_format(value):
    """Converts a string to HTML using Markdown."""
    # Configure markdown with extensions for tables, code highlighting, etc.
    extensions = [
        'markdown.extensions.tables',        # For tables
        'markdown.extensions.fenced_code',   # For code blocks
        'markdown.extensions.nl2br',         # Convert newlines to <br>
        'markdown.extensions.sane_lists',    # Better list handling
        'markdown.extensions.smarty',        # Smart quotes, dashes, etc.
    ]
    
    # Convert markdown to HTML and mark as safe for Django templates
    html = markdown.markdown(value, extensions=extensions)
    return mark_safe(html) 