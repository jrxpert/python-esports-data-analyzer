# -*- coding: UTF-8 -*-
# flake8: noqa: E303, W503, E712

import os
import sys
from collections import OrderedDict

import pytest
import psycopg2.extras

postgre_dirpath = '{}{}'.format(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'), os.sep)
sys.path.append(postgre_dirpath)

from postgre import Sql as PostgreSql, ConnectionDoesNotExist, TransactionDoesNotExist  # noqa


@pytest.mark.incremental
class TestSql(object):

    def test_connection(self, sql):
        assert str(type(sql.connect())) == "<class 'psycopg2.extensions.connection'>"


    def test_cursor(self, sql):
        cur = sql.cursor()
        assert str(type(cur)) == "<class 'postgre.SqlCursor'>"
        assert str(type(cur.get())) == "<class 'postgre._PgCursor'>"
        # Have to disconnect, because in global object connection already exists
        sql.disconnect()
        with pytest.raises(ConnectionDoesNotExist):
            sql.finish_trans_mode()


    def test_esc_name(self, sql):
        assert '"aaa"' == sql.esc_name('aaa')
        assert ['"aaa"'] == sql.esc_name(['aaa'])
        assert {'0': '"aaa"'} == sql.esc_name({'0': 'aaa'})


    def test_esc_value(self, sql):
        assert "''aaa''" == sql.esc_value("'aaa'")
        assert ["''aaa''"] == sql.esc_value(["'aaa'"])
        assert {'0': "''aaa''"} == sql.esc_value({'0': "'aaa'"})


    def test_start_trans_mode(self, sql):
        sql.start_trans_mode()
        cur = sql.cursor()
        assert False == cur.get().connection.autocommit
        assert str(type(cur)) == "<class 'postgre.SqlCursor'>"
        cur.close()


    def test_finish_trans_mode(self, sql):
        sql.start_trans_mode()
        sql.finish_trans_mode()
        cur = sql.cursor()
        assert True == cur.get().connection.autocommit
        sql.connect().autocommit = True
        with pytest.raises(TransactionDoesNotExist):
            sql.finish_trans_mode()
        # Have to disconnect, because in global object connection already exists
        sql.disconnect()
        with pytest.raises(ConnectionDoesNotExist):
            sql.finish_trans_mode()


    def test_cursor_get(self, sql):
        cur = sql.cursor()
        assert str(type(cur.get())) == "<class 'postgre._PgCursor'>"
        cur.close()


    def test_cursor__q(self, sql):
        cur = sql.cursor()
        assert True == cur.get().connection.autocommit
        with pytest.raises(psycopg2.ProgrammingError):
            cur._q('INSERT INTO "_py_neexistuje" ("id", "user_id", "abbrev", "name") VALUES (1, 1, \'unique\', \'Test\')', None)
        with pytest.raises(psycopg2.ProgrammingError):
            cur._q('SELECT * FROM "_py_neexistuje"', None)
        assert True == cur._q('ALTER SEQUENCE "s._py_test" RESTART WITH 2', None)
        assert True == cur._q('ALTER SEQUENCE "s._py_test" RESTART WITH 1', None)
        assert True == cur._q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (1, 1, \'unique\', \'Test\')', None)
        assert True == cur._q('SELECT * FROM "_py_test"', None)
        assert True == cur._q('DELETE FROM "_py_test"', None)
        assert True == cur._q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (1, 1, \'unique\', \'Test\')', None)
        with pytest.raises(psycopg2.IntegrityError):
            cur._q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (1, 1, \'unique\', \'Test\')', None)
        assert True == cur._q('UPDATE "_py_test" SET "name" = \'Test Updated\'  WHERE "id" = 1', None)
        assert True == cur._q('CREATE TABLE "_py_test2" ("id" "d.primary_key")', None)
        with pytest.raises(psycopg2.ProgrammingError):
            cur._q('CREATE TABLE "_py_test2" ("id" "d.primary_key", "name" VARCHAR(255))', None)
        assert True == cur._q('DROP TABLE "_py_test2"', None)
        assert True == cur._q('DELETE FROM "_py_test" WHERE "id" = 1', None)

        # TODO: add test to execute query with params


    def test_cursor_q(self, sql):
        cur = sql.cursor()
        assert True == cur.get().connection.autocommit
        with pytest.raises(psycopg2.ProgrammingError):
            cur.q('SELECT * FROM "_py_neexistuje"')
        assert True == cur.q('SELECT * FROM "_py_test"')
        assert True == cur.q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (1, 1, \'unique\', \'Test\')')
        assert True == cur.q('DELETE FROM "_py_test" WHERE "id" = 1')
        assert True == cur.q('SELECT * FROM "_py_test"')

        # TODO: add test to execute query with params


    def test_cursor_fo(self, sql):
        cur = sql.cursor()
        cur.q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (1, 1, \'unique\', \'Test\')')
        cur.q('SELECT * FROM "_py_test"')
        data = cur.fo()
        assert str(type(data)) == "<class 'psycopg2.extras.RealDictRow'>"
        assert 4 == len(data.keys())
        cur.q('DELETE FROM "_py_test" WHERE "id" = 1')


    def test_cursor_fa(self, sql):
        cur = sql.cursor()
        cur.q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (1, 1, \'unique\', \'Test\')')
        cur.q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (2, 1, \'unique2\', \'Test2\')')
        cur.q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (3, 1, \'unique3\', \'Test3\')')
        cur.q('SELECT * FROM "_py_test"')
        data = cur.fa()
        assert str(type(data)) == "<class 'list'>"
        assert 3 == len(data)
        cur.q('SELECT * FROM "_py_test"')
        data = cur.fa('id')
        assert str(type(data)) == "<class 'collections.OrderedDict'>"
        assert 3 == len(data)
        cur.q('DELETE FROM "_py_test"')


    def test_cursor_fm(self, sql):
        cur = sql.cursor()
        cur.q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (1, 1, \'unique\', \'Test\')')
        cur.q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (2, 1, \'unique2\', \'Test2\')')
        cur.q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (3, 1, \'unique3\', \'Test3\')')
        cur.q('SELECT * FROM "_py_test"')
        data = cur.fm(2)
        assert str(type(data)) == "<class 'list'>"
        assert 2 == len(data)
        cur.q('SELECT * FROM "_py_test"')
        data = cur.fm(1, 'id')
        assert str(type(data)) == "<class 'collections.OrderedDict'>"
        assert 1 == len(data)
        cur.q('DELETE FROM "_py_test"')


    def test_cursor_qfo(self, sql):
        cur = sql.cursor()
        cur.q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (1, 1, \'unique\', \'Test\')')
        data = cur.qfo('SELECT * FROM "_py_test"')
        assert str(type(data)) == "<class 'psycopg2.extras.RealDictRow'>"
        assert 4 == len(data.keys())
        cur.q('DELETE FROM "_py_test" WHERE "id" = 1')


    def test_cursor_qfa(self, sql):
        cur = sql.cursor()
        cur.q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (1, 1, \'unique\', \'Test\')')
        cur.q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (2, 1, \'unique2\', \'Test2\')')
        cur.q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (3, 1, \'unique3\', \'Test3\')')
        data = cur.qfa('SELECT * FROM "_py_test"')
        assert str(type(data)) == "<class 'list'>"
        assert 3 == len(data)
        data = cur.qfa('SELECT * FROM "_py_test"', key='id')
        assert str(type(data)) == "<class 'collections.OrderedDict'>"
        assert 3 == len(data)
        cur.q('DELETE FROM "_py_test"')


    def test_cursor_qfm(self, sql):
        cur = sql.cursor()
        cur.q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (1, 1, \'unique\', \'Test\')')
        cur.q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (2, 1, \'unique2\', \'Test2\')')
        cur.q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (3, 1, \'unique3\', \'Test3\')')
        data = cur.qfm('SELECT * FROM "_py_test"', 2)
        assert str(type(data)) == "<class 'list'>"
        assert 2 == len(data)
        data = cur.qfm('SELECT * FROM "_py_test"', 1, key='id')
        assert str(type(data)) == "<class 'collections.OrderedDict'>"
        assert 1 == len(data)
        cur.q('DELETE FROM "_py_test"')


    def test_cursor__prepare_insert(self, sql):
        cur = sql.cursor()
        data = OrderedDict()
        data['id'] = 1
        data['user_id'] = 1
        data['abbrev'] = 'unique'
        data['name'] = 'Test'
        data = list(data.keys())
        query = 'INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (%s, %s, %s, %s)'
        assert query == cur._prepare_insert('_py_test', data).strip()


    def test_cursor__prepare_update(self, sql):
        cur = sql.cursor()
        data = OrderedDict()
        data['id'] = 1
        data['user_id'] = 1
        data['abbrev'] = 'unique'
        data['name'] = 'Test'
        data = list(data.keys())
        conditions = OrderedDict()
        conditions['id'] = 1
        conditions = list(conditions.keys())
        query = 'UPDATE "_py_test" SET "id"=%s, "user_id"=%s, "abbrev"=%s, "name"=%s WHERE "id"=%s'
        assert query == cur._prepare_update('_py_test', data, conditions).strip()


    def test_cursor_insert(self, sql):
        cur = sql.cursor()
        # dict
        data1 = {'id': 1, 'user_id': 1, 'abbrev': 'unique', 'name': 'Test'}
        assert True == cur.insert('_py_test', data1)
        assert 1 == len(cur.qfa('SELECT * FROM "_py_test"'))
        # OrderedDict
        data2 = OrderedDict()
        data2['id'] = 2
        data2['user_id'] = 1
        data2['abbrev'] = 'unique2'
        data2['name'] = 'Test 2'
        assert True == cur.insert('_py_test', data2)
        assert 2 == len(cur.qfa('SELECT * FROM "_py_test"'))
        # raises
        with pytest.raises(psycopg2.errors.UndefinedTable):
            cur.insert(1, data2)
        with pytest.raises(AttributeError):
            cur.insert('_py_test', [])
        cur.q('DELETE FROM "_py_test"')


    def test_cursor_update(self, sql):
        cur = sql.cursor()
        cur.q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (1, 1, \'unique\', \'Test\')')
        # dict
        data1 = {'id': 1, 'user_id': 2, 'abbrev': 'unique2', 'name': 'Test 2'}
        conditions1 = {'id': 1}
        assert True == cur.update('_py_test', data1, conditions1)
        assert [{'id': 1, 'user_id': 2, 'abbrev': 'unique2', 'name': 'Test 2'}] == cur.qfa('SELECT * FROM "_py_test"')
        # OrderedDict
        data2 = OrderedDict()
        data2['id'] = 1
        data2['user_id'] = 1
        data2['abbrev'] = 'unique3'
        data2['name'] = 'Test 3'
        conditions2 = OrderedDict()
        conditions2['id'] = 1
        assert True == cur.update('_py_test', data2, conditions2)
        assert [{'id': 1, 'user_id': 1, 'abbrev': 'unique3', 'name': 'Test 3'}] == cur.qfa('SELECT * FROM "_py_test"')
        # raises
        with pytest.raises(psycopg2.errors.UndefinedTable):
            cur.update(1, data2, conditions2)
        with pytest.raises(AttributeError):
            cur.update('_py_test', [], conditions2)
        with pytest.raises(AttributeError):
            cur.update('_py_test', data2, [])
        cur.q('DELETE FROM "_py_test"')


    def test_cursor_rows(self, sql):
        cur = sql.cursor()
        cur.q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (1, 1, \'unique\', \'Test\')')
        res = cur.rows()
        assert 1 == cur.rows()
        cur.q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (2, 2, \'unique2\', \'Test2\')')
        assert 1 == cur.rows()
        cur.q('UPDATE "_py_test" SET "name" = \'Test 2\' WHERE "id" = 2')
        assert 1 == cur.rows()
        cur.q('SELECT * FROM "_py_test"')
        assert 2 == cur.rows()
        cur.q('DELETE FROM "_py_test"')
        assert 2 == cur.rows()
        cur.q('SELECT * FROM "_py_test"')
        assert 0 == cur.rows()


    def test_cursor_gen_id(self, sql):
        cur = sql.cursor()
        cur.q('SELECT SETVAL(\'"s._py_test"\', 1)')
        cur.q('SELECT SETVAL(\'"s._py_test_user"\', 2)')
        assert 2 == cur.gen_id('_py_test')
        assert 3 == cur.gen_id('_py_test_user')
        with pytest.raises(ValueError):
            cur.gen_id('')


    def test_cursor_get_last_id(self, sql):
        cur = sql.cursor()
        assert 2 == cur.get_last_id('_py_test')
        assert 3 == cur.get_last_id('_py_test_user')
        with pytest.raises(ValueError):
            cur.get_last_id('')


    def test_cursor_set_gen_id(self, sql):
        cur = sql.cursor()
        assert True == cur.set_gen_id('_py_test', 5)
        assert 5 == cur.get_last_id('_py_test')
        assert True == cur.set_gen_id('_py_test_user', 2)
        assert 2 == cur.get_last_id('_py_test_user')
        with pytest.raises(psycopg2.errors.UndefinedTable):
            cur.set_gen_id('', 1)
        with pytest.raises(psycopg2.errors.NumericValueOutOfRange):
            cur.set_gen_id('_py_test_user', 0)


    def test_cursor_get_table_fields(self, sql):
        cur = sql.cursor()
        assert sorted(['id', 'user_id', 'abbrev', 'name']) == sorted(cur.get_table_fields('_py_test'))
        with pytest.raises(psycopg2.errors.SyntaxError):
            cur.get_table_fields('')


    def test_cursor_commit_rollback(self, sql):  # TODO:
        sql.start_trans_mode()
        cur = sql.cursor()
        assert False == cur.get().connection.autocommit
        cur.q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (1, 1, \'unique\', \'Test\')')
        with pytest.raises(psycopg2.IntegrityError):
            cur.q('DELETE FROM "_py_test_user" WHERE "id" = 1')
        sql.finish_trans_mode()

        sql.start_trans_mode()
        assert 0 == len(cur.qfa('SELECT * FROM "_py_test"', key='id').keys())
        assert 2 == len(cur.qfa('SELECT * FROM "_py_test_user"'))
        cur.q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (1, 1, \'unique\', \'Test\')')
        assert 1 == len(cur.qfa('SELECT * FROM "_py_test"', key='id').keys())
        cur.q('DELETE FROM "_py_test" WHERE "id" = 1')
        sql.finish_trans_mode()

        sql.start_trans_mode()
        cur.q('INSERT INTO "_py_test" ("id", "user_id", "abbrev", "name") VALUES (1, 1, \'unique\', \'Test\')')
        cur.q('INSERT INTO "_py_test_user" ("id", "first_name", "last_name") VALUES (3, \'Rollback\', \'Vracec\');')
        sql.finish_trans_mode(action='rollback')
        assert 0 == len(cur.qfa('SELECT * FROM "_py_test"'))
        assert 2 == len(cur.qfa('SELECT * FROM "_py_test_user"'))


    def test_escape_bytea(self, sql):
        assert False == sql.esc_bytea('')
        assert False == sql.esc_bytea(121)
        assert b'aaa' == sql.esc_bytea('aaa')


    def test_unescape_bytea(self, sql):
        assert False == sql.unesc_bytea('')
        assert False == sql.unesc_bytea(121)
        assert 'aaa' == sql.unesc_bytea(sql.esc_bytea('aaa'))


    def test_bytea_type(self, sql):
        cur = sql.cursor()
        bytea_data = '{"a":1}'
        assert True == cur.q('INSERT INTO "_py_test_bytea" ("id", "user_id", "string", "bytea") VALUES (1, 2, \'string\', \'{}\')'.format(bytea_data))
        res1 = cur.qfo('SELECT "id", "user_id", "string", "bytea" FROM "_py_test_bytea"')
        assert {'id': 1, 'user_id': 2, 'string': 'string', 'bytea': bytea_data} == res1
        res2 = cur.qfa('SELECT "id", "user_id", "string", "bytea" FROM "_py_test_bytea"')
        assert {'id': 1, 'user_id': 2, 'string': 'string', 'bytea': bytea_data} == res2[0]
        res3 = cur.qfm('SELECT "id", "user_id", "string", "bytea" FROM "_py_test_bytea"', 1)
        assert {'id': 1, 'user_id': 2, 'string': 'string', 'bytea': bytea_data} == res3[0]
