# Databricks notebook source
# MAGIC %md
# MAGIC # InspectIQ — Phase 3: RAG Pipeline (PDF → Vector Search)
# MAGIC
# MAGIC Steps:
# MAGIC 1. Read all 10 PDFs from UC Volume
# MAGIC 2. Parse text with pypdf
# MAGIC 3. Chunk with RecursiveCharacterTextSplitter (800 chars / 100 overlap)
# MAGIC 4. Write chunks to Delta table with CDF enabled (VS sync source)
# MAGIC 5. Create Vector Search endpoint and Delta Sync index
# MAGIC 6. Smoke-test similarity search

# COMMAND ----------

# MAGIC %pip install pypdf langchain-text-splitters databricks-vectorsearch --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

catalog  = "mbi_demo"
schema   = "inspectiq"
volume   = "inspection_docs"

chunk_table  = f"{catalog}.{schema}.doc_chunks"
vs_endpoint  = "mbi-inspectiq-vs"
vs_index     = f"{catalog}.{schema}.doc_index"
embed_model  = "databricks-bge-large-en"

CHUNK_SIZE    = 800
CHUNK_OVERLAP = 100

# COMMAND ----------
# MAGIC %md ## Step 1 — Parse PDFs

import os
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pyspark.sql import Row
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

base_vol = f"/Volumes/{catalog}/{schema}/{volume}"
subdirs  = ["structural_steel", "concrete", "asphalt"]

DISC_MAP = {
    "structural_steel": "Structural Steel",
    "concrete":         "Concrete",
    "asphalt":          "Asphalt",
}

def extract_pdf_text(path: str) -> str:
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)

all_pdfs = []
for sub in subdirs:
    d = f"{base_vol}/{sub}"
    for fname in os.listdir(d):
        if fname.endswith(".pdf"):
            all_pdfs.append({
                "path":       f"{d}/{fname}",
                "filename":   fname,
                "discipline": DISC_MAP[sub],
                "doc_id":     fname.replace(".pdf", ""),
            })

print(f"Found {len(all_pdfs)} PDFs:")
for p in all_pdfs:
    print(f"  [{p['discipline']:20s}] {p['doc_id']}")

# COMMAND ----------
# MAGIC %md ## Step 2 — Chunk

splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    length_function=len,
)

rows = []
for pdf in all_pdfs:
    raw_text = extract_pdf_text(pdf["path"])
    chunks   = splitter.split_text(raw_text)
    for i, chunk in enumerate(chunks):
        rows.append(Row(
            chunk_id    = f"{pdf['doc_id']}__chunk_{i:04d}",
            doc_id      = pdf["doc_id"],
            discipline  = pdf["discipline"],
            chunk_index = i,
            content     = chunk,
            source_path = pdf["path"],
        ))

print(f"Total chunks: {len(rows)}")
for disc in DISC_MAP.values():
    n = sum(1 for r in rows if r.discipline == disc)
    print(f"  {disc}: {n} chunks")

# COMMAND ----------
# MAGIC %md ## Step 3 — Write chunk table (CDF enabled for VS sync)

schema_spark = StructType([
    StructField("chunk_id",    StringType(),  False),
    StructField("doc_id",      StringType(),  False),
    StructField("discipline",  StringType(),  False),
    StructField("chunk_index", IntegerType(), False),
    StructField("content",     StringType(),  False),
    StructField("source_path", StringType(),  False),
])

df_chunks = spark.createDataFrame(rows, schema=schema_spark)
(df_chunks.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .option("delta.enableChangeDataFeed", "true")
    .saveAsTable(chunk_table))

print(f"Written {df_chunks.count()} chunks to {chunk_table}")
display(df_chunks.limit(5))

# COMMAND ----------
# MAGIC %md ## Step 4 — Create Vector Search Endpoint

from databricks.vector_search.client import VectorSearchClient
import time

vsc = VectorSearchClient(disable_notice=True)

existing = [e["name"] for e in vsc.list_endpoints().get("endpoints", [])]
if vs_endpoint not in existing:
    print(f"Creating VS endpoint: {vs_endpoint}")
    vsc.create_endpoint(name=vs_endpoint, endpoint_type="STANDARD")
    while True:
        state = vsc.get_endpoint(vs_endpoint)["endpoint_status"]["state"]
        print(f"  Endpoint state: {state}")
        if state == "ONLINE":
            break
        time.sleep(15)
else:
    print(f"VS endpoint '{vs_endpoint}' already exists")

# COMMAND ----------
# MAGIC %md ## Step 5 — Create Delta Sync Index

try:
    idx = vsc.get_index(vs_endpoint, vs_index)
    print(f"Index {vs_index} already exists — triggering sync")
    idx.sync()
except Exception:
    print(f"Creating index: {vs_index}")
    vsc.create_delta_sync_index(
        endpoint_name                = vs_endpoint,
        index_name                   = vs_index,
        source_table_name            = chunk_table,
        pipeline_type                = "TRIGGERED",
        primary_key                  = "chunk_id",
        embedding_source_column      = "content",
        embedding_model_endpoint_name= embed_model,
    )

# Wait for ONLINE
print("Waiting for VS index to be ONLINE...")
for _ in range(60):
    try:
        status = vsc.get_index(vs_endpoint, vs_index).describe()
        ready = status.get("status", {}).get("ready", False)
        state = status.get("status", {}).get("provisioning_state", "?")
        print(f"  ready={ready}, state={state}")
        if ready:
            print("Index is ONLINE")
            break
    except Exception as ex:
        print(f"  Waiting... {ex}")
    time.sleep(15)

# COMMAND ----------
# MAGIC %md ## Step 6 — Smoke Test

idx = vsc.get_index(vs_endpoint, vs_index)

TEST_QUERIES = [
    "Were any immediate safety risks identified in the parking garage?",
    "What causes concrete deterioration in these reports?",
    "What corrective actions are recommended for alligator cracking?",
    "Which projects have exposed rebar?",
]

for q in TEST_QUERIES:
    print(f"\nQ: {q}")
    results = idx.similarity_search(
        query_text = q,
        columns    = ["chunk_id", "doc_id", "discipline", "content"],
        num_results= 3,
    )
    for r in results["result"]["data_array"]:
        print(f"  [{r[1]}] ({r[2]}) — {r[3][:120].strip()}...")

print("\n--- Phase 3 complete ---")
print(f"  VS endpoint : {vs_endpoint}")
print(f"  VS index    : {vs_index}")
print(f"  Total chunks: {df_chunks.count()}")
