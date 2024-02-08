from cryptography.fernet import Fernet
import sys
import os

def generate_key():
    """Gera uma chave criptográfica."""
    return Fernet.generate_key()

def encrypt_file(file_path, key):
    """Criptografa um arquivo usando a chave."""
    with open(key, 'rb') as key_file:
        cipher_suite = Fernet(key_file.read())
    
    with open(file_path, 'r') as file:
        plaintext_data = file.read().encode()

    encrypted_data = cipher_suite.encrypt(plaintext_data)

    return encrypted_data

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python encrypt_file.py <arquivo_a_criptografar> [chave_secreta]")
        sys.exit(1)

    file_to_encrypt = sys.argv[1]

    if len(sys.argv) == 3:
        secret_key_path = sys.argv[2]
    else:
        secret_key_path = 'secret.key'

        # Gera uma nova chave se não foi fornecida
        key = generate_key()
        with open(secret_key_path, 'wb') as key_file:
            key_file.write(key)

    try:
        encrypted_content = encrypt_file(file_to_encrypt, secret_key_path)

        encrypted_file_path = f"{file_to_encrypt}.encrypted"
        with open(encrypted_file_path, 'wb') as encrypted_file:
            encrypted_file.write(encrypted_content)

        print(f"Arquivo criptografado salvo em: {encrypted_file_path}")
    except Exception as e:
        print(f"Erro ao criptografar o arquivo: {str(e)}")
