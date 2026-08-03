"""
Wahabix Medicare Solution — PDF Report Service
==============================================
Architecture: OOP with a single abstract BaseClinicPDF that handles
branding (header, footer, logo, watermark) and page layout.
Every concrete report class overrides `build_story()` only.

Usage:
    from apps.core.services.pdf_service import LabReportPDF, PrescriptionPDF
    pdf = LabReportPDF(order, clinic)
    return pdf.as_response()          # → HttpResponse (inline)
    return pdf.as_download_response() # → HttpResponse (attachment)
"""
from __future__ import annotations
from django.utils import timezone

import io
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from django.http import HttpResponse

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, HRFlowable, Image, PageTemplate,
    Paragraph, Spacer, Table, TableStyle, KeepTogether,
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import re as _re

# ─── Urdu / Nastaliq font (optional, pluggable) ────────────────────────────
# ReportLab's built-in fonts (Helvetica etc.) have ZERO Urdu/Arabic glyphs —
# they render as blank boxes or raise encoding errors. Proper Nastaliq
# shaping also needs a real font file, which isn't bundled with this repo
# (no font file was available to include). To enable Urdu instructions in
# the DOWNLOADABLE PDF (the HTML "Print Letterhead" already renders Urdu
# correctly via the browser — no action needed there):
#   1. Download a free Urdu font, e.g. "Noto Nastaliq Urdu"
#      (fonts.google.com/noto/specimen/Noto+Nastaliq+Urdu)
#   2. Save it as: static/fonts/NotoNastaliqUrdu-Regular.ttf
#   3. Restart the server — it's auto-detected below, no code changes needed.
URDU_FONT_NAME = 'Helvetica'  # falls back to this if no Urdu font is found
_URDU_FONT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    'static', 'fonts', 'NotoNastaliqUrdu-Regular.ttf'
)
try:
    if os.path.exists(_URDU_FONT_PATH):
        pdfmetrics.registerFont(TTFont('UrduNastaliq', _URDU_FONT_PATH))
        URDU_FONT_NAME = 'UrduNastaliq'
except Exception:
    pass  # keep the Helvetica fallback — never let a bad font file crash PDF generation

_URDU_RANGE = _re.compile(r'[\u0600-\u06FF\u0750-\u077F]')  # Arabic/Urdu Unicode block


def contains_urdu(text: str) -> bool:
    return bool(text) and bool(_URDU_RANGE.search(text))


_NUM_RANGE_PATTERNS = [
    # "70-140", "70 – 140", "3.4 - 7.0 mg/dL" — two numbers = low/high band
    _re.compile(r'(-?\d+\.?\d*)\s*(?:-|–|to)\s*(-?\d+\.?\d*)'),
]
_LESS_THAN_PATTERN = _re.compile(r'(?:normal:?\s*)?<\s*=?\s*(-?\d+\.?\d*)')
_GREATER_THAN_PATTERN = _re.compile(r'(?:normal:?\s*)?>\s*=?\s*(-?\d+\.?\d*)')


def auto_detect_abnormal(result_value: str, reference_range: str):
    """
    Determines whether a numeric result falls outside its reference range,
    parsed straight from the free-text range (handles the common patterns
    lab staff actually type: "70-140 mg/dL", "3.4 - 7.0", "Normal: < 5.7",
    "< 200 mg/dL", etc). Returns True/False when it can tell, or None when
    the range/result isn't numeric (e.g. "Negative", "Non-Reactive",
    "Normal Sinus Rhythm") — those stay exactly as manually flagged.

    This exists because relying purely on a person remembering to tick an
    "abnormal" checkbox at data-entry time is exactly the kind of thing
    that gets missed under real clinic workload — a genuinely out-of-range
    number should never silently print looking "normal".
    """
    if not result_value or not reference_range:
        return None
    try:
        value = float(_re.sub(r'[^\d.\-]', '', result_value.strip().split()[0]))
    except (ValueError, IndexError):
        return None

    range_match = _NUM_RANGE_PATTERNS[0].search(reference_range)
    if range_match:
        try:
            low, high = float(range_match.group(1)), float(range_match.group(2))
            if low > high:
                low, high = high, low
            return value < low or value > high
        except ValueError:
            pass

    lt_match = _LESS_THAN_PATTERN.search(reference_range)
    if lt_match:
        try:
            return value >= float(lt_match.group(1))
        except ValueError:
            pass

    gt_match = _GREATER_THAN_PATTERN.search(reference_range)
    if gt_match:
        try:
            return value <= float(gt_match.group(1))
        except ValueError:
            pass

    return None


def is_result_abnormal(result) -> bool:
    """Auto-detected abnormality takes precedence over the manual flag
    whenever the reference range is actually numeric/parseable — a real
    out-of-range number should never be shown as normal just because no
    one ticked a box. Falls back to the manual flag for non-numeric
    results (Negative/Positive/Reactive/etc) where auto-detection can't
    apply."""
    auto = auto_detect_abnormal(getattr(result, 'result_value', ''), getattr(result.test, 'reference_range', ''))
    return auto if auto is not None else result.is_abnormal


def safe_instruction_text(text: str) -> str:
    """
    Returns text safe to render in the PDF's default (Helvetica) font.
    If Urdu is present and no real Urdu font is registered, it's replaced
    with a clear placeholder instead of crashing PDF generation or
    silently showing blank boxes — the HTML "Print Letterhead" version
    always has the real Urdu text regardless.
    """
    if contains_urdu(text) and URDU_FONT_NAME == 'Helvetica':
        return '(Urdu instructions — see printed letterhead copy or Patient Portal)'
    return text

# ─── Brand palette ────────────────────────────────────────────────────────────
PRIMARY      = colors.HexColor('#0ea5e9')   # sky blue accent
PRIMARY_DARK = colors.HexColor('#0369a1')   # darker header
BG_HEADER    = colors.HexColor('#0f172a')   # near-black header bg
BG_ROW_ALT   = colors.HexColor('#f0f9ff')   # alternating row tint
DANGER       = colors.HexColor('#ef4444')
WARNING      = colors.HexColor('#f59e0b')
SUCCESS      = colors.HexColor('#10b981')
MUTED        = colors.HexColor('#64748b')
BLACK        = colors.HexColor('#0f172a')
WHITE        = colors.white
BORDER       = colors.HexColor('#e2e8f0')
GREEN_LIGHT  = colors.HexColor('#dcfce7')
RED_LIGHT    = colors.HexColor('#fee2e2')

# ─── Shared styles ────────────────────────────────────────────────────────────
_base = getSampleStyleSheet()

def _style(name, **kw) -> ParagraphStyle:
    s = ParagraphStyle(name, **kw)
    return s

S_H1 = _style('wms_h1', fontName='Helvetica-Bold', fontSize=18,
               textColor=BLACK, spaceAfter=2)
S_H2 = _style('wms_h2', fontName='Helvetica-Bold', fontSize=12,
               textColor=PRIMARY_DARK, spaceAfter=4, spaceBefore=8)
S_H3 = _style('wms_h3', fontName='Helvetica-Bold', fontSize=10,
               textColor=BLACK, spaceAfter=2)
S_BODY = _style('wms_body', fontName='Helvetica', fontSize=9,
                textColor=BLACK, leading=14)
S_SMALL = _style('wms_small', fontName='Helvetica', fontSize=8,
                 textColor=MUTED, leading=11)
S_CENTER = _style('wms_center', fontName='Helvetica', fontSize=9,
                  alignment=TA_CENTER, textColor=BLACK, leading=14)
S_RIGHT = _style('wms_right', fontName='Helvetica', fontSize=9,
                 alignment=TA_RIGHT, textColor=BLACK, leading=14)
S_LABEL = _style('wms_label', fontName='Helvetica-Bold', fontSize=8,
                 textColor=MUTED, spaceAfter=0)
S_VALUE = _style('wms_value', fontName='Helvetica', fontSize=9,
                 textColor=BLACK, leading=13)
S_TH = _style('wms_th', fontName='Helvetica-Bold', fontSize=9,
              textColor=WHITE, alignment=TA_CENTER)
S_TD = _style('wms_td', fontName='Helvetica', fontSize=9,
              textColor=BLACK, leading=13)
S_TD_C = _style('wms_td_c', fontName='Helvetica', fontSize=9,
                textColor=BLACK, alignment=TA_CENTER, leading=13)
S_TD_R = _style('wms_td_r', fontName='Helvetica', fontSize=9,
                textColor=BLACK, alignment=TA_RIGHT, leading=13)
S_DANGER = _style('wms_danger', fontName='Helvetica-Bold', fontSize=9,
                  textColor=DANGER, leading=13)
S_SUCCESS = _style('wms_success', fontName='Helvetica-Bold', fontSize=9,
                   textColor=SUCCESS, leading=13)

def _table_style(has_alt_rows=True, header_bg=None) -> TableStyle:
    """Standard professional table style."""
    hbg = header_bg or PRIMARY_DARK
    cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), hbg),
        ('TEXTCOLOR',  (0, 0), (-1, 0), WHITE),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, 0), 8),
        ('ROWBACKGROUND', (0, 1), (-1, -1), WHITE),
        ('FONTNAME',   (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',   (0, 1), (-1, -1), 8.5),
        ('GRID',       (0, 0), (-1, -1), 0.4, BORDER),
        ('LINEBELOW',  (0, 0), (-1, 0), 1, PRIMARY),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
    ]
    return TableStyle(cmds)


# ─── Abstract base ────────────────────────────────────────────────────────────
class BaseClinicPDF(ABC):
    """
    Abstract base class for all clinic PDF reports.
    Handles: A4 page layout, clinic logo + header, professional footer with
    page numbers, watermark-style report type label, and the ReportLab
    BaseDocTemplate plumbing.

    Concrete subclasses must implement `build_story()` which returns a list
    of Platypus flowables representing the body of the report.
    """

    # Override in subclasses
    REPORT_TITLE: str = 'Report'
    REPORT_SUBTITLE: str = ''
    FILENAME_PREFIX: str = 'report'

    PAGE_W, PAGE_H = A4
    MARGIN_L = 18 * mm
    MARGIN_R = 18 * mm
    MARGIN_T = 22 * mm
    MARGIN_B = 20 * mm
    HEADER_H = 28 * mm   # space reserved for header on every page
    FOOTER_H = 14 * mm

    def __init__(self, clinic, generated_by: str = ''):
        self.clinic = clinic
        self.generated_by = generated_by
        self.generated_at = datetime.now().strftime('%d %b %Y, %I:%M %p')
        self._buffer = io.BytesIO()

    # ── Public API ────────────────────────────────────────────────────────────
    def as_response(self) -> HttpResponse:
        """Return HTTP response with PDF inline (browser preview)."""
        self._render()
        self._buffer.seek(0)
        resp = HttpResponse(self._buffer, content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="{self._filename()}"'
        return resp

    def as_download_response(self) -> HttpResponse:
        """Return HTTP response with PDF as a file download."""
        self._render()
        self._buffer.seek(0)
        resp = HttpResponse(self._buffer, content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="{self._filename()}"'
        return resp

    # ── Internal ──────────────────────────────────────────────────────────────
    def _filename(self) -> str:
        stamp = datetime.now().strftime('%Y%m%d_%H%M')
        safe = self.clinic.name.replace(' ', '_').replace('/', '-')[:20]
        return f'{self.FILENAME_PREFIX}_{safe}_{stamp}.pdf'

    def _render(self):
        doc = BaseDocTemplate(
            self._buffer,
            pagesize=A4,
            leftMargin=self.MARGIN_L,
            rightMargin=self.MARGIN_R,
            topMargin=self.MARGIN_T + self.HEADER_H,
            bottomMargin=self.MARGIN_B + self.FOOTER_H,
        )
        frame = Frame(
            self.MARGIN_L,
            self.MARGIN_B + self.FOOTER_H,
            self.PAGE_W - self.MARGIN_L - self.MARGIN_R,
            self.PAGE_H - self.MARGIN_T - self.HEADER_H - self.MARGIN_B - self.FOOTER_H,
            id='main',
        )
        template = PageTemplate(
            id='wms',
            frames=[frame],
            onPage=self._draw_page,
        )
        doc.addPageTemplates([template])
        doc.build(self.build_story())

    def _draw_page(self, canvas, doc):
        canvas.saveState()
        self._draw_header(canvas, doc)
        self._draw_footer(canvas, doc)
        canvas.restoreState()

    def _draw_header(self, canvas, doc):
        """Professional clinic header with logo on every page."""
        w, h = self.PAGE_W, self.PAGE_H
        # Header background band
        canvas.setFillColor(BG_HEADER)
        canvas.rect(0, h - self.MARGIN_T - self.HEADER_H,
                    w, self.HEADER_H + self.MARGIN_T, fill=1, stroke=0)
        # Accent bottom line
        canvas.setFillColor(PRIMARY)
        canvas.rect(0, h - self.MARGIN_T - self.HEADER_H - 2,
                    w, 2, fill=1, stroke=0)

        # --- Clinic logo ---
        logo_x = self.MARGIN_L
        logo_y = h - self.MARGIN_T - self.HEADER_H + 4 * mm
        logo_size = 18 * mm
        try:
            if self.clinic.logo and os.path.exists(self.clinic.logo.path):
                canvas.drawImage(
                    self.clinic.logo.path,
                    logo_x, logo_y, logo_size, logo_size,
                    preserveAspectRatio=True, mask='auto',
                )
            else:
                self._draw_fallback_logo(canvas, logo_x, logo_y, logo_size)
        except Exception:
            self._draw_fallback_logo(canvas, logo_x, logo_y, logo_size)

        # --- Clinic name + contact ---
        name_x = logo_x + logo_size + 5 * mm
        canvas.setFillColor(WHITE)
        canvas.setFont('Helvetica-Bold', 14)
        canvas.drawString(name_x, h - self.MARGIN_T - 9 * mm,
                          self.clinic.name)
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#94a3b8'))
        contact = []
        if self.clinic.phone:
            contact.append(f'Tel: {self.clinic.phone}')
        if getattr(self.clinic, 'email', ''):
            contact.append(self.clinic.email)
        if self.clinic.address:
            contact.append(self.clinic.address[:60])
        for i, line in enumerate(contact[:2]):
            canvas.drawString(name_x,
                              h - self.MARGIN_T - 14 * mm - i * 4 * mm,
                              line)

        # --- Report type badge (right side) ---
        badge_w = 52 * mm
        badge_x = w - self.MARGIN_R - badge_w
        badge_y = h - self.MARGIN_T - self.HEADER_H + 4 * mm
        canvas.setFillColor(PRIMARY)
        canvas.roundRect(badge_x, badge_y, badge_w, 14 * mm, 3, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont('Helvetica-Bold', 9)
        canvas.drawCentredString(badge_x + badge_w / 2,
                                 badge_y + 4.5 * mm,
                                 self.REPORT_TITLE.upper())
        if self.REPORT_SUBTITLE:
            canvas.setFont('Helvetica', 7)
            canvas.setFillColor(colors.HexColor('#bae6fd'))
            canvas.drawCentredString(badge_x + badge_w / 2,
                                     badge_y + 1.5 * mm,
                                     self.REPORT_SUBTITLE)

        # Page number (top-right corner)
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.HexColor('#94a3b8'))
        canvas.drawRightString(w - self.MARGIN_R,
                               h - self.MARGIN_T - 4 * mm,
                               f'Page {doc.page}')

    def _draw_fallback_logo(self, canvas, x, y, size):
        """Draw a clean monogram box when no logo is uploaded."""
        canvas.setFillColor(PRIMARY)
        canvas.roundRect(x, y, size, size, 4, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont('Helvetica-Bold', 14)
        initial = self.clinic.name[0].upper() if self.clinic.name else 'W'
        canvas.drawCentredString(x + size / 2, y + size / 3, initial)

    def _draw_footer(self, canvas, doc):
        """Footer with divider line, generated info, and confidentiality note."""
        y = self.MARGIN_B + self.FOOTER_H - 2 * mm
        # Divider
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.6)
        canvas.line(self.MARGIN_L, y + 8 * mm,
                    self.PAGE_W - self.MARGIN_R, y + 8 * mm)
        # Left: generated info
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(self.MARGIN_L, y + 4 * mm,
                          f'Generated: {self.generated_at}')
        if self.generated_by:
            canvas.drawString(self.MARGIN_L, y,
                              f'By: {self.generated_by}')
        # Right: confidentiality
        canvas.drawRightString(self.PAGE_W - self.MARGIN_R, y + 4 * mm,
                               'CONFIDENTIAL — For authorized use only')
        canvas.drawRightString(self.PAGE_W - self.MARGIN_R, y,
                               f'{self.clinic.name} — Powered by Wahabix Medicare')

    # ── Helpers available to all subclasses ───────────────────────────────────
    def _section(self, title: str) -> list:
        """Returns a styled section heading with an accent underline."""
        return [
            Spacer(1, 6),
            Paragraph(title, S_H2),
            HRFlowable(width='100%', thickness=1, color=PRIMARY,
                       spaceAfter=6, spaceBefore=0),
        ]

    def _info_grid(self, rows: list[tuple[str, str]], cols: int = 2) -> Table:
        """
        Renders a label/value grid (like a patient info card).
        rows: [('Label', 'Value'), ...]
        cols: how many label-value pairs per row (1 or 2)
        """
        usable_w = self.PAGE_W - self.MARGIN_L - self.MARGIN_R
        if cols == 2:
            col_w = [28 * mm, usable_w / 2 - 28 * mm - 4 * mm,
                     28 * mm, usable_w / 2 - 28 * mm]
        else:
            col_w = [32 * mm, usable_w - 32 * mm]

        data = []
        if cols == 2:
            for i in range(0, len(rows), 2):
                l1, v1 = rows[i]
                l2, v2 = rows[i + 1] if i + 1 < len(rows) else ('', '')
                data.append([
                    Paragraph(l1, S_LABEL), Paragraph(safe_instruction_text(str(v1)), S_VALUE),
                    Paragraph(l2, S_LABEL), Paragraph(safe_instruction_text(str(v2)), S_VALUE),
                ])
        else:
            for l, v in rows:
                data.append([Paragraph(l, S_LABEL), Paragraph(safe_instruction_text(str(v)), S_VALUE)])

        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('GRID',       (0, 0), (-1, -1), 0.4, BORDER),
            ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING',   (0, 0), (-1, -1), 7),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 7),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (0, -1), MUTED),
            ('FONTSIZE', (0, 0), (0, -1), 7.5),
            ('FONTSIZE', (1, 0), (-1, -1), 9),
        ])
        if cols == 2:
            style.add('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold')
            style.add('TEXTCOLOR', (2, 0), (2, -1), MUTED)
            style.add('FONTSIZE', (2, 0), (2, -1), 7.5)
        return Table(data, colWidths=col_w, style=style, hAlign='LEFT')

    def _amount_table(self, rows: list[tuple[str, str]],
                      total_label='TOTAL', total_value='') -> Table:
        """Totals/summary table (right-aligned, used at end of invoices)."""
        usable_w = self.PAGE_W - self.MARGIN_L - self.MARGIN_R
        data = [[Paragraph(l, S_LABEL), Paragraph(str(v), S_TD_R)]
                for l, v in rows]
        # Total row
        data.append([
            Paragraph(total_label, _style('tot_l', fontName='Helvetica-Bold',
                                          fontSize=10, textColor=WHITE,
                                          alignment=TA_LEFT)),
            Paragraph(str(total_value), _style('tot_r', fontName='Helvetica-Bold',
                                               fontSize=10, textColor=WHITE,
                                               alignment=TA_RIGHT)),
        ])
        n = len(data)
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, -2), colors.HexColor('#f8fafc')),
            ('BACKGROUND', (0, n - 1), (-1, n - 1), PRIMARY_DARK),
            ('GRID',       (0, 0), (-1, -1), 0.4, BORDER),
            ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING',   (0, 0), (-1, -1), 10),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
        ])
        label_w = 45 * mm
        return Table(data, colWidths=[usable_w - label_w - 35 * mm, 35 * mm],
                     style=style, hAlign='RIGHT')

    @abstractmethod
    def build_story(self) -> list:
        """Return a list of ReportLab Platypus flowables for the report body."""
        ...


# ═════════════════════════════════════════════════════════════════════════════
# 1. LAB RESULT REPORT
# ═════════════════════════════════════════════════════════════════════════════
class LabReportPDF(BaseClinicPDF):
    REPORT_TITLE = 'Lab Report'
    REPORT_SUBTITLE = 'Diagnostic Results'
    FILENAME_PREFIX = 'lab_report'

    def __init__(self, order, clinic, generated_by='', is_online_copy=False):
        super().__init__(clinic, generated_by)
        self.order = order
        self.is_online_copy = is_online_copy
        self.results = {r.test_id: r for r in order.results.filter(is_deleted=False).select_related('test')}

    def build_story(self) -> list:
        o = self.order
        story = []

        # ── Online-copy / court-validity badges — ONLY when this PDF is
        #    being generated for the Patient Portal (self-service copy).
        #    The staff-facing report (Lab dashboard view/print/download)
        #    is the official copy and should NOT carry this watermark.
        if self.is_online_copy:
            badge_row = Table(
                [[Paragraph('<b>ONLINE COPY</b>',
                            _style('badge_l', fontName='Helvetica-Bold', fontSize=9,
                                   textColor=colors.HexColor('#334155'), borderWidth=0.75,
                                   borderColor=BORDER, borderPadding=4)),
                  Paragraph('Not valid for court', S_RIGHT)]],
                colWidths=[45 * mm, (self.PAGE_W - self.MARGIN_L - self.MARGIN_R) - 45 * mm],
                style=TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]),
            )
            story.append(badge_row)
            story.append(Spacer(1, 8))

        # ── Order meta card ──────────────────────────────────────────────────
        story += self._section('Patient & Order Information')
        story.append(self._info_grid([
            ('Patient Name', o.patient.full_name),
            ('Patient ID',   o.patient.patient_id),
            ('Age / Gender', f"{o.patient.age} yrs / {o.patient.get_gender_display()}"),
            ('Blood Group',  o.patient.blood_group or '—'),
            ('Voucher Code', o.voucher_code),
            ('Report Status', 'FINAL REPORT' if o.status in ('completed', 'delivered') else o.get_status_display().upper()),
            ('Referred By',  o.doctor_name or '—'),
            ('Visit Date',   o.ordered_at.strftime('%d %b %Y, %I:%M %p')),
            ('Sample Collected', o.sample_collected_at.strftime('%d %b %Y, %I:%M %p') if o.sample_collected_at else '—'),
            ('Report Generated', timezone.now().strftime('%d %b %Y, %I:%M %p')),
        ]))
        story.append(Spacer(1, 6))

        # ── Results table (grouped by category, with a Last Available
        #    Result column comparing against the patient's most recent
        #    prior result for the same test — matches the physical lab
        #    report convention) ────────────────────────────────────────────
        story += self._section('Test Results')
        usable_w = self.PAGE_W - self.MARGIN_L - self.MARGIN_R
        headers = [
            Paragraph('Test Name', S_TH),
            Paragraph('Result', S_TH),
            Paragraph('*Last Available', S_TH),
            Paragraph('Unit', S_TH),
            Paragraph('Reference Range', S_TH),
        ]
        col_w = [48 * mm, 22 * mm, 26 * mm, 15 * mm, 69 * mm]
        data = [headers]
        row_styles = []  # (row_index, is_category_header, is_abnormal)

        from apps.laboratory.models import LabResult

        tests_by_category = {}
        for test in o.tests.all():
            tests_by_category.setdefault(test.get_category_display(), []).append(test)

        for category_name, tests in tests_by_category.items():
            # Category header bar spanning the full table width.
            data.append([Paragraph(f'<b>{category_name}</b>', S_H3), '', '', '', ''])
            row_styles.append(('category', len(data) - 1))

            for test in tests:
                res = self.results.get(test.pk)
                last_result = (
                    LabResult.objects.filter(test=test, order__patient=o.patient, is_deleted=False)
                    .exclude(order=o).order_by('-order__ordered_at').first()
                )
                last_val = f"{last_result.result_value}\n({last_result.order.ordered_at.strftime('%d-%b-%Y')})" if last_result else '—'

                if res:
                    abnormal = is_result_abnormal(res)
                    result_style = S_DANGER if abnormal else S_TD
                    data.append([
                        Paragraph(test.test_name, S_TD),
                        Paragraph(f"<b>{res.result_value}</b>" if abnormal else res.result_value, result_style),
                        Paragraph(last_val, S_SMALL),
                        Paragraph(test.unit or '—', S_TD_C),
                        Paragraph(test.reference_range, S_TD),
                    ])
                    if abnormal:
                        row_styles.append(('abnormal', len(data) - 1))
                else:
                    data.append([
                        Paragraph(test.test_name, S_TD),
                        Paragraph('Pending', _style('p_muted', fontName='Helvetica', fontSize=9, textColor=MUTED)),
                        Paragraph(last_val, S_SMALL),
                        Paragraph(test.unit or '—', S_TD_C),
                        Paragraph(test.reference_range, S_TD),
                    ])

        ts = _table_style()
        for kind, idx in row_styles:
            if kind == 'category':
                ts.add('SPAN', (0, idx), (-1, idx))
                ts.add('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#e2e8f0'))
            elif kind == 'abnormal':
                ts.add('BACKGROUND', (0, idx), (-1, idx), RED_LIGHT)
        table = Table(data, colWidths=col_w, style=ts, repeatRows=1)
        story.append(table)
        story.append(Paragraph(
            '*Last Available Result shows the same test from this patient\'s most recent prior visit, if any.',
            _style('last_avail_note', fontName='Helvetica-Oblique', fontSize=7, textColor=MUTED)))

        # ── Remarks ──────────────────────────────────────────────────────────
        remarks = [(t.test_name, self.results[t.pk].remarks)
                   for t in o.tests.all()
                   if t.pk in self.results and self.results[t.pk].remarks]
        if remarks:
            story += self._section('Technician Remarks')
            for name, remark in remarks:
                story.append(Paragraph(f'<b>{name}:</b> {remark}', S_BODY))

        # ── Disclaimer ───────────────────────────────────────────────────────
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER))
        story.append(Spacer(1, 4))
        disclaimer = (
            'This report is generated electronically and is valid without a signature. '
            'Results should be interpreted by a qualified clinician in context of the patient\'s '
            'clinical presentation. In case of discrepancy, please contact the laboratory.'
        )
        story.append(Paragraph(disclaimer,
                               _style('disc', fontName='Helvetica-Oblique', fontSize=7.5,
                                      textColor=MUTED, leading=11)))

        if getattr(o.patient, 'portal_password_hash', ''):
            story.append(Spacer(1, 8))
            care_data = [[Paragraph(
                f'<b>Online Patient Care:</b> View this and past reports anytime at the Patient Portal '
                f'using Patient ID <b>{o.patient.patient_id}</b> and your registration password.',
                _style('care_lab', fontName='Helvetica', fontSize=8.5, textColor=MUTED, leading=12))]]
            story.append(Table(
                care_data, colWidths=[self.PAGE_W - self.MARGIN_L - self.MARGIN_R],
                style=TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#eff6ff')),
                    ('BOX', (0, 0), (-1, -1), 0.5, PRIMARY),
                    ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ])))

        # ── Signature block ───────────────────────────────────────────────────
        story.append(Spacer(1, 16))
        sig_data = [
            [Paragraph('_____________________', S_CENTER),
             Paragraph('_____________________', S_CENTER)],
            [Paragraph('Lab Supervisor / Pathologist', S_CENTER),
             Paragraph('Authorized Signatory', S_CENTER)],
        ]
        sig_table = Table(sig_data,
                          colWidths=[(self.PAGE_W - self.MARGIN_L - self.MARGIN_R) / 2] * 2,
                          style=TableStyle([('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
                                            ('ALIGN',  (0, 0), (-1, -1), 'CENTER')]))
        story.append(sig_table)

        # ── QR Verification (Smart Verification & QR Generation) ───────────────
        if getattr(o, 'is_verified', False) and o.verification_hash:
            story.append(Spacer(1, 14))
            story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER))
            story.append(Spacer(1, 8))
            try:
                import qrcode
                verify_url = f"/lab/verify/{o.voucher_code}/{o.verification_hash}/"
                qr_img = qrcode.make(verify_url)
                qr_buf = io.BytesIO()
                qr_img.save(qr_buf, format='PNG')
                qr_buf.seek(0)
                qr_flowable = Image(qr_buf, width=22 * mm, height=22 * mm)
                qr_row = Table(
                    [[qr_flowable, Paragraph(
                        f'<b>✅ QR-Verified Report</b><br/>Scan to confirm authenticity.<br/>'
                        f'Voucher: {o.voucher_code}<br/>Verified: {o.verified_at.strftime("%d %b %Y, %I:%M %p") if o.verified_at else "—"}',
                        _style('qr_txt', fontName='Helvetica', fontSize=8, textColor=MUTED, leading=11))]],
                    colWidths=[24 * mm, (self.PAGE_W - self.MARGIN_L - self.MARGIN_R) - 24 * mm],
                    style=TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]),
                )
                story.append(qr_row)
            except Exception:
                pass  # qrcode not installed — report still prints without QR block
        return story


# ═════════════════════════════════════════════════════════════════════════════
# 2. PRESCRIPTION
# ═════════════════════════════════════════════════════════════════════════════
class PrescriptionPDF(BaseClinicPDF):
    REPORT_TITLE = 'Prescription'
    REPORT_SUBTITLE = 'Medical Rx'
    FILENAME_PREFIX = 'prescription'

    def __init__(self, prescription, clinic, generated_by=''):
        super().__init__(clinic, generated_by)
        self.rx = prescription
        self.medicines = list(prescription.medicines.all())

    def build_story(self) -> list:
        rx = self.rx
        story = []

        # ── Rx# header ───────────────────────────────────────────────────────
        rx_no = f'RX-{rx.pk:04d}'
        story.append(Paragraph(rx_no, _style('rxno', fontName='Helvetica-Bold',
                                              fontSize=20, textColor=PRIMARY_DARK,
                                              spaceAfter=2)))
        story.append(Paragraph(
            rx.visit_date.strftime('%A, %d %B %Y — %I:%M %p'),
            _style('rxdate', fontName='Helvetica', fontSize=9,
                   textColor=MUTED, spaceAfter=8)))

        # ── Patient + Doctor info ─────────────────────────────────────────────
        story += self._section('Patient Information')
        story.append(self._info_grid([
            ('Patient Name', rx.patient.full_name),
            ('Patient ID',   rx.patient.patient_id),
            ('Age / Gender', f"{rx.patient.age} yrs / {rx.patient.get_gender_display()}"),
            ('Blood Group',  rx.patient.blood_group or '—'),
            ('Phone',        rx.patient.phone or '—'),
            ('Allergies',    rx.patient.allergies or 'None reported'),
        ]))
        story.append(Spacer(1, 4))
        if rx.doctor:
            story += self._section('Attending Physician')
            story.append(self._info_grid([
                ('Doctor', f"Dr. {rx.doctor.user.get_full_name()}"),
                ('Specialization', rx.doctor.specialization),
                ('Qualification', rx.doctor.qualification),
                ('PMDC No.', rx.doctor.pmdc_number or '—'),
            ]))

        # ── Clinical notes ────────────────────────────────────────────────────
        story += self._section('Clinical Notes')
        story.append(self._info_grid([
            ('Chief Complaint / Symptoms', rx.symptoms),
            ('', ''),
        ], cols=1))
        story.append(Spacer(1, 2))
        # Diagnosis box
        diag_data = [[Paragraph('DIAGNOSIS', S_LABEL),
                      Paragraph(safe_instruction_text(rx.diagnosis),
                                _style('diag', fontName='Helvetica-Bold',
                                       fontSize=11, textColor=PRIMARY_DARK))]]
        diag_table = Table(diag_data,
                           colWidths=[28 * mm, self.PAGE_W - self.MARGIN_L - self.MARGIN_R - 28 * mm],
                           style=TableStyle([
                               ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#eff6ff')),
                               ('GRID',       (0, 0), (-1, -1), 0.5, PRIMARY),
                               ('TOPPADDING', (0, 0), (-1, -1), 8),
                               ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                               ('LEFTPADDING',   (0, 0), (-1, -1), 10),
                               ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
                           ]))
        story.append(diag_table)

        # ── Medicines ────────────────────────────────────────────────────────
        story += self._section('Prescribed Medicines')
        if self.medicines:
            headers = [Paragraph(h, S_TH)
                       for h in ['#', 'Medicine', 'Dosage', 'Frequency', 'Duration', 'Instructions']]
            data = [headers]
            for i, m in enumerate(self.medicines, 1):
                data.append([
                    Paragraph(str(i), S_TD_C),
                    Paragraph(m.medicine_name, _style('med', fontName='Helvetica-Bold',
                                                       fontSize=9, textColor=BLACK)),
                    Paragraph(m.dosage, S_TD_C),
                    Paragraph(m.frequency, S_TD_C),
                    Paragraph(m.duration, S_TD_C),
                    Paragraph(safe_instruction_text(m.instructions or '—'),
                              _style('med_instr', fontName=URDU_FONT_NAME if contains_urdu(m.instructions or '') else 'Helvetica',
                                     fontSize=9, textColor=MUTED, leading=12,
                                     alignment=TA_RIGHT if contains_urdu(m.instructions or '') else TA_LEFT)),
                ])
            col_w = [8 * mm, 48 * mm, 25 * mm, 25 * mm, 25 * mm, 40 * mm]
            story.append(Table(data, colWidths=col_w, style=_table_style(), repeatRows=1))
        else:
            story.append(Paragraph('No medicines prescribed for this visit.', S_BODY))

        # ── Notes + Follow-up ─────────────────────────────────────────────────
        if rx.notes or rx.follow_up_date:
            story += self._section('Additional Notes')
            note_rows = []
            if rx.notes:
                note_rows.append(('Advice / Notes', rx.notes))
            if rx.follow_up_date:
                note_rows.append(('Follow-up Date',
                                   rx.follow_up_date.strftime('%A, %d %B %Y')))
            story.append(self._info_grid(note_rows, cols=1))

        # ── Doctor signature ──────────────────────────────────────────────────
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER))
        story.append(Spacer(1, 4))
        sig_data = [
            [Paragraph('_______________________', S_CENTER), ''],
            [Paragraph(f"Dr. {rx.doctor.user.get_full_name() if rx.doctor else '—'}", S_CENTER), ''],
            [Paragraph(rx.doctor.specialization if rx.doctor else '', S_SMALL), ''],
        ]
        col_w = [(self.PAGE_W - self.MARGIN_L - self.MARGIN_R) / 2] * 2
        story.append(Table(sig_data, colWidths=col_w,
                           style=TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')])))
        return story


# ═════════════════════════════════════════════════════════════════════════════
# 3. PHARMACY INVOICE
# ═════════════════════════════════════════════════════════════════════════════
class PharmacyInvoicePDF(BaseClinicPDF):
    REPORT_TITLE = 'Pharmacy Invoice'
    REPORT_SUBTITLE = 'Point of Sale'
    FILENAME_PREFIX = 'pharmacy_invoice'

    def __init__(self, sale, clinic, generated_by=''):
        super().__init__(clinic, generated_by)
        self.sale = sale
        self.items = list(sale.items.select_related('medicine').all())

    def build_story(self) -> list:
        s = self.sale
        story = []

        # ── Invoice header ────────────────────────────────────────────────────
        story.append(Paragraph(f'Invoice #{s.invoice_number}',
                               _style('inv_no', fontName='Helvetica-Bold',
                                      fontSize=18, textColor=PRIMARY_DARK, spaceAfter=2)))
        story.append(Paragraph(
            s.created_at.strftime('%A, %d %B %Y — %I:%M %p'),
            _style('inv_date', fontName='Helvetica', fontSize=9,
                   textColor=MUTED, spaceAfter=8)))

        # ── Patient ───────────────────────────────────────────────────────────
        story += self._section('Billed To')
        story.append(self._info_grid([
            ('Patient Name', s.patient_name or 'Walk-in Customer'),
            ('Status', s.get_status_display()),
        ], cols=1))

        # ── Items ─────────────────────────────────────────────────────────────
        story += self._section('Dispensed Medicines')
        headers = [Paragraph(h, S_TH) for h in
                   ['#', 'Medicine', 'Brand', 'Unit', 'Qty', 'Unit Price', 'Total']]
        data = [headers]
        for i, item in enumerate(self.items, 1):
            data.append([
                Paragraph(str(i), S_TD_C),
                Paragraph(item.medicine.name, _style('mname', fontName='Helvetica-Bold',
                                                      fontSize=9, textColor=BLACK)),
                Paragraph(item.medicine.brand or '—', S_TD),
                Paragraph(item.medicine.get_unit_display(), S_TD_C),
                Paragraph(str(item.quantity), S_TD_C),
                Paragraph(f'Rs. {item.unit_price:,.2f}', S_TD_R),
                Paragraph(f'Rs. {item.subtotal:,.2f}', S_TD_R),
            ])
        col_w = [8 * mm, 45 * mm, 28 * mm, 18 * mm, 12 * mm, 25 * mm, 25 * mm]
        story.append(Table(data, colWidths=col_w, style=_table_style(), repeatRows=1))

        # ── Totals ────────────────────────────────────────────────────────────
        story.append(Spacer(1, 8))
        rows = [('Subtotal', f'Rs. {s.subtotal:,.2f}')]
        if s.discount:
            rows.append(('Discount', f'- Rs. {s.discount:,.2f}'))
        story.append(self._amount_table(rows, 'NET TOTAL', f'Rs. {s.total:,.2f}'))

        # ── Thank-you ─────────────────────────────────────────────────────────
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER))
        story.append(Paragraph(
            'Thank you for choosing our pharmacy. '
            'Please retain this invoice for your records. '
            'All medicines must be taken as directed by your physician.',
            _style('ty', fontName='Helvetica-Oblique', fontSize=8,
                   textColor=MUTED, alignment=TA_CENTER, spaceAfter=4)))
        return story


# ═════════════════════════════════════════════════════════════════════════════
# 4. BILLING INVOICE
# ═════════════════════════════════════════════════════════════════════════════
class BillingInvoicePDF(BaseClinicPDF):
    REPORT_TITLE = 'Invoice'
    REPORT_SUBTITLE = 'Billing & Accounts'
    FILENAME_PREFIX = 'invoice'

    def __init__(self, invoice, clinic, generated_by=''):
        super().__init__(clinic, generated_by)
        self.invoice = invoice
        self.items = list(invoice.items.all())

    def build_story(self) -> list:
        inv = self.invoice
        story = []

        story.append(Paragraph(f'Invoice #{inv.invoice_number}',
                               _style('bn', fontName='Helvetica-Bold',
                                      fontSize=18, textColor=PRIMARY_DARK, spaceAfter=2)))
        story.append(Paragraph(inv.created_at.strftime('%A, %d %B %Y'),
                               _style('bd', fontName='Helvetica', fontSize=9,
                                      textColor=MUTED, spaceAfter=8)))

        story += self._section('Patient Information')
        story.append(self._info_grid([
            ('Patient Name', inv.patient.full_name),
            ('Patient ID',   inv.patient.patient_id),
            ('Age / Gender', f"{inv.patient.age} yrs / {inv.patient.get_gender_display()}"),
            ('Phone',        inv.patient.phone or '—'),
        ]))

        story += self._section('Charges')
        headers = [Paragraph(h, S_TH) for h in ['#', 'Description', 'Qty', 'Unit Price', 'Amount']]
        data = [headers]
        for i, item in enumerate(self.items, 1):
            data.append([
                Paragraph(str(i), S_TD_C),
                Paragraph(item.description, _style('idesc', fontName='Helvetica', fontSize=9)),
                Paragraph(str(item.quantity), S_TD_C),
                Paragraph(f'Rs. {item.unit_price:,.2f}', S_TD_R),
                Paragraph(f'Rs. {item.subtotal:,.2f}', S_TD_R),
            ])
        col_w = [8 * mm, 80 * mm, 15 * mm, 30 * mm, 30 * mm]
        story.append(Table(data, colWidths=col_w, style=_table_style(), repeatRows=1))

        story.append(Spacer(1, 8))
        rows = [('Subtotal', f'Rs. {inv.subtotal:,.2f}')]
        if inv.discount:
            rows.append(('Discount', f'- Rs. {inv.discount:,.2f}'))
        if inv.tax:
            rows.append(('Tax', f'+ Rs. {inv.tax:,.2f}'))
        rows.append(('Amount Paid', f'Rs. {inv.amount_paid:,.2f}'))
        story.append(self._amount_table(rows, 'BALANCE DUE', f'Rs. {inv.balance_due:,.2f}'))

        # Status badge
        story.append(Spacer(1, 8))
        status_color = SUCCESS if inv.status == 'paid' else WARNING
        status_data = [[Paragraph(f'Payment Status: {inv.get_status_display().upper()}',
                                  _style('stbadge', fontName='Helvetica-Bold', fontSize=10,
                                         textColor=WHITE, alignment=TA_CENTER))]]
        story.append(Table(status_data,
                           colWidths=[self.PAGE_W - self.MARGIN_L - self.MARGIN_R],
                           style=TableStyle([
                               ('BACKGROUND', (0, 0), (0, 0), status_color),
                               ('TOPPADDING', (0, 0), (0, 0), 8),
                               ('BOTTOMPADDING', (0, 0), (0, 0), 8),
                               ('ROUNDEDCORNERS', [4]),
                           ])))

        if inv.notes:
            story.append(Spacer(1, 6))
            story.append(Paragraph(f'<b>Notes:</b> {inv.notes}', S_SMALL))

        # ── Online Patient Care box (only if this patient actually has
        #    portal access set up — never invite to a login that won't work) ──
        if getattr(inv.patient, 'portal_password_hash', ''):
            story.append(Spacer(1, 12))
            care_data = [[Paragraph(
                f'<b>Online Patient Care:</b> View your prescriptions, lab reports, and invoices online. '
                f'Log in at the Patient Portal using Patient ID <b>{inv.patient.patient_id}</b> and the '
                f'password given to you at registration.',
                _style('care', fontName='Helvetica', fontSize=8.5, textColor=MUTED, leading=12))]]
            care_table = Table(
                care_data, colWidths=[self.PAGE_W - self.MARGIN_L - self.MARGIN_R],
                style=TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#eff6ff')),
                    ('BOX', (0, 0), (-1, -1), 0.5, PRIMARY),
                    ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ]))
            story.append(care_table)
        return story


# ═════════════════════════════════════════════════════════════════════════════
# 4B. GENERAL LEDGER / ACCOUNTS REPORT
# ═════════════════════════════════════════════════════════════════════════════
class LedgerReportPDF(BaseClinicPDF):
    """Autonomous General Ledger export — accounts / bookkeeping PDF."""
    REPORT_TITLE = 'General Ledger'
    REPORT_SUBTITLE = 'Accounts Statement'
    FILENAME_PREFIX = 'ledger'

    def __init__(self, entries, clinic, generated_by='', total_debit=0, total_credit=0, account_filter=None):
        super().__init__(clinic, generated_by)
        self.entries = list(entries)
        self.total_debit = total_debit
        self.total_credit = total_credit
        self.account_filter = account_filter

    def build_story(self) -> list:
        story = []
        subtitle = f'Filtered: {self.account_filter}' if self.account_filter else 'All Accounts'
        story.append(Paragraph('General Ledger Statement',
                               _style('ln', fontName='Helvetica-Bold', fontSize=18, textColor=PRIMARY_DARK, spaceAfter=2)))
        story.append(Paragraph(f'{subtitle} · Generated {datetime.now().strftime("%d %B %Y")}',
                               _style('ld', fontName='Helvetica', fontSize=9, textColor=MUTED, spaceAfter=8)))

        story += self._section('Entries')
        headers = [Paragraph(h, S_TH) for h in ['Date', 'Account', 'Type', 'Amount', 'Reference', 'Description']]
        data = [headers]
        for e in self.entries:
            amt_style = S_SUCCESS if e.entry_type == 'debit' else S_TD_R
            data.append([
                Paragraph(str(e.date), S_TD_C),
                Paragraph(e.get_account_display(), S_TD),
                Paragraph(e.get_entry_type_display(), S_TD_C),
                Paragraph(f'Rs. {e.amount:,.2f}', amt_style),
                Paragraph(e.reference, S_TD),
                Paragraph(e.description or '—', S_TD),
            ])
        col_w = [20 * mm, 32 * mm, 16 * mm, 26 * mm, 30 * mm, 46 * mm]
        story.append(Table(data, colWidths=col_w, style=_table_style(), repeatRows=1))

        story.append(Spacer(1, 8))
        story.append(self._amount_table(
            [('Total Debit', f'Rs. {self.total_debit:,.2f}'), ('Total Credit', f'Rs. {self.total_credit:,.2f}')],
            'NET', f'Rs. {(self.total_debit - self.total_credit):,.2f}'
        ))
        return story


# ═════════════════════════════════════════════════════════════════════════════
# 5. PAYROLL SLIP
# ═════════════════════════════════════════════════════════════════════════════
import calendar as _cal

class PayrollSlipPDF(BaseClinicPDF):
    REPORT_TITLE = 'Payroll Slip'
    REPORT_SUBTITLE = 'Salary Statement'
    FILENAME_PREFIX = 'payroll_slip'

    def __init__(self, slip, clinic, generated_by=''):
        super().__init__(clinic, generated_by)
        self.slip = slip

    def build_story(self) -> list:
        s = self.slip
        emp = s.employee
        month_label = f"{_cal.month_name[s.month]} {s.year}"
        story = []

        # Period header
        story.append(Paragraph('Salary Statement',
                               _style('ss_title', fontName='Helvetica-Bold',
                                      fontSize=18, textColor=PRIMARY_DARK, spaceAfter=2)))
        story.append(Paragraph(month_label,
                               _style('ss_period', fontName='Helvetica', fontSize=11,
                                      textColor=MUTED, spaceAfter=8)))

        story += self._section('Employee Information')
        story.append(self._info_grid([
            ('Full Name',    emp.user.get_full_name()),
            ('Employee ID',  emp.employee_id),
            ('Department',   emp.get_department_display()),
            ('Designation',  emp.designation),
            ('CNIC',         emp.cnic or '—'),
            ('Join Date',    emp.join_date.strftime('%d %b %Y')),
        ]))

        story += self._section('Earnings')
        earnings = [
            ('Basic Salary',            f'Rs. {s.basic_salary:,.2f}'),
            ('Allowances',              f'Rs. {s.allowances:,.2f}'),
            ('Performance Bonus',       f'Rs. {s.bonus:,.2f}'),
        ]
        story.append(self._info_grid(earnings, cols=1))

        story += self._section('Deductions')
        deductions = [
            ('Deductions',  f'Rs. {s.deductions:,.2f}'),
            ('Tax',         f'Rs. {s.tax:,.2f}'),
        ]
        story.append(self._info_grid(deductions, cols=1))

        # Net salary highlight
        story.append(Spacer(1, 8))
        net_data = [[
            Paragraph('NET SALARY', _style('net_l', fontName='Helvetica-Bold',
                                            fontSize=14, textColor=WHITE)),
            Paragraph(f'Rs. {s.net_salary:,.2f}',
                      _style('net_r', fontName='Helvetica-Bold', fontSize=16,
                             textColor=WHITE, alignment=TA_RIGHT)),
        ]]
        usable_w = self.PAGE_W - self.MARGIN_L - self.MARGIN_R
        net_table = Table(net_data, colWidths=[usable_w * 0.45, usable_w * 0.55],
                          style=TableStyle([
                              ('BACKGROUND',    (0, 0), (-1, -1), PRIMARY_DARK),
                              ('TOPPADDING',    (0, 0), (-1, -1), 12),
                              ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                              ('LEFTPADDING',   (0, 0), (-1, -1), 14),
                              ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
                              ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
                          ]))
        story.append(net_table)

        # Payment status
        paid_color = SUCCESS if s.is_paid else WARNING
        paid_label = f'PAID on {s.paid_on.strftime("%d %b %Y")}' if s.is_paid else 'PAYMENT PENDING'
        story.append(Spacer(1, 4))
        paid_data = [[Paragraph(paid_label,
                                _style('paid', fontName='Helvetica-Bold', fontSize=9,
                                       textColor=WHITE, alignment=TA_CENTER))]]
        story.append(Table(paid_data,
                           colWidths=[usable_w],
                           style=TableStyle([
                               ('BACKGROUND',    (0, 0), (0, 0), paid_color),
                               ('TOPPADDING',    (0, 0), (0, 0), 5),
                               ('BOTTOMPADDING', (0, 0), (0, 0), 5),
                           ])))

        if s.remarks:
            story.append(Spacer(1, 6))
            story.append(Paragraph(f'<b>Remarks:</b> {s.remarks}', S_SMALL))

        story.append(Spacer(1, 20))
        story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER))
        sig_data = [
            [Paragraph('_____________________', S_CENTER),
             Paragraph('_____________________', S_CENTER)],
            [Paragraph('HR Manager', S_CENTER),
             Paragraph('Employee Signature', S_CENTER)],
        ]
        story.append(Table(sig_data,
                           colWidths=[usable_w / 2, usable_w / 2],
                           style=TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                             ('TOPPADDING', (0, 0), (-1, -1), 8)])))
        return story
