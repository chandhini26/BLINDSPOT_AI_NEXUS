from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm

def create_pdf(data):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm)
    styles = getSampleStyleSheet()
    story = [Paragraph("BLINDSPOT AI – ANALYSIS REPORT", styles["Title"]),
             Spacer(1,10), Paragraph("Project: " + str(data.get("project_name","")), styles["Normal"]),
             Spacer(1,10), Paragraph("Project Summary", styles["Heading2"]),
             Paragraph(str(data.get("project_summary",{})), styles["BodyText"]),
             Spacer(1,10), Paragraph("Findings", styles["Heading2"])]
    for i, f in enumerate(data.get("findings",[]), 1):
        story += [Paragraph(f"{i}. {f.get('title','Finding')}", styles["Heading3"]),
                  Paragraph(f"Category: {f.get('category','')} | Severity: {f.get('severity','')} | Confidence: {f.get('confidence','')}", styles["BodyText"]),
                  Paragraph(str(f.get("description","")), styles["BodyText"]),
                  Paragraph("Evidence: " + str(f.get("evidence","")), styles["BodyText"]),
                  Paragraph("Source: " + str(f.get("source","")), styles["BodyText"]), Spacer(1,7)]
    story.append(Paragraph("Recommendations", styles["Heading2"]))
    for r in data.get("recommendations",[]):
        story += [Paragraph(str(r.get("title","Recommendation")), styles["Heading3"]),
                  Paragraph(str(r.get("recommendation","")), styles["BodyText"]), Spacer(1,6)]
    story.append(Paragraph(str(data.get("disclaimer","")), styles["Italic"]))
    doc.build(story)
    return buf.getvalue()
