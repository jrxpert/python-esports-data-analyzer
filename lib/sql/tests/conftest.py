# -*- coding: UTF-8 -*-
# flake8: noqa: E303, W503

# http://doc.pytest.org/en/latest/example/simple.html

import pytest
import os
import sys

postgre_dirpath = '{}{}'.format(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'), os.sep)
sys.path.append(postgre_dirpath)

from postgre import Sql  # noqa


# Incremental testing - test steps, to disable comment two functions below
def pytest_runtest_makereport(item, call):
    if "incremental" in item.keywords:
        if call.excinfo is not None:
            parent = item.parent
            parent._previousfailed = item


def pytest_runtest_setup(item):
    if "incremental" in item.keywords:
        previousfailed = getattr(item.parent, "_previousfailed", None)
        if previousfailed is not None:
            pytest.xfail("previous test failed ({})".format(previousfailed.name))


class PostgreDB(object):

    def set_up(self):
        sql = Sql(params={'db': 'database-test'})
        cursor = sql.cursor()

        # delete old tables and generators
        cursor.q('DROP TABLE IF EXISTS "_py_test";')
        cursor.q('DROP SEQUENCE IF EXISTS "s._py_test";')
        cursor.q('DROP TABLE IF EXISTS "_py_test_bytea";')
        cursor.q('DROP TABLE IF EXISTS "_py_test_user";')
        cursor.q('DROP SEQUENCE IF EXISTS "s._py_test_user";')

        # create tables and generators
        cursor.q("""
            CREATE TABLE "_py_test_user" (
                "id" "d.primary_key",
                "first_name" VARCHAR(255),
                "last_name" VARCHAR(255),
                "var" "d.boolean" DEFAULT false,

                CONSTRAINT "pk._py_test_user"
                    PRIMARY KEY ("id")
            );
        """)
        cursor.q('INSERT INTO "_py_test_user" ("id", "first_name", "last_name") VALUES (1, \'Dobron\', \'Tester\');')
        cursor.q('INSERT INTO "_py_test_user" ("id", "first_name", "last_name") VALUES (2, \'Spaton\', \'Kazic\');')
        cursor.q('CREATE SEQUENCE "s._py_test_user" START WITH 2;')
        cursor.q("""
            CREATE TABLE "_py_test" (
                "id" "d.primary_key",
                "user_id" "d.foreign_key",
                "abbrev" VARCHAR(25),
                "name" VARCHAR(255),

                CONSTRAINT "pk._py_test"
                    PRIMARY KEY("id"),

                CONSTRAINT "fk._py_test.user"
                    FOREIGN KEY ("user_id")
                    REFERENCES "_py_test_user" ("id")
                    ON UPDATE CASCADE
                    ON DELETE NO ACTION,

                CONSTRAINT "uk._py_test.abbrev"
                    UNIQUE ("abbrev")
            );
        """)
        cursor.q('CREATE SEQUENCE "s._py_test" START WITH 1;')

        cursor.q("""
            CREATE TABLE "_py_test_bytea" (
                "id" "d.primary_key",
                "user_id" "d.foreign_key",
                "string" VARCHAR(255),
                "bytea" BYTEA,

                CONSTRAINT "pk._py_test_bytea"
                    PRIMARY KEY("id"),

                CONSTRAINT "fk._py_test_bytea.user"
                    FOREIGN KEY ("user_id")
                    REFERENCES "_py_test_user" ("id")
                    ON UPDATE CASCADE
                    ON DELETE NO ACTION
            );
        """)

        sql.disconnect()


    def tear_down(self):
        sql = Sql(params={'db': 'database-test'})

        # create tables and generators
        cursor = sql.cursor()
        cursor.q('DROP TABLE "_py_test";')
        cursor.q('DROP SEQUENCE "s._py_test";')
        cursor.q('DROP TABLE "_py_test_bytea";')
        cursor.q('DROP TABLE "_py_test_user";')
        cursor.q('DROP SEQUENCE "s._py_test_user";')
        sql.disconnect()


@pytest.fixture(scope="module")
def sql():  # Provide the fixture name
    # NOTE: In tests method fixture is used as first argument of each, e.g. `def test_one(self, sql):`
    pgdb = PostgreDB()
    pgdb.set_up()
    propagate_obj = Sql(params={'db': 'database-test'})
    yield propagate_obj  # Provide the fixture value
    pgdb.tear_down()
