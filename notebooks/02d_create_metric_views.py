# Databricks notebook source
# MAGIC %md
# MAGIC # InspectIQ — Phase 2d: Create UC Metric Views
# MAGIC
# MAGIC Creates Unity Catalog metric views on top of the DLT gold tables.
# MAGIC Metric views are the **semantic layer** — they define governed business
# MAGIC dimensions and measures with rich descriptions and synonyms.
# MAGIC
# MAGIC **Who consumes them:**
# MAGIC - **Genie** reads metric view definitions to generate more accurate SQL
# MAGIC   from natural language questions
# MAGIC - **AI/BI Dashboards** can query metric views directly
# MAGIC - **Supervisor agent** SQL tool benefits from governed measure definitions
# MAGIC
# MAGIC **Syntax:** `CREATE OR REPLACE VIEW ... WITH METRICS LANGUAGE YAML AS $$ ... $$`

# COMMAND ----------

catalog = "mbi_demo"
schema  = "inspectiq"

print(f"Creating metric views in {catalog}.{schema}")

# COMMAND ----------
# MAGIC %md ## 1. metrics_asset_portfolio
# MAGIC
# MAGIC The primary metric view — covers the full inspection portfolio.
# MAGIC Source: `project_assets` (denormalized DLT gold table)

# COMMAND ----------

asset_portfolio_yaml = f"""version: 1.1

source: {catalog}.{schema}.project_assets

comment: "InspectIQ asset portfolio semantic layer. Defines governed dimensions and measures for the full MBI inspection project portfolio across structural steel, concrete, and asphalt disciplines. Used by Genie, AI/BI dashboards, and downstream agents to answer questions about asset health, repair costs, safety risk, and inspection scheduling."

dimensions:
  - name: inspection_type
    expr: inspection_type
    comment: "The engineering discipline of the inspection — Structural Steel, Concrete, or Asphalt. Used to segment the portfolio by asset class."
    display_name: Inspection Type
    synonyms:
      - discipline
      - asset type
      - inspection category
      - engineering discipline
      - asset class
      - type of inspection

  - name: state
    expr: state
    comment: "Two-letter US state code where the inspected asset is located (e.g., PA, NJ, DE, MD, VA, NY). Used for geographic analysis and regional prioritization."
    display_name: State
    synonyms:
      - location state
      - state abbreviation
      - US state
      - region
      - geography

  - name: location
    expr: location
    comment: "City name where the inspection took place."
    display_name: Location
    synonyms:
      - city
      - project city
      - project location
      - municipality

  - name: condition_category
    expr: condition_category
    comment: "Categorical health classification derived from the FHWA condition rating — Critical (rating 1-3), Poor (4-5), Fair (6-7), or Good (8-9)."
    display_name: Condition Category
    synonyms:
      - condition
      - health
      - asset health
      - condition tier
      - rating category
      - health category

  - name: priority
    expr: priority
    comment: "Action priority assigned to the inspection — Critical, High, Medium, or Low."
    display_name: Priority
    synonyms:
      - urgency
      - priority level
      - action priority
      - severity
      - urgency level

  - name: inspector
    expr: inspector
    comment: "The Professional Engineer (PE) who conducted the inspection."
    display_name: Inspector
    synonyms:
      - inspector name
      - inspecting engineer
      - PE
      - lead inspector
      - professional engineer
      - engineer

  - name: client
    expr: client
    comment: "The MBI client organization that owns the asset (e.g., Pennsylvania DOT, Delaware DOT, Philadelphia Airport Authority)."
    display_name: Client
    synonyms:
      - client organization
      - asset owner
      - customer
      - account

  - name: project_name
    expr: project_name
    comment: "The full descriptive name of the inspected asset."
    display_name: Project Name
    synonyms:
      - project
      - asset name
      - structure name

  - name: safety_flagged
    expr: safety_flagged
    comment: "Boolean flag indicating whether the inspection identified an immediate safety risk. True means a safety risk was documented."
    display_name: Safety Flagged
    synonyms:
      - safety risk
      - safety hazard
      - has safety flag
      - hazard identified
      - safety concern

  - name: overdue
    expr: overdue
    comment: "Boolean flag indicating whether the next scheduled inspection date has passed."
    display_name: Overdue
    synonyms:
      - is overdue
      - past due
      - late
      - inspection overdue
      - overdue for inspection

  - name: nbis_deficient
    expr: nbis_deficient
    comment: "Boolean flag indicating whether the asset fails NBIS (National Bridge Inspection Standards) compliance requirements."
    display_name: NBIS Deficient
    synonyms:
      - NBIS deficient
      - structurally deficient
      - functionally deficient
      - FHWA deficient
      - bridge deficient

  - name: condition_rating
    expr: condition_rating
    comment: "The FHWA numeric condition rating from 1 (worst) to 9 (best). Ratings 1-3 are Critical, 4-5 Poor, 6-7 Fair, 8-9 Good."
    display_name: Condition Rating
    synonyms:
      - rating
      - FHWA rating
      - numeric rating
      - health score
      - condition score

  - name: inspection_date
    expr: inspection_date
    comment: "The date the field inspection was conducted."
    display_name: Inspection Date
    synonyms:
      - date of inspection
      - inspected on
      - field inspection date

  - name: next_inspection_date
    expr: next_inspection_date
    comment: "The scheduled date of the next required inspection."
    display_name: Next Inspection Date
    synonyms:
      - next scheduled inspection
      - reinspection date
      - next due date

measures:
  - name: asset_count
    expr: COUNT(*)
    comment: "Total number of inspection project records. Use to count assets in the portfolio by any dimension."
    display_name: Asset Count
    format:
      type: number
      decimal_places:
        type: exact
        places: 0
    synonyms:
      - number of projects
      - project count
      - number of assets
      - inspection count
      - count of inspections
      - total projects

  - name: avg_condition_rating
    expr: AVG(condition_rating)
    comment: "Average FHWA condition rating across the selected portfolio. Lower values indicate worse average asset health."
    display_name: Average Condition Rating
    format:
      type: number
      decimal_places:
        type: exact
        places: 2
    synonyms:
      - mean rating
      - average rating
      - avg health score
      - mean condition score

  - name: min_condition_rating
    expr: MIN(condition_rating)
    comment: "Worst (lowest) condition rating in the selected portfolio."
    display_name: Minimum Condition Rating
    format:
      type: number
      decimal_places:
        type: exact
        places: 0
    synonyms:
      - worst rating
      - lowest rating
      - minimum rating

  - name: total_repair_cost
    expr: SUM(estimated_repair_cost)
    comment: "Total estimated repair cost across the selected portfolio, in US dollars. Used for budget planning and CapEx forecasting."
    display_name: Total Repair Cost
    format:
      type: currency
      currency_code: USD
      decimal_places:
        type: exact
        places: 0
    synonyms:
      - total cost
      - total repair budget
      - aggregate repair cost
      - sum of repair costs
      - total CapEx

  - name: avg_repair_cost
    expr: AVG(estimated_repair_cost)
    comment: "Average estimated repair cost per project, in US dollars."
    display_name: Average Repair Cost
    format:
      type: currency
      currency_code: USD
      decimal_places:
        type: exact
        places: 0
    synonyms:
      - mean cost
      - avg cost per project
      - average repair budget
      - mean repair cost

  - name: max_repair_cost
    expr: MAX(estimated_repair_cost)
    comment: "Highest single-project estimated repair cost in the portfolio."
    display_name: Maximum Repair Cost
    format:
      type: currency
      currency_code: USD
      decimal_places:
        type: exact
        places: 0
    synonyms:
      - highest cost
      - max cost
      - most expensive project

  - name: safety_flagged_count
    expr: SUM(CAST(safety_flagged AS INT))
    comment: "Count of assets with an active safety risk flag."
    display_name: Safety Flagged Count
    format:
      type: number
      decimal_places:
        type: exact
        places: 0
    synonyms:
      - safety risk count
      - number of safety flags
      - hazard count
      - count of safety risks

  - name: safety_flagged_pct
    expr: "SUM(CAST(safety_flagged AS INT)) * 100.0 / NULLIF(COUNT(*), 0)"
    comment: "Percentage of assets in the portfolio that carry an active safety risk flag."
    display_name: Safety Flagged Percent
    format:
      type: number
      decimal_places:
        type: exact
        places: 1
    synonyms:
      - safety flag rate
      - pct with safety risk
      - safety hazard percentage

  - name: overdue_count
    expr: SUM(CAST(overdue AS INT))
    comment: "Count of assets whose next scheduled inspection date has passed."
    display_name: Overdue Count
    format:
      type: number
      decimal_places:
        type: exact
        places: 0
    synonyms:
      - number overdue
      - overdue inspections
      - late inspections
      - past due count

  - name: overdue_pct
    expr: "SUM(CAST(overdue AS INT)) * 100.0 / NULLIF(COUNT(*), 0)"
    comment: "Percentage of assets in the selected portfolio that are overdue for inspection."
    display_name: Overdue Percent
    format:
      type: number
      decimal_places:
        type: exact
        places: 1
    synonyms:
      - overdue rate
      - pct overdue
      - percentage overdue

  - name: critical_asset_count
    expr: "SUM(CASE WHEN condition_rating <= 3 THEN 1 ELSE 0 END)"
    comment: "Count of assets with a Critical condition rating (1-3)."
    display_name: Critical Asset Count
    format:
      type: number
      decimal_places:
        type: exact
        places: 0
    synonyms:
      - critical count
      - number of critical assets
      - critical condition count
      - severely degraded count

  - name: poor_asset_count
    expr: "SUM(CASE WHEN condition_rating BETWEEN 4 AND 5 THEN 1 ELSE 0 END)"
    comment: "Count of assets with a Poor condition rating (4-5)."
    display_name: Poor Asset Count
    format:
      type: number
      decimal_places:
        type: exact
        places: 0
    synonyms:
      - poor count
      - number of poor assets

  - name: nbis_deficient_count
    expr: SUM(CAST(nbis_deficient AS INT))
    comment: "Count of assets classified as deficient per NBIS."
    display_name: NBIS Deficient Count
    format:
      type: number
      decimal_places:
        type: exact
        places: 0
    synonyms:
      - deficient count
      - number of deficient bridges
      - structurally deficient count

  - name: avg_priority_score
    expr: AVG(priority_score)
    comment: "Average composite priority score across the portfolio. Higher scores mean more urgent action needed."
    display_name: Average Priority Score
    format:
      type: number
      decimal_places:
        type: exact
        places: 2
    synonyms:
      - mean priority
      - avg urgency score
      - composite priority

  - name: avg_finding_count
    expr: AVG(finding_count)
    comment: "Average number of documented deficiency findings per inspection report."
    display_name: Average Findings per Inspection
    format:
      type: number
      decimal_places:
        type: exact
        places: 1
    synonyms:
      - avg findings
      - mean deficiencies
      - average deficiencies per report
"""

spark.sql(
    f"CREATE OR REPLACE VIEW {catalog}.{schema}.metrics_asset_portfolio "
    f"WITH METRICS LANGUAGE YAML AS $${asset_portfolio_yaml}$$"
)
print(f"Created {catalog}.{schema}.metrics_asset_portfolio")

# COMMAND ----------
# MAGIC %md ## 2. metrics_overdue_risk
# MAGIC
# MAGIC Focused metric view for scheduling backlog and re-inspection triage.
# MAGIC Source: `gold_overdue_inspections`

# COMMAND ----------

overdue_risk_yaml = f"""version: 1.1

source: {catalog}.{schema}.gold_overdue_inspections

comment: "InspectIQ overdue inspection risk semantic layer. Focused metric view for scheduling backlog, overdue asset prioritization, and re-inspection triage."

dimensions:
  - name: inspection_type
    expr: inspection_type
    comment: "The engineering discipline of the overdue inspection — Structural Steel, Concrete, or Asphalt."
    display_name: Inspection Type
    synonyms:
      - discipline
      - asset type
      - inspection category
      - asset class

  - name: state
    expr: state
    comment: "Two-letter US state code where the overdue asset is located."
    display_name: State
    synonyms:
      - state code
      - US state
      - region
      - geography

  - name: location
    expr: location
    comment: "City where the overdue asset is located."
    display_name: Location
    synonyms:
      - city
      - project location

  - name: priority
    expr: priority
    comment: "Action priority of the overdue asset — Critical, High, Medium, or Low."
    display_name: Priority
    synonyms:
      - urgency
      - priority level
      - severity

  - name: condition_category
    expr: condition_category
    comment: "Condition category of the overdue asset."
    display_name: Condition Category
    synonyms:
      - condition
      - health
      - asset health

  - name: inspector
    expr: inspector
    comment: "The Professional Engineer assigned to the overdue inspection."
    display_name: Inspector
    synonyms:
      - assigned inspector
      - PE
      - engineer

  - name: safety_flagged
    expr: safety_flagged
    comment: "Whether the overdue asset also carries an active safety risk flag. True means overdue AND safety-flagged — highest urgency combination."
    display_name: Safety Flagged
    synonyms:
      - safety risk
      - hazard flag
      - safety concern

  - name: project_name
    expr: project_name
    comment: "The name of the overdue inspection project/asset."
    display_name: Project Name
    synonyms:
      - asset name
      - project

  - name: report_id
    expr: report_id
    comment: "The MBI inspection report identifier (e.g., INS-SS-002)."
    display_name: Report ID
    synonyms:
      - report identifier
      - report number
      - inspection ID

measures:
  - name: overdue_asset_count
    expr: COUNT(*)
    comment: "Number of assets that are overdue for inspection."
    display_name: Overdue Asset Count
    format:
      type: number
      decimal_places:
        type: exact
        places: 0
    synonyms:
      - number of overdue assets
      - overdue count
      - count of overdue inspections
      - backlog count
      - total overdue

  - name: avg_days_overdue
    expr: AVG(days_overdue)
    comment: "Average number of days past the scheduled next-inspection date across all overdue assets."
    display_name: Average Days Overdue
    format:
      type: number
      decimal_places:
        type: exact
        places: 0
    synonyms:
      - mean days overdue
      - average backlog days
      - avg days late
      - mean days late

  - name: max_days_overdue
    expr: MAX(days_overdue)
    comment: "Longest overdue interval in days."
    display_name: Maximum Days Overdue
    format:
      type: number
      decimal_places:
        type: exact
        places: 0
    synonyms:
      - longest overdue
      - worst backlog days
      - most days late

  - name: total_overdue_cost
    expr: SUM(estimated_repair_cost)
    comment: "Total estimated repair cost across all overdue assets — the dollar exposure of the inspection backlog."
    display_name: Total Overdue Repair Cost
    format:
      type: currency
      currency_code: USD
      decimal_places:
        type: exact
        places: 0
    synonyms:
      - overdue repair exposure
      - total backlog cost
      - overdue cost
      - cost of overdue work

  - name: safety_flagged_overdue_count
    expr: SUM(CAST(safety_flagged AS INT))
    comment: "Count of assets that are BOTH overdue AND flagged for safety — the highest urgency combination."
    display_name: Safety Flagged Plus Overdue Count
    format:
      type: number
      decimal_places:
        type: exact
        places: 0
    synonyms:
      - overdue with safety risk
      - high urgency count
      - overdue hazards
      - overdue safety flags

  - name: critical_overdue_count
    expr: "SUM(CASE WHEN priority = 'Critical' THEN 1 ELSE 0 END)"
    comment: "Count of overdue assets with Critical priority."
    display_name: Critical Priority Overdue Count
    format:
      type: number
      decimal_places:
        type: exact
        places: 0
    synonyms:
      - critical overdue
      - critical backlog count

  - name: avg_overdue_cost
    expr: AVG(estimated_repair_cost)
    comment: "Average repair cost per overdue asset."
    display_name: Average Cost per Overdue Asset
    format:
      type: currency
      currency_code: USD
      decimal_places:
        type: exact
        places: 0
    synonyms:
      - mean overdue cost
      - avg repair cost of overdue asset
"""

spark.sql(
    f"CREATE OR REPLACE VIEW {catalog}.{schema}.metrics_overdue_risk "
    f"WITH METRICS LANGUAGE YAML AS $${overdue_risk_yaml}$$"
)
print(f"Created {catalog}.{schema}.metrics_overdue_risk")

# COMMAND ----------
# MAGIC %md ## Verify

# COMMAND ----------

display(spark.sql(f"""
    SELECT table_name, table_type, comment
    FROM {catalog}.information_schema.tables
    WHERE table_schema = '{schema}'
      AND table_name LIKE 'metrics_%'
    ORDER BY table_name
"""))

# COMMAND ----------
# MAGIC %md ## Sample queries against the metric view
# MAGIC
# MAGIC Once created, metric views can be queried like regular views, but downstream
# MAGIC tools (Genie, dashboards) benefit from the semantic layer's governed definitions.

# COMMAND ----------

# Example 1: Asset count and avg condition by discipline
display(spark.sql(f"""
SELECT
    MEASURE(asset_count)           AS asset_count,
    MEASURE(avg_condition_rating)  AS avg_rating,
    MEASURE(total_repair_cost)     AS total_cost,
    MEASURE(safety_flagged_count)  AS safety_flags
FROM {catalog}.{schema}.metrics_asset_portfolio
GROUP BY inspection_type
"""))

# COMMAND ----------

# Example 2: Overdue breakdown by state
display(spark.sql(f"""
SELECT
    MEASURE(overdue_asset_count)    AS overdue_count,
    MEASURE(avg_days_overdue)       AS avg_days_overdue,
    MEASURE(total_overdue_cost)     AS total_cost_exposure
FROM {catalog}.{schema}.metrics_overdue_risk
GROUP BY state
ORDER BY avg_days_overdue DESC
"""))
