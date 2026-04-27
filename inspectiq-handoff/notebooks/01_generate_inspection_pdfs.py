# Databricks notebook source
# MAGIC %md
# MAGIC # InspectIQ — Phase 1: Generate Inspection Report PDFs
# MAGIC
# MAGIC Produces 10 realistic inspection reports across three disciplines:
# MAGIC - **Structural Steel** (3): Parker Street Overpass, Commerce Center Garage, Riverside Industrial
# MAGIC - **Concrete** (3): I-95 Bridge Deck, Terminal C Parking, SR-422 Retaining Wall
# MAGIC - **Asphalt** (4): PHL Runway, I-78 Eastbound, Valley Forge Industrial, Chestnut Street
# MAGIC
# MAGIC PDFs are written to `mbi_demo.inspectiq.inspection_docs` Unity Catalog Volume.

# COMMAND ----------

# MAGIC %pip install reportlab --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

catalog = "mbi_demo"
schema  = "inspectiq"
volume  = "inspection_docs"

spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {catalog}.{schema}.{volume}")

import os
base_path = f"/Volumes/{catalog}/{schema}/{volume}"
for sub in ["structural_steel", "concrete", "asphalt"]:
    os.makedirs(f"{base_path}/{sub}", exist_ok=True)

print(f"Volume ready: {base_path}")

# COMMAND ----------
# ── Style helpers ─────────────────────────────────────────────────────────────

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

MBI_NAVY   = colors.HexColor("#1a3a5c")
MBI_ORANGE = colors.HexColor("#e87722")
MBI_GRAY   = colors.HexColor("#f0f4f8")
MBI_LIGHT  = colors.HexColor("#cccccc")

styles = getSampleStyleSheet()

def h1(text):
    return Paragraph(text, ParagraphStyle("h1", parent=styles["Heading1"],
        fontSize=13, fontName="Helvetica-Bold", textColor=MBI_NAVY,
        spaceAfter=6, spaceBefore=10))

def h2(text):
    return Paragraph(text, ParagraphStyle("h2", parent=styles["Heading2"],
        fontSize=11, fontName="Helvetica-Bold", textColor=MBI_NAVY,
        spaceAfter=4, spaceBefore=6))

def body(text):
    return Paragraph(text, ParagraphStyle("body", parent=styles["Normal"],
        fontSize=10, leading=14, spaceAfter=6, alignment=TA_JUSTIFY))

def sp(n=1):
    return Spacer(1, n * 0.12 * inch)

def header_table(data, col_widths=None):
    t = Table(data, colWidths=col_widths or [1.5*inch, 2.25*inch, 1.5*inch, 2.25*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), MBI_NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("BACKGROUND",    (0,1), (-1,-1), MBI_GRAY),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("GRID",          (0,0), (-1,-1), 0.5, MBI_LIGHT),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    return t

def findings_table(rows, col_widths=None):
    t = Table(rows, colWidths=col_widths)
    ts = TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), MBI_NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("GRID",          (0,0), (-1,-1), 0.5, MBI_LIGHT),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [MBI_GRAY, colors.white]),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ])
    t.setStyle(ts)
    return t

def mbi_cover(story, report_id, title, subtitle, client, date_str, inspector):
    story.append(Paragraph("MICHAEL BAKER INTERNATIONAL",
        ParagraphStyle("co", fontSize=11, fontName="Helvetica-Bold",
            alignment=TA_CENTER, textColor=MBI_NAVY, spaceAfter=4)))
    story.append(Paragraph("Inspection Report",
        ParagraphStyle("rt", fontSize=18, fontName="Helvetica-Bold",
            alignment=TA_CENTER, textColor=MBI_NAVY, spaceAfter=2)))
    story.append(Paragraph(title,
        ParagraphStyle("tl", fontSize=13, fontName="Helvetica-Bold",
            alignment=TA_CENTER, textColor=MBI_ORANGE, spaceAfter=12)))
    story.append(sp(2))
    story.append(header_table([
        ["Report ID", report_id,   "Inspection Date", date_str],
        ["Project",   title,       "Discipline",      subtitle],
        ["Client",    client,      "Lead Inspector",  inspector],
    ]))
    story.append(sp(2))

# COMMAND ----------
# ── STRUCTURAL STEEL REPORT 1: Parker Street Highway Overpass ─────────────────

def build_SS001():
    story = []
    mbi_cover(story,
        report_id  = "INS-SS-001",
        title      = "Parker Street Highway Overpass",
        subtitle   = "Structural Steel Inspection",
        client     = "Pennsylvania DOT — District 11",
        date_str   = "October 15, 2024",
        inspector  = "Sarah Chen, PE, S.E.")

    story.append(h1("1. Executive Summary"))
    story.append(body(
        "The Parker Street Highway Overpass carrying Route 28 over Chartiers Creek in Pittsburgh, PA "
        "was inspected on October 15, 2024 in accordance with FHWA Bridge Inspector's Reference Manual (BIRM) "
        "and AASHTO Manual for Bridge Evaluation. The structure is a three-span continuous steel plate girder "
        "bridge constructed in 1971. The overall condition rating is 5 out of 9 (Poor). "
        "Active section loss on fascia girders and fatigue cracking at web-to-flange welds require "
        "priority repair within 6 months. A load rating reduction is recommended pending structural assessment."
    ))
    story.append(sp())

    story.append(header_table([
        ["Overall Rating", "5 / 9 — Poor",        "Structure Type",    "Steel Plate Girder"],
        ["Year Built",     "1971",                 "Total Span",        "210 ft (3 spans)"],
        ["Location",       "Pittsburgh, PA",       "Avg Daily Traffic", "28,400 vehicles/day"],
        ["Next Inspection","October 2025 (Annual)", "NBIS Compliant",   "No — Deficient"],
    ]))
    story.append(sp(2))

    story.append(h1("2. Deficiency Findings"))

    story.append(h2("2.1  Section Loss — Fascia Girders at Pier 2 Cap"))
    story.append(body(
        "Moderate to severe section loss was observed on both fascia girders at the Pier 2 bearing seat. "
        "Estimated cross-sectional area reduction of 18–23% on the bottom flange and lower web, driven by "
        "long-term water ponding from failed deck drainage. Corrosion product thickness averaged 0.38 inches. "
        "The section loss exceeds the 15% threshold requiring immediate engineering evaluation per FHWA "
        "Action Plan guidelines."
    ))
    story.append(findings_table(
        [["Severity", "Element", "Area Affected", "Urgency"],
         ["High", "Bottom flange + lower web, Pier 2 fascia girders", "~22% section loss", "Immediate — 0-6 months"]],
        col_widths=[0.8*inch, 2.8*inch, 1.4*inch, 1.5*inch]
    ))
    story.append(sp())

    story.append(h2("2.2  Fatigue Cracking — Web-to-Flange Welds, Spans 2 and 4"))
    story.append(body(
        "Hairline fatigue cracks measuring 1.4 to 2.7 inches were identified at the web-to-bottom-flange "
        "weld toes in Spans 2 and 4. Cracks initiate at re-entrant weld terminations consistent with "
        "AASHTO Category C fatigue details. Ultrasonic testing (UT) was performed at four locations; "
        "two cracks were confirmed as full-thickness through-cracks in the web. Traffic loading at "
        "28,400 vpd places these details well within the finite-fatigue-life zone. Immediate fracture-critical "
        "hands-on re-inspection and stop-hole drilling are required."
    ))
    story.append(findings_table(
        [["Severity", "Element", "Crack Length", "Urgency"],
         ["High", "Web-to-flange weld, Spans 2 and 4", "1.4–2.7 in (confirmed through-cracks)", "Immediate — stop-hole within 30 days"]],
        col_widths=[0.8*inch, 2.4*inch, 2.0*inch, 1.3*inch]
    ))
    story.append(sp())

    story.append(h2("2.3  Paint System Failure — Full Structure"))
    story.append(body(
        "The original lead-based paint system has failed across approximately 70% of exposed steel surfaces. "
        "Active rust, pitting, and blister formation are visible on all primary members. "
        "The upper chord and portal framing show complete paint delamination with rust scale averaging "
        "3/16 inch thickness. Full repainting is required per SSPC-SP10 Near-White Blast. "
        "Environmental containment is required for lead-paint removal under EPA NESHAP 40 CFR Part 63."
    ))
    story.append(sp())

    story.append(h2("2.4  Bearing Seat Corrosion — Pier 3"))
    story.append(body(
        "Fixed bearings at Pier 3 are heavily corroded and show binding. The anchor bolt nuts are seized. "
        "Expansion bearings have lost effective thermal range of motion; girder riding on concrete seat edge. "
        "Continued thermal loading may induce secondary forces in the girder system. "
        "Cleaning, lubrication, and replacement of seized anchors required within one maintenance cycle."
    ))
    story.append(sp(2))

    story.append(h1("3. Recommendations"))
    story.append(findings_table(
        [["Priority", "Action", "Timeframe", "Est. Cost"],
         ["1 — High", "Stop-hole drilling at fatigue crack tips (Spans 2 & 4) + UT reinspection", "30 days", "$28,000"],
         ["2 — High", "Corrosion treatment and section-loss repair: fascia girders at Pier 2", "0–6 months", "$185,000"],
         ["3 — High", "Full repainting (SSPC-SP10) with lead-containment", "6–12 months", "$620,000"],
         ["4 — Medium", "Bearing replacement and seat restoration at Pier 3", "6–18 months", "$95,000"],
         ["5 — Medium", "Load rating update under AASHTO LRFR pending section-loss repair", "After repair", "$22,000"]],
        col_widths=[1.0*inch, 3.2*inch, 1.1*inch, 1.2*inch]
    ))
    story.append(sp(2))

    story.append(body(
        "<b>Prepared by:</b> Sarah Chen, PE, S.E. | Michael Baker International — Pittsburgh, PA Office | "
        "October 15, 2024. This report is prepared in accordance with 23 CFR Part 650, Subpart C. "
        "All findings are based on visual inspection supplemented by ultrasonic testing. "
        "MBI assumes no responsibility for conditions not observable at time of inspection."
    ))
    return story

# COMMAND ----------
# ── STRUCTURAL STEEL REPORT 2: Commerce Center Parking Garage ─────────────────

def build_SS002():
    story = []
    mbi_cover(story,
        report_id  = "INS-SS-002",
        title      = "Commerce Center Parking Garage — Level 3 & 4 Steel",
        subtitle   = "Structural Steel Inspection",
        client     = "Commerce Center Associates, LLC",
        date_str   = "March 22, 2024",
        inspector  = "David Park, PE, SE")

    story.append(h1("1. Executive Summary"))
    story.append(body(
        "The Commerce Center Parking Garage in Philadelphia, PA was inspected on March 22, 2024. "
        "This six-level post-tensioned concrete structure incorporates structural steel moment connections "
        "at columns on Levels 3 and 4. The inspection was triggered by a report of visible spalling and "
        "staining on Level 3. The overall structural steel condition is rated 4 out of 9 (Poor). "
        "<b>An immediate safety risk was identified: exposed and severely corroded rebar in Column C-14 "
        "on Level 3, with visible reduction in column capacity. Partial closure of Level 3 and immediate "
        "shoring of Column C-14 are required.</b>"
    ))
    story.append(sp())

    story.append(header_table([
        ["Overall Rating", "4 / 9 — Poor",           "Structure Type", "Steel moment frame in PT concrete"],
        ["Year Built",     "1989",                    "Stories",        "6 levels + roof deck"],
        ["Location",       "Philadelphia, PA",        "Parking Spaces", "1,240"],
        ["Next Inspection","March 2025 (Annual)",     "Safety Flag",    "YES — Level 3 partial closure required"],
    ]))
    story.append(sp(2))

    story.append(h1("2. Deficiency Findings"))

    story.append(h2("2.1  IMMEDIATE SAFETY RISK — Exposed Rebar, Column C-14, Level 3"))
    story.append(body(
        "<b>PRIORITY FINDING:</b> Column C-14 on Level 3 has experienced advanced concrete spalling exposing "
        "the primary vertical reinforcement (6 #9 bars). Corrosion pitting on exposed bars was measured at "
        "an average section loss of 31%, with two bars showing kinking consistent with loss of lateral "
        "confinement. The column cap plate and base plate connection to the Level 3 steel beam show active "
        "rust pack jacking. This condition constitutes an immediate structural safety risk. "
        "Column C-14 should be assumed to have reduced load-carrying capacity pending detailed structural analysis. "
        "<b>Recommended immediate action: install shoring within 24 hours and restrict vehicular access to "
        "the Level 3 northeast quadrant (Bays B-D / 3-5).</b>"
    ))
    story.append(findings_table(
        [["Severity", "Element", "Finding", "Urgency"],
         ["CRITICAL", "Column C-14, Level 3", "Exposed rebar (31% avg section loss), kinking, structural capacity reduction", "IMMEDIATE — shore within 24 hours"]],
        col_widths=[0.85*inch, 1.5*inch, 3.0*inch, 2.15*inch]
    ))
    story.append(sp())

    story.append(h2("2.2  Steel Connection Corrosion — Columns B-8 and D-12"))
    story.append(body(
        "Structural steel moment connection plates at Columns B-8 and D-12 on Level 3 show heavy surface "
        "corrosion with visible section loss on the gusset plate fillet welds. Paint system has failed "
        "completely in both locations. Weld inspection revealed undercut defects at two toe locations "
        "consistent with original fabrication. Estimated 12–15% section loss on gusset plates. "
        "Repair by corrosion treatment, weld repair, and protective coating required within 90 days."
    ))
    story.append(sp())

    story.append(h2("2.3  Delamination — Level 3 Floor Plate at Grid C/3-5"))
    story.append(body(
        "Composite floor plate on Level 3 between Grids C/3-5 shows delamination from the underlying "
        "concrete slab. Chain-drag sounding identified hollow areas covering approximately 280 square feet. "
        "The delamination is attributed to chloride-induced corrosion of the top reinforcement mat "
        "and inadequate waterproofing membrane maintenance. Full-depth patch replacement required."
    ))
    story.append(sp())

    story.append(h2("2.4  Section Loss — Secondary Beam W14×48, Grid C/4"))
    story.append(body(
        "A secondary floor beam (W14×48) at Grid C/4 on Level 3 shows 9% section loss on the bottom "
        "flange from persistent water drip exposure. Condition is below the 15% action threshold but "
        "should be monitored annually. Protective coating and improved drainage above are recommended."
    ))
    story.append(sp(2))

    story.append(h1("3. Recommendations"))
    story.append(findings_table(
        [["Priority", "Action", "Timeframe", "Est. Cost"],
         ["1 — CRITICAL", "Install shoring at Column C-14 and restrict Level 3 NE quadrant", "24 hours", "$12,000"],
         ["2 — High", "Structural assessment of Column C-14 load capacity by licensed SE", "7 days", "$18,000"],
         ["3 — High", "Epoxy injection and column jacket repair at C-14", "30–60 days", "$140,000"],
         ["4 — High", "Corrosion treatment and weld repair at B-8 and D-12", "90 days", "$65,000"],
         ["5 — Medium", "Full-depth floor patch, Grid C/3-5 Level 3", "6 months", "$88,000"],
         ["6 — Medium", "Protective coating of W14×48 at C/4, improve drainage above", "6 months", "$14,000"]],
        col_widths=[1.05*inch, 3.0*inch, 1.1*inch, 1.1*inch]
    ))
    story.append(sp(2))

    story.append(body(
        "<b>Prepared by:</b> David Park, PE, SE | Michael Baker International — Philadelphia, PA Office | "
        "March 22, 2024. This report constitutes an engineering inspection opinion only. "
        "Owner should retain a licensed structural engineer for immediate load-capacity analysis of Column C-14."
    ))
    return story

# COMMAND ----------
# ── STRUCTURAL STEEL REPORT 3: Riverside Industrial Steel Frame ───────────────

def build_SS003():
    story = []
    mbi_cover(story,
        report_id  = "INS-SS-003",
        title      = "Riverside Industrial Complex — Building 4 Steel Frame",
        subtitle   = "Structural Steel Inspection",
        client     = "Riverside Holdings Group",
        date_str   = "July 8, 2024",
        inspector  = "Marcus Webb, PE")

    story.append(h1("1. Executive Summary"))
    story.append(body(
        "Building 4 of the Riverside Industrial Complex in Baltimore, MD was inspected on July 8, 2024. "
        "The structure is a single-story steel moment frame industrial building constructed in 1984 with "
        "a clear-span of 120 ft. The overall condition is rated 6 out of 9 (Fair). "
        "No immediate safety concerns were identified. Corrosion on bracing connections and bearing plate "
        "deterioration at column bases require attention within the next maintenance cycle (12–18 months). "
        "Routine annual monitoring is recommended."
    ))
    story.append(sp())

    story.append(header_table([
        ["Overall Rating", "6 / 9 — Fair",         "Structure Type",    "Steel Moment Frame"],
        ["Year Built",     "1984",                  "Clear Span",        "120 ft × 280 ft"],
        ["Location",       "Baltimore, MD",         "Occupancy",         "Industrial warehouse"],
        ["Next Inspection","July 2026 (Biennial)",  "NBIS Compliant",    "N/A (non-bridge)"],
    ]))
    story.append(sp(2))

    story.append(h1("2. Deficiency Findings"))

    story.append(h2("2.1  Corrosion — Bracing Connections, Bays D–E / 3–4"))
    story.append(body(
        "X-brace connections in Bays D–E / 3–4 show moderate surface corrosion on gusset plates and "
        "brace-to-gusset welds. Paint system has delaminated in these areas, allowing moisture ingress "
        "from roof penetration leaks directly above. Estimated section loss is 5–8% on gusset plates — "
        "below the 15% action threshold but trending. Protective coating repair and roof penetration "
        "correction are recommended within 12 months."
    ))
    story.append(sp())

    story.append(h2("2.2  Bearing Plate Deterioration — 6 Column Bases, South Row"))
    story.append(body(
        "Six column base bearing plates along the south row (columns S-1 through S-6) show rust pack "
        "jacking between the plate and concrete pedestal, averaging 3/8 inch pack thickness. "
        "Two anchor bolts at S-3 are corroded through at the grout pad interface and cannot achieve "
        "design torque. Replacement of affected anchor bolts and resetting of bearing plates is "
        "required within 18 months. No structural instability observed during inspection."
    ))
    story.append(sp())

    story.append(h2("2.3  Minor Section Loss — Secondary Purlins, Bay C"))
    story.append(body(
        "Secondary roof purlins in Bay C show minor surface pitting consistent with long-term "
        "condensation exposure. Section loss is estimated at 3–4%, well within acceptable limits. "
        "Annual monitoring is sufficient; protective coating is recommended at next scheduled "
        "maintenance painting."
    ))
    story.append(sp(2))

    story.append(h1("3. Recommendations"))
    story.append(findings_table(
        [["Priority", "Action", "Timeframe", "Est. Cost"],
         ["1 — Medium", "Repair roof penetrations above Bays D–E to eliminate moisture source", "6 months", "$22,000"],
         ["2 — Medium", "Protective coating on bracing connections, Bays D–E / 3–4 (SSPC-SP6)", "12 months", "$38,000"],
         ["3 — Medium", "Replace corroded anchor bolts at S-3; reset bearing plates S-1 through S-6", "18 months", "$54,000"],
         ["4 — Low", "Monitor purlin section loss annually; apply protective coating at next painting cycle", "Routine", "$8,000"]],
        col_widths=[1.0*inch, 3.35*inch, 1.1*inch, 1.05*inch]
    ))
    story.append(sp(2))

    story.append(body(
        "<b>Prepared by:</b> Marcus Webb, PE | Michael Baker International — Baltimore, MD Office | "
        "July 8, 2024."
    ))
    return story

# COMMAND ----------
# ── CONCRETE REPORT 1: I-95 Northbound Bridge Deck ───────────────────────────

def build_CO001():
    story = []
    mbi_cover(story,
        report_id  = "INS-CO-001",
        title      = "I-95 Northbound Bridge Deck — Wilmington Interchange",
        subtitle   = "Concrete Condition Assessment",
        client     = "Delaware DOT — Structures Management",
        date_str   = "September 3, 2024",
        inspector  = "Lisa Tran, PE")

    story.append(h1("1. Executive Summary"))
    story.append(body(
        "The I-95 Northbound Bridge Deck at the Wilmington Interchange was assessed on September 3, 2024. "
        "The structure is a five-span prestressed concrete box-beam bridge built in 1978. "
        "Condition is rated 4 out of 9 (Poor). Three significant deficiencies require priority action: "
        "deck delamination covering approximately 34% of surface area, active rebar corrosion in Span 2, "
        "and scour erosion of 2.1 ft at the Pier 1 footing. The scour condition is classified as "
        "<b>Scour Critical</b> under FHWA guidelines and requires countermeasures prior to the next "
        "high-flow event, expected in spring 2025."
    ))
    story.append(sp())

    story.append(header_table([
        ["Overall Rating", "4 / 9 — Poor",         "Structure Type",    "Prestressed Concrete Box Beam"],
        ["Year Built",     "1978",                  "Total Span",        "380 ft (5 spans)"],
        ["Location",       "Wilmington, DE (I-95)", "Avg Daily Traffic", "67,400 vehicles/day"],
        ["Next Inspection","March 2025 (Scour)",    "Scour Critical",    "YES — Pier 1"],
    ]))
    story.append(sp(2))

    story.append(h1("2. Deficiency Findings"))

    story.append(h2("2.1  Deck Delamination and Map Cracking"))
    story.append(body(
        "Map cracking and delamination are present across approximately 34% of the deck surface. "
        "Chain-drag sounding conducted over the full deck area revealed hollow zones primarily in "
        "Spans 1 and 3, with isolated patches in Spans 2 and 5. Chloride content sampling at 3/4-inch "
        "depth in delaminated areas averaged 1.8 lb/cy, well above the corrosion threshold of 1.0 lb/cy. "
        "Full-depth deck replacement is anticipated for Spans 1 and 3 within the next 3-year program cycle."
    ))
    story.append(sp())

    story.append(h2("2.2  Rebar Corrosion and Spalling — Span 2 Soffit"))
    story.append(body(
        "Active reinforcing steel corrosion was confirmed in the soffit of Span 2. Spalling has progressed "
        "to a depth of 3.5 inches with exposed bars showing section loss averaging 18%. "
        "Six locations of active rust staining and delamination blistering were mapped. "
        "One spall measuring 14 × 8 inches fell during the inspection (no injury). "
        "Immediate temporary netting below Span 2 is recommended pending patch repair. "
        "Corrective action: epoxy mortar patch repair per ASTM C928 with bar cleaning to SSPC-SP11."
    ))
    story.append(findings_table(
        [["Severity", "Element", "Extent", "Urgency"],
         ["High", "Span 2 soffit reinforcing steel", "18% avg bar section loss, active spalling", "Immediate — netting + repair within 3 months"]],
        col_widths=[0.8*inch, 2.3*inch, 2.2*inch, 2.2*inch]
    ))
    story.append(sp())

    story.append(h2("2.3  Scour Erosion — Pier 1 Footing"))
    story.append(body(
        "Underwater inspection at Pier 1 revealed scour erosion of 2.1 ft below the channel bed elevation, "
        "exposing the footing on the downstream face. The footing is founded on spread footing with no "
        "pile support. The exposed footing depth exceeds the critical threshold established in the FHWA "
        "Scour Critical Bridge Action Plan. This bridge is classified as Scour Critical (Category 2). "
        "Riprap scour countermeasures (D50 = 18 in, 3.5 ft thick) are required at Pier 1 prior to "
        "the spring 2025 high-flow season. A monitoring plan must be established immediately."
    ))
    story.append(sp())

    story.append(h2("2.4  Expansion Joint Failure — Station 142+50"))
    story.append(body(
        "The compression-seal expansion joint at Station 142+50 has failed, packed solid with debris "
        "and incompressible material. The elastomeric seal is torn and extruded. Water and chlorides "
        "are channeling directly through the joint onto the pier cap below, causing active staining "
        "and concrete surface deterioration on the Pier 3 cap. Joint replacement with a pourable "
        "seal system is recommended within 12 months."
    ))
    story.append(sp(2))

    story.append(h1("3. Recommendations"))
    story.append(findings_table(
        [["Priority", "Action", "Timeframe", "Est. Cost"],
         ["1 — High", "Install temporary fall protection netting below Span 2 soffit", "7 days", "$9,500"],
         ["1 — High", "Riprap scour countermeasures at Pier 1 (D50=18in, 3.5ft)", "Before spring 2025", "$280,000"],
         ["2 — High", "Epoxy mortar patch repair, Span 2 soffit (bar cleaning to SP-11)", "3 months", "$165,000"],
         ["3 — Medium", "Full-depth deck replacement, Spans 1 and 3", "Year 2–3 capital program", "$2,400,000"],
         ["4 — Medium", "Expansion joint replacement at Sta. 142+50", "12 months", "$95,000"],
         ["5 — Low", "Chloride content monitoring program (annual cores)", "Ongoing", "$18,000"]],
        col_widths=[1.0*inch, 3.2*inch, 1.4*inch, 0.9*inch]
    ))
    story.append(sp(2))

    story.append(body(
        "<b>Prepared by:</b> Lisa Tran, PE | Michael Baker International — Wilmington, DE Office | "
        "September 3, 2024. Scour critical status reported to DelDOT Bridge Management."
    ))
    return story

# COMMAND ----------
# ── CONCRETE REPORT 2: Terminal C Parking Structure ──────────────────────────

def build_CO002():
    story = []
    mbi_cover(story,
        report_id  = "INS-CO-002",
        title      = "Philadelphia Int'l Airport — Terminal C Parking Structure",
        subtitle   = "Concrete Condition Assessment",
        client     = "Philadelphia Airport Authority",
        date_str   = "January 19, 2024",
        inspector  = "Angela Foster, PE")

    story.append(h1("1. Executive Summary"))
    story.append(body(
        "The Terminal C Parking Structure at Philadelphia International Airport was assessed on January 19, 2024. "
        "The eight-level cast-in-place concrete structure was constructed in 1997 and last assessed in 2019. "
        "Overall condition is rated 6 out of 9 (Fair). Surface cracking and minor spalling were observed "
        "along slab edges and around column bases on Levels 2 through 4. Localized rebar exposure was "
        "noted in areas of advanced spalling. The primary causes are moisture intrusion and freeze–thaw "
        "cycling. No immediate structural safety concerns were identified; however, timely repair is "
        "recommended to prevent further degradation and maintain serviceability of the structure."
    ))
    story.append(sp())

    story.append(header_table([
        ["Overall Rating", "6 / 9 — Fair",            "Structure Type", "Cast-in-Place Concrete Garage"],
        ["Year Built",     "1997",                     "Levels",         "8 above grade + 1 below"],
        ["Location",       "Philadelphia, PA (PHL)",   "Capacity",       "2,800 spaces"],
        ["Next Inspection","January 2026 (Biennial)",  "Safety Flag",    "None"],
    ]))
    story.append(sp(2))

    story.append(h1("2. Deficiency Findings"))

    story.append(h2("2.1  Surface Cracking and Spalling — Slab Edges, Levels 2–4"))
    story.append(body(
        "Surface cracking and minor spalling were observed along slab edges and around column bases on "
        "Levels 2, 3, and 4. Crack widths range from hairline to 0.03 inches. Spalling depths are "
        "generally 1 to 2 inches, confined to the cover concrete. Total affected area is approximately "
        "1,850 square feet across the three levels. The spalling pattern is consistent with deicing salt "
        "ingress from the roof deck and ramps above."
    ))
    story.append(sp())

    story.append(h2("2.2  Localized Rebar Exposure — Column Bases, Level 3"))
    story.append(body(
        "Localized rebar exposure was noted in areas of advanced spalling at seven column bases on Level 3. "
        "Exposed bar lengths range from 4 to 11 inches. Bar section loss at exposed locations averaged 8%, "
        "with a maximum of 14% at Column Row C, Bay 6. No kinking or loss of confinement was observed. "
        "Epoxy mortar patch repair is recommended for all exposed bar locations within 6 months."
    ))
    story.append(sp())

    story.append(h2("2.3  Moisture Intrusion — Failed Drains, Level 4 Deck"))
    story.append(body(
        "Fourteen of the twenty-two floor drains on Level 4 are fully clogged with debris, directing "
        "runoff across the slab toward the building core and down open joints to Level 3. "
        "Salt-laden water staining is visible on Level 3 soffits below Level 4 drain locations. "
        "Drain cleaning and replacement of failed drain collars is required within 90 days to "
        "prevent accelerated chloride ingress."
    ))
    story.append(sp())

    story.append(h2("2.4  Freeze–Thaw Surface Damage — Exterior Faces, Levels 4–7"))
    story.append(body(
        "Exterior faces of the structure on Levels 4 through 7 show surface popout and scaling consistent "
        "with freeze–thaw damage. The damage is limited to the top 1/4 inch of the concrete cover and "
        "does not compromise structural capacity. Application of a penetrating silane-siloxane sealer "
        "is recommended at the next maintenance cycle to reduce water absorption."
    ))
    story.append(sp(2))

    story.append(h1("3. Recommendations"))
    story.append(findings_table(
        [["Priority", "Action", "Timeframe", "Est. Cost"],
         ["1 — Medium", "Clean and replace 14 clogged drain collars on Level 4", "90 days", "$28,000"],
         ["2 — Medium", "Epoxy crack injection for cracks >0.020 in on Levels 2–4", "6 months", "$55,000"],
         ["3 — Medium", "Epoxy mortar patch repair at all rebar exposure locations, Level 3", "6 months", "$82,000"],
         ["4 — Medium", "Protective sealant application (silane-siloxane), exterior Levels 4–7", "12 months", "$44,000"],
         ["5 — Low", "Crack width monitoring program — bi-annual readings at flagged locations", "Ongoing", "$6,000"]],
        col_widths=[1.0*inch, 3.2*inch, 1.1*inch, 1.2*inch]
    ))
    story.append(sp(2))

    story.append(body(
        "<b>Prepared by:</b> Angela Foster, PE | Michael Baker International — Philadelphia, PA Office | "
        "January 19, 2024. No immediate structural risk identified; timely repair recommended."
    ))
    return story

# COMMAND ----------
# ── CONCRETE REPORT 3: SR-422 Retaining Wall ─────────────────────────────────

def build_CO003():
    story = []
    mbi_cover(story,
        report_id  = "INS-CO-003",
        title      = "SR-422 Retaining Wall — Section 3, Norristown",
        subtitle   = "Concrete Condition Assessment",
        client     = "Pennsylvania DOT — District 6",
        date_str   = "May 14, 2024",
        inspector  = "Robert Castillo, PE")

    story.append(h1("1. Executive Summary"))
    story.append(body(
        "The SR-422 Retaining Wall Section 3 in Norristown, PA (Montgomery County) was assessed on "
        "May 14, 2024. This 340-ft cast-in-place concrete cantilever retaining wall was constructed in 1992 "
        "and carries SR-422 on the retained side. Overall condition is rated 7 out of 9 (Good). "
        "No immediate safety concerns were identified. Observed deficiencies include minor shrinkage "
        "and construction joint cracking, efflorescence from drainage deficiencies, and minor toe "
        "undercutting. These conditions are consistent with normal aging and do not represent structural risk. "
        "Annual monitoring and targeted maintenance are recommended."
    ))
    story.append(sp())

    story.append(header_table([
        ["Overall Rating", "7 / 9 — Good",          "Structure Type", "Cantilever Concrete Retaining Wall"],
        ["Year Built",     "1992",                   "Wall Length",    "340 ft; avg height 22 ft"],
        ["Location",       "Norristown, PA (SR-422)","Client",        "PennDOT District 6"],
        ["Next Inspection","May 2026 (Biennial)",    "Safety Flag",   "None"],
    ]))
    story.append(sp(2))

    story.append(h1("2. Deficiency Findings"))

    story.append(h2("2.1  Shrinkage and Construction Joint Cracking — Wall Face"))
    story.append(body(
        "Hairline cracking was observed at 14 of the 18 construction joints along the wall face. "
        "Crack widths range from 0.005 to 0.012 inches — within acceptable limits per ACI 224R. "
        "No efflorescence or moisture seepage is associated with these cracks at this time. "
        "Tuck-pointing with elastomeric sealant is recommended at the next scheduled maintenance cycle "
        "to prevent water infiltration."
    ))
    story.append(sp())

    story.append(h2("2.2  Efflorescence and Staining — Lower Wall, Stations 40–65"))
    story.append(body(
        "White efflorescence deposits and rust-orange staining are present on the lower 6 ft of the "
        "wall face between Stations 40 and 65. This pattern is consistent with inadequate drainage "
        "causing water to migrate through the wall and dissolve calcium hydroxide from the concrete. "
        "The drainage relief holes in this section are partially blocked. Cleaning and reopening of "
        "the drain holes is recommended within 6 months."
    ))
    story.append(sp())

    story.append(h2("2.3  Minor Toe Undermining — Station 28–34"))
    story.append(body(
        "Minor undermining of the wall toe was observed at Stations 28–34, attributed to stormwater "
        "erosion during high-flow events along the adjacent drainage ditch. Soil loss depth is "
        "approximately 3 inches, exposing the top of the footing. No structural distress was observed. "
        "Rip-rap erosion protection (D50 = 6 in) is recommended at the toe for a 30-ft zone within 12 months."
    ))
    story.append(sp(2))

    story.append(h1("3. Recommendations"))
    story.append(findings_table(
        [["Priority", "Action", "Timeframe", "Est. Cost"],
         ["1 — Low", "Clear and reopen drainage relief holes, Stations 40–65", "6 months", "$6,500"],
         ["2 — Low", "Tuck-point construction joints with elastomeric sealant (18 joints)", "12 months", "$22,000"],
         ["3 — Low", "Rip-rap toe protection, Stations 28–34 (30 ft × D50=6in)", "12 months", "$18,000"],
         ["4 — Low", "Annual crack width monitoring (14 flagged joints)", "Ongoing", "$4,000"]],
        col_widths=[1.0*inch, 3.35*inch, 1.1*inch, 1.05*inch]
    ))
    story.append(sp(2))

    story.append(body(
        "<b>Prepared by:</b> Robert Castillo, PE | Michael Baker International — Philadelphia, PA Office | "
        "May 14, 2024. Structure is in Good overall condition. No immediate safety concern."
    ))
    return story

# COMMAND ----------
# ── ASPHALT REPORT 1: PHL Airport Runway 09L-27R ─────────────────────────────

def build_AP001():
    story = []
    mbi_cover(story,
        report_id  = "INS-AP-001",
        title      = "PHL Airport — Runway 09L-27R Pavement Assessment",
        subtitle   = "Asphalt Pavement Inspection",
        client     = "Philadelphia Airport Authority — Airfield Engineering",
        date_str   = "August 20, 2024",
        inspector  = "James Hargrove, PE (Pavement)")

    story.append(h1("1. Executive Summary"))
    story.append(body(
        "Runway 09L-27R at Philadelphia International Airport was evaluated on August 20, 2024 "
        "using ASTM D5340 Pavement Condition Index (PCI) methodology. The runway is 10,506 ft long "
        "and 150 ft wide. Overall PCI is 52 (Fair). High-severity transverse cracking in the approach "
        "zones (T1–T4), rutting averaging 0.5 inches in landing zones, and Foreign Object Debris (FOD) "
        "generation potential in Zone T3 are the primary concerns. "
        "<b>Zone T3 requires FOD mitigation within 30 days per FAA Advisory Circular 150/5380-6.</b> "
        "A hot-mix asphalt overlay program for Zones T1–T3 is recommended within 12 months."
    ))
    story.append(sp())

    story.append(header_table([
        ["Overall PCI",     "52 — Fair",             "Pavement Type", "HMA over concrete (overlay 2009)"],
        ["Runway Length",   "10,506 ft",             "Width",         "150 ft"],
        ["Location",        "Philadelphia, PA (PHL)","FAA Standard",  "FAA AC 150/5380-6"],
        ["Next Inspection", "August 2025 (Annual)",  "FOD Alert",     "YES — Zone T3"],
    ]))
    story.append(sp(2))

    story.append(h1("2. Deficiency Findings"))

    story.append(h2("2.1  High-Severity Transverse Cracking — Zones T1–T4"))
    story.append(body(
        "High-severity transverse cracking was observed throughout Zones T1 through T4 (approximately "
        "the first 2,500 ft from each threshold). Crack widths range from 0.5 to 1.5 inches with "
        "spalling on crack edges. The cracking pattern is consistent with reflective cracking from "
        "the underlying concrete slab joints. Crack density is 18 ft per 1,000 sf in Zone T1, "
        "increasing to 27 ft per 1,000 sf in Zone T3. This severity requires overlay or reclamation."
    ))
    story.append(sp())

    story.append(h2("2.2  Rutting — Approach and Departure Zones"))
    story.append(body(
        "Pavement rutting averaging 0.5 inches depth (maximum 0.8 inches) was measured in the "
        "approach and departure zones using a 10-foot straightedge per FAA standards. "
        "Rutting of this magnitude creates standing water potential and reduces tire friction "
        "coefficient below FAA minimums in wet conditions. Groove grinding is required in "
        "affected approach zones prior to the next wet season (November 2024)."
    ))
    story.append(sp())

    story.append(h2("2.3  FOD Generation Potential — Zone T3"))
    story.append(body(
        "Zone T3 (Stations 2,000–2,500 from the 09L threshold) has advanced spalling and loose "
        "aggregate at crack edges. During the inspection, 14 pieces of aggregate were collected "
        "from the pavement surface in a single 500-ft walk. This level of FOD generation "
        "presents an aircraft engine ingestion hazard and requires immediate remediation. "
        "Per FAA AC 150/5380-6, a crack seal program or temporary surface treatment must be "
        "applied within 30 days. Monthly FOD walks are required until overlay is complete."
    ))
    story.append(sp())

    story.append(h2("2.4  Longitudinal Cracking — Runway Centerline, Full Length"))
    story.append(body(
        "A low-severity longitudinal crack follows the runway centerline for approximately 6,800 ft. "
        "Crack width is 0.1 to 0.3 inches. This is likely a construction joint in the underlying "
        "concrete slab. Crack sealing with hot-pour rubberized asphalt is recommended within 6 months."
    ))
    story.append(sp(2))

    story.append(h1("3. Recommendations"))
    story.append(findings_table(
        [["Priority", "Action", "Timeframe", "Est. Cost"],
         ["1 — High", "FOD mitigation: crack seal Zone T3 and monthly FOD walks", "30 days", "$48,000"],
         ["1 — High", "Groove grinding in rutted approach and departure zones", "Nov 2024", "$185,000"],
         ["2 — High", "Hot-mix overlay (2-inch) Zones T1–T3 (approx. 240,000 sf)", "12 months", "$1,850,000"],
         ["3 — Medium", "Hot-pour crack seal, centerline crack, full runway length", "6 months", "$65,000"],
         ["4 — Low", "Annual PCI re-evaluation and friction testing program", "Annual", "$22,000"]],
        col_widths=[1.0*inch, 3.25*inch, 1.1*inch, 1.15*inch]
    ))
    story.append(sp(2))

    story.append(body(
        "<b>Prepared by:</b> James Hargrove, PE | Michael Baker International — Philadelphia, PA Office | "
        "August 20, 2024. FAA notification of FOD condition transmitted to Airport Authority on inspection date."
    ))
    return story

# COMMAND ----------
# ── ASPHALT REPORT 2: I-78 Eastbound Segment 3 ───────────────────────────────

def build_AP002():
    story = []
    mbi_cover(story,
        report_id  = "INS-AP-002",
        title      = "I-78 Eastbound — Pavement Condition Assessment, Segment 3 (MM 12–18)",
        subtitle   = "Asphalt Pavement Inspection",
        client     = "Pennsylvania DOT — District 5",
        date_str   = "April 11, 2024",
        inspector  = "Priya Nair, PE")

    story.append(h1("1. Executive Summary"))
    story.append(body(
        "Segment 3 of I-78 Eastbound (Mile Markers 12–18) in Lehigh County, PA was evaluated on "
        "April 11, 2024. Overall Pavement Condition Index is 41 (Poor). "
        "The 6-mile segment shows extensive block cracking, pothole clusters at two locations, "
        "full-length longitudinal joint cracking, and pavement deformation near the weigh station "
        "at MM 14.2. Sections MM 13–15 require full-depth reclamation due to base failure. "
        "Sections MM 15–18 can be addressed with mill-and-overlay. Immediate temporary pothole "
        "patching is required at MM 13.2 and 14.7 to maintain safe operations."
    ))
    story.append(sp())

    story.append(header_table([
        ["Overall PCI",    "41 — Poor",              "Pavement Type",  "HMA, 4-inch surface over granular base"],
        ["Segment Length", "6.0 miles (MM 12–18)",   "Lanes",          "3 EB + shoulder"],
        ["Location",       "Lehigh County, PA",      "AADT",           "52,000 (29% trucks)"],
        ["Next Inspection","April 2025 (Annual)",    "Safety Alert",   "Pothole patching required immediately"],
    ]))
    story.append(sp(2))

    story.append(h1("2. Deficiency Findings"))

    story.append(h2("2.1  Block Cracking — High Density, Full Segment"))
    story.append(body(
        "High-density block cracking covers approximately 30% of the pavement surface across the "
        "6-mile segment. Block sizes range from 2 to 12 sq ft. The pattern is consistent with "
        "age hardening of the asphalt binder and thermal cycling without adequate crack relief. "
        "Block cracking density is highest in MM 13–15 (45% surface area) corresponding to "
        "a section with thinner pavement structure overlying a poorly draining subbase."
    ))
    story.append(sp())

    story.append(h2("2.2  Pothole Clusters — MM 13.2 and MM 14.7"))
    story.append(body(
        "Two pothole cluster zones were identified. At MM 13.2, 23 potholes ranging from 6 to "
        "18 inches diameter and up to 5 inches deep are present in the travel and passing lanes. "
        "At MM 14.7, 17 potholes of similar severity are concentrated near the weigh station approach. "
        "Both locations present an immediate vehicle damage and safety hazard. "
        "Temporary cold-mix patching is required within 48 hours pending permanent repair programming."
    ))
    story.append(sp())

    story.append(h2("2.3  Longitudinal Joint Cracking — Full 6-Mile Length"))
    story.append(body(
        "A continuous longitudinal crack follows the lane line between the travel and passing lanes "
        "for the full 6-mile segment. Crack widths range from 0.25 to 0.75 inches. "
        "The crack is consistent with a cold construction joint from the original paving operation. "
        "In sections where water infiltration has occurred, secondary transverse cracks and "
        "edge-drop depressions are developing. Hot-pour rubberized crack seal is recommended "
        "for sections with crack widths less than 0.5 inches; wider sections require routing and sealing."
    ))
    story.append(sp())

    story.append(h2("2.4  Pavement Deformation — MM 14.0–14.4 (Weigh Station Approach)"))
    story.append(body(
        "Significant shoving and rutting (maximum 1.3 inches) is present on the weigh station "
        "approach ramp and the through-lanes at MM 14.0–14.4. The deformation is caused by "
        "slow-speed heavy vehicle loading on an asphalt mixture with insufficient stability. "
        "The underlying base shows pumping under load, indicating moisture intrusion and "
        "base saturation. Full-depth reclamation with cement-treated base is required for this zone."
    ))
    story.append(sp(2))

    story.append(h1("3. Recommendations"))
    story.append(findings_table(
        [["Priority", "Action", "Timeframe", "Est. Cost"],
         ["1 — High", "Cold-mix pothole patching: MM 13.2 (23 holes) and MM 14.7 (17 holes)", "48 hours", "$18,000"],
         ["2 — High", "Full-depth reclamation with CTB: MM 13.0–15.0 (2 miles)", "Summer 2024", "$3,200,000"],
         ["3 — Medium", "Mill and overlay (3-inch): MM 15.0–18.0 (3 miles)", "Fall 2024", "$2,800,000"],
         ["4 — Medium", "Route and seal longitudinal joint: full segment", "Summer 2024", "$120,000"],
         ["5 — Low", "Annual PCI reassessment and drainage improvements", "Annual", "$35,000"]],
        col_widths=[1.0*inch, 3.25*inch, 1.1*inch, 1.15*inch]
    ))
    story.append(sp(2))

    story.append(body(
        "<b>Prepared by:</b> Priya Nair, PE | Michael Baker International — Allentown, PA Office | "
        "April 11, 2024. Emergency pothole patching notification provided to PennDOT District 5 on inspection date."
    ))
    return story

# COMMAND ----------
# ── ASPHALT REPORT 3: Valley Forge Industrial Roads ──────────────────────────

def build_AP003():
    story = []
    mbi_cover(story,
        report_id  = "INS-AP-003",
        title      = "Valley Forge Industrial Park — Access Road Network",
        subtitle   = "Asphalt Pavement Inspection",
        client     = "Valley Forge Industrial Partners, LP",
        date_str   = "June 25, 2024",
        inspector  = "Tom Ellison, PE")

    story.append(h1("1. Executive Summary"))
    story.append(body(
        "The access road network at Valley Forge Industrial Park in Chester County, PA was evaluated "
        "on June 25, 2024. The network comprises 4.2 lane-miles of asphalt pavement serving industrial "
        "and heavy vehicle traffic. Overall PCI is 36 (Poor). "
        "The pavement is experiencing significant load-related distress from overweight vehicles, "
        "particularly alligator cracking (40% surface coverage), shoving at loading dock approaches, "
        "and a zone of base failure in the southwest quadrant. "
        "Full-depth reclamation is required for the southwest quadrant. Hot-mix repairs and "
        "weight limit enforcement are required at loading docks B and C within 60 days."
    ))
    story.append(sp())

    story.append(header_table([
        ["Overall PCI",    "36 — Poor",            "Pavement Type",  "HMA, variable 3–5 inch thickness"],
        ["Road Network",   "4.2 lane-miles",        "Primary Loading","Heavy industrial (overweight trucks)"],
        ["Location",       "Chester County, PA",   "Year Paved",     "2008 (partial overlay 2016)"],
        ["Next Inspection","June 2025 (Annual)",   "Safety Alert",   "Weight limit enforcement required"],
    ]))
    story.append(sp(2))

    story.append(h1("2. Deficiency Findings"))

    story.append(h2("2.1  Alligator Cracking — 40% of Network Surface"))
    story.append(body(
        "Alligator (fatigue) cracking covers approximately 40% of the total pavement surface. "
        "The pattern is consistent with structural failure from repeated heavy vehicle loading "
        "on an originally under-designed pavement section. The cracking is most severe on the "
        "primary circulation loop and access roads serving Loading Docks B and C, where "
        "tandem-axle trucks make frequent slow-speed turns. "
        "Areas with alligator cracking are no longer candidates for surface treatment and "
        "require full-depth reclamation or reconstruction."
    ))
    story.append(sp())

    story.append(h2("2.2  Shoving and Distortion — Main Entrance and Loading Dock Turns"))
    story.append(body(
        "Plastic deformation (shoving) up to 2.1 inches is present at the main entrance turn and "
        "at both Loading Dock B and C approach aprons. The shoving is caused by slow-speed, "
        "high-load truck movements on asphalt with insufficient shear strength at ambient summer "
        "temperatures. The turn geometry also concentrates braking and turning forces. "
        "Hot-mix repair with a polymer-modified mix (PG 76-22) is required. "
        "Turning radius redesign for Dock B is recommended to reduce pavement stress."
    ))
    story.append(sp())

    story.append(h2("2.3  Pothole Concentration — Loading Docks B and C Aprons"))
    story.append(body(
        "Nineteen potholes (6 to 24 inches diameter, 3 to 7 inches deep) are concentrated on "
        "the dock aprons at Loading Docks B and C. The potholes have developed from advanced "
        "alligator cracking that progressed to structural failure under repeated truck loading. "
        "Cold-mix patching is an insufficient solution for this traffic level; "
        "full-depth hot-mix repairs with proper base restoration are required."
    ))
    story.append(sp())

    story.append(h2("2.4  Base Failure — Southwest Quadrant"))
    story.append(body(
        "The southwest quadrant of the network (approximately 0.7 lane-miles) shows pumping, "
        "severe alligator cracking, and surface displacement consistent with complete base failure "
        "and subgrade saturation. A drainage investigation revealed a blocked storm sewer "
        "contributing to subgrade moisture. This zone cannot be addressed with surface-only "
        "treatment and requires full-depth reclamation with drainage correction and "
        "cement-treated base stabilization."
    ))
    story.append(sp(2))

    story.append(h1("3. Recommendations"))
    story.append(findings_table(
        [["Priority", "Action", "Timeframe", "Est. Cost"],
         ["1 — High", "Full-depth hot-mix repair: Loading Dock B and C aprons (19 potholes)", "60 days", "$95,000"],
         ["2 — High", "Weight limit enforcement: 80,000 lb GVW on primary loop pending reconstruction", "Immediate", "$0"],
         ["3 — High", "Full-depth reclamation + CTB + HMA overlay: SW quadrant (0.7 lane-mi)", "Summer 2025", "$920,000"],
         ["4 — Medium", "Shoving repair with PG 76-22 HMA at main entrance and dock approaches", "Fall 2024", "$145,000"],
         ["5 — Medium", "Dock B turning radius redesign and reconstruction", "Year 2", "$280,000"],
         ["6 — Medium", "Mill and overlay (3-inch): remaining alligator-cracked areas", "Year 2", "$650,000"]],
        col_widths=[1.0*inch, 3.2*inch, 1.2*inch, 1.1*inch]
    ))
    story.append(sp(2))

    story.append(body(
        "<b>Prepared by:</b> Tom Ellison, PE | Michael Baker International — Philadelphia, PA Office | "
        "June 25, 2024."
    ))
    return story

# COMMAND ----------
# ── ASPHALT REPORT 4: Chestnut Street Streetscape ────────────────────────────

def build_AP004():
    story = []
    mbi_cover(story,
        report_id  = "INS-AP-004",
        title      = "Chestnut Street Streetscape Pavement Assessment",
        subtitle   = "Asphalt Pavement Inspection",
        client     = "City of Philadelphia — Streets Department",
        date_str   = "February 28, 2024",
        inspector  = "Helen Kozlowski, PE")

    story.append(h1("1. Executive Summary"))
    story.append(body(
        "The Chestnut Street Streetscape pavement (8th to 15th Streets) in Center City Philadelphia "
        "was evaluated on February 28, 2024. The corridor is 0.9 miles long with dedicated bus lanes, "
        "bicycle infrastructure, and high pedestrian volumes. Overall PCI is 68 (Good). "
        "The pavement is in generally good condition with localized deficiencies around utility cuts, "
        "catch basin collars, and the bus stop zone at 11th Street. "
        "No immediate safety concerns were identified. A targeted maintenance program for utility "
        "cut restoration and catch basin collar replacement is recommended within 12 months."
    ))
    story.append(sp())

    story.append(header_table([
        ["Overall PCI",    "68 — Good",             "Pavement Type",   "HMA streetscape mix"],
        ["Corridor",       "8th to 15th St (0.9 mi)","Width",          "Variable 40–60 ft"],
        ["Location",       "Philadelphia, PA",      "Context",         "Urban streetscape, high ped"],
        ["Next Inspection","February 2026 (Biennial)","Safety Flag",   "None"],
    ]))
    story.append(sp(2))

    story.append(h1("2. Deficiency Findings"))

    story.append(h2("2.1  Utility Cut Deterioration — Multiple Locations"))
    story.append(body(
        "Thirty-seven utility cut patches were evaluated along the corridor. Nineteen (51%) show "
        "edge cracking and surface settlement ranging from 0.25 to 0.75 inches below grade, "
        "creating tripping hazards and water pooling. The deteriorated cuts are concentrated "
        "between 10th and 13th Streets where recent utility work was performed. "
        "A corridor-wide utility cut restoration program using saw-cut edges and full-depth hot-mix "
        "is recommended within 12 months."
    ))
    story.append(sp())

    story.append(h2("2.2  Catch Basin Collar Cracking and Settlement"))
    story.append(body(
        "Twelve of the twenty-four catch basin collars along the corridor show cracking and settlement, "
        "creating lips of 0.5 to 1.2 inches above surrounding pavement level. "
        "These conditions create bicycle and pedestrian trip hazards and accelerate pavement deterioration "
        "around the structures. Cast-iron frame and grate replacement with proper collar reconstruction "
        "is recommended for the twelve affected units."
    ))
    story.append(sp())

    story.append(h2("2.3  Rutting — Bus Stop Zone, 11th Street"))
    story.append(body(
        "Moderate rutting (0.4 to 0.7 inches) is present in the bus stop zone at 11th Street "
        "on both the eastbound and westbound sides. The rutting is caused by repeated bus "
        "braking and acceleration over a soft mix. "
        "Replacement with a polymer-modified or concrete bus pad insert is recommended to "
        "provide a durable, rut-resistant surface at this high-frequency stop."
    ))
    story.append(sp())

    story.append(h2("2.4  Surface Delamination — Prior Resurfacing Bond Failure"))
    story.append(body(
        "Isolated delamination of the top 0.75-inch lift is present in three locations between "
        "8th and 9th Streets, covering approximately 240 sf. The delamination is attributed to "
        "a poor tack coat bond during the 2019 resurfacing. The areas are currently stable but "
        "will deteriorate into potholes within 1–2 freeze-thaw cycles. "
        "Remove and replace the delaminated layer with a properly tacked surface course."
    ))
    story.append(sp(2))

    story.append(h1("3. Recommendations"))
    story.append(findings_table(
        [["Priority", "Action", "Timeframe", "Est. Cost"],
         ["1 — Medium", "Utility cut restoration program: 19 failing cuts, saw-cut and full-depth HMA", "12 months", "$145,000"],
         ["2 — Medium", "Catch basin collar reconstruction: 12 units", "12 months", "$96,000"],
         ["3 — Medium", "Bus stop pad replacement with polymer-modified or concrete: 11th St EB and WB", "12 months", "$68,000"],
         ["4 — Low", "Delaminated surface removal and replacement (240 sf): 8th–9th St", "6 months", "$12,000"],
         ["5 — Low", "Bi-annual monitoring of PCI; route and seal any new crack development", "Ongoing", "$8,000"]],
        col_widths=[1.0*inch, 3.25*inch, 1.1*inch, 1.15*inch]
    ))
    story.append(sp(2))

    story.append(body(
        "<b>Prepared by:</b> Helen Kozlowski, PE | Michael Baker International — Philadelphia, PA Office | "
        "February 28, 2024. Overall pavement is in Good condition; targeted maintenance recommended."
    ))
    return story

# COMMAND ----------
# ── Generate all 10 PDFs ──────────────────────────────────────────────────────

REPORTS = [
    (build_SS001, f"{base_path}/structural_steel/INS-SS-001_Parker_Street_Overpass.pdf"),
    (build_SS002, f"{base_path}/structural_steel/INS-SS-002_Commerce_Center_Parking_Garage.pdf"),
    (build_SS003, f"{base_path}/structural_steel/INS-SS-003_Riverside_Industrial_Frame.pdf"),
    (build_CO001, f"{base_path}/concrete/INS-CO-001_I95_Bridge_Deck.pdf"),
    (build_CO002, f"{base_path}/concrete/INS-CO-002_Terminal_C_Parking_Structure.pdf"),
    (build_CO003, f"{base_path}/concrete/INS-CO-003_SR422_Retaining_Wall.pdf"),
    (build_AP001, f"{base_path}/asphalt/INS-AP-001_PHL_Runway_09L.pdf"),
    (build_AP002, f"{base_path}/asphalt/INS-AP-002_I78_Eastbound_Segment3.pdf"),
    (build_AP003, f"{base_path}/asphalt/INS-AP-003_Valley_Forge_Industrial.pdf"),
    (build_AP004, f"{base_path}/asphalt/INS-AP-004_Chestnut_Street_Streetscape.pdf"),
]

for build_fn, filepath in REPORTS:
    story = build_fn()
    doc = SimpleDocTemplate(
        filepath, pagesize=LETTER,
        rightMargin=0.75*inch, leftMargin=0.75*inch,
        topMargin=0.75*inch, bottomMargin=0.75*inch,
    )
    doc.build(story)
    print(f"Generated: {os.path.basename(filepath)}")

print("\nAll 10 inspection reports generated.")
for sub in ["structural_steel", "concrete", "asphalt"]:
    files = os.listdir(f"{base_path}/{sub}")
    print(f"  {sub}: {len(files)} files")
