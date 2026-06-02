"""Inspect local MongoDB databases for recovery assessment."""

from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=5000)


def inspect_recovered_users(db) -> None:
    for u in db.users.find({}, {"email": 1, "username": 1, "firebase_uid": 1}):
        print(
            f"  user: {u.get('email')} / {u.get('username')} / {u.get('firebase_uid')}"
        )


for db_name in ("rbt", "user_information"):
    db = client[db_name]
    print(f"\n=== {db_name} ===")
    for coll in sorted(db.list_collection_names()):
        if not coll.startswith("_"):
            print(f"  {coll}: {db[coll].count_documents({})}")

    if db_name == "rbt":
        resume = db.resumes.find_one()
        if resume:
            print("  sample resume fields:", sorted(resume.keys()))
            print("  has content dict:", bool(resume.get("content")))
        with_content = sum(1 for r in db.resumes.find() if r.get("content"))
        print(f"  resumes with content: {with_content}/{db.resumes.count_documents({})}")
        inspect_recovered_users(db)

    if db_name == "user_information":
        resume = db.resumes.find_one()
        if resume:
            print("  legacy embedded sections:", "work_experience" in resume)

client.close()

print("\nRecovery: uv run python scripts/recover_local_mongodb.py [--dry-run] [--target-uri URI]")
