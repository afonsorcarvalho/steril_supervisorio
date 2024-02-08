from cryptography.fernet import Fernet
import hashlib
import os

def generate_key():
    """Gera uma chave criptográfica."""
    return Fernet.generate_key()

def encrypt_hash(key, hash_value):
    """Criptografa o valor do hash."""
    cipher_suite = Fernet(key)
    cipher_text = cipher_suite.encrypt(hash_value.encode())
    return cipher_text

def decrypt_hash(key, cipher_text):
    """Descriptografa o valor do hash."""
    cipher_suite = Fernet(key)
    hash_value = cipher_suite.decrypt(cipher_text).decode()
    return hash_value

def calculate_file_hash(file_path):
    """Calcula o hash SHA-256 de um arquivo."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as file:
        for byte_block in iter(lambda: file.read(4096), b''):
            sha256.update(byte_block)
    return sha256.hexdigest()

def is_file_modified(file_path, stored_hash, key):
    """Verifica se um arquivo foi modificado."""
    current_hash = calculate_file_hash(file_path)
    decrypted_hash = decrypt_hash(key, stored_hash)
    return current_hash != decrypted_hash

def store_encrypted_hash(file_path, hash_file_path, key):
    """Armazena o hash criptografado de um arquivo."""
    file_hash = calculate_file_hash(file_path)
    encrypted_hash = encrypt_hash(key, file_hash)
    with open(hash_file_path, 'wb') as hash_file:
        hash_file.write(encrypted_hash)

# Exemplo de uso
file_path = 'teste.txt.hash'
hash_file_path = 'teste.txt.hash.crypt'
key_path = 'secret.key'

# Verifica se a chave já existe, se não, gera uma nova
if not os.path.exists(key_path):
    key = generate_key()
    with open(key_path, 'wb') as key_file:
        key_file.write(key)
else:
    with open(key_path, 'rb') as key_file:
        key = key_file.read()

# Verifica se o arquivo hash já existe
if os.path.exists(hash_file_path):
    # O arquivo foi hashado anteriormente, verifica modificações
    stored_hash = open(hash_file_path, 'rb').read()
    if is_file_modified(file_path, stored_hash, key):
        print(f'O arquivo {file_path} foi modificado.')
    else:
        print(f'O arquivo {file_path} está inalterado.')
else:
    # O arquivo não foi hashado anteriormente, cria o hash e armazena
    store_encrypted_hash(file_path, hash_file_path, key)
    print(f'O hash para {file_path} foi armazenado criptografado.')


