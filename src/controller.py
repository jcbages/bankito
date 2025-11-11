from tabulate import tabulate
from src.exceptions.app_exception import AppException
from src.model import BankModel


class BankController():
    def __init__(self):
        self.model = BankModel()
        self.user = None
        self.isolation = 'READ_COMMITTED'

    def __requires_login(self):
        if not self.user:
            raise AppException('No user logged in')
        
    def set_isolation_level(self, isolation):
        if isolation not in ['READ_COMMITTED', 'REPEATABLE_READ', 'SERIALIZABLE']:
            raise AppException('Invalid isolation level. Must be one of: READ_COMMITTED, REPEATABLE_READ, SERIALIZABLE')
        self.model.set_isolation_level(isolation)
        self.isolation = isolation

    def get_isolation_level(self):
        return self.isolation

    def login(self, username, password):
        uid = self.model.login(username, password)
        if not uid:
            raise AppException('No user found with those credentials')
        self.user = {'uid': uid, 'username': username}

    def logout(self):
        self.__requires_login()
        self.user = None

    def get_account(self, account_name):
        self.__requires_login()
        account = self.model.find_account(self.user['uid'], account_name)
        return tabulate(
            [account],
            headers=['name', 'balance', 'currency', 'status'],
            tablefmt="grid"
        )

    def list_accounts(self):
        self.__requires_login()
        accounts = self.model.list_accounts(self.user['uid'])
        return tabulate(
            accounts,
            headers=['name', 'balance', 'currency', 'status'],
            tablefmt="grid"
        )

    def list_transactions(self, account_name):
        self.__requires_login()
        transactions = self.model.list_transactions(self.user['uid'], account_name)
        return tabulate(
            transactions,
            headers=['reference_id', 'type', 'amount', 'description', 'balance_after', 'created_at'],
            tablefmt="grid"
        )
    
    def list_transfers(self, account_name):
        self.__requires_login()
        transfers = self.model.list_transfers(self.user['uid'], account_name)
        return tabulate(
            transfers,
            headers=['reference_id', 'type', 'origin', 'destination', 'amount', 'description', 'balance_after', 'created_at'],
            tablefmt="grid"
        )
    
    def transfer(self, scenario, from_account_name, to_account_id, amount):
        self.__requires_login()
        self.model.transfer(self.user['uid'], from_account_name, to_account_id, amount, description='', opt={scenario: True})
        return self.get_account(from_account_name)
