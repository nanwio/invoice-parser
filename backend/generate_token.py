# backend/generate_token.py
import jwt
from datetime import datetime, timezone, timedelta
from configuration.app_settings import app_settings

def main():
    # Datos del usuario para el token
    payload = {
        'subject': {'username': 'local_tester', 'role': 'admin'},
        'exp': datetime.now(timezone.utc) + timedelta(hours=1),
        'iat': datetime.now(timezone.utc)
    }

    # Generar token con la clave secreta de la configuración
    token = jwt.encode(payload, app_settings.security.JWT_SECRET_KEY, algorithm='HS256')

    print("\n--- Tu token JWT para pruebas ---")
    print(token)
    print("\nCópialo y úsalo en el comando curl.\n")

if __name__ == "__main__":
    main()