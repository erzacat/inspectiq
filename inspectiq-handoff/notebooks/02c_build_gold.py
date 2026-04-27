# Databricks notebook source
# MAGIC %md
# MAGIC # InspectIQ — DLT Pipeline: Build Gold
# MAGIC
# MAGIC Reads from silver tables and produces gold-layer aggregates
# MAGIC that power the AI/BI Dashboard, Genie Space, and agent tools.
# MAGIC
# MAGIC **Pipeline:** `inspectiq-dlt`
# MAGIC **Catalog:** `mbi_demo.inspectiq`

# COMMAND ----------

import dlt
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# ---------------------------------------------------------------------------
# gold_condition_summary
# Condition breakdown by discipline and category — powers dashboard KPI cards.
# ---------------------------------------------------------------------------

@dlt.table(
    name="gold_condition_summary",
    comment="Condition rating summary by inspection type and condition category. Powers the AI/BI dashboard condition breakdown and Genie questions about asset health distribution."
)
def gold_condition_summary():
    return (
        dlt.read("silver_inspections")
        .groupBy("inspection_type", "condition_category")
        .agg(
            F.count("*").alias("project_count"),
            F.round(F.avg("condition_rating"), 1).alias("avg_rating"),
            F.sum("estimated_repair_cost").alias("total_repair_cost"),
            F.sum(F.col("safety_flagged").cast("int")).alias("safety_flagged_count"),
            F.round(F.avg("priority_score"), 1).alias("avg_priority_score"),
        )
    )


# ---------------------------------------------------------------------------
# gold_cost_by_discipline
# Repair cost summary by discipline and condition — bar chart + Genie.
# ---------------------------------------------------------------------------

@dlt.table(
    name="gold_cost_by_discipline",
    comment="Estimated repair cost aggregated by inspection discipline and condition category. Powers cost-by-type bar charts and Genie cost analysis questions."
)
def gold_cost_by_discipline():
    return (
        dlt.read("silver_inspections")
        .groupBy("inspection_type", "condition_category")
        .agg(
            F.count("*").alias("project_count"),
            F.round(F.sum("estimated_repair_cost") / 1e6, 2).alias("total_cost_millions"),
            F.round(F.avg("estimated_repair_cost"), 0).alias("avg_cost_per_project"),
            F.max("estimated_repair_cost").alias("max_single_project_cost"),
        )
    )


# ---------------------------------------------------------------------------
# gold_overdue_inspections
# All overdue inspections ranked by urgency — dashboard table + Genie.
# ---------------------------------------------------------------------------

@dlt.table(
    name="gold_overdue_inspections",
    comment="Overdue inspection records sorted by days overdue. Powers the overdue inspections dashboard widget and Genie queries about scheduling backlog."
)
def gold_overdue_inspections():
    return (
        dlt.read("silver_inspections")
        .filter(F.col("overdue") == True)
        .select(
            "report_id", "project_name", "inspection_type", "state", "location",
            "condition_category", "priority", "inspector",
            "next_inspection_date", "days_overdue",
            "estimated_repair_cost", "safety_flagged",
        )
        .orderBy(F.col("days_overdue").desc())
    )


# ---------------------------------------------------------------------------
# gold_priority_queue
# Top projects ranked by composite priority score — action queue for PMs.
# ---------------------------------------------------------------------------

@dlt.table(
    name="gold_priority_queue",
    comment="Top 20 highest-priority projects ranked by composite priority score (condition + safety + overdue). Powers the priority work queue table and Genie prioritization queries."
)
def gold_priority_queue():
    return (
        dlt.read("silver_inspections")
        .select(
            "report_id", "project_name", "inspection_type", "state", "location",
            "condition_rating", "condition_category", "priority", "priority_score",
            "estimated_repair_cost", "safety_flagged", "overdue", "days_overdue",
            "key_findings",
        )
        .orderBy(F.col("priority_score").desc())
        .limit(20)
    )


# ---------------------------------------------------------------------------
# gold_state_summary
# Geographic breakdown — map/bar chart by state.
# ---------------------------------------------------------------------------

@dlt.table(
    name="gold_state_summary",
    comment="Inspection portfolio summary by state. Powers geographic dashboard views and Genie queries about regional asset health and cost distribution."
)
def gold_state_summary():
    return (
        dlt.read("silver_inspections")
        .groupBy("state")
        .agg(
            F.count("*").alias("project_count"),
            F.round(F.avg("condition_rating"), 2).alias("avg_condition_rating"),
            F.min("condition_rating").alias("min_rating"),
            F.sum("estimated_repair_cost").alias("total_repair_cost"),
            F.sum(F.col("safety_flagged").cast("int")).alias("safety_flagged_count"),
            F.sum(F.col("overdue").cast("int")).alias("overdue_count"),
            F.sum(F.col("nbis_deficient").cast("int")).alias("nbis_deficient_count"),
        )
    )


# ---------------------------------------------------------------------------
# gold_inspector_workload
# Inspector assignment and workload — workforce management.
# ---------------------------------------------------------------------------

@dlt.table(
    name="gold_inspector_workload",
    comment="Inspector assignment summary with workload metrics. Supports Genie questions about inspector capacity, coverage, and assignment balance."
)
def gold_inspector_workload():
    return (
        dlt.read("silver_inspections")
        .groupBy("inspector")
        .agg(
            F.count("*").alias("assigned_projects"),
            F.round(F.avg("condition_rating"), 1).alias("avg_condition_rating"),
            F.sum(F.col("safety_flagged").cast("int")).alias("safety_flagged_count"),
            F.sum(F.col("overdue").cast("int")).alias("overdue_count"),
            F.sum("estimated_repair_cost").alias("total_portfolio_cost"),
            F.collect_set("inspection_type").alias("disciplines"),
            F.collect_set("state").alias("states_covered"),
        )
    )


# ---------------------------------------------------------------------------
# project_assets — full denormalized table (replaces the old 02_structured_data)
# This is the primary table for the Genie Space and SQL tool.
# ---------------------------------------------------------------------------

@dlt.table(
    name="project_assets",
    comment="Complete denormalized inspection project asset table. Primary source for the Genie Space, AI/BI Dashboard datasets, and the supervisor agent SQL tool. Contains all inspection records with computed fields."
)
def project_assets():
    return (
        dlt.read("silver_inspections")
        .select(
            "report_id", "project_name", "location", "state", "county", "client",
            "inspection_type", "inspection_date", "inspector",
            "condition_rating", "condition_category", "priority",
            "estimated_repair_cost", "next_inspection_date", "finding_count",
            "safety_flagged", "nbis_deficient", "overdue",
            "days_since_inspection", "days_overdue", "priority_score",
            "key_findings",
        )
    )
