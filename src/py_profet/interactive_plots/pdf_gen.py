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

def get_figures_story(system_arch: dict, selected_nodes: list, figures: list) -> list:
    """Generate a PNG image from a Plotly figure and return it as an in-memory binary stream."""
    # Pre: assume the system_arch minus the selected_nodes is the same length as the figures
    # inches converted to points (72 points per inch)
    width_margin = 2
    pdf_width = (8.5 - width_margin) * 72
    height_margin = 4
    pdf_height = (11 - height_margin) * 72 / 2
    
    # Define styles for headings
    styles = getSampleStyleSheet()
    heading1_style = styles['Heading1']
    heading2_style = styles['Heading2']

    dpi = 150
    
    story = []
    i_fig = 0
    figures_per_page = 2  # Number of figures per page
    story.append(PageBreak())
    while i_fig < len(figures):
        # Insert a page break for each new page
        if i_fig > 0:
            story.append(PageBreak())
        
        for node_name, sockets in system_arch.items():
            if node_name not in selected_nodes:
                continue
            # Add node name as a heading
            story.append(Paragraph(f"Node {node_name}", heading1_style))
            
            for i_socket, i_mc in sockets.items():
                if len(i_mc) > 1:
                    story.append(Paragraph(f"Socket {i_socket}", heading2_style))
                for mc in i_mc:
                    # Create a list of figures for the current page
                    page_figures = []
                    for _ in range(figures_per_page):
                        if i_fig < len(figures):
                            fig = figures[i_fig]
                            i_fig += 1
                            img_stream = BytesIO()
                            img_bytes = pio.to_image(fig, format="png",width=pdf_width * dpi / 72, height=pdf_height * dpi / 72)

                            img_stream.write(img_bytes)
                            img_stream.seek(0)
                            img = Image(img_stream, width=pdf_width, height=pdf_height)
                            page_figures.append(img)
                    
                    # Add the list of figures to the current page
                    if page_figures:
                        story.extend(page_figures)
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

    # Add figures
    story.extend(get_figures_story(system_arch, selected_nodes, figures))
    
    # Build the PDF
    doc.build(story)
    pdf_string = buffer.getvalue()
    buffer.close()

    return pdf_string