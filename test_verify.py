#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/kochnik/LEM')
from app.auth import verify_user, _load_users

print("Users:", _load_users())
result = verify_user('admin', 'admin')
print(f"verify_user('admin', 'admin') = {result}")
