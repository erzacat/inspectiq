# Databricks notebook source
# MAGIC %md
# MAGIC # InspectIQ — Phase 2: Structured Project Asset Data
# MAGIC
# MAGIC Creates the `project_assets` Delta table in `mbi_demo.inspectiq`.
# MAGIC This table powers the **Genie Space** for NL queries like:
# MAGIC - "Which projects in Pennsylvania have a Poor condition rating?"
# MAGIC - "What is the total estimated repair cost by discipline?"
# MAGIC - "Show me all safety-flagged projects"

# COMMAND ----------

catalog = "mbi_demo"
schema  = "inspectiq"

spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")

# COMMAND ----------

import pandas as pd
from datetime import date, timedelta

# The 10 generated report records + 40 synthetic supporting records
# These align with the PDFs generated in notebook 01

REPORT_RECORDS = [
    # ── Structural Steel ──────────────────────────────────────────────────────
    {
        "report_id": "INS-SS-001", "project_name": "Parker Street Highway Overpass",
        "location": "Pittsburgh", "state": "PA", "county": "Allegheny",
        "client": "Pennsylvania DOT — District 11", "inspection_type": "Structural Steel",
        "inspection_date": "2024-10-15", "inspector": "Sarah Chen, PE, S.E.",
        "condition_rating": 5, "condition_category": "Poor",
        "priority": "High", "estimated_repair_cost": 930000,
        "next_inspection_date": "2025-10-15", "finding_count": 4,
        "safety_flagged": False, "nbis_deficient": True, "overdue": False,
        "key_findings": "Section loss fascia girders, fatigue cracking web-to-flange welds, paint failure, bearing corrosion"
    },
    {
        "report_id": "INS-SS-002", "project_name": "Commerce Center Parking Garage",
        "location": "Philadelphia", "state": "PA", "county": "Philadelphia",
        "client": "Commerce Center Associates LLC", "inspection_type": "Structural Steel",
        "inspection_date": "2024-03-22", "inspector": "David Park, PE, SE",
        "condition_rating": 4, "condition_category": "Poor",
        "priority": "Critical", "estimated_repair_cost": 337000,
        "next_inspection_date": "2025-03-22", "finding_count": 4,
        "safety_flagged": True, "nbis_deficient": True, "overdue": False,
        "key_findings": "Exposed rebar Column C-14 (SAFETY RISK), connection corrosion B-8/D-12, floor delamination, secondary beam section loss"
    },
    {
        "report_id": "INS-SS-003", "project_name": "Riverside Industrial Steel Frame — Bldg 4",
        "location": "Baltimore", "state": "MD", "county": "Baltimore City",
        "client": "Riverside Holdings Group", "inspection_type": "Structural Steel",
        "inspection_date": "2024-07-08", "inspector": "Marcus Webb, PE",
        "condition_rating": 6, "condition_category": "Fair",
        "priority": "Medium", "estimated_repair_cost": 122000,
        "next_inspection_date": "2026-07-08", "finding_count": 3,
        "safety_flagged": False, "nbis_deficient": False, "overdue": False,
        "key_findings": "Bracing connection corrosion, bearing plate deterioration, minor purlin section loss"
    },
    # ── Concrete ──────────────────────────────────────────────────────────────
    {
        "report_id": "INS-CO-001", "project_name": "I-95 Northbound Bridge Deck — Wilmington Interchange",
        "location": "Wilmington", "state": "DE", "county": "New Castle",
        "client": "Delaware DOT — Structures Management", "inspection_type": "Concrete",
        "inspection_date": "2024-09-03", "inspector": "Lisa Tran, PE",
        "condition_rating": 4, "condition_category": "Poor",
        "priority": "Critical", "estimated_repair_cost": 2967500,
        "next_inspection_date": "2025-03-03", "finding_count": 4,
        "safety_flagged": True, "nbis_deficient": True, "overdue": False,
        "key_findings": "34% deck delamination, rebar corrosion span 2, scour critical Pier 1 (2.1 ft), joint failure Sta 142+50"
    },
    {
        "report_id": "INS-CO-002", "project_name": "Terminal C Parking Structure — PHL Airport",
        "location": "Philadelphia", "state": "PA", "county": "Philadelphia",
        "client": "Philadelphia Airport Authority", "inspection_type": "Concrete",
        "inspection_date": "2024-01-19", "inspector": "Angela Foster, PE",
        "condition_rating": 6, "condition_category": "Fair",
        "priority": "Medium", "estimated_repair_cost": 215000,
        "next_inspection_date": "2026-01-19", "finding_count": 4,
        "safety_flagged": False, "nbis_deficient": False, "overdue": False,
        "key_findings": "Slab edge cracking/spalling Levels 2-4, rebar exposure column bases Level 3, drain failures Level 4, freeze-thaw damage"
    },
    {
        "report_id": "INS-CO-003", "project_name": "SR-422 Retaining Wall — Section 3",
        "location": "Norristown", "state": "PA", "county": "Montgomery",
        "client": "Pennsylvania DOT — District 6", "inspection_type": "Concrete",
        "inspection_date": "2024-05-14", "inspector": "Robert Castillo, PE",
        "condition_rating": 7, "condition_category": "Good",
        "priority": "Low", "estimated_repair_cost": 50500,
        "next_inspection_date": "2026-05-14", "finding_count": 3,
        "safety_flagged": False, "nbis_deficient": False, "overdue": False,
        "key_findings": "Construction joint hairline cracking, efflorescence/staining Sta 40-65, minor toe undermining Sta 28-34"
    },
    # ── Asphalt ───────────────────────────────────────────────────────────────
    {
        "report_id": "INS-AP-001", "project_name": "PHL Airport Runway 09L-27R",
        "location": "Philadelphia", "state": "PA", "county": "Philadelphia",
        "client": "Philadelphia Airport Authority", "inspection_type": "Asphalt",
        "inspection_date": "2024-08-20", "inspector": "James Hargrove, PE",
        "condition_rating": 5, "condition_category": "Fair",
        "priority": "High", "estimated_repair_cost": 2170000,
        "next_inspection_date": "2025-08-20", "finding_count": 4,
        "safety_flagged": True, "nbis_deficient": False, "overdue": False,
        "key_findings": "High-severity transverse cracking Zones T1-T4, rutting 0.5in approach zones, FOD generation Zone T3, centerline longitudinal crack"
    },
    {
        "report_id": "INS-AP-002", "project_name": "I-78 Eastbound Pavement — Segment 3",
        "location": "Allentown", "state": "PA", "county": "Lehigh",
        "client": "Pennsylvania DOT — District 5", "inspection_type": "Asphalt",
        "inspection_date": "2024-04-11", "inspector": "Priya Nair, PE",
        "condition_rating": 4, "condition_category": "Poor",
        "priority": "High", "estimated_repair_cost": 6173000,
        "next_inspection_date": "2025-04-11", "finding_count": 4,
        "safety_flagged": True, "nbis_deficient": False, "overdue": False,
        "key_findings": "High-density block cracking 30% surface, pothole clusters MM 13.2 and 14.7, longitudinal joint cracking full length, base failure near weigh station"
    },
    {
        "report_id": "INS-AP-003", "project_name": "Valley Forge Industrial Park Access Roads",
        "location": "Valley Forge", "state": "PA", "county": "Chester",
        "client": "Valley Forge Industrial Partners LP", "inspection_type": "Asphalt",
        "inspection_date": "2024-06-25", "inspector": "Tom Ellison, PE",
        "condition_rating": 4, "condition_category": "Poor",
        "priority": "High", "estimated_repair_cost": 2090000,
        "next_inspection_date": "2025-06-25", "finding_count": 4,
        "safety_flagged": True, "nbis_deficient": False, "overdue": False,
        "key_findings": "Alligator cracking 40% surface, shoving at entrance and dock approaches, pothole cluster docks B/C, SW quadrant base failure"
    },
    {
        "report_id": "INS-AP-004", "project_name": "Chestnut Street Streetscape Pavement",
        "location": "Philadelphia", "state": "PA", "county": "Philadelphia",
        "client": "City of Philadelphia — Streets Dept", "inspection_type": "Asphalt",
        "inspection_date": "2024-02-28", "inspector": "Helen Kozlowski, PE",
        "condition_rating": 7, "condition_category": "Good",
        "priority": "Low", "estimated_repair_cost": 329000,
        "next_inspection_date": "2026-02-28", "finding_count": 4,
        "safety_flagged": False, "nbis_deficient": False, "overdue": False,
        "key_findings": "Utility cut deterioration (19 of 37), catch basin collar cracking (12 units), bus stop rutting 11th St, surface delamination 8th-9th St"
    },
]

# ── Synthetic supporting records ─────────────────────────────────────────────

import random
random.seed(77)

INSPECTORS = [
    "Sarah Chen, PE", "David Park, PE", "Marcus Webb, PE", "Lisa Tran, PE",
    "Angela Foster, PE", "Robert Castillo, PE", "James Hargrove, PE",
    "Priya Nair, PE", "Tom Ellison, PE", "Helen Kozlowski, PE",
]
CLIENTS = [
    "Pennsylvania DOT", "New Jersey DOT", "Delaware DOT", "Maryland SHA",
    "Virginia DOT", "FHWA", "County Public Works", "City Public Works",
    "Airport Authority", "Private Owner",
]
TYPES = ["Structural Steel", "Concrete", "Asphalt"]
STATES = {"PA": "Pennsylvania", "NJ": "New Jersey", "DE": "Delaware",
          "MD": "Maryland", "VA": "Virginia", "NY": "New York"}
CITIES = {
    "PA": ["Philadelphia", "Pittsburgh", "Harrisburg", "Allentown", "Erie", "Scranton"],
    "NJ": ["Newark", "Trenton", "Camden", "Jersey City", "Elizabeth"],
    "DE": ["Wilmington", "Dover", "Newark", "Middletown"],
    "MD": ["Baltimore", "Annapolis", "Silver Spring", "Rockville"],
    "VA": ["Richmond", "Norfolk", "Virginia Beach", "Arlington"],
    "NY": ["Buffalo", "Rochester", "Syracuse", "Albany"],
}

synthetic = []
for i in range(40):
    state = random.choice(list(STATES.keys()))
    itype = random.choice(TYPES)
    cond  = random.choices(range(3, 10), weights=[4, 8, 14, 18, 20, 18, 10], k=1)[0]
    ccat  = ("Critical" if cond <= 3 else "Poor" if cond <= 5 else "Fair" if cond <= 7 else "Good")
    insp_date = date(2023, 1, 1) + timedelta(days=random.randint(0, 600))
    freq_days = 180 if cond <= 4 else 365 if cond <= 6 else 730
    next_date = insp_date + timedelta(days=freq_days)
    overdue   = next_date < date.today()
    cost      = round(random.randint(20, 5000) * 1000)
    safety    = cond <= 4 and random.random() > 0.6

    synthetic.append({
        "report_id":             f"INS-{itype[:2].upper()}-{str(i+100).zfill(3)}",
        "project_name":          f"{random.choice(['North', 'South', 'East', 'West', 'Central'])} {random.choice(['Bridge', 'Overpass', 'Facility', 'Structure', 'Road', 'Corridor'])} {chr(65+i%26)}",
        "location":              random.choice(CITIES[state]),
        "state":                 state,
        "county":                f"{random.choice(['Monroe','Warren','Franklin','Adams','Chester'])} County",
        "client":                random.choice(CLIENTS),
        "inspection_type":       itype,
        "inspection_date":       insp_date.isoformat(),
        "inspector":             random.choice(INSPECTORS),
        "condition_rating":      cond,
        "condition_category":    ccat,
        "priority":              ("Critical" if cond <= 3 else "High" if cond <= 5 else "Medium" if cond <= 7 else "Low"),
        "estimated_repair_cost": cost,
        "next_inspection_date":  next_date.isoformat(),
        "finding_count":         random.randint(1, 6),
        "safety_flagged":        safety,
        "nbis_deficient":        cond < 5,
        "overdue":               overdue,
        "key_findings":          random.choice([
            "Section loss and corrosion on primary members",
            "Deck delamination and rebar exposure",
            "Alligator cracking and base failure",
            "Expansion joint failure and drainage issues",
            "Bearing deterioration and paint failure",
            "Spalling at column bases, moisture intrusion",
            "Pothole clusters and longitudinal cracking",
            "Fatigue cracking at weld connections",
        ]),
    })

all_records = REPORT_RECORDS + synthetic
df = pd.DataFrame(all_records)

# Derive computed columns
df["days_since_inspection"] = (
    pd.to_datetime("today") - pd.to_datetime(df["inspection_date"])
).dt.days
df["days_overdue"] = (
    (pd.to_datetime("today") - pd.to_datetime(df["next_inspection_date"])).dt.days
    .clip(lower=0)
)
df["priority_score"] = (
    (10 - df["condition_rating"]) * 2
    + df["safety_flagged"].astype(int) * 5
    + df["days_overdue"].clip(upper=365) / 365 * 3
).round(1)

print(f"Total records: {len(df)}")
print(f"\nCondition distribution:\n{df['condition_category'].value_counts()}")
print(f"\nInspection type breakdown:\n{df['inspection_type'].value_counts()}")
print(f"\nSafety-flagged projects: {df['safety_flagged'].sum()}")
print(f"Overdue inspections: {df['overdue'].sum()}")
print(f"\nTotal estimated repair cost: ${df['estimated_repair_cost'].sum():,.0f}")

# COMMAND ----------

df_spark = spark.createDataFrame(df)
(df_spark.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{catalog}.{schema}.project_assets"))

print(f"Written to {catalog}.{schema}.project_assets")

# COMMAND ----------
# MAGIC %md ## Create Dashboard Views

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE VIEW {catalog}.{schema}.vw_condition_summary AS
SELECT
    inspection_type,
    condition_category,
    COUNT(*) as project_count,
    ROUND(AVG(condition_rating), 1) as avg_rating,
    SUM(estimated_repair_cost) as total_repair_cost,
    SUM(CAST(safety_flagged AS INT)) as safety_flagged_count
FROM {catalog}.{schema}.project_assets
GROUP BY inspection_type, condition_category
ORDER BY inspection_type, condition_category
""")

spark.sql(f"""
CREATE OR REPLACE VIEW {catalog}.{schema}.vw_cost_by_type AS
SELECT
    inspection_type,
    condition_category,
    COUNT(*) as projects,
    ROUND(SUM(estimated_repair_cost) / 1e6, 2) as total_cost_millions,
    ROUND(AVG(estimated_repair_cost), 0) as avg_cost_per_project
FROM {catalog}.{schema}.project_assets
GROUP BY inspection_type, condition_category
""")

spark.sql(f"""
CREATE OR REPLACE VIEW {catalog}.{schema}.vw_overdue_inspections AS
SELECT
    report_id, project_name, inspection_type, state, location,
    condition_category, priority, inspector,
    next_inspection_date, days_overdue, estimated_repair_cost, safety_flagged
FROM {catalog}.{schema}.project_assets
WHERE days_overdue > 0
ORDER BY days_overdue DESC
""")

spark.sql(f"""
CREATE OR REPLACE VIEW {catalog}.{schema}.vw_priority_queue AS
SELECT
    report_id, project_name, inspection_type, state,
    condition_category, priority, priority_score,
    estimated_repair_cost, safety_flagged, key_findings
FROM {catalog}.{schema}.project_assets
ORDER BY priority_score DESC
LIMIT 20
""")

print("Views created: vw_condition_summary, vw_cost_by_type, vw_overdue_inspections, vw_priority_queue")
display(spark.sql(f"SELECT * FROM {catalog}.{schema}.vw_condition_summary"))
