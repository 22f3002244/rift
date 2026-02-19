from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Checking for user_id column in upload_sessions table...")
    inspector = db.inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('upload_sessions')]
    
    if 'user_id' not in columns:
        print("Adding user_id column...")
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE upload_sessions ADD COLUMN user_id VARCHAR(36)"))
            conn.execute(text("CREATE INDEX ix_upload_sessions_user_id ON upload_sessions (user_id)"))
            conn.commit()
        print("Column added successfully.")
    else:
        print("user_id column already exists.")
