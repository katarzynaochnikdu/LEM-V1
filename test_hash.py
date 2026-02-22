#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/kochnik/LEM')
from app.auth import _hash_password, _load_users

users = _load_users()
admin = users.get('admin', {})
stored_hash = admin.get('password_hash')
salt = admin.get('salt')

print(f"Stored hash: {stored_hash}")
print(f"Salt: {salt}")

computed_hash = _hash_password('admin', salt)
print(f"Computed hash for 'admin': {computed_hash}")
print(f"Match: {stored_hash == computed_hash}")
