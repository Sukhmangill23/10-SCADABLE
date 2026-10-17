from app.db.database import Base, engine
import app.db.models


def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")


if __name__ == "__main__":
    init_db()