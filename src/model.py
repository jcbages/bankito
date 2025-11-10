import logging
import time
import uuid
from src.db import DB
import psycopg2.extensions

from src.exceptions.app_exception import AppException
from src.exceptions.db_exception import DBException

class BankModel():
    def __init__(self):
        self.db = DB()

    def __get_account(self, uid, account_name):
        account = self.find_account(uid, account_name)
        if not account:
            raise AppException('No account found with that name')
        return account

    def set_isolation_level(self, isolation):
        if isolation == 'READ_COMMITTED':
            self.db.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
        elif isolation == 'REPEATABLE_READ':
            self.db.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ)
        elif isolation == 'SERIALIZABLE':
            self.db.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)

    def login(self, username, password):
        try:
            query = 'SELECT id FROM users WHERE username=%s AND password=%s'
            row = self.db.find_one(query, (username, password))
            if not row:
                return None
            return row[0]
        except DBException as e:
            logging.debug(e)
            raise AppException('Failed to fetch user data', e)
        
    def find_account(self, uid, account_name):
        try:
            query = '''
            SELECT id, name, balance, currency, status
            FROM accounts
            WHERE user_id = %s AND name = %s
            '''
            account = self.db.find_one(query, (uid, account_name))
            if not account:
                return None
            return account
        except DBException as e:
            logging.debug(e)
            raise AppException('Failed to fetch accounts data', e)        

    def list_accounts(self, uid):
        try:
            query = '''
            SELECT name, balance, currency, status, created_at
            FROM accounts
            WHERE user_id = %s
            ORDER BY created_at DESC
            '''
            return self.db.find_many(query, (uid,))
        except DBException as e:
            logging.debug(e)
            raise AppException('Failed to fetch accounts data', e)

    def list_transactions(self, uid, account_name):
        account = self.__get_account(uid, account_name)
        try:
            query = '''
            SELECT reference_id, type, amount, description, balance_after, created_at
            FROM transactions
            WHERE account_id = %s
            ORDER BY created_at DESC
            '''
            return self.db.find_many(query, (account[0],))
        except DBException as e:
            logging.debug(e)
            raise AppException('Failed to fetch transactions data', e)

    def list_transfers(self, uid, account_name):
        account = self.__get_account(uid, account_name)
        try:
            query = '''
            SELECT t1.reference_id, t1.type, a1.name, a2.name, t1.amount, t1.description, t1.balance_after, t1.created_at
            FROM transactions AS t1
            INNER JOIN transactions AS t2
            ON t1.reference_id = t2.reference_id AND t1.id <> t2.id AND (t1.account_id = %s OR t2.account_id = %s)
            LEFT JOIN accounts AS a1
            ON t1.account_id = a1.id
            LEFT JOIN accounts AS a2
            ON t2.account_id = a2.id
            '''
            return self.db.find_many(query, (account[0], account[0]))
        except DBException as e:
            logging.debug(e)
            raise AppException('Failed to fetch transfers data', e)
        
    def transfer(self, uid, from_account_name, to_account_id, amount, description='', opt={}):
        account = self.__get_account(uid, from_account_name)
        if account[-1] != 'active':
            raise AppException('Account must be active')
        if account[0] == to_account_id:
            raise AppException('Can not transfer to same account as origin')

        try:
            tid = self.db.start_transaction()
            
            # Test what happens when there's no consistent lock
            if 'skip_consistent_lock' not in opt:
                locks = sorted([account[0], to_account_id])
            else:
                logging.warning('Skipping consistent lock, this can cancel other loop transactions to prevent dead-lock')
                locks = [account[0], to_account_id]

            # Test what happens when there's no lock
            if 'skip_for_update' not in opt:
                # Lock first account
                stmt = '''
                SELECT * FROM accounts WHERE id = %s FOR UPDATE 
                '''
                self.db.exec_transaction(tid, stmt, (locks[0],))
                
                logging.warning(f'Lock acquired for account id {locks[0]}')
                time.sleep(5)

                # Lock second account
                stmt = '''
                SELECT * FROM accounts WHERE id = %s FOR UPDATE 
                '''
                self.db.exec_transaction(tid, stmt, (locks[1],))

                logging.warning(f'Lock acquired for account id {locks[1]}')
            else:
                logging.warning('Skipping for update lock, this can cause phantom reads to overdraft the account')

            # Check first account has enough balance
            stmt = '''
            SELECT balance FROM accounts WHERE id = %s
            '''
            current_from_balance = self.db.find_one_transaction(tid, stmt, (account[0],))[0]
            if current_from_balance < amount:
                self.db.cancel_transaction(tid)
                raise AppException('Insufficient balance for transfer')
            
            logging.warning('Lock acquired and balance checked, ready to proceed')
            time.sleep(5)
            
            # Update balance of origin account
            stmt = '''
            UPDATE accounts
            SET balance = balance - %s
            WHERE id = %s
            RETURNING balance
            '''
            self.db.exec_transaction(tid, stmt, (amount, account[0]))
            
            stmt = '''
            SELECT balance FROM accounts WHERE id = %s
            '''
            new_from_balance = self.db.find_one_transaction(tid, stmt, (account[0],))[0]

            # Update balance of destination account
            stmt = '''
            UPDATE accounts
            SET balance = balance + %s
            WHERE id = %s
            RETURNING balance
            '''
            self.db.exec_transaction(tid, stmt, (amount, to_account_id))

            stmt = '''
            SELECT balance FROM accounts WHERE id = %s
            '''
            new_to_balance = self.db.find_one_transaction(tid, stmt, (to_account_id,))[0]

            # Create transactions
            reference_id = str(uuid.uuid4())

            stmt = '''
            INSERT INTO transactions(account_id, type, amount, balance_after, reference_id, description)
            VALUES(%s, %s, %s, %s, %s, %s)
            '''
            self.db.exec_transaction(tid, stmt, (account[0], 'debit', amount, new_from_balance, reference_id, description))

            stmt = '''
            INSERT INTO transactions(account_id, type, amount, balance_after, reference_id, description)
            VALUES(%s, %s, %s, %s, %s, %s)
            '''
            self.db.exec_transaction(tid, stmt, (to_account_id, 'credit', amount, new_to_balance, reference_id, description))

            # Finish
            self.db.commit_transaction(tid)
        except DBException as e:
            logging.debug(e)
            raise AppException('Failed to execute transfer', e)
        finally:
            self.db.cancel_transaction(tid)
