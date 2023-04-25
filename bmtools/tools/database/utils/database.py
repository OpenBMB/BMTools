import psycopg2
import pymysql
import json
import logging

class DBArgs(object):

    def __init__(self, dbtype, config, dbname=None):
        self.dbtype = dbtype
        if self.dbtype == 'mysql':
            self.host = config['host']
            self.port = config['port']
            self.user = config['user']
            self.password = config['password']
            self.dbname = dbname if dbname else config['dbname']
            self.driver = 'com.mysql.jdbc.Driver'
            self.jdbc = 'jdbc:mysql://'
        else:
            self.host = config['host']
            self.port = config['port']
            self.user = config['user']
            self.password = config['password']
            self.dbname = dbname if dbname else config['dbname']
            self.driver = 'org.postgresql.Driver'
            self.jdbc = 'jdbc:postgresql://'


class Database():

    def __init__(self, args, timeout=-1):
        self.args = args
        self.conn = None
        self.resetConn(timeout)

    def resetConn(self, timeout=-1):
        if self.args.dbtype == 'mysql':
            self.conn = pymysql.connect(
                host=self.args.host,
                user=self.args.user,
                passwd=self.args.password,
                database=self.args.dbname,
                port=int(self.args.port),
                charset='utf8',
                connect_timeout=timeout,
                read_timeout=timeout,
                write_timeout=timeout)
        else:
            if timeout > 0:
                self.conn = psycopg2.connect(database=self.args.dbname,
                                            user=self.args.user,
                                            password=self.args.password,
                                            host=self.args.host,
                                            port=self.args.port,
                                            options='-c statement_timeout={}s'.format(timeout))
            else:
                self.conn = psycopg2.connect(database=self.args.dbname,
                                            user=self.args.user,
                                            password=self.args.password,
                                            host=self.args.host,
                                            port=self.args.port)

    def exec_fetch(self, statement, one=True):
        cur = self.conn.cursor()
        cur.execute(statement)
        if one:
            return cur.fetchone()
        return cur.fetchall()

    def simulate_index(self, index):
        #table_name = index.table()
        statement = (
            "SELECT * FROM hypopg_create_index(E'{}');".format(index)
        )
        result = self.execute_sql(statement)

        return result

    def drop_simulated_index(self, oid):
        statement = f"select * from hypopg_drop_index({oid})"
        result = self.execute_sql(statement)

        assert result[0] is True, f"Could not drop simulated index with oid = {oid}."

    def execute_sql(self, sql):
        fail = 1
        cur = self.conn.cursor()
        i = 0
        cnt = 3
        while fail == 1 and i < cnt:
            try:
                fail = 0
                cur.execute(sql)
            except BaseException:
                fail = 1
            res = []
            if fail == 0:
                res = cur.fetchall()
            i = i + 1
        logging.debug('database {}, return flag {}, execute sql {}\n'.format(self.args.dbname, 1 - fail, sql))
        if fail == 1:
            # print("SQL Execution Fatal!!")
            return 0, ''
        elif fail == 0:
            # print("SQL Execution Succeed!!")
            return 1, res

    def pgsql_cost_estimation(self, sql):
        try:
            #success, res = self.execute_sql('explain (FORMAT JSON, analyze) ' + sql)
            success, res = self.execute_sql('explain (FORMAT JSON) ' + sql)
            if success == 1:
                cost = res[0][0][0]['Plan']['Total Cost']
                return cost
            else:
                logging.error('pgsql_cost_estimation Fails!')
                return 0
        except Exception as error:
            logging.error('pgsql_cost_estimation Exception', error)
            return 0

    def pgsql_actual_time(self, sql):
        try:
            #success, res = self.execute_sql('explain (FORMAT JSON, analyze) ' + sql)
            success, res = self.execute_sql('explain (FORMAT JSON, analyze) ' + sql)
            if success == 1:
                cost = res[0][0][0]['Plan']['Actual Total Time']
                return cost
            else:
                return -1
        except Exception as error:
            logging.error('pgsql_actual_time Exception', error)
            return -1

    def pgsql_results(self, sql):
        try:
            #success, res = self.execute_sql('explain (FORMAT JSON, analyze) ' + sql)
            success, res = self.execute_sql(sql)
            if success == 1:
                return res
            else:
                return "<fail>"
        except Exception as error:
            logging.error('pgsql_results Exception', error)
            return "<fail>"


    def mysql_cost_estimation(self, sql):
        try:
            success, res = self.execute_sql('explain format=json ' + sql)
            if success == 1:
                total_cost = self.get_mysql_total_cost(0, json.loads(res[0][0]))
                return float(total_cost)
            else:
                return -1
        except Exception as error:
            logging.error('mysql_cost_estimation Exception', error)
            return -1

    def get_mysql_total_cost(self, total_cost, res):
        if isinstance(res, dict):
            if 'query_cost' in res.keys():
                total_cost += float(res['query_cost'])
            else:
                for key in res:
                    total_cost += self.get_mysql_total_cost(0, res[key])
        elif isinstance(res, list):
            for i in res:
                total_cost += self.get_mysql_total_cost(0, i)

        return total_cost


    def get_tables(self):
        if self.args.dbtype == 'mysql':
            return self.mysql_get_tables()
        else:
            return self.pgsql_get_tables()

    # query cost estimated by the optimizer
    def cost_estimation(self, sql):
        if self.args.dbtype == 'mysql':
            return self.mysql_cost_estimation(sql)
        else:
            return self.pgsql_cost_estimation(sql)
