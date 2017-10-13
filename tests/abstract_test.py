# standard libraries
from unittest import TestCase
import os
import string
# ethereum package
from ethereum.tools import tester
from ethereum.tools.tester import keys, accounts, TransactionFailed, ABIContract
import ethereum.utils as utils
from ethereum.tools import _solidity
from ethereum.state import State
from ethereum.abi import ContractTranslator

OWN_DIR = os.path.dirname(os.path.realpath(__file__))

class AbstractTestContracts(TestCase):

    def __init__(self, *args, **kwargs):
        super(AbstractTestContracts, self).__init__(*args, **kwargs)
        self.t = tester
        self.c = self.t.Chain()
        self.s = self.t.Chain()
        self.c.head_state.gas_limit = 10999999
        self.c.head_state.block_number = 4097900

    @staticmethod
    def is_hex(s):
        return all(c in string.hexdigits for c in s)

    def get_dirs(self, path):
        abs_contract_path = os.path.realpath(os.path.join(OWN_DIR, '..', '..', 'contracts'))
        sub_dirs = [x[0] for x in os.walk(abs_contract_path)]
        extra_args = ' '.join(['{}={}'.format(d.split('/')[-1], d) for d in sub_dirs])
        path = '{}/{}'.format(abs_contract_path, path)
        return path, extra_args

    def create_abi(self, path):
        path, extra_args = self.get_dirs(path)
        abi = _solidity.compile_last_contract(path, combined='abi', extra_args=extra_args)['abi']
        return ContractTranslator(abi)

    def create_contract(self, path, args=[]):
        contract_path = os.path.realpath(os.path.join(OWN_DIR, '..', 'contracts', path))
        contract_code = open(contract_path).read()
        contract = self.c.contract(contract_code, args=args, language='solidity')
        self.s.mine()
        return contract