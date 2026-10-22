"""Interactive comparison page renderer, independent of any browser UI."""
from __future__ import annotations
import base64
import io
from pathlib import Path

import fitz
from PIL import Image, ImageChops, ImageFilter


def _render(doc: fitz.Document, page_no: int, target_width: int) -> Image.Image | None:
    if page_no >= len(doc):
        return None
    page = doc[page_no]
    if page.rect.width <= 0 or page.rect.height <= 0:
        raise ValueError('Invalid PDF page dimensions.')
    scale = min(target_width / page.rect.width, 1100 / page.rect.height, 2.5)
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    return Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB')


def _encode(im: Image.Image) -> str:
    dest = io.BytesIO()
    im.save(dest, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(dest.getvalue()).decode('ascii')


def compare_page(original: Path, revised: Path, page: int, target_width: int = 720,
                 password: str = '') -> dict:
    """Render two PDFs at matched pixel coordinates for a slider/overlay UI.

    Diff percentage is an *illustrative, rendered pixel comparison*, not a
    measure of semantic, textual or legal document equivalence.
    """
    if not 1 <= page <= 500:
        raise ValueError('Page number must be between 1 and 500.')
    if not 320 <= target_width <= 1200:
        raise ValueError('Preview width must be between 320 and 1200 pixels.')
    from .processor import pdfopen
    with pdfopen(original, {'password': password}) as a, pdfopen(revised, {'password': password}) as b:
        total = max(len(a), len(b))
        if total > 500:
            raise ValueError('Interactive preview is limited to 500 pages per file.')
        if page > total:
            raise ValueError('Page does not exist in the comparison.')
        i = page - 1
        before, after = _render(a, i, target_width), _render(b, i, target_width)
        w = max(before.width if before else 0, after.width if after else 0)
        h = max(before.height if before else 0, after.height if after else 0)
        if not w or not h:
            raise ValueError('Both input pages are empty.')
        old = Image.new('RGB', (w,h), 'white')
        new = Image.new('RGB', (w,h), 'white')
        if before: old.paste(before, (0,0))
        if after: new.paste(after, (0,0))
        diff = ImageChops.difference(old, new).convert('L')
        # 28 gray-level sensitivity ignores many subpixel antialiasing changes.
        mask = diff.point(lambda px: 255 if px > 28 else 0)
        num_changed = mask.histogram()[255]
        diff_mask = mask.filter(ImageFilter.MaxFilter(3))
        highlighted = new.copy()
        highlighted.paste(Image.new('RGB',(w,h),(248,112,135)),(0,0),diff_mask)
        text_a = a[i].get_text('text',sort=True) if i < len(a) else ''
        text_b = b[i].get_text('text',sort=True) if i < len(b) else ''
        return {
            'page': page,
            'total_pages': total,
            'original_page_exists': i < len(a),
            'revised_page_exists': i < len(b),
            'changed_pixels_percent': round(100 * num_changed / (w*h), 2),
            'text_changed': text_a != text_b,
            'width': w,
            'height': h,
            'original': _encode(old),
            'revised': _encode(new),
            'highlighted': _encode(highlighted),
        }
