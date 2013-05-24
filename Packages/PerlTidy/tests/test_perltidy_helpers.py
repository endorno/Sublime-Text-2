# -*- coding: utf-8 -*-

import sys
import shutil
import re
import sublime_mocked
sys.modules['sublime'] = sublime_mocked

from perltidy.helpers import *
from nose.tools import assert_equal, assert_regexp_matches, assert_true, assert_false, assert_raises, assert_is_none
from nose.plugins.skip import SkipTest


PERLTIDY_INPUTS = {
    'ascii': {
        'input': u'#!/usr/bin/env perl\n  use strict;',
        'output': u'#!/usr/bin/env perl\nuse strict;\n',
    },
    'utf8': {
        'input': u'#!/usr/bin/env perl\nuse strict;\n  use utf8; $foo = "äöüÄÖÜ";',
        'output': u'#!/usr/bin/env perl\nuse strict;\nuse utf8;\n$foo = "äöüÄÖÜ";\n',
    },
}


def is_windows():
    return sys.platform.startswith('win32')


class PerlTidyTestLogger:
    def __init__(self):
        self._log_level = 3
        self._log_buffer = ''

    def log(self, level, message):
        self._log_buffer += 'PerlTidy: ' + message + "\n"
        print 'PerlTidy: ' + message

    def log_level(self):
        return self._log_level

    def get_log_buffer(self):
        return self._log_buffer

    def clear_log_buffer(self):
        self._log_buffer = ''


class PerlTidyTestCase():
    def setUp(self):
        self.logger = PerlTidyTestLogger()
        self.skip_reason = None

    def skip_if_have_reason(self):
        if self.skip_reason:
            raise SkipTest(self.skip_reason)


class PerlTidyInterpreterTestCase(PerlTidyTestCase):
    def setUp(self):
        PerlTidyTestCase.setUp(self)
        self.perltidy_cmd = None

    def test_is_valid_perltidy_cmd(self):
        self.skip_if_have_reason()
        assert_equal(True, is_valid_perltidy_cmd(cmd=self.perltidy_cmd, logger=self.logger))

    def test_run_perltidy(self):
        self.skip_if_have_reason()
        for key in ['ascii', 'utf8']:
            success, output, error_output, error_hints = run_perltidy(cmd=self.perltidy_cmd, input=PERLTIDY_INPUTS[key]['input'], logger=self.logger)
            assert_equal(success, True)
            assert_equal(output, PERLTIDY_INPUTS[key]['output'])
            assert_equal(error_output, '')
            assert_equal(error_hints, [])


class TestPerlTidyHelpersMisc(PerlTidyTestCase):
    def test_make_coverage_happy(self):
        e = PerlTidyRuntimeError('FOOBARBAZ')
        l = PerlTidyNullLogger()
        l.log(0, 'Hello world')
        assert_equal(l.log_level(), 0)


class TestPerlTidyHelpers(PerlTidyTestCase):
    def test_pp(self):
        assert_equal(pp(None), '<None>')
        assert_equal(pp('Hello world'), '"Hello world"')
        assert_equal(pp(['Hello', 'world']), '"Hello" "world"')

    def test_get_perltidy_env_flag(self):
        os.environ['PERLTIDY_TEST_FOOBARBAZ'] = "1"
        assert_true(get_perltidy_env_flag('foobarbaz'))

        os.environ['PERLTIDY_TEST_FOOBARBAZ'] = "0"
        assert_false(get_perltidy_env_flag('foobarbaz'))

        if 'PERLTIDY_TEST_FOOBARBAZ' in os.environ:
            del os.environ['PERLTIDY_TEST_FOOBARBAZ']
        assert_false(get_perltidy_env_flag('foobarbaz'))

        assert_false(get_perltidy_env_flag('nonexistant'))

    def test_set_perltidy_env_flag(self):
        if 'PERLTIDY_TEST_FOOBARBAZ' in os.environ:
            del os.environ['PERLTIDY_TEST_FOOBARBAZ']

        set_perltidy_env_flag('foobarbaz', True)
        assert_equal(os.environ['PERLTIDY_TEST_FOOBARBAZ'], '1')

        set_perltidy_env_flag('foobarbaz', False)
        assert_equal(os.environ['PERLTIDY_TEST_FOOBARBAZ'], '0')

        set_perltidy_env_flag('foobarbaz', None)
        assert_true('PERLTIDY_TEST_FOOBARBAZ' not in os.environ)

        if 'PERLTIDY_TEST_FOOBARBAZ' in os.environ:
            del os.environ['PERLTIDY_TEST_FOOBARBAZ']

    def test_find_perltidy_in_path(self):
        old_path = os.environ['PATH']
        os.environ['PATH'] = ""
        assert_equal(None, find_perltidy_in_path(logger=self.logger))
        os.environ['PATH'] = old_path

    def test_run_perltidy(self):
        # Check argument validation in run_perltidy() only. Actual runs will
        # be made by PerlTidyInterpreterTestCase.
        f = lambda: run_perltidy(cmd=None, input='', logger=self.logger)
        assert_raises(ValueError, f)
        f = lambda: run_perltidy(cmd=[''], input=None, logger=self.logger)
        assert_raises(ValueError, f)

    def test_find_perltidy_in_platform_default_paths(self):
        def perltidy_clear_env_flags():
            for key in ['ignore_activeperl', 'ignore_cygwin', 'ignore_strawberry_perl']:
                set_perltidy_env_flag(key, None)

        if is_windows():
            if get_perltidy_env_flag('test_strawberry_perl'):
                perltidy_clear_env_flags()

                # Must return Strawberry Perl installation first.
                out = ['C:\\Strawberry\\perl\\bin\\perl.exe', 'C:\\Strawberry\\perl\\site\\bin\\perltidy']
                assert_equal(out, find_perltidy_in_platform_default_paths(logger=self.logger))

            if get_perltidy_env_flag('test_activeperl'):
                perltidy_clear_env_flags()

                # Simulate, we don't have Strawberry Perl. Must return ActivePerl
                # location, either 32-bit or 64-bit.
                set_perltidy_env_flag('ignore_strawberry_perl', True)
                out = ['C:\\Perl\\bin\\perl.exe', 'C:\\Perl\\site\\bin\\perltidy']
                assert_equal(out, find_perltidy_in_platform_default_paths(logger=self.logger))

            # Simulate, we don't have Strawberry Perl and don't have
            # ActivePerl. Must return Cygwin location.
            if get_perltidy_env_flag('test_cygwin'):
                perltidy_clear_env_flags()

                set_perltidy_env_flag('ignore_strawberry_perl', True)
                set_perltidy_env_flag('ignore_activeperl', True)
                out = ['C:\\Cygwin\\bin\\perl.exe', '/usr/local/bin/perltidy']
                assert_equal(out, find_perltidy_in_platform_default_paths(logger=self.logger))

    def test_is_valid_perltidy_cmd(self):
        assert_equal(False, is_valid_perltidy_cmd(cmd=None, logger=self.logger))
        assert_equal(False, is_valid_perltidy_cmd(cmd=[], logger=self.logger))

        self.logger.clear_log_buffer()
        assert_equal(False, is_valid_perltidy_cmd(cmd=['NONE'], logger=self.logger))
        r = re.compile(r'Checking\ for\ perltidy\:\ \"NONE\"$', re.MULTILINE)
        assert_regexp_matches(self.logger.get_log_buffer(), r)
        r = re.compile(r'Command\ not\ found\:\ \"NONE\"$', re.MULTILINE)
        assert_regexp_matches(self.logger.get_log_buffer(), r)

        self.logger.clear_log_buffer()
        assert_equal(False, is_valid_perltidy_cmd(cmd=['C:\ThisCommandDoesNotExist'], logger=self.logger, cmd_source='user'))
        assert_regexp_matches(self.logger.get_log_buffer(), r'specified\ in\ user\ setting')


# Tests, which will be run on Windows platforms only.
class TestPerlTidyHelpersWindows(PerlTidyTestCase):
    def setUp(self):
        PerlTidyTestCase.setUp(self)
        if not is_windows():
            self.skip_reason = 'Not running on Windows'

    def test_find_perltidy_in_path(self):
        self.skip_if_have_reason()
        old_path = os.environ['PATH']
        os.environ['PATH'] = 'C:\\Perl\\site\\bin' + os.pathsep + old_path

        cmd = ['C:\\Perl\\site\\bin\\perltidy.bat']
        assert_equal(cmd, find_perltidy_in_path(logger=self.logger))

        os.environ['PATH'] = old_path

    def test_cygwin_path_from_windows_path(self):
        self.skip_if_have_reason()
        assert_equal(cygwin_path_from_windows_path(None), None)
        assert_equal(cygwin_path_from_windows_path('C:\\Users\\FooBarBaz'), '/cygdrive/c/Users/FooBarBaz')
        assert_equal(cygwin_path_from_windows_path('f:\\'), '/cygdrive/f/')
        assert_equal(cygwin_path_from_windows_path('D:\\Temp\\sometempfile.html'), '/cygdrive/d/Temp/sometempfile.html')

        f = lambda: cygwin_path_from_windows_path('D:RelativePath')
        assert_raises(ValueError, f)


class TestPerlTidyHelpersFindPerltidyrcInProject(PerlTidyTestCase):
    def setUp(self):
        PerlTidyTestCase.setUp(self)

        self.temp_dirs = []
        self.temp_dirs.append(tempfile.mkdtemp())
        self.temp_dirs.append(tempfile.mkdtemp())

        # Create temp perltidyrc files.
        with open(os.path.join(self.temp_dirs[0], 'perltidyrc'), 'wb') as f:
            f.write("-l=120\n")
        with open(os.path.join(self.temp_dirs[1], '.perltidyrc'), 'wb') as f:
            f.write("-l=40\n")

    def tearDown(self):
        for temp_dir in self.temp_dirs:
            shutil.rmtree(temp_dir)

    def test_find_perltidyrc_in_project(self):
        # We must not get any results.
        result = find_perltidyrc_in_project(directories=self.temp_dirs, perltidyrc_paths=[], logger=self.logger)
        assert_is_none(result)
        result = find_perltidyrc_in_project(directories=None, perltidyrc_paths=None, logger=self.logger)
        assert_is_none(result)

        # Must return perltidyrc in first temp directory.
        result = find_perltidyrc_in_project(directories=self.temp_dirs, perltidyrc_paths=['perltidyrc'], logger=self.logger)
        assert_equal(result, os.path.join(self.temp_dirs[0], 'perltidyrc'))

        # Must still return perltidyrc in first temp directory.
        result = find_perltidyrc_in_project(directories=self.temp_dirs, perltidyrc_paths=['.perltidyrc', 'perltidyrc'], logger=self.logger)
        assert_equal(result, os.path.join(self.temp_dirs[0], 'perltidyrc'))

        # Must return perltidyrc in second temp directory.
        result = find_perltidyrc_in_project(directories=self.temp_dirs, perltidyrc_paths=['perltidyrcXXX', '.perltidyrc'], logger=self.logger)
        assert_equal(result, os.path.join(self.temp_dirs[1], '.perltidyrc'))


# Tests, which will be run on non-Windows platforms.
class TestPerlTidyHelpersNonWindows(PerlTidyTestCase):
    def setUp(self):
        PerlTidyTestCase.setUp(self)
        if sys.platform.startswith('win'):
            self.skip_reason = 'Running on Windows'

    def test_cygwin_path_from_windows_path(self):
        self.skip_if_have_reason()
        assert_equal(cygwin_path_from_windows_path(None), None)
        assert_equal(cygwin_path_from_windows_path('C:\\Users\\FooBarBaz'), None)


# Interpreter specific tests on Windows/ActivePerl.
class TestPerlTidyHelpersWindowsActivePerlInterpreter(PerlTidyInterpreterTestCase):
    def setUp(self):
        PerlTidyInterpreterTestCase.setUp(self)
        self.perltidy_cmd = ['C:\\Perl\\bin\\perl.exe', 'C:\\Perl\\site\\bin\\perltidy', '-ole=unix', '-se']

        if not is_windows():
            self.skip_reason = 'Not running on Windows'
        elif not get_perltidy_env_flag('test_activeperl'):
            self.skip_reason = "Not testing ActivePerl (ENV['PERLTIDY_TEST_HAVE_ACTIVEPERL'] not set)"

    def test_is_valid_perltidy_cmd(self):
        PerlTidyInterpreterTestCase.test_is_valid_perltidy_cmd(self)
        assert_equal(True, is_valid_perltidy_cmd(cmd=['C:\\Perl\\site\\bin\\perltidy.bat'], logger=self.logger))


# Interpreter specific tests on Windows/Cygwin.
class TestPerlTidyHelpersWindowsCygwinInterpreter(PerlTidyInterpreterTestCase):
    def setUp(self):
        PerlTidyInterpreterTestCase.setUp(self)
        self.perltidy_cmd = ['C:\\Cygwin\\bin\\perl.exe', '/usr/local/bin/perltidy', '-ole=unix', '-se']

        if not is_windows():
            self.skip_reason = 'Not running on Windows'
        elif not get_perltidy_env_flag('test_cygwin'):
            self.skip_reason = "Not testing Cygwin (ENV['PERLTIDY_TEST_TEST_CYGWIN'] not set)"


# Interpreter specific tests on Windows/Strawberry Perl.
class TestPerlTidyHelpersWindowsStrawberryPerlInterpreter(PerlTidyInterpreterTestCase):
    def setUp(self):
        PerlTidyInterpreterTestCase.setUp(self)
        self.perltidy_cmd = ['C:\\Strawberry\\perl\\bin\\perl.exe', 'C:\\Strawberry\\perl\\site\\bin\\perltidy', '-ole=unix', '-se']

        if not is_windows():
            self.skip_reason = 'Not running on Windows'
        elif not get_perltidy_env_flag('test_strawberry_perl'):
            self.skip_reason = "Not testing Strawberry Perl (ENV['PERLTIDY_TEST_TEST_STRAWBERRY_PERL'] not set)"

    def test_is_valid_perltidy_cmd(self):
        PerlTidyInterpreterTestCase.test_is_valid_perltidy_cmd(self)
        assert_equal(True, is_valid_perltidy_cmd(cmd=['C:\\Strawberry\\perl\\site\\bin\\perltidy.bat'], logger=self.logger))

# Interpreter specific tests on non-Windows with default perltidy.
class TestPerlTidyHelpersNonWindowsDefaultInterpreter(PerlTidyInterpreterTestCase):
    def setUp(self):
        PerlTidyInterpreterTestCase.setUp(self)
        self.perltidy_cmd = ['/usr/bin/perltidy', '-ole=unix', '-se']

        if is_windows():
            self.skip_reason = 'Running on Windows'
        elif not get_perltidy_env_flag('test_perltidy'):
            self.skip_reason = "Not testing perltidy (ENV['PERLTIDY_TEST_TEST_PERLTIDY'] not set)"

    def test_is_valid_perltidy_cmd(self):
        PerlTidyInterpreterTestCase.test_is_valid_perltidy_cmd(self)
        assert_equal(True, is_valid_perltidy_cmd(self.perltidy_cmd, logger=self.logger))
