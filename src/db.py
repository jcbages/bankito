import logging
import uuid
import psycopg2
import os

from src.exceptions.db_exception import DBException

class DB():
    def __init__(self):
        db_uri = os.environ.get("DATABASE_URL")
        self.conn = psycopg2.connect(db_uri)
        self.conn.autocommit = False
        self.transactions = {}

    def __exec(self, stmt, args, callback=None):
        try:
            cur = self.conn.cursor()
            cur.execute(stmt, args)
            self.conn.commit()
            return callback(cur) if callback else None
        except Exception as e:
            logging.debug(e)
            raise DBException('Something went wrong', e)
        finally:
            cur.close()

    def find_many(self, query, args):
        callback = lambda cur: list(cur.fetchall())
        return self.__exec(query, args, callback)

    def find_one(self, query, args):
        callback = lambda cur: cur.fetchone()
        return self.__exec(query, args, callback)

    def exec(self, stmt, args):
        return self.__exec(stmt, args)
    
    def __generate_tid(self):
        return str(uuid.uuid4())

    def start_transaction(self):
        try:
            tid = self.__generate_tid()
            cur = self.conn.cursor()
            self.transactions[tid] = cur
            return tid
        except Exception as e:
            logging.debug(e)
            raise DBException('Something went wrong', e)
        
    def __check_transaction(self, tid):
        if tid not in self.transactions:
            raise DBException(f'No transaction with tid {tid} in progress')
        
    def __exec_transaction(self, tid, stmt, args, callback=None):
        self.__check_transaction(tid)
        try:
            self.transactions[tid].execute(stmt, args)
            return callback(self.transactions[tid]) if callback else None
        except Exception as e:
            logging.debug(e)
            self.conn.rollback()
            self.transactions[tid].close()
            self.transactions.pop(tid)
            raise DBException('Something went wrong', e)
        
    def find_many_transaction(self, tid, query, args):
        callback = lambda cur: list(cur.fetchall())
        return self.__exec_transaction(tid, query, args, callback)

    def find_one_transaction(self, tid, query, args):
        callback = lambda cur: cur.fetchone()
        return self.__exec_transaction(tid, query, args, callback)
    
    def exec_transaction(self, tid, stmt, args):
        return self.__exec_transaction(tid, stmt, args)
    
    def cancel_transaction(self, tid):
        try:
            self.__check_transaction(tid)
        except DBException:
            return
        try:
            self.conn.rollback()
        except Exception as e:
            logging.debug(e)
            raise DBException('Something went wrong', e)
        finally:
            self.transactions[tid].close()
            self.transactions.pop(tid)

    def commit_transaction(self, tid):
        self.__check_transaction(tid)
        try:
            self.conn.commit()
        except Exception as e:
            logging.debug(e)
            self.conn.rollback()
            raise DBException('Something went wrong', e)
        finally:
            self.transactions[tid].close()
            self.transactions.pop(tid)
