from app.schema_reader import get_all_table_descriptions

descriptions = get_all_table_descriptions("../data/company_data.db")

for table_name, desc in descriptions.items():
    print("=" * 60)
    print(desc)