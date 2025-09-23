from api.security.jwt_auth import create_access_token
    import asyncio

    async def main():
        # Datos del usuario para el token (pueden ser cualquiera para la prueba)
        user_data = {"username": "local_tester", "role": "admin"}
        
        # Generamos el token con una duración de 1 hora
        token = create_access_token(subject=user_data, expires_minutes=60)
        
        print("\n--- Tu token JWT para pruebas ---")
        print(token)
        print("\nCópialo y úsalo en el comando curl.\n")

    if __name__ == "__main__":
        asyncio.run(main())