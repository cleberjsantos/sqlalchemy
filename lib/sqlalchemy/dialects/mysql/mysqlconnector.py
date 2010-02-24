"""Support for the MySQL database via the MySQL Connector/Python adapter.

# TODO: add docs/notes here regarding MySQL Connector/Python

"""

import re

from sqlalchemy.dialects.mysql.base import (MySQLDialect,
    MySQLExecutionContext, MySQLCompiler, MySQLIdentifierPreparer,
    BIT, NUMERIC)

from sqlalchemy.engine import base as engine_base, default
from sqlalchemy.sql import operators as sql_operators
from sqlalchemy import exc, log, schema, sql, types as sqltypes, util
from sqlalchemy import processors

class MySQL_mysqlconnectorExecutionContext(MySQLExecutionContext):

    def get_lastrowid(self):
        return self.cursor.lastrowid


class MySQL_mysqlconnectorCompiler(MySQLCompiler):
    def visit_mod(self, binary, **kw):
        return self.process(binary.left) + " %% " + self.process(binary.right)

    def post_process_text(self, text):
        return text.replace('%', '%%')


class MySQL_mysqlconnectorIdentifierPreparer(MySQLIdentifierPreparer):

    def _escape_identifier(self, value):
        value = value.replace(self.escape_quote, self.escape_to_quote)
        return value.replace("%", "%%")

class _myconnpyNumeric(NUMERIC):
    def result_processor(self, dialect, coltype):
        if self.asdecimal:
            return None
        return processors.to_float

class _myconnpyBIT(BIT):
    def result_processor(self, dialect, coltype):
        """MySQL-connector already converts mysql bits, so."""

        return None

class MySQL_mysqlconnector(MySQLDialect):
    driver = 'mysqlconnector'
    supports_unicode_statements = False
    supports_unicode_binds = True
    supports_sane_rowcount = False
    supports_sane_multi_rowcount = True
    description_encoding = None

    default_paramstyle = 'format'
    execution_ctx_cls = MySQL_mysqlconnectorExecutionContext
    statement_compiler = MySQL_mysqlconnectorCompiler

    preparer = MySQL_mysqlconnectorIdentifierPreparer

    colspecs = util.update_copy(
        MySQLDialect.colspecs,
        {
            sqltypes.Numeric: _myconnpyNumeric,
            BIT: _myconnpyBIT,
        }
    )

    @classmethod
    def dbapi(cls):
        from mysql import connector
        return connector

    def create_connect_args(self, url):
        opts = url.translate_connect_args(username='user')
        opts.update(url.query)

        util.coerce_kw_type(opts, 'buffered', bool)
        util.coerce_kw_type(opts, 'raise_on_warnings', bool)
        opts['buffered'] = True
        opts['raise_on_warnings'] = True

        return [[], opts]

    def _get_server_version_info(self, connection):
        dbapi_con = connection.connection

        from mysql.connector.constants import ClientFlag
        dbapi_con.set_client_flag(ClientFlag.FOUND_ROWS)

        version = dbapi_con.get_server_version()
        return tuple(version)

    def _detect_charset(self, connection):
        return connection.connection.get_characterset_info()

    def _extract_error_code(self, exception):
        try:
            return exception.orig.errno
        except AttributeError:
            return None

    def is_disconnect(self, e):
        errnos = (2006, 2013, 2014, 2045, 2055, 2048)
        exceptions = (self.dbapi.OperationalError,self.dbapi.InterfaceError)
        if isinstance(e, exceptions):
            return e.errno in errnos
        else:
            return False

    def _compat_fetchall(self, rp, charset=None):
        return rp.fetchall()

    def _compat_fetchone(self, rp, charset=None):
        return rp.fetchone()

dialect = MySQL_mysqlconnector
