# -*- coding: utf-8 -*-

import traceback, sys
from subprocess import check_output, CalledProcessError
from noronha.common.exception import NhaTestError
from noronha.common.utils import clear_nones_from_dict, assert_json


n_test_cases = 0


class TestCase(object):
    
    def __init__(self, cmd, name=None, desc=None, callback=None, pre_steps=None, pos_steps=None, expect_error=False):
        
        self._cmd = self.parse_cmd(cmd)
        self._name = name
        self._desc = desc
        self._callback = callback
        self._expect_error = expect_error
        self._passed = None
        self._details = None
        self._pre_steps = [self.parse_cmd(s) for s in pre_steps or []]
        self._pos_steps = [self.parse_cmd(s) for s in pos_steps or []]
        
        global n_test_cases
        self._index = n_test_cases
        n_test_cases += 1
    
    @classmethod
    def parse_cmd(cls, cmd):
        
        if not isinstance(cmd, list):
            cmd = cmd.strip().split(' ')
        
        return cmd
    
    @property
    def index(self):
        
        return self._index
    
    @property
    def passed(self):
        
        return self._passed
    
    @property
    def report(self):
        
        assert self._passed is not None
        
        return clear_nones_from_dict(dict(
            name=self._name,
            index=self._index,
            desc=self._desc,
            details=self._details,
            passed=self._passed
        ))
    
    @classmethod
    def _exec(cls, cmd):
        
        out, err = None, None
        
        try:
            out = check_output(cmd)
        except CalledProcessError as e:
            err = e
        
        return out, err
    
    def __call__(self):
        
        pre_err = [bool(self._exec(s)[1]) for s in self._pre_steps]
        
        if True in pre_err:
            self._passed = False
            self._details = 'Pre-step failure on index {}'.format(pre_err.index(True))
            return
        
        out, err = self._exec(self._cmd)
        
        self._passed = \
            False if \
            (err and not self._expect_error) or \
            (self._expect_error and not err) or \
            (callable(self._callback) and not self._callback(out, err)) \
            else True
        
        pos_err = [bool(self._exec(s)[1]) for s in self._pre_steps]
        
        if True in pos_err:
            self._passed = False
            self._details = 'Post-step failure on index {}'.format(pre_err.index(True))
            return


def run_all(test_cases):

    failed_reports = []
    
    for test_case in test_cases:
        
        try:
            test_case()
        except Exception as e:
            traceback.print_exc()
            raise NhaTestError(
                "Error executing the test case #'{0}': {1}"
                .format(test_case.index, e))
        
        if not test_case.passed:
            failed_reports.append(test_case.report)
    
    print(assert_json(failed_reports, indent=4))
    sys.exit(0 if len(failed_reports) == 0 else 1)
