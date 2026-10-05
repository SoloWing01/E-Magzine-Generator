from app.database.database import create_database
from app.database import models


if __name__ == "__main__":
    create_database()
    print("Database created successfully.")