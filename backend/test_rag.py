from app.vector_store import build_vector_store, retrieve_relevant_tables, expand_with_related_tables
collection = build_vector_store("../data/company_data.db")

test_questions = [
    "What is the total revenue by region?",
    "How many customers are in the Wholesale segment?",
    "Which product has the highest profit margin?",
    "What is the average order quantity?",
]

for question in test_questions:
    print("=" * 60)
    print("Question:", question)
    relevant_tables = retrieve_relevant_tables(collection, question, top_k=3)
    expanded_tables = expand_with_related_tables("../data/company_data.db", relevant_tables)
    for table in expanded_tables:
        dist = f"{table['distance']:.4f}" if table['distance'] is not None else "via relationship"
        print(f"  -> {table['table_name']} ({dist})")