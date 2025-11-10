import cmd
import getpass
import logging

from src.controller import BankController

class BankCLI(cmd.Cmd):
    intro = 'Welcome to bank "Bankito". Type help or ? to list commands.\n'
    prompt = '[anonymous] > '
    bank = BankController()

    def onecmd(self, line):
        'Override onecmd to catch all command exceptions.'
        try:
            return super().onecmd(line)
        except Exception as e:
            logging.error(e)
            return False
        
    def do_exit(self, _):
        'Exit the program'
        logging.info('Bye bye!')
        return True
    
    def do_set_isolation_level(self, args):
        'Change the bank isolation level to any of: READ_COMMITTED (default), REPEATABLE_READ, SERIALIZABLE'
        self.bank.set_isolation_level(args)
        logging.info(f'Isolation level changed to {args}')

    def do_get_isolation_level(self, _):
        'Get the bank isolation level'
        isolation = self.bank.get_isolation_level()
        logging.info(f'Current isolation level: {isolation}')

    def do_login(self, _):
        'Login to your account - prompts for username and password'
        username = input('Enter your username: ')
        password = getpass.getpass('Enter your password: ')
        self.bank.login(username, password)
        logging.info('Hello there, welcome back!')
        self.prompt = f'[{username}] > '

    def do_logout(self, _):
        'Logout of the current account'
        self.bank.logout()
        self.prompt = f'[anonymous] > '

    def do_list_accounts(self, _):
        'List all accounts owned by this user'
        accounts = self.bank.list_accounts()
        logging.info(accounts)

    def do_list_transactions(self, args):
        'List all transactions made by the given ACCOUNT_NAME'
        transactions = self.bank.list_transactions(args)
        logging.info(transactions)

    def do_list_transfers(self, args):
        'List all transfers made by this account'
        transfers = self.bank.list_transfers(args)
        logging.info(transfers)

    def do_transfer(self, args):
        'Transfer with SCENARIO from FROM_ACCOUNT_NAME to DESTINATION_ACCOUNT_ID the AMOUNT'
        scenario, from_account_name, to_account_id, amount = args.split(' ')
        result = self.bank.transfer(scenario, from_account_name, int(to_account_id), int(amount))
        logging.info(result)
