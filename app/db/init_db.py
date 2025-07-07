# app/db/init_db.py

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.exc import SQLAlchemyError
from db.session import engine
from db.base_class import Base
import db.base  # 👈 importér alle modeller

def init_db():
    print("🔧 Initialiserer databasen...")

    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database og tabeller oprettet (eller eksisterer allerede).")
    except SQLAlchemyError as e:
        print("❌ Fejl under databaseinitialisering:")
        print(e)

if __name__ == "__main__":
    print("▶️ Kører init_db direkte...")
    init_db()
