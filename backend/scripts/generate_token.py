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
    secret_key = "c178c471524b37f64665a81f4ebf8e99d46504c890f71bc133c193da7cc11b71"
    token = jwt.encode(payload, secret_key, algorithm='HS256')

    print("\n--- Tu token JWT para pruebas ---")
    print(token)
    print("\nCópialo y úsalo en el comando curl.\n")

if __name__ == "__main__":
    main()