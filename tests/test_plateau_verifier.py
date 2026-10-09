"""Worker coverage and failure propagation for the selected finite verifier.

These dispatch tests reuse the frozen child receipts. The package verifier
separately replays both complete words and compares the canonical certificate.
Prepared with OpenAI Codex assistance; Apache-2.0.
"""
import importlib.util
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1]/'research/paired-cube-plateau-162'
spec = importlib.util.spec_from_file_location('plateau_verifier', PACKAGE/'verify.py')
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class SelectedVerifierWorkers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expected = json.loads((PACKAGE/'certificate.json').read_text())

    def test_both_worker_budgets_check_both_children_and_reproduce_certificate(self):
        for jobs in (1, 2):
            with self.subTest(jobs=jobs):
                calls = []
                barrier = threading.Barrier(2) if jobs == 2 else None
                def child(relative):
                    calls.append(relative)
                    if barrier:
                        barrier.wait(timeout=10)
                    return self.expected[relative.split('/')[0]]
                with patch.object(verifier, 'run', side_effect=child):
                    result = verifier.build(jobs)
                self.assertEqual(result, self.expected)
                self.assertCountEqual(calls, ['complex/prove.py', 'bit/prove.py'])
                if jobs == 1:
                    self.assertEqual(calls, ['complex/prove.py', 'bit/prove.py'])

    def test_failure_in_either_parallel_child_rejects_verification(self):
        for failed in ('complex', 'bit'):
            with self.subTest(failed=failed):
                barrier = threading.Barrier(2)
                def child(relative):
                    barrier.wait(timeout=10)
                    name = relative.split('/')[0]
                    if name == failed:
                        raise ValueError('rejected '+name+' child')
                    return self.expected[name]
                with patch.object(verifier, 'run', side_effect=child):
                    with self.assertRaisesRegex(ValueError, 'rejected '+failed+' child'):
                        verifier.build(2)


if __name__ == '__main__':
    unittest.main()
