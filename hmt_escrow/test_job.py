#!/usr/bin/env python3

import logging
import os
import sys
import unittest
from decimal import *

from typing import Dict, Any

from unittest.mock import MagicMock, ANY
import schematics
from unittest.mock import patch
from web3 import Web3

os.environ['HMT_ETH_SERVER'] = os.getenv('HMT_ETH_SERVER',
                                         "http://localhost:8545")
import basemodels
from storage import _decrypt, _encrypt, upload

REQ_JSON = 'file:///tmp/req.json'
ANS_JSON = 'file:///tmp/ans.json'
CALLBACK_URL = 'http://google.com/webback'

GAS_PAYER = Web3.toChecksumAddress(
    "0x1413862c2b7054cdbfdc181b83962cb0fc11fd92")
GAS_PAYER_PRIV = "28e516f1e2f99e96a48a23cea1f94ee5f073403a1c68e818263f0eb898f1c8e5"

ADDR = GAS_PAYER
TO_ADDR = '0x6b7E3C31F34cF38d1DFC1D9A8A59482028395809'
TO_ADDR2 = '0xa30E4681db25f0f32E8C79b28F2A80A653A556A2'

PUB1 = b'b1bd4192dd7134d869f992fafcf4ed60ef8c566f2649b773f5562bc6736ff8dd8c459b36201dd8ce417cc96275a11f209942eacb14aef5b91a8e6ea0703b4bf8'
PRIV1 = b'657b6497a355a3982928d5515d48a84870f057c4d16923eb1d104c0afada9aa8'
PUB2 = b'94e67e63b2bf9b960b5a284aef8f4cc2c41ce08b083b89d17c027eb6f11994140d99c0aeadbf32fbcdac4785c5550bf28eefd0d339c74a033d55b1765b6503bf'
PRIV2 = b'f22d4fc42da79aa5ba839998a0a9f2c2c45f5e55ee7f1504e464d2c71ca199e1'

FAKE_ORACLE = ADDR
FAKE_URL = 'http://google.com/fake'
IMAGE_LABEL_BINARY = 'image_label_binary'

REP_ORACLE = Web3.toChecksumAddress(
    os.getenv("REP_ORACLE", "0x61F9F0B31eacB420553da8BCC59DC617279731Ac"))
REC_ORACLE = Web3.toChecksumAddress(
    os.getenv("REC_ORACLE", "0xD979105297fB0eee83F7433fC09279cb5B94fFC6"))
FACTORY_ADDR = os.getenv("FACTORYADDR", None)


def test_manifest(number_of_tasks=100,
                  bid_amount=1.0,
                  oracle_stake=0.05,
                  expiration_date=0,
                  minimum_trust=.1,
                  request_type=IMAGE_LABEL_BINARY,
                  request_config=None,
                  job_mode='batch') -> basemodels.Manifest:
    model = {
        'requester_restricted_answer_set': {
            '0': {
                'en': 'English Answer 1'
            },
            '1': {
                'en': 'English Answer 2',
                'answer_example_uri':
                'https://hcaptcha.com/example_answer2.jpg'
            }
        },
        'job_mode': job_mode,
        'request_type': request_type,
        'unsafe_content': False,
        'task_bid_price': bid_amount,
        'oracle_stake': oracle_stake,
        'expiration_date': expiration_date,
        'minimum_trust_server': minimum_trust,
        'minimum_trust_client': minimum_trust,
        'requester_accuracy_target': minimum_trust,
        'recording_oracle_addr': GAS_PAYER,
        'reputation_oracle_addr': GAS_PAYER,
        'reputation_agent_addr': GAS_PAYER,
        'instant_result_delivery_webhook': CALLBACK_URL,
        'requester_question': {
            "en": "How much money are we to make"
        },
        'requester_question_example': FAKE_URL,
        'job_total_tasks': number_of_tasks,
        'taskdata_uri': FAKE_URL
    }

    if request_config:
        model.update({'request_config': request_config})

    manifest = basemodels.Manifest(model)
    manifest.validate()

    return manifest


class JobTest(unittest.TestCase):
    """
    Tests the Job API's functions.

    Some of the blockchain specific functionality is mocked.
    Solidity specific functionality is delegated to JS tests.
    """

    def setUp(self):
        """Set up the fields for Job class testing, based on the test manifest."""
        self.manifest = a_manifest()
        self.job = hmt_escrow.Job(self.manifest, GAS_PAYER, GAS_PAYER_PRIV)
        self.per_job_cost = Decimal(self.manifest["task_bid_price"])
        self.total_tasks = self.manifest["job_total_tasks"]
        self.oracle_stake = self.manifest["oracle_stake"]
        self.amount = self.per_job_cost * self.total_tasks

    def test_deploy(self):
        """Tests that deploy assigns correct field values to Job class state."""
        self.job.deploy(PUB2)
        self.assertEqual(self.job.amount, self.amount)
        self.assertEqual(self.job.oracle_stake, self.oracle_stake)
        self.assertEqual(self.job.serialized_manifest["job_total_tasks"],
                         self.total_tasks)

    def test_fund(self):
        """Tests that fund calls _transfer_to_address with correct parameters."""
        hmt_escrow._fund = MagicMock()
        self.job.deploy(PUB2)
        self.job.fund()
        hmt_escrow._fund.assert_called_once_with(self.job)

    def test_abort(self):
        """Tests that abort calls _abort with correct parameters."""
        hmt_escrow._abort = MagicMock()
        self.job.deploy(PUB2)
        self.job.abort()
        hmt_escrow._abort.assert_called_once_with(self.job)

    def test_complete(self):
        """Tests that complete calls _complete with correct parameters."""
        hmt_escrow._complete = MagicMock()
        self.job.deploy(PUB2)
        self.job.complete()
        hmt_escrow._complete.assert_called_once_with(self.job)

    def test_setup(self):
        """Tests that launch calls _setup with correct parameters."""
        hmt_escrow._setup = MagicMock()
        self.job.deploy(PUB2)
        self.job.setup()
        hmt_escrow._setup.assert_called_once_with(self.job)

    def test_store_intermediate(self):
        """Tests that store_intermediate calls _store_results without parameters."""
        hmt_escrow._store_intermediate_results = MagicMock()
        self.job.deploy(PUB2)
        self.job.store_intermediate_results({}, PUB2)
        hmt_escrow._store_intermediate_results.assert_called_once()

    def test_refund(self):
        """Tests that refund calls _refund with correct parameters."""
        hmt_escrow._refund = MagicMock()
        self.job.deploy(PUB2)
        self.job.refund()
        hmt_escrow._refund.assert_called_once_with(self.job)

    def test_bulk_payout(self):
        """Tests that bulk_payout calls _bulk_payout with correct amounts after HMT decimal conversion."""
        hmt_escrow._bulk_payout = MagicMock()
        self.job.deploy(PUB2)
        payouts = [(TO_ADDR, 10), (TO_ADDR2, 20)]
        self.job.bulk_payout(payouts, {}, PUB2)
        assert_addrs = [TO_ADDR, TO_ADDR2]
        assert_amounts = [10, 20]
        hmt_escrow._bulk_payout.assert_called_once_with(
            self.job, assert_addrs, assert_amounts, ANY, ANY)


class EncryptionTest(unittest.TestCase):
    def test_encryption_decryption_identity(self):
        """Tests _decrypt of _encrypt message returns the same message."""
        plaintext = 'asdfasdf'
        cipher = _encrypt(PUB2, plaintext)
        self.assertEqual(_decrypt(PRIV2, cipher), plaintext)


def add_bytes(args):
    pass


def encrypt(public_key, msg):
    pass


class StorageTest(unittest.TestCase):
    @patch('hmt_escrow.storage.API.add_bytes', side_effect=add_bytes)
    @patch('hmt_escrow.storage._encrypt', side_effect=encrypt)
    def test_upload(self, add_bytes, _encrypt):
        upload(a_manifest().serialize(), PUB1)


if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger("urllib3").setLevel(logging.INFO)
    unittest.main()