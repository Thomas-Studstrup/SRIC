# app/db/base.py
# Import alle modeller efter Base er defineret for at undgå cirkulære imports
def import_models():
    from models import user_model  # 👈 importer alle model-filer, for at registrere klasser
    from models import chat_model, message_model  # så tabeller registreres

# Kald funktionen for at registrere modellerne
import_models()
