from cryptography.fernet import Fernet
import sys

def decrypt_file(file_path, key):
    """Descriptografa um arquivo usando a chave."""
    with open(key, 'rb') as key_file:
        cipher_suite = Fernet(key_file.read())
    
    with open(file_path, 'rb') as file:
        encrypted_data = file.read()

    decrypted_data = cipher_suite.decrypt(encrypted_data).decode()

    return decrypted_data

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python decrypt_file.py <arquivo_criptografado> <chave_secreta>")
        sys.exit(1)

    encrypted_file_path = sys.argv[1]
    secret_key_path = sys.argv[2]

    try:
        decrypted_content = decrypt_file(encrypted_file_path, secret_key_path)
        print(f"{decrypted_content}")
    except Exception as e:
        print(f"Erro ao descriptografar o arquivo: {str(e)}")
