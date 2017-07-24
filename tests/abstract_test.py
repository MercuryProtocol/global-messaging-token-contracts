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

    HOMESTEAD_BLOCK = 1467446000
    MAX_UINT256 = (2 ** 256) - 1 # Max num256 value

    def __init__(self, *args, **kwargs):
        super(AbstractTestContracts, self).__init__(*args, **kwargs)
        self.t = tester
        self.c = tester.Chain()
        self.s = self.t.Chain({self.t.a1: {"balance": self.MAX_UINT256 * 3}, self.t.a2: {"balance": utils.denoms.ether * 1}})
        # self.s.block_number = self.HOMESTEAD_BLOCK
        tester.gas_limit = 471238899
        

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

    def create_contract_old(self, path, params=None, libraries=None, sender=None):
        path, extra_args = self.get_dirs(path)
        if params:
            params = [x.address if isinstance(x, t.ABIContract) else x for x in params]
        if libraries:
            for name, address in libraries.items():
                if type(address) == str:
                    if self.is_hex(address):
                        libraries[name] = address
                    else:
                        libraries[name] = ContractTranslator.encode_function_call(address, 'hex')
                elif isinstance(address, t.ABIContract):
                    libraries[name] = ContractTranslator.encode_function_call(address.address, 'hex')
                else:
                    raise ValueError
        return self.s.abi_contract(None,
                                   path=path,
                                   constructor_parameters=params,
                                   libraries=libraries,
                                   language='solidity',
                                   extra_args=extra_args,
                                   sender=keys[sender if sender else 0])