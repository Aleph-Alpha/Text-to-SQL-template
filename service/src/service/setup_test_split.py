import json
import os
from collections import Counter, defaultdict
from pathlib import Path

from service.db_service import SQLiteDatabase

parent_dir = Path(__file__).parent.parent
path_to_data = os.path.join(parent_dir, "data")

with open(os.path.join(path_to_data, "spider_data", "dev.json"), "r") as f:
    test_examples = json.load(f)

examples_by_db = defaultdict(list)
for example in test_examples:
    db_id = example.get("db_id")
    examples_by_db[db_id].append(example)

db_counts = Counter([example.get("db_id") for example in test_examples])
print(f"Number of unique databases: {len(db_counts)}")
for db_id, count in sorted(db_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"{db_id}: {count} examples")

suitable_databases = [
    db_id for db_id, examples in examples_by_db.items() if len(examples) >= 20
]
print(f"Databases with 20+ examples: {len(suitable_databases)}")

selected_databases = suitable_databases[:5]

for db_id in selected_databases:
    try:
        path_to_database = os.path.join(
            path_to_data,
            "spider_data",
            "database",
            db_id,
            f"{db_id}.sqlite",
        )

        print(f"Processing database: {db_id}")
        print(f"Database path: {path_to_database}")

        db = SQLiteDatabase(path_to_database)

        structure = db.structure()

        structure_file = os.path.join(path_to_data, f"{db_id}.txt")
        with open(structure_file, "w") as f:
            f.write(structure)

        print(f"Database structure saved to: {structure_file}")

    except Exception as e:
        print(f"Error processing database {db_id}: {e}")

test_dataset = []

for db_id in selected_databases:
    db_examples = examples_by_db[db_id][:20]

    for example in db_examples:
        structured_example = {
            "question": example.get("question", ""),
            "query": example.get("query", ""),
            "db_id": example.get("db_id", ""),
        }
        test_dataset.append(structured_example)

    print(f"Added 20 examples from database: {db_id}")

print(f"\nTotal test examples created: {len(test_dataset)}")

db_id_counts = Counter([example["db_id"] for example in test_dataset])
for db_id, count in db_id_counts.items():
    print(f"{db_id}: {count} examples")

output_file = os.path.join(path_to_data, "test_split.json")
with open(output_file, "w") as f:
    json.dump(test_dataset, f, indent=2)
