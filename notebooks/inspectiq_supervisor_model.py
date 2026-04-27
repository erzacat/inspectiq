"""InspectIQ Supervisor — code-based pyfunc model.

Kept in a standalone file (not a notebook cell) so cloudpickle does not walk
notebook-globals that hold a reference to dbutils / the Spark session.

The model config (set via `model_config=` on log_model) must contain:
  - vs_endpoint, vs_index       (Databricks Vector Search)
  - asset_table                 (UC table for SQL tool)
  - warehouse_id                (Databricks SQL warehouse)
  - llm_model                   (Foundation Model API endpoint)
  - system_prompt               (Supervisor routing prompt)
"""

import mlflow
import pandas as pd


class InspectIQSupervisor(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        from databricks_langchain import ChatDatabricks, DatabricksVectorSearch
        from langchain.tools.retriever import create_retriever_tool
        from langchain.agents import AgentExecutor, create_tool_calling_agent
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain_core.tools import tool
        from databricks.sdk import WorkspaceClient

        cfg = context.model_config

        _vs = DatabricksVectorSearch(
            endpoint=cfg["vs_endpoint"],
            index_name=cfg["vs_index"],
            columns=["chunk_id", "doc_id", "discipline", "content"],
        ).as_retriever(search_kwargs={"k": 6})
        _rag_tool = create_retriever_tool(
            retriever=_vs,
            name="search_inspection_reports",
            description="Search full text of MBI inspection reports for findings, deficiencies, recommendations.",
        )

        _llm_sql = ChatDatabricks(endpoint=cfg["llm_model"], temperature=0, max_tokens=512)
        _asset_table = cfg["asset_table"]
        _warehouse_id = cfg["warehouse_id"]
        _w = WorkspaceClient()

        @tool
        def query_project_database(question: str) -> str:
            """Query structured MBI project asset database for counts, costs, trends, filtered lists."""
            schema_desc = (
                f"Table: {_asset_table}\n"
                "Columns: report_id, project_name, location, state, inspection_type, inspection_date, inspector, "
                "condition_rating (1-9), condition_category (Critical/Poor/Fair/Good), priority, "
                "estimated_repair_cost (USD), finding_count, safety_flagged, overdue, days_overdue, key_findings"
            )
            sql_prompt = (
                f"Write a single SQL SELECT for: {question}\n\n"
                f"{schema_desc}\n\nReturn ONLY the SQL, no markdown.\n\nSQL:"
            )
            sql_resp = _llm_sql.invoke(sql_prompt)
            sql = sql_resp.content.strip().strip("```").strip()
            if sql.lower().startswith("sql"):
                sql = sql[3:].strip()
            if not sql.upper().lstrip().startswith("SELECT"):
                return "Only SELECT queries permitted."
            try:
                resp = _w.statement_execution.execute_statement(
                    warehouse_id=_warehouse_id,
                    statement=sql,
                    wait_timeout="30s",
                )
                if resp.status.state.value != "SUCCEEDED":
                    err = resp.status.error.message if resp.status.error else resp.status.state
                    return f"Query error: {err}"
                result = resp.result
                if not result or not result.data_array:
                    return "No results."
                cols = [c.name for c in resp.manifest.schema.columns]
                rows = result.data_array[:20]
                header = " | ".join(cols)
                sep = "-+-".join("-" * len(c) for c in cols)
                body = "\n".join(" | ".join(str(v) for v in r) for r in rows)
                return f"{header}\n{sep}\n{body}"
            except Exception as e:
                return f"Query error: {e}"

        _llm = ChatDatabricks(endpoint=cfg["llm_model"], temperature=0.1, max_tokens=3000)
        _tools = [_rag_tool, query_project_database]
        _prompt = ChatPromptTemplate.from_messages([
            ("system", cfg["system_prompt"]),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ])
        _agent = create_tool_calling_agent(llm=_llm, tools=_tools, prompt=_prompt)
        self.executor = AgentExecutor(
            agent=_agent, tools=_tools, verbose=False,
            max_iterations=8, handle_parsing_errors=True,
        )

    def predict(self, context, model_input, params=None):
        if isinstance(model_input, pd.DataFrame):
            rows = model_input.to_dict(orient="records")
        else:
            rows = [model_input]
        results = []
        for row in rows:
            msgs = row.get("messages", [])
            history, user_msg = [], ""
            for m in msgs:
                if m["role"] == "user":
                    user_msg = m["content"]
                elif m["role"] == "assistant":
                    history.append(("assistant", m["content"]))
            out = self.executor.invoke({"input": user_msg, "chat_history": history})
            results.append(out["output"])
        return results


mlflow.models.set_model(InspectIQSupervisor())
