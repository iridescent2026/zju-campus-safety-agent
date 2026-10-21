"""Serialize the persisted factory state across scaled container instances."""
import json
import os
import threading
from common.database import connect

_registry_lock = threading.Lock()
_locks = {}


class SharedStateLock:
    def __init__(self, owner):
        self.owner = owner
        self.key = 'campus-factory-state:' + owner.path.name
        with _registry_lock:
            self.lock = _locks.setdefault(str(owner.path.resolve()), threading.RLock())
        self.local = threading.local()

    def __enter__(self):
        self.lock.acquire()
        level = getattr(self.local, 'level', 0)
        if level:
            self.local.level = level + 1
            return self
        self.local.db = None
        try:
            db = self.local.db = connect(self.owner.path)
            if os.getenv('DATABASE_URL'):
                db.execute('SELECT pg_advisory_xact_lock(hashtext(?))', (self.key,))
            if hasattr(self.owner, 'data'):
                row = db.execute('SELECT payload FROM factory_state WHERE id=1').fetchone()
                if row:
                    self.owner.data = json.loads(row[0])
            self.local.level = 1
            return self
        except BaseException:
            try:
                self._close()
            finally:
                self.lock.release()
            raise

    def _close(self):
        db = self.local.db
        if db is not None:
            try:
                db.close()
            finally:
                self.local.db = None

    def __exit__(self, *error):
        self.local.level -= 1
        try:
            if self.local.level == 0:
                self._close()
        finally:
            self.lock.release()
