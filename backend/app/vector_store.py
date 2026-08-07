import chromadb
from app.schema_reader import get_all_table_descriptions, get_table_schema, get_table_names


def build_vector_store(db_path: str, collection_name: str = "schema_store"):
    """
    Embeds all table descriptions from the database into an in-memory Chroma collection.
    Returns the collection, ready for querying.
    """
    client = chromadb.Client()

    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    collection = client.create_collection(name=collection_name)

    descriptions = get_all_table_descriptions(db_path)

    ids = list(descriptions.keys())
    documents = list(descriptions.values())

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=[{"table_name": name} for name in ids],
    )

    return collection


def retrieve_relevant_tables(collection, question: str, top_k: int = 3) -> list[dict]:
    """
    Given a question, returns the top_k most relevant tables with their
    full descriptions, ranked by relevance.
    """
    results = collection.query(
        query_texts=[question],
        n_results=top_k,
    )

    relevant = []
    for i in range(len(results["ids"][0])):
        relevant.append({
            "table_name": results["ids"][0][i],
            "description": results["documents"][0][i],
            "distance": results["distances"][0][i],
        })

    return relevant


def expand_with_related_tables(db_path: str, relevant_tables: list[dict], max_tables: int = 6) -> list[dict]:
    """
    Given retrieved tables, also pull in directly connected tables via foreign keys —
    both tables THIS table references, and tables that reference THIS table.
    Capped at max_tables total to prevent context bloat on large schemas.
    """
    all_table_names = {t["table_name"] for t in relevant_tables}
    expanded = list(relevant_tables)
    all_tables_in_db = get_table_names(db_path)

    all_schemas = {name: get_table_schema(db_path, name) for name in all_tables_in_db}

    for table in relevant_tables:
        if len(expanded) >= max_tables:
            break
        table_name = table["table_name"]

        # Forward: tables this table references
        for fk in all_schemas[table_name]["foreign_keys"]:
            if len(expanded) >= max_tables:
                break
            related = fk["references_table"]
            if related not in all_table_names:
                expanded.append({
                    "table_name": related,
                    "description": f"Table: {related} (included via relationship)",
                    "distance": None,
                })
                all_table_names.add(related)

        # Reverse: tables that reference this table
        for other_name, other_schema in all_schemas.items():
            if len(expanded) >= max_tables:
                break
            if other_name in all_table_names:
                continue
            for fk in other_schema["foreign_keys"]:
                if fk["references_table"] == table_name:
                    expanded.append({
                        "table_name": other_name,
                        "description": f"Table: {other_name} (included via relationship)",
                        "distance": None,
                    })
                    all_table_names.add(other_name)
                    break

    return expanded