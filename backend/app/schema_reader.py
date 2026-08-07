import sqlite3


def get_table_names(db_path: str) -> list[str]:
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables


def get_table_schema(db_path: str, table_name: str) -> dict:
    """Returns column info, foreign keys, and sample rows for one table."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    columns_info = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    columns = [{"name": col["name"], "type": col["type"]} for col in columns_info]

    fk_info = conn.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()
    foreign_keys = [
        {"column": fk["from"], "references_table": fk["table"], "references_column": fk["to"]}
        for fk in fk_info
    ]

    sample_rows = conn.execute(f"SELECT * FROM {table_name} LIMIT 3").fetchall()
    sample_rows = [dict(row) for row in sample_rows]

    row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

    conn.close()

    return {
        "table_name": table_name,
        "columns": columns,
        "foreign_keys": foreign_keys,
        "sample_rows": sample_rows,
        "row_count": row_count,
    }


def build_table_description(schema: dict) -> str:
    """Turns a table's schema info into a natural-language description for embedding."""
    lines = [f"Table: {schema['table_name']} ({schema['row_count']} rows)"]

    col_lines = [f"  - {col['name']} ({col['type']})" for col in schema["columns"]]
    lines.append("Columns:\n" + "\n".join(col_lines))

    if schema["foreign_keys"]:
        fk_lines = [
            f"  - {fk['column']} references {fk['references_table']}.{fk['references_column']}"
            for fk in schema["foreign_keys"]
        ]
        lines.append("Relationships:\n" + "\n".join(fk_lines))

    if schema["sample_rows"]:
        lines.append(f"Sample row: {schema['sample_rows'][0]}")

    return "\n".join(lines)


def get_all_table_descriptions(db_path: str) -> dict[str, str]:
    """Returns {table_name: description_text} for every table in the database."""
    descriptions = {}
    for table_name in get_table_names(db_path):
        schema = get_table_schema(db_path, table_name)
        descriptions[table_name] = build_table_description(schema)
    return descriptions