# Databricks notebook source
# MAGIC %md
# MAGIC # InspectIQ — Document Ingestion Pipeline
# MAGIC
# MAGIC **End-to-end pipeline**: UC Volumes → PDF parsing → Chunking → Delta tables → Vector Search indexes
# MAGIC
# MAGIC This notebook processes three document sources for the InspectIQ Knowledge Assistant:
# MAGIC 1. **Inspection Reports** (10 PDFs) — Field inspection findings for bridges, buildings, and pavements
# MAGIC 2. **Policy & Standards** (4 PDFs) — MBI SOPs, safety protocols, and engineering repair guides
# MAGIC 3. **Regional Intelligence** (4 PDFs) — State DOT reports, FHWA statistics, and funding updates
# MAGIC
# MAGIC **Architecture**: PDF files in UC Volumes → `pypdf` text extraction → `langchain` chunking → Delta tables (CDF-enabled) → Vector Search Delta Sync indexes with `databricks-bge-large-en` embeddings

# COMMAND ----------

# MAGIC %pip install pypdf langchain-text-splitters databricks-vectorsearch --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md ## Configuration

# COMMAND ----------

catalog     = "mbi_demo"
schema      = "inspectiq"
vs_endpoint = "mbi-inspectiq-vs"
embed_model = "databricks-bge-large-en"

# Source volumes
SOURCES = {
    "inspection_reports": {
        "volume": "inspection_docs",
        "subdirs": ["structural_steel", "concrete", "asphalt"],
        "chunk_table": f"{catalog}.{schema}.doc_chunks",
        "vs_index": f"{catalog}.{schema}.doc_index",
        "chunk_size": 800,
        "chunk_overlap": 100,
        "discipline_map": {
            "structural_steel": "Structural Steel",
            "concrete": "Concrete",
            "asphalt": "Asphalt",
        },
    },
    "policy_standards": {
        "volume": "policy_standards",
        "subdirs": ["."],
        "chunk_table": f"{catalog}.{schema}.policy_chunks",
        "vs_index": f"{catalog}.{schema}.policy_index",
        "chunk_size": 1200,
        "chunk_overlap": 150,
        "discipline_map": {".": "Policy & Standards"},
    },
    "regional_intelligence": {
        "volume": "regional_intelligence",
        "subdirs": ["."],
        "chunk_table": f"{catalog}.{schema}.regional_chunks",
        "vs_index": f"{catalog}.{schema}.regional_index",
        "chunk_size": 1200,
        "chunk_overlap": 150,
        "discipline_map": {".": "Regional Intelligence"},
    },
}

print(f"Catalog: {catalog}")
print(f"Schema:  {schema}")
print(f"VS Endpoint: {vs_endpoint}")
print(f"Embedding Model: {embed_model}")
print(f"Sources: {list(SOURCES.keys())}")

# COMMAND ----------

# MAGIC %md ## Step 1 — Discover and Parse PDFs from UC Volumes

# COMMAND ----------

import os
from pypdf import PdfReader

def extract_pdf_text(path: str) -> str:
    """Extract text from a PDF file using pypdf."""
    reader = PdfReader(path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)

# Discover all PDFs across all sources
all_docs = {}
for source_name, config in SOURCES.items():
    docs = []
    base_vol = f"/Volumes/{catalog}/{schema}/{config['volume']}"
    for sub in config["subdirs"]:
        scan_dir = base_vol if sub == "." else f"{base_vol}/{sub}"
        if not os.path.exists(scan_dir):
            print(f"  WARN: {scan_dir} does not exist, skipping")
            continue
        for fname in sorted(os.listdir(scan_dir)):
            if fname.lower().endswith(".pdf"):
                fpath = f"{scan_dir}/{fname}"
                text = extract_pdf_text(fpath)
                discipline = config["discipline_map"].get(sub, sub)
                docs.append({
                    "path": fpath,
                    "filename": fname,
                    "doc_id": fname.replace(".pdf", ""),
                    "discipline": discipline,
                    "text": text,
                    "char_count": len(text),
                })
    all_docs[source_name] = docs
    print(f"\n📄 {source_name}: {len(docs)} PDFs, {sum(d['char_count'] for d in docs):,} total chars")
    for d in docs:
        print(f"   {d['doc_id'][:50]:50s}  {d['char_count']:>6,} chars  [{d['discipline']}]")

# COMMAND ----------

# MAGIC %md ## Step 2 — Chunk Documents

# COMMAND ----------

from langchain_text_splitters import RecursiveCharacterTextSplitter

all_chunks = {}
for source_name, config in SOURCES.items():
    docs = all_docs[source_name]
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config["chunk_size"],
        chunk_overlap=config["chunk_overlap"],
        length_function=len,
    )
    chunks = []
    for doc in docs:
        splits = splitter.split_text(doc["text"])
        for i, chunk_text in enumerate(splits):
            chunks.append({
                "chunk_id": f"{doc['doc_id']}__chunk_{i:04d}",
                "doc_id": doc["doc_id"],
                "discipline": doc["discipline"],
                "content": chunk_text,
            })
    all_chunks[source_name] = chunks
    print(f"📦 {source_name}: {len(docs)} docs → {len(chunks)} chunks "
          f"(avg {sum(len(c['content']) for c in chunks) // max(1,len(chunks))} chars/chunk)")

# COMMAND ----------

# MAGIC %md ## Step 3 — Write Chunks to Delta Tables (CDF-enabled)

# COMMAND ----------

from pyspark.sql import Row

for source_name, config in SOURCES.items():
    chunks = all_chunks[source_name]
    table_name = config["chunk_table"]

    # Create DataFrame
    rows = [Row(**c) for c in chunks]
    df = spark.createDataFrame(rows)

    # Write to Delta table
    df.write \
        .mode("overwrite") \
        .option("overwriteSchema", "true") \
        .saveAsTable(table_name)

    # Enable Change Data Feed (required for VS Delta Sync)
    spark.sql(f"""
        ALTER TABLE {table_name}
        SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
    """)

    # Grant permissions
    spark.sql(f"GRANT SELECT ON TABLE {table_name} TO `account users`")

    count = spark.table(table_name).count()
    print(f"✅ {table_name}: {count} chunks written (CDF enabled)")

# COMMAND ----------

# MAGIC %md ## Step 4 — Create Vector Search Endpoint (if needed)

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient

vsc = VectorSearchClient()

# Check if endpoint exists
existing_endpoints = [ep["name"] for ep in vsc.list_endpoints().get("endpoints", [])]
if vs_endpoint in existing_endpoints:
    print(f"✅ Vector Search endpoint '{vs_endpoint}' already exists")
else:
    print(f"🔄 Creating Vector Search endpoint '{vs_endpoint}'...")
    vsc.create_endpoint(name=vs_endpoint, endpoint_type="STANDARD")
    print(f"✅ Endpoint created (may take a few minutes to become ONLINE)")

# COMMAND ----------

# MAGIC %md ## Step 5 — Create or Sync Vector Search Indexes

# COMMAND ----------

import time

existing_indexes = []
try:
    for idx in vsc.list_indexes(vs_endpoint).get("vector_indexes", []):
        existing_indexes.append(idx["name"])
except Exception:
    pass

for source_name, config in SOURCES.items():
    index_name = config["vs_index"]
    table_name = config["chunk_table"]

    if index_name in existing_indexes:
        print(f"🔄 Index '{index_name}' exists — triggering sync...")
        try:
            vsc.get_index(vs_endpoint, index_name).sync()
            print(f"   Sync triggered for {index_name}")
        except Exception as e:
            print(f"   Sync skipped ({e})")
    else:
        print(f"🆕 Creating Delta Sync index '{index_name}'...")
        vsc.create_delta_sync_index(
            endpoint_name=vs_endpoint,
            index_name=index_name,
            source_table_name=table_name,
            pipeline_type="TRIGGERED",
            primary_key="chunk_id",
            embedding_source_column="content",
            embedding_model_endpoint_name=embed_model,
        )
        print(f"   ✅ Index creation initiated for {index_name}")

print("\n⏳ Indexes may take 5-10 minutes to become ready.")

# COMMAND ----------

# MAGIC %md ## Step 6 — Verify Index Status

# COMMAND ----------

for source_name, config in SOURCES.items():
    index_name = config["vs_index"]
    try:
        idx = vsc.get_index(vs_endpoint, index_name)
        status = idx.describe()
        ready = status.get("status", {}).get("ready", False)
        num_rows = status.get("status", {}).get("num_rows", "?")
        state = "✅ READY" if ready else "⏳ PROVISIONING"
        print(f"{state}  {index_name}  ({num_rows} rows)")
    except Exception as e:
        print(f"❌ {index_name}: {e}")

# COMMAND ----------

# MAGIC %md ## Step 7 — Test Retrieval Quality

# COMMAND ----------

test_queries = {
    "inspection_reports": [
        "What structural issues were found in the parking garage?",
        "What corrective actions were recommended for exposed rebar?",
        "What pavement distress was found on the I-78 eastbound segment?",
    ],
    "policy_standards": [
        "What does a condition rating of 4 mean?",
        "How should safety risks be classified and reported?",
        "What causes chloride-induced corrosion in concrete?",
    ],
    "regional_intelligence": [
        "How many bridges are structurally deficient in Pennsylvania?",
        "What IIJA funding is available for bridge projects?",
        "What is the national bridge repair backlog?",
    ],
}

for source_name, queries in test_queries.items():
    config = SOURCES[source_name]
    index_name = config["vs_index"]
    print(f"\n{'='*60}")
    print(f"Testing: {index_name}")
    print(f"{'='*60}")

    try:
        idx = vsc.get_index(vs_endpoint, index_name)
        for query in queries:
            print(f"\n🔍 Query: {query}")
            results = idx.similarity_search(
                query_text=query,
                columns=["chunk_id", "doc_id", "discipline", "content"],
                num_results=3,
            )
            docs = results.get("result", {}).get("data_array", [])
            for i, doc in enumerate(docs):
                chunk_id, doc_id, discipline, content, score = doc
                print(f"   [{i+1}] score={score:.3f}  doc={doc_id}  [{discipline}]")
                print(f"       {content[:120]}...")
    except Exception as e:
        print(f"   ⚠️  Index not ready yet: {e}")
        print(f"   Run this cell again in a few minutes.")

# COMMAND ----------

# MAGIC %md ## Summary
# MAGIC
# MAGIC | Source | Volume | Chunks Table | VS Index | Docs | Chunks |
# MAGIC |--------|--------|-------------|----------|------|--------|
# MAGIC | Inspection Reports | `inspection_docs` | `doc_chunks` | `doc_index` | 10 | ~60 |
# MAGIC | Policy & Standards | `policy_standards` | `policy_chunks` | `policy_index` | 4 | ~30 |
# MAGIC | Regional Intelligence | `regional_intelligence` | `regional_chunks` | `regional_index` | 4 | ~20 |
# MAGIC
# MAGIC All indexes use **Delta Sync** (triggered) with **BGE-Large-EN** embeddings on the `mbi-inspectiq-vs` endpoint.
