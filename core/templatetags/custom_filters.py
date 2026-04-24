from django import template
import os
import re
import html as html_lib
import markdown as _md
import bleach
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def filename(value):
    return os.path.basename(value)

@register.filter
def markdown_format(value):
    """Converts a string to HTML using Markdown."""
    extensions = [
        'markdown.extensions.tables',
        'markdown.extensions.fenced_code',
        'markdown.extensions.nl2br',
        'markdown.extensions.sane_lists',
        'markdown.extensions.smarty',
    ]
    html = _md.markdown(value, extensions=extensions)
    return mark_safe(html)


_CITATION_RE = re.compile(r'\[\[(visit|med|test|file|testfile):(\d+)\]\]')
# Matches malformed tokens the AI sometimes emits when it doesn't know the id
# (e.g. "[[file:]]", "[[med:?]]"). Used to scrub them from final output.
_BROKEN_CITATION_RE = re.compile(r'\[\[(visit|med|test|file|testfile):[^\]\s]{0,8}\]\]')
_BROKEN_MARKER = ('<span class="sw-pill-missing" '
                  'title="The assistant referenced something but did not provide a valid link.">'
                  '— reference unavailable</span>')

# Markdown extensions we use consistently
_MD_EXTENSIONS = [
    'markdown.extensions.tables',
    'markdown.extensions.fenced_code',
    'markdown.extensions.nl2br',
    'markdown.extensions.sane_lists',
    'markdown.extensions.smarty',
]

# Allow-list of tags / attributes bleach will keep. Anything else is stripped.
_ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'b', 'i', 'u', 's', 'del', 'ins',
    'ul', 'ol', 'li',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'blockquote', 'code', 'pre', 'hr',
    'a', 'span',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
]
_ALLOWED_ATTRS = {
    'a':    ['href', 'title', 'class', 'target', 'rel',
             'data-pill-kind', 'data-pill-id', 'data-pill-url',
             'data-pill-label', 'data-pill-mime'],
    'span': ['class', 'title', 'aria-hidden'],
    'code': ['class'],
    'pre':  ['class'],
    'th':   ['align'],
    'td':   ['align'],
}


def _build_pill_html(ref, kind_raw, fallback_id):
    """Generate the final pill anchor HTML for a citation."""
    display_kind = 'file' if kind_raw in ('file', 'testfile') else kind_raw
    if not ref:
        return (f'<span class="sw-pill sw-pill-{display_kind} sw-pill-stale" '
                f'title="Reference no longer available">&mdash;</span>')
    label = html_lib.escape(ref.get('label') or 'Reference')
    subtitle = ref.get('subtitle') or ''
    url = html_lib.escape(ref.get('url') or '#', quote=True)
    mime = html_lib.escape(ref.get('mime') or '', quote=True)
    rid_attr = html_lib.escape(str(ref.get('id') or fallback_id), quote=True)
    title = html_lib.escape(
        (ref.get('label') or '') + (f' — {subtitle}' if subtitle else '')
    )
    label_attr = html_lib.escape(ref.get('label') or '', quote=True)
    return (
        f'<a href="{url}" class="sw-pill sw-pill-{display_kind}" title="{title}"'
        f' data-pill-kind="{display_kind}"'
        f' data-pill-id="{rid_attr}"'
        f' data-pill-url="{url}"'
        f' data-pill-label="{label_attr}"'
        f' data-pill-mime="{mime}">'
        f'<span class="sw-pill-icon" aria-hidden="true"></span>'
        f'<span class="sw-pill-label">{label}</span>'
        f'</a>'
    )


@register.filter(name='render_citations')
def render_citations(value, refs_map):
    """Render a chat message as sanitized HTML with citation pills.

    Pipeline:
      1. Extract every [[kind:id]] token and swap it with a placeholder the
         markdown processor won't touch.
      2. Run markdown (tables, lists, fenced code, etc.).
      3. Run bleach to sanitize — only safelisted tags/attrs survive.
      4. Restore placeholders as pill anchor HTML.

    This keeps rich markdown formatting while the citations still render as
    clickable pills with data-attributes for the file drawer / deep links.
    """
    if not value:
        return ''
    refs_map = refs_map or {}
    text = str(value)

    # Step 1: extract tokens
    pills = []   # list of (kind, id, ref)
    def _collect(match):
        kind_raw, rid = match.group(1), match.group(2)
        ref = refs_map.get(f'{kind_raw}:{rid}')
        pills.append((kind_raw, rid, ref))
        # Use a placeholder that has no markdown meaning and survives bleach
        # intact (alphanumeric only).
        return f'SWPILL{len(pills)-1}ENDPILL'

    text = _CITATION_RE.sub(_collect, text)

    # Step 1b: scrub any malformed tokens the AI might have emitted with an
    # empty or non-numeric id (e.g. "[[file:]]"). Replace with a muted marker.
    text = _BROKEN_CITATION_RE.sub('SWBROKENPILL', text)

    # Step 1c: auto-link plain filename mentions to a file pill when the exact
    # filename appears in refs and the message did not already cite it.
    cited_ids = {(k, rid) for (k, rid, _ref) in pills}
    filename_refs = []
    for key, ref in refs_map.items():
        if not key.startswith(('file:', 'testfile:')):
            continue
        label = (ref or {}).get('label') or ''
        if not label or len(label) < 4:
            continue
        kind_raw = key.split(':', 1)[0]
        rid = str((ref or {}).get('id') or '')
        if (kind_raw, rid) in cited_ids:
            continue
        filename_refs.append((label, kind_raw, rid, ref))
    # Longest-label-first so a filename isn't consumed by a shorter prefix match.
    filename_refs.sort(key=lambda t: -len(t[0]))
    for label, kind_raw, rid, ref in filename_refs:
        # Only substitute the first occurrence to avoid runaway replacement.
        pattern = re.compile(r'(?<![\w/\-])' + re.escape(label) + r'(?![\w])')
        def _auto(_m, _kind=kind_raw, _rid=rid, _ref=ref):
            pills.append((_kind, _rid, _ref))
            return f'SWPILL{len(pills)-1}ENDPILL'
        text, n = pattern.subn(_auto, text, count=1)

    # Step 2: markdown -> HTML
    html = _md.markdown(text, extensions=_MD_EXTENSIONS, output_format='html')

    # Step 3: sanitize
    html = bleach.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        protocols=['http', 'https', 'mailto'],
        strip=True,
    )

    # Step 4: restore pills
    def _restore(match):
        idx = int(match.group(1))
        if idx >= len(pills):
            return match.group(0)
        kind_raw, rid, ref = pills[idx]
        return _build_pill_html(ref, kind_raw, rid)

    html = re.sub(r'SWPILL(\d+)ENDPILL', _restore, html)
    html = html.replace('SWBROKENPILL', _BROKEN_MARKER)

    return mark_safe(html)