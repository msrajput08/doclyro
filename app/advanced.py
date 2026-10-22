"""Interactive-editor commands, PDF form widgets and reusable workflows.

All page coordinates are PDF points in the unrotated page coordinate system.
Only bounded declarative actions are accepted; uploaded image bytes are decoded and
re-encoded with Pillow, not embedded verbatim.
"""
from __future__ import annotations
import base64
import io
import json
import re
from pathlib import Path

import fitz
from PIL import Image


def read_elements(value, limit=200):
    if isinstance(value, str):
        try: value = json.loads(value)
        except ValueError: raise ValueError('Editor elements must be JSON.')
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError(f'Provide a list of at most {limit} editor elements.')
    if any(not isinstance(item, dict) for item in value):
        raise ValueError('Every editor element must be an object.')
    return value


def num(value, default=0, low=-50000, high=50000):
    try: v = float(default if value is None else value)
    except (ValueError, TypeError): raise ValueError('Invalid drawing coordinate.')
    if not low <= v <= high: raise ValueError('Drawing coordinate out of range.')
    return v


def color(value, default='#273043'):
    v = str(value or default).strip()
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', v): raise ValueError('Invalid hex color.')
    return tuple(int(v[n:n+2],16)/255 for n in (1,3,5))


def image_stream(data_uri):
    s = str(data_uri or '')
    if not re.match(r'^data:image/(png|jpeg|webp);base64,',s):
        raise ValueError('Upload a PNG, JPEG or WebP image.')
    data=s.split(',',1)[1]
    if len(data) > 6_000_000: raise ValueError('Image is too large (4 MB max).')
    try:
        raw = base64.b64decode(data,validate=True)
        with Image.open(io.BytesIO(raw)) as im:
            im.load()
            if im.width*im.height > 16_000_000: raise ValueError('Image dimensions are too large.')
            converted=im.convert('RGBA')
            output=io.BytesIO(); converted.save(output,format='PNG',optimize=True)
            return output.getvalue()
    except (OSError, ValueError) as ex:
        raise ValueError('Invalid uploaded image: '+str(ex))


def field_widget(page, entry):
    field = str(entry.get('name') or entry.get('text') or '').strip()[:100]
    if not field: raise ValueError('Enter a form field name.')
    x=num(entry.get('x'),72);y=num(entry.get('y'),100)
    w=num(entry.get('w'),190,14,2000);h=num(entry.get('h'),28,12,1000)
    rect=fitz.Rect(x,y,x+w,y+h)
    if not page.rect.contains(rect): raise ValueError('Field must fit inside the PDF page.')
    widget=fitz.Widget();widget.field_name=field;widget.rect=rect
    typ=entry['type']
    if typ in ('field-text','field-multiline'):
        widget.field_type=fitz.PDF_WIDGET_TYPE_TEXT
        if typ=='field-multiline':widget.field_flags=fitz.PDF_TX_FIELD_IS_MULTILINE
        widget.field_value=str(entry.get('value',''))[:3000]
    elif typ=='field-checkbox':
        widget.field_type=fitz.PDF_WIDGET_TYPE_CHECKBOX
    elif typ in ('field-dropdown','field-listbox'):
        widget.field_type=fitz.PDF_WIDGET_TYPE_COMBOBOX if typ=='field-dropdown' else fitz.PDF_WIDGET_TYPE_LISTBOX
        choices=entry.get('choices',[])
        if isinstance(choices,str): choices=[c.strip() for c in choices.split(',')]
        if not isinstance(choices,list) or not 1 <= len(choices) <= 30:
            raise ValueError('Dropdown needs 1–30 comma-separated options.')
        widget.choice_values=[str(x)[:80] for x in choices]
        widget.field_value=widget.choice_values[0]
    else:raise ValueError('Unknown form field type.')
    widget.text_font='Helv';widget.text_fontsize=11
    widget.border_color=(.52,.56,.65);widget.border_width=1
    widget.fill_color=(1,1,1)
    page.add_widget(widget)


def apply_elements(doc, value):
    """Applies additive edits and *permanent* rectangle redactions in two passes."""
    elements = read_elements(value)
    if not elements: raise ValueError('Add at least one element on the page first.')
    grouped={}
    for e in elements:
        try: index=int(e.get('page',1))-1
        except (ValueError,TypeError): raise ValueError('Invalid page number.')
        if index<0 or index>=len(doc): raise ValueError('Editor page does not exist.')
        grouped.setdefault(index,[]).append(e)
    for index, group in grouped.items():
        page=doc[index]
        # Remove underlying content first so overlays are not themselves redacted.
        found=False
        for e in group:
            typ=e.get('type')
            if typ not in ('redact','replace-text'):continue
            if typ=='redact':
                rect=make_rect(e,page)
                page.add_redact_annot(rect,fill=color(e.get('color'),'#000000'))
                found=True
            else:
                needle=str(e.get('search','')).strip()
                if not needle:raise ValueError('Enter text to replace.')
                matches=page.search_for(needle)
                if not matches:raise ValueError(f'Text not found for replacement on page {index+1}.')
                for rect in matches:
                    page.add_redact_annot(rect,fill=(1,1,1));found=True
                e['_replace_rects']=[list(r) for r in matches]
        if found:page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS,graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED,text=fitz.PDF_REDACT_TEXT_REMOVE)
        for e in group:
            typ=e.get('type')
            if typ=='redact':continue
            x=num(e.get('x'),60);y=num(e.get('y'),80)
            stroke=color(e.get('color'))
            thick=num(e.get('thickness'),2,.2,25)
            if typ=='text':
                text=str(e.get('text',''))[:4000]
                if not text:raise ValueError('Enter text for the text element.')
                size=num(e.get('font_size'),16,5,96)
                r=fitz.Rect(x,y,x+num(e.get('w'),280,20,3000),y+num(e.get('h'),100,14,2500))
                remaining=page.insert_textbox(r,text,fontsize=size,fontname='helv',color=stroke,overlay=True)
                if remaining<0:raise ValueError('Text box too small to fit the text.')
            elif typ=='replace-text':
                text=str(e.get('text',''))
                for coords in e['_replace_rects']:
                    r=fitz.Rect(*coords)
                    size=num(e.get('font_size'),max(7,min(14,r.height*.85)),5,72)
                    expanded=fitz.Rect(r.x0,r.y0,r.x1+max(80, len(text)*size*.5),r.y1+size)
                    page.insert_textbox(expanded,text,fontsize=size,color=stroke,fontname='helv')
            elif typ in ('rectangle','highlight','ellipse'):
                r=make_rect(e,page)
                if typ=='ellipse':page.draw_oval(r,color=stroke,width=thick,overlay=True)
                elif typ=='highlight':page.draw_rect(r,fill=stroke,fill_opacity=.25,color=None,overlay=True)
                else:page.draw_rect(r,color=stroke,width=thick,overlay=True)
            elif typ=='line':
                x2=num(e.get('x2'),x+100);y2=num(e.get('y2'),y+20)
                page.draw_line((x,y),(x2,y2),color=stroke,width=thick,overlay=True)
            elif typ=='freehand':
                pts=e.get('points')
                if not isinstance(pts,list) or not 2<=len(pts)<=3000:
                    raise ValueError('Freehand drawing requires 2–3000 points.')
                points=[(num(p[0]),num(p[1])) for p in pts if isinstance(p,list) and len(p)==2]
                if len(points)!=len(pts):raise ValueError('Invalid freehand path.')
                shape=page.new_shape();shape.draw_polyline(points);shape.finish(color=stroke,width=thick,closePath=False);shape.commit()
            elif typ=='image':
                r=make_rect(e,page)
                page.insert_image(r,stream=image_stream(e.get('data')),keep_proportion=True,overlay=True)
            elif typ=='sticky-note':
                page.add_text_annot((x,y),str(e.get('text','Review this section'))[:2000])
            elif typ=='link':
                url=str(e.get('url') or e.get('text') or '').strip()
                if not re.fullmatch(r'https://[A-Za-z0-9._~:/?#\[\]@!$&\'()*+,;=%-]{1,1800}',url):
                    raise ValueError('Link must be a safe HTTPS URL.')
                page.insert_link({'kind':fitz.LINK_URI,'uri':url,'from':make_rect(e,page)})
            elif typ in ('field-text','field-multiline','field-checkbox','field-dropdown','field-listbox'):
                field_widget(page,e)
            else:raise ValueError('Unsupported editor element: '+str(typ))
    return len(elements)


def make_rect(e,page):
    x=num(e.get('x'),40);y=num(e.get('y'),40)
    w=num(e.get('w'),100,2,3000);h=num(e.get('h'),40,2,3000)
    r=fitz.Rect(x,y,x+w,y+h)
    if not page.rect.intersects(r):raise ValueError('Element falls outside the PDF page.')
    return r


def detect_labeled_fields(doc):
    """Heuristic labelled-blank detection, returns candidates for manual verification."""
    patterns=re.compile(r'\b(name|full name|email|phone|mobile|date|address|signature|company|department|student id)\s*[:：]',re.I)
    fields=[]
    for i,page in enumerate(doc):
        if len(fields)>=60:break
        for line in page.get_text('blocks'):
            if len(fields)>=60:break
            x0,y0,x1,y1,text,*_=line
            match=patterns.search(str(text)[:180])
            if not match:continue
            label=match.group(1).title().replace(' ','_')
            x=max(20,min(page.rect.width-130,x1+8))
            y=max(10,min(page.rect.height-28,y0-1))
            fields.append({'page':i+1,'type':'field-text','name':f'{label}_{i+1}_{len(fields)+1}',
                           'x':round(x,1),'y':round(y,1),'w':min(175,round(page.rect.width-x-10,1)), 'h':24})
    return fields
