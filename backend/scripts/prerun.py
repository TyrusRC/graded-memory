from app.db import DB
from app.pipeline import run_pipeline

if __name__ == "__main__":
    db = DB("graded.sqlite"); db.init()
    run_pipeline(db, root="seed/org_prompts")
