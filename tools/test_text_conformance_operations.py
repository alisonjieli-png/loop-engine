"""The DuckDB column profile quotes its table name and refuses text that is not one.

code_nodes/text_conformance is parked on main (forbidden_paths.json
suite_collection_exceptions), so its own checks are not collected here; this
owning check runs on main.
"""
import importlib.util
import unittest

from loop_engine.code_nodes.text_conformance_operations import duckdb_profile_sql


class DuckdbProfileSql(unittest.TestCase):
    def test_a_table_that_is_not_a_plain_or_qualified_name_is_refused(self):
        # Known-wrong control: the table was placed in FROM unquoted, so
        # "rows; DROP TABLE secrets; --" ran a second statement.
        for table in ("rows; DROP TABLE secrets; --", "rows UNION ALL SELECT 1, 1, 1, 1, 1", "rows--",
                      "'data.csv'", "read_csv('data.csv')", 'my"table', "my table", "", ".rows", "rows.",
                      "a.b.c.d", "1rows", None, 7):
            with self.subTest(table=table):
                with self.assertRaises(ValueError):
                    duckdb_profile_sql(table, "name")

    def test_table_parts_and_the_column_are_quoted(self):
        self.assertTrue(duckdb_profile_sql("rows", "name").endswith(' FROM "rows"'))
        self.assertTrue(duckdb_profile_sql("main.rows", "name").endswith(' FROM "main"."rows"'))
        self.assertIn('regexp_matches("na""me", ', duckdb_profile_sql("rows", 'na"me'))

    @unittest.skipUnless(importlib.util.find_spec("duckdb"), "duckdb is not installed")
    def test_the_query_runs_in_duckdb_and_an_injected_name_never_reaches_it(self):
        import duckdb
        connection = duckdb.connect()
        connection.execute('CREATE TABLE "order"("first name" VARCHAR); '
                           "INSERT INTO \"order\" VALUES ('ACME'), ('beta'), (' x '), ('Zoë'); "
                           "CREATE SCHEMA s; CREATE TABLE s.t(v VARCHAR); INSERT INTO s.t VALUES ('A'); "
                           "CREATE TABLE secrets(v VARCHAR)")
        # A reserved word needs the quotes: total, all_upper, all_lower, whitespace_issue, non_ascii.
        self.assertEqual(connection.execute(duckdb_profile_sql("order", "first name")).fetchone(), (4, 1, 2, 1, 1))
        self.assertEqual(connection.execute(duckdb_profile_sql("s.t", "v")).fetchone()[:2], (1, 1))
        with self.assertRaises(ValueError):
            connection.execute(duckdb_profile_sql("s.t; DROP TABLE secrets; --", "v"))
        self.assertEqual(connection.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = 'secrets'").fetchone(), (1,))


if __name__ == "__main__":
    unittest.main()
