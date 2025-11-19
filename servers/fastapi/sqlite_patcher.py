"""
SQLite version patcher for ChromaDB compatibility
This script attempts to use pysqlite3 if available to provide a newer SQLite version
"""

import sys

def patch_sqlite():
    try:
        # Try to import pysqlite3 first
        import pysqlite3.dbapi2 as sqlite3
        # Replace the standard sqlite3 module
        sys.modules['sqlite3'] = sqlite3
        print(f"Using pysqlite3 with SQLite version: {sqlite3.sqlite_version}")
        return True
    except ImportError:
        # Fall back to standard sqlite3
        import sqlite3
        print(f"Using standard sqlite3 with version: {sqlite3.sqlite_version}")
        version_tuple = tuple(map(int, sqlite3.sqlite_version.split('.')))
        required_tuple = (3, 35, 0)
        
        if version_tuple >= required_tuple:
            print("SQLite version is compatible")
            return True
        else:
            print(f"Warning: SQLite version {sqlite3.sqlite_version} is below required 3.35.0")
            return False

if __name__ == "__main__":
    patch_sqlite()