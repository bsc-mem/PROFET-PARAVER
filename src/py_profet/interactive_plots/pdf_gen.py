import pandas as pd
from io import BytesIO
import plotly.io as pio

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

import summary_info

styles = getSampleStyleSheet()

# Define a new ParagraphStyles for paragraph titles
heading1_style = ParagraphStyle(
    'PrimaryTitle',
    parent=styles['Heading1'],
    fontSize=18,
    leftIndent=0
)
heading2_style = ParagraphStyle(
    'SecondaryTitle',
    parent=styles['Heading2'],
    fontSize=16,
    leftIndent=0
)
heading3_style = ParagraphStyle(
    'TertiaryTitle',
    parent=styles['Heading3'],
    fontSize=14,
    leftIndent=0
)

def get_summary_bullets(summary_part: dict, bullet_style: ParagraphStyle) -> ListFlowable:
    bullets = []
    for _, bullet in summary_part.items():
        bullets.append(ListItem(Paragraph(f"{bullet['label']}: {bullet['value']}", bullet_style)))
    return ListFlowable(
        bullets,
        bulletType='bullet',
        start='\u2022' # bullet point symbol
    )

def get_summary(df: pd.DataFrame, config: dict, system_arch: dict) -> list:
    summary = summary_info.get_summary_info(df, config, system_arch)
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=styles['Normal'],
        fontSize=12,
        textColor='black'
    )
    return [
        Paragraph("Summary", heading1_style),
        # Platform
        Paragraph("Platform", heading2_style),
        Paragraph("Server", heading3_style),
        get_summary_bullets(summary['platform']['server'], bullet_style),
        Paragraph("CPU", heading3_style),
        get_summary_bullets(summary['platform']['cpu'], bullet_style),
        Paragraph("Memory", heading3_style),
        get_summary_bullets(summary['platform']['memory'], bullet_style),

        # Memory profile
        Paragraph("Memory profile", heading2_style),
        get_summary_bullets(summary['memory_profile'], bullet_style),

        # Trace info
        Paragraph("Trace", heading2_style),
        get_summary_bullets(summary['trace_info'], bullet_style),
    ]

# def save_graphs_as_images(graphs: list, prefix: str = "graph") -> list:
#     """Save graphs as PNG images and return the list of filenames."""
#     filenames = []
#     for index, data in enumerate(graphs):
#         filename = f"{prefix}_{index}.png"
#         pio.write_image(data, filename)
#         filenames.append(filename)
#     return filenames

def get_figure_images(figures: list) -> list:
    """Generate a PNG image from a Plotly figure and return it as an in-memory binary stream."""
    # inches converted to points (72 points per inch)
    width_margin = 1.5
    pdf_width = (8.5 - width_margin) * 72
    # allow 2 images per pdf page
    height_margin = 3
    pdf_height = (11 - height_margin) * 72 / 2
    story = []
    for fig in figures:
        img_stream = BytesIO()
        # a scale of 2 doubles the resolution of the image
        img_bytes = pio.to_image(fig, format="png")
        img_stream.write(img_bytes)
        img_stream.seek(0)

        img = Image(img_stream, width=pdf_width, height=pdf_height)
        story.append(img)
        story.append(Spacer(1, 12))  # Optional spacer for better layout
    return story

def generate_pdf(df: pd.DataFrame, config: dict, system_arch: dict, selected_nodes: list, figures: list) -> bytes:
    buffer = BytesIO()
    # Set up the document and styles
    doc = SimpleDocTemplate(buffer, pagesize=letter, title="Report")

    # Add a title
    story = [
        Paragraph("Report", styles['Title']),
        Spacer(1, 12),
    ]

    # Add summary info
    story.extend(get_summary(df, config, system_arch))

    # Insert a page break
    story.append(PageBreak())

    # Add figures
    story.extend(get_figure_images(figures))

    # Build the PDF
    doc.build(story)
    pdf_string = buffer.getvalue()
    buffer.close()

    return pdf_string