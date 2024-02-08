"""
File Integrity Checker

This script provides functions to generate and check the integrity of a text file by creating and comparing hash values.

Usage:
1. Use -g or --generate option to generate a hash file for the specified text file.
   Example: python script_name.py teste.txt -g

2. Omit the option to check for any modifications in the text file since the last hash generation.
   Example: python script_name.py teste.txt

Functions:
- generate_hash_file(file_path): Generates a hash file for the specified text file.
  Parameters:
    - file_path (str): The path to the text file.
  Raises:
    - FileNotFoundError: If the specified file is not found.

- check_file_changes(file_path): Checks for changes in the text file since the last hash generation.
  Parameters:
    - file_path (str): The path to the text file.
  Raises:
    - FileNotFoundError: If the specified file is not found.

- generate_hash(data): Generates a SHA-256 hash for the given data.
  Parameters:
    - data (str): The input data to be hashed.

Example:
```bash
# To generate hash file
python script_name.py teste.txt -g

# To check file changes
python script_name.py teste.txt

"""

import argparse
import hashlib
import os

def generate_hash_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        hash_file_path = file_path + ".hash"

        with open(hash_file_path, 'w', encoding='utf-8') as hash_file:
            for i, line in enumerate(lines, start=1):
                current_hash = generate_hash(line.strip())
                hash_file.write(f"{i}:{current_hash}\n")

        print(f"Hash file generated: {hash_file_path}")

    except FileNotFoundError:
        print(f"File not found: {file_path}")

def check_file_changes(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        hash_file_path = file_path + ".hash"
        stored_hashes = {}

        if os.path.exists(hash_file_path):
            with open(hash_file_path, 'r', encoding='utf-8') as hash_file:
                for line in hash_file:
                    line_data = line.strip().split(":")
                    stored_hashes[line_data[0]] = line_data[1]

        for i, line in enumerate(lines, start=1):
            current_hash = generate_hash(line.strip())
            if str(i) in stored_hashes and stored_hashes[str(i)] == current_hash:
                print(f"Line {i}: Unchanged")
            else:
                print(f"Line {i}: Modified")

    except FileNotFoundError:
        print(f"File not found: {file_path}")

def generate_hash(data):
    return hashlib.sha256(data.encode()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description="File Integrity Checker")
    parser.add_argument('file_path', type=str, help="Path to the text file")
    parser.add_argument('-g', '--generate', action='store_true', help="Generate hash file")
    args = parser.parse_args()

    if args.generate:
        generate_hash_file(args.file_path)
    else:
        check_file_changes(args.file_path)

if __name__ == "__main__":
    main()
