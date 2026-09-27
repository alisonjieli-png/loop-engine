"""Private, resumable analysis cache for exact cross-corpus set comparison.

This database is an expendable report artifact, never a component catalogue.
It stores captured comparison views and computed indexes, and mutates no source.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import zlib
from collections import Counter
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

from loop_engine.core.library_ingestion.duplicates import normalized, shingles


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def pack(value):
    return zlib.compress(encode(value), level=3)


def unpack(raw):
    return json.loads(zlib.decompress(raw))


class DiskComparison:
    def __init__(self, path, binding, *, resume=False):
        self.path = Path(path).absolute()
        if self.path.is_symlink() or self.path.resolve() != self.path:
            raise ValueError('analysis_cache_path_not_plain')
        if self.path.exists() != resume:
            raise ValueError('analysis_cache_resume_mismatch')
        self.connection = sqlite3.connect(str(self.path))
        self.connection.execute('PRAGMA journal_mode=DELETE')
        self.connection.execute('PRAGMA synchronous=NORMAL')
        self.connection.execute('PRAGMA cache_size=-32768')
        self.connection.execute('PRAGMA temp_store=FILE')
        if not resume:
            self.connection.executescript('''
                CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE groups(id INTEGER PRIMARY KEY, group_key TEXT UNIQUE NOT NULL,
                    text BLOB NOT NULL, size INTEGER, profile BLOB, prefix BLOB, compared INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE subjects(key TEXT PRIMARY KEY, group_id INTEGER NOT NULL,
                    package_digest TEXT NOT NULL, corpus TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE INDEX subjects_group ON subjects(group_id);
                CREATE INDEX subjects_package ON subjects(package_digest);
                CREATE INDEX groups_order ON groups(size,id);
                CREATE TABLE postings(token TEXT NOT NULL, group_id INTEGER NOT NULL, size INTEGER NOT NULL);
                CREATE INDEX postings_token ON postings(token,size);
                CREATE TABLE pairs(left_id INTEGER NOT NULL, right_id INTEGER NOT NULL,
                    intersection INTEGER NOT NULL, union_size INTEGER NOT NULL,
                    PRIMARY KEY(left_id,right_id));
            ''')
            self.set_meta('binding', binding)
            self.set_meta('phase', 'collecting')
            self.connection.commit()
        elif self.get_meta('binding') != binding:
            self.close()
            raise ValueError('analysis_cache_binding_changed')

    def close(self):
        self.connection.close()

    def get_meta(self, key):
        row = self.connection.execute('SELECT value FROM metadata WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def set_meta(self, key, value):
        self.connection.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)', (key, encode(value).decode()))

    def add(self, subject):
        if self.get_meta('phase') != 'collecting':
            raise ValueError('analysis_collection_already_frozen')
        subject = dict(subject)
        text = subject.pop('text')
        normal = normalized(text)
        if not normal:
            raise ValueError('empty_comparison_text')
        group = hashlib.sha256(normal.encode()).hexdigest()
        self.connection.execute('INSERT OR IGNORE INTO groups(group_key,text) VALUES (?,?)', (group, pack(text)))
        group_id = self.connection.execute('SELECT id FROM groups WHERE group_key=?', (group,)).fetchone()[0]
        subject['comparison_group'] = group
        self.connection.execute('INSERT INTO subjects VALUES (?,?,?,?,?)',
            (subject['key'], group_id, subject['package_digest'], subject['corpus'], encode(subject).decode()))

    def freeze_collection(self, collection):
        if self.get_meta('phase') != 'collecting':
            raise ValueError('analysis_collection_already_frozen')
        self.set_meta('collection', collection)
        self.set_meta('phase', 'profiling')
        self.connection.commit()

    def build_profiles(self, threshold, progress=None):
        if not isinstance(threshold, Fraction) or not 0 < threshold <= 1:
            raise ValueError('explicit_fraction_threshold_required')
        phase = self.get_meta('phase')
        if phase == 'collecting':
            raise ValueError('incomplete_collection_requires_new_snapshot')
        previous = self.get_meta('threshold')
        if previous is not None and previous != str(threshold):
            raise ValueError('analysis_threshold_changed')
        if phase in ('joining', 'finished'):
            return
        self.set_meta('threshold', str(threshold))
        self.connection.commit()
        # A global word-frequency order keeps rare terms early without retaining
        # every document's shingle strings or a huge global shingle vocabulary.
        frequencies = Counter()
        for _identity, raw in self.connection.execute('SELECT id,text FROM groups ORDER BY id'):
            frequencies.update(set(normalized(unpack(raw)).split()))
        for done, (identity, raw) in enumerate(self.connection.execute(
                'SELECT id,text FROM groups WHERE profile IS NULL ORDER BY id'), 1):
            profile = shingles(unpack(raw))
            size = len(profile)
            minimum = (size * threshold.numerator + threshold.denominator - 1) // threshold.denominator
            ordered = sorted(profile, key=lambda token: (min(frequencies[word] for word in token.split()), token))
            prefix = ordered[:size - minimum + 1] if size else []
            self.connection.execute('UPDATE groups SET size=?,profile=?,prefix=? WHERE id=?',
                                    (size, pack(sorted(profile)), pack(prefix), identity))
            if done % 250 == 0:
                self.connection.commit()
                if progress:
                    progress({'phase': 'profiling', 'new_profiles': done})
        self.set_meta('phase', 'joining')
        self.connection.commit()

    def compare(self, threshold, progress=None, *, stop_after=None):
        if self.get_meta('threshold') != str(threshold):
            raise ValueError('analysis_threshold_changed')
        if self.get_meta('phase') == 'finished':
            return True
        if self.get_meta('phase') != 'joining':
            raise ValueError('analysis_profiles_not_ready')

        @lru_cache(maxsize=16)
        def profile_for(identity):
            raw = self.connection.execute('SELECT profile FROM groups WHERE id=?', (identity,)).fetchone()[0]
            return frozenset(unpack(raw))

        for processed, (identity, size, raw_prefix) in enumerate(self.connection.execute(
                'SELECT id,size,prefix FROM groups WHERE compared=0 ORDER BY size,id'), 1):
            minimum = (size * threshold.numerator + threshold.denominator - 1) // threshold.denominator
            prefix = unpack(raw_prefix)
            candidates = set()
            for offset in range(0, len(prefix), 128):
                chunk = prefix[offset:offset+128]
                placeholders = ','.join('?' for _ in chunk)
                query = 'SELECT DISTINCT group_id FROM postings WHERE token IN (' + placeholders + ') AND size>=?'
                candidates.update(row[0] for row in self.connection.execute(query, (*chunk, minimum)))
            own = profile_for(identity)
            # One document's pairs, posting additions and completion mark commit
            # together. A resumed join does not silently skip interrupted work.
            with self.connection:
                for other in sorted(candidates):
                    second = profile_for(other)
                    intersection = len(own & second)
                    union = size + len(second) - intersection
                    if union and intersection * threshold.denominator >= union * threshold.numerator:
                        left, right = sorted((identity, other))
                        self.connection.execute('INSERT INTO pairs VALUES (?,?,?,?)', (left, right, intersection, union))
                self.connection.executemany('INSERT INTO postings VALUES (?,?,?)',
                                            ((token, identity, size) for token in prefix))
                self.connection.execute('UPDATE groups SET compared=1 WHERE id=?', (identity,))
            if processed % 250 == 0 and progress:
                progress({'phase': 'joining', 'new_compared': processed,
                          'pairs': self.connection.execute('SELECT count(*) FROM pairs').fetchone()[0]})
            if stop_after is not None and processed >= stop_after:
                return False
        self.set_meta('phase', 'finished')
        self.connection.commit()
        return True

    def pair_rows(self):
        for left, right, intersection, union in self.connection.execute(
                'SELECT left_id,right_id,intersection,union_size FROM pairs ORDER BY left_id,right_id'):
            left_key = self.connection.execute('SELECT group_key FROM groups WHERE id=?', (left,)).fetchone()[0]
            right_key = self.connection.execute('SELECT group_key FROM groups WHERE id=?', (right,)).fetchone()[0]
            yield left_key, right_key, intersection, union
