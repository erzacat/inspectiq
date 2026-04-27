# Databricks notebook source
# MAGIC %md
# MAGIC # InspectIQ — DLT Pipeline: Ingest & Clean (Bronze → Silver)
# MAGIC
# MAGIC Reads raw JSON from the source volume and produces validated silver tables.
# MAGIC Uses DLT expectations for data quality enforcement.
# MAGIC
# MAGIC **Pipeline:** `inspectiq-dlt`
# MAGIC **Catalog:** `mbi_demo.inspectiq`

# COMMAND ----------

import dlt
from pyspark.sql import functions as F

CATALOG = spark.conf.get("source_catalog", "mbi_demo")
SCHEMA  = spark.conf.get("source_schema", "inspectiq")
SOURCE_BASE = f"/Volumes/{CATALOG}/{SCHEMA}/source_data"

# ---------------------------------------------------------------------------
# bronze_inspections — raw ingestion, no transformation
# ---------------------------------------------------------------------------

@dlt.table(
    name="bronze_inspections",
    comment="Raw inspection records ingested from the MBI inspection management system JSON export. No cleaning applied — preserves source data as-is for lineage."
)
def bronze_inspections():
    return (
        spark.read.option("multiLine", True)
        .json(f"{SOURCE_BASE}/inspection_records.json")
        .withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source_file", F.lit("inspection_records.json"))
    )


# ---------------------------------------------------------------------------
# silver_inspections — cleaned, typed, validated
# ---------------------------------------------------------------------------

@dlt.expect_or_drop("valid_report_id", "report_id IS NOT NULL AND report_id != ''")
@dlt.expect_or_drop("valid_condition_rating", "condition_rating BETWEEN 1 AND 9")
@dlt.expect_or_drop("valid_inspection_type", "inspection_type IN ('Structural Steel', 'Concrete', 'Asphalt')")
@dlt.expect_or_drop("valid_inspection_date", "inspection_date IS NOT NULL")
@dlt.expect_or_drop("non_null_project_name", "project_name IS NOT NULL")
# Warning-only expectations — violations show in DLT UI but rows are kept
@dlt.expect("positive_repair_cost", "estimated_repair_cost >= 0")
@dlt.expect("recent_inspection", "inspection_date >= date_sub(current_date(), 730)")
@dlt.expect("reasonable_repair_cost", "estimated_repair_cost <= 5000000")
@dlt.expect("safety_flag_requires_poor_condition", "NOT safety_flagged OR condition_rating <= 5")
@dlt.table(
    name="silver_inspections",
    comment="Cleaned and validated inspection records with proper types, computed fields (days_since_inspection, days_overdue, priority_score), and data quality enforcement."
)
def silver_inspections():
    return (
        dlt.read("bronze_inspections")
        # Cast to proper types
        .withColumn("inspection_date", F.col("inspection_date").cast("date"))
        .withColumn("next_inspection_date", F.col("next_inspection_date").cast("date"))
        .withColumn("condition_rating", F.col("condition_rating").cast("int"))
        .withColumn("estimated_repair_cost", F.col("estimated_repair_cost").cast("long"))
        .withColumn("finding_count", F.col("finding_count").cast("int"))
        .withColumn("safety_flagged", F.col("safety_flagged").cast("boolean"))
        .withColumn("nbis_deficient", F.col("nbis_deficient").cast("boolean"))
        # Standardize text fields
        .withColumn("state", F.upper(F.trim(F.col("state"))))
        .withColumn("location", F.initcap(F.trim(F.col("location"))))
        .withColumn("inspection_type", F.trim(F.col("inspection_type")))
        # Derive condition_category from rating (normalize — don't trust source)
        .withColumn("condition_category",
            F.when(F.col("condition_rating") <= 3, "Critical")
            .when(F.col("condition_rating") <= 5, "Poor")
            .when(F.col("condition_rating") <= 7, "Fair")
            .otherwise("Good")
        )
        # Derive priority from rating + safety flag
        .withColumn("priority",
            F.when(F.col("condition_rating") <= 3, "Critical")
            .when(F.col("condition_rating") <= 5, "High")
            .when(F.col("condition_rating") <= 7, "Medium")
            .otherwise("Low")
        )
        # Computed fields
        .withColumn("days_since_inspection",
            F.datediff(F.current_date(), F.col("inspection_date"))
        )
        .withColumn("days_overdue",
            F.greatest(
                F.datediff(F.current_date(), F.col("next_inspection_date")),
                F.lit(0)
            )
        )
        .withColumn("overdue",
            F.col("next_inspection_date") < F.current_date()
        )
        .withColumn("priority_score",
            F.round(
                (10 - F.col("condition_rating")) * 2
                + F.col("safety_flagged").cast("int") * 5
                + F.least(F.col("days_overdue").cast("double"), F.lit(365.0)) / 365.0 * 3,
                1
            )
        )
        # Audit columns
        .withColumn("_cleaned_at", F.current_timestamp())
    )
