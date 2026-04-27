# Databricks notebook source
# MAGIC %md
# MAGIC # InspectIQ — Phase 2a: Generate Source Data (JSON)
# MAGIC
# MAGIC Writes raw inspection records as JSON into a UC Volume.
# MAGIC This simulates the "landing zone" — raw data arriving from MBI's
# MAGIC inspection management system before any cleaning or transformation.
# MAGIC
# MAGIC The DLT pipeline (`02b_ingest_and_clean`, `02c_build_gold`) reads from here.

# COMMAND ----------

import json, random, os
from datetime import date, timedelta

catalog = "mbi_demo"
schema  = "inspectiq"
volume  = "source_data"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {catalog}.{schema}.{volume}")

source_path = f"/Volumes/{catalog}/{schema}/{volume}"
print(f"Source volume: {source_path}")

# COMMAND ----------
# MAGIC %md ## Core Inspection Records (10 real reports)

# COMMAND ----------

CORE_RECORDS = [
    # ── Structural Steel ─────────────────────────────────────────────────────
    {
        "report_id": "INS-SS-001", "project_name": "Parker Street Highway Overpass",
        "location": "Pittsburgh", "state": "PA", "county": "Allegheny",
        "client": "Pennsylvania DOT — District 11", "inspection_type": "Structural Steel",
        "inspection_date": "2024-10-15", "inspector": "Sarah Chen, PE, S.E.",
        "condition_rating": 5, "condition_category": "Poor",
        "priority": "High", "estimated_repair_cost": 930000,
        "next_inspection_date": "2025-10-15", "finding_count": 4,
        "safety_flagged": False, "nbis_deficient": True,
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
        "safety_flagged": True, "nbis_deficient": True,
        "key_findings": "Exposed rebar Column C-14 (SAFETY RISK), connection corrosion B-8/D-12, floor delamination, secondary beam section loss"
    },
    {
        "report_id": "INS-SS-003", "project_name": "Riverside Industrial Complex — Building 4",
        "location": "Baltimore", "state": "MD", "county": "Baltimore City",
        "client": "Riverside Holdings Group", "inspection_type": "Structural Steel",
        "inspection_date": "2024-07-08", "inspector": "Marcus Webb, PE",
        "condition_rating": 6, "condition_category": "Fair",
        "priority": "Medium", "estimated_repair_cost": 122000,
        "next_inspection_date": "2026-07-08", "finding_count": 3,
        "safety_flagged": False, "nbis_deficient": False,
        "key_findings": "Bracing connection corrosion, bearing plate deterioration, minor purlin section loss"
    },
    # ── Concrete ─────────────────────────────────────────────────────────────
    {
        "report_id": "INS-CO-001", "project_name": "I-95 Northbound Bridge Deck — Wilmington Interchange",
        "location": "Wilmington", "state": "DE", "county": "New Castle",
        "client": "Delaware DOT — Structures Management", "inspection_type": "Concrete",
        "inspection_date": "2024-09-03", "inspector": "Lisa Tran, PE",
        "condition_rating": 4, "condition_category": "Poor",
        "priority": "Critical", "estimated_repair_cost": 2967500,
        "next_inspection_date": "2025-03-03", "finding_count": 4,
        "safety_flagged": True, "nbis_deficient": True,
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
        "safety_flagged": False, "nbis_deficient": False,
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
        "safety_flagged": False, "nbis_deficient": False,
        "key_findings": "Construction joint hairline cracking, efflorescence/staining Sta 40-65, minor toe undermining Sta 28-34"
    },
    # ── Asphalt ──────────────────────────────────────────────────────────────
    {
        "report_id": "INS-AP-001", "project_name": "PHL Airport Runway 09L-27R",
        "location": "Philadelphia", "state": "PA", "county": "Philadelphia",
        "client": "Philadelphia Airport Authority", "inspection_type": "Asphalt",
        "inspection_date": "2024-08-20", "inspector": "James Hargrove, PE",
        "condition_rating": 5, "condition_category": "Fair",
        "priority": "High", "estimated_repair_cost": 2170000,
        "next_inspection_date": "2025-08-20", "finding_count": 4,
        "safety_flagged": True, "nbis_deficient": False,
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
        "safety_flagged": True, "nbis_deficient": False,
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
        "safety_flagged": True, "nbis_deficient": False,
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
        "safety_flagged": False, "nbis_deficient": False,
        "key_findings": "Utility cut deterioration (19 of 37), catch basin collar cracking (12 units), bus stop rutting 11th St, surface delamination 8th-9th St"
    },
]

# COMMAND ----------
# MAGIC %md ## Synthetic Records (40 additional)

# COMMAND ----------

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
TYPES  = ["Structural Steel", "Concrete", "Asphalt"]
STATES = {"PA": "Pennsylvania", "NJ": "New Jersey", "DE": "Delaware",
          "MD": "Maryland",    "VA": "Virginia",    "NY": "New York"}
CITIES = {
    "PA": ["Philadelphia", "Pittsburgh", "Harrisburg", "Allentown", "Erie"],
    "NJ": ["Newark", "Trenton", "Camden", "Jersey City"],
    "DE": ["Wilmington", "Dover", "Newark"],
    "MD": ["Baltimore", "Annapolis", "Silver Spring"],
    "VA": ["Richmond", "Norfolk", "Virginia Beach"],
    "NY": ["Buffalo", "Rochester", "Syracuse"],
}
FINDINGS_POOL = [
    "Section loss and corrosion on primary members",
    "Deck delamination and rebar exposure",
    "Alligator cracking and base failure",
    "Expansion joint failure and drainage issues",
    "Bearing deterioration and paint failure",
    "Spalling at column bases, moisture intrusion",
    "Pothole clusters and longitudinal cracking",
    "Fatigue cracking at weld connections",
]

synthetic = []
for i in range(40):
    state = random.choice(list(STATES.keys()))
    itype = random.choice(TYPES)
    cond  = random.choices(range(3, 10), weights=[4, 8, 14, 18, 20, 18, 10], k=1)[0]
    ccat  = ("Critical" if cond <= 3 else "Poor" if cond <= 5 else "Fair" if cond <= 7 else "Good")
    insp_date = date(2023, 1, 1) + timedelta(days=random.randint(0, 600))
    freq_days = 180 if cond <= 4 else 365 if cond <= 6 else 730
    next_date = insp_date + timedelta(days=freq_days)
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
        "key_findings":          random.choice(FINDINGS_POOL),
    })

# COMMAND ----------
# MAGIC %md ## Write to Volume as JSON

# COMMAND ----------

all_records = CORE_RECORDS + synthetic

filepath = f"{source_path}/inspection_records.json"
with open(filepath, "w") as f:
    json.dump(all_records, f, indent=2, default=str)

print(f"Wrote {len(all_records)} records to {filepath}")
print(f"  Core reports: {len(CORE_RECORDS)}")
print(f"  Synthetic:    {len(synthetic)}")
print(f"  File size:    {os.path.getsize(filepath) // 1024} KB")
