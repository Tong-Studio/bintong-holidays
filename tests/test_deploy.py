import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import deploy


class DeploymentTests(unittest.TestCase):
    history = json.dumps([{'created_on': '2026-09-30T00:00:00Z',
                           'versions': [{'version_id': 'previous', 'percentage': 100}]}])

    def run_deployment(self, verification=None, upload_error=None):
        with patch.object(deploy.subprocess, 'check_output', return_value=self.history), \
                patch.object(deploy, 'upload_version', return_value='candidate', side_effect=upload_error), \
                patch.object(deploy, 'activate') as activate, \
                patch.object(deploy, 'verify', side_effect=verification) as verify, \
                patch.object(deploy.time, 'sleep'):
            if upload_error or isinstance(verification, Exception):
                with self.assertRaises(RuntimeError):
                    deploy.deploy('https://example.test')
            else:
                deploy.deploy('https://example.test')
            return [call.args[0] for call in activate.call_args_list], verify.call_count

    def test_success_keeps_candidate(self):
        self.assertEqual(self.run_deployment(), (['candidate'], 1))

    def test_bad_https_response_restores_previous_version(self):
        self.assertEqual(self.run_deployment(RuntimeError('bad published hash')),
                         (['candidate', 'previous'], 6))

    def test_upload_failure_leaves_production_untouched(self):
        self.assertEqual(self.run_deployment(upload_error=RuntimeError('upload denied')),
                         ([], 0))

    def test_transient_https_failure_does_not_rollback(self):
        self.assertEqual(self.run_deployment([RuntimeError('temporary timeout'), None]),
                         (['candidate'], 2))

    def test_split_traffic_refuses_unsafe_rollback(self):
        history = json.dumps([{'created_on': '2026-09-30T00:00:00Z',
                               'versions': [{'version_id': 'previous', 'percentage': 50}]}])
        with patch.object(deploy.subprocess, 'check_output', return_value=history), \
                patch.object(deploy, 'upload_version') as upload:
            with self.assertRaises(RuntimeError):
                deploy.deploy('https://example.test')
            upload.assert_not_called()


if __name__ == '__main__':
    unittest.main()
