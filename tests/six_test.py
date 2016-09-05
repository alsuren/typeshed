#!/usr/bin/env python3
"""
six.moves creates fake modules in a way that we can't expect
type-checkers to understand. To work around this problem, we copy
files from stdlib into the appropriate place in six.moves.  This
script exists to check that both versions of each file are the same.

Passing --fix will attempt to fix any differences by copying the
relevant files from stdlib.
"""

from glob import glob
from os.path import exists
import re
from shutil import copy2
from subprocess import Popen, PIPE
import sys

IMPORT_REGEX = re.compile("^import (.*) as (.*)$")


class CheckError(Exception):
    pass


class FatalError(Exception):
    pass


def check_all_six_modules_in_sync(fix=False):
    error_count = 0
    for filename in glob("third_party/*/six/moves/__init__.pyi"):
        root = filename.replace("/six/moves/__init__.pyi", "")
        with open(filename) as file:
            for line in file.readlines():
                try:
                    check_import_line(root, line)
                except CheckError as e:
                    print(e.args[0])
                    error_count += 1
                    if fix:
                        fix_import_line(root, line)
                except FatalError as e:
                    print(e.args[0])
                    exit(1)
    if error_count and not fix:
        print("Finished with", error_count, "errors. Add --fix to correct.")
        exit(1)


def fix_import_line(root, line):
    match = IMPORT_REGEX.match(line)
    assert match
    original_module = match.group(1)
    original_filename = get_filename_from_module(root, original_module)
    try:
        six_module_name = match.group(2)
        copy_module = "six.moves." + six_module_name
        copy_filename = get_filename_from_module(root, copy_module)
    except CheckError:
        copy_filename = root + "/six/moves/" + six_module_name + ".pyi"
    print("Copying", original_filename, "to", copy_filename)
    copy2(original_filename, copy_filename)


def check_import_line(root, line, fix=False):
    match = IMPORT_REGEX.match(line)
    if match:
        original_module = match.group(1)
        original_filename = get_filename_from_module(root, original_module)
        copy_module = "six.moves." + match.group(2)
        copy_filename = get_filename_from_module(root, copy_module)
        check_files_match(original_filename, copy_filename)


def get_filename_from_module(root, module_name):
    if "six.moves" not in module_name:
        root = root.replace("third_party", "stdlib", 1)
    mod_path_root = root + "/" + module_name.replace(".", "/")
    for filename in [mod_path_root + "/__init__.pyi", mod_path_root + ".pyi"]:
        if exists(filename):
            return filename
    raise CheckError(module_name + " does not exist in " + root)


def check_files_match(original_file, six_copy):
    diff = Popen("diff -u %s %s" % (original_file, six_copy),
                 shell=True, stdout=PIPE)
    diff_output, diff_error = diff.communicate()
    if diff.returncode == 127:
        raise FatalError("diff is not installed. Quitting.")
    if diff.returncode != 0:
        raise CheckError("%s and %s differ.\ndiff says:\n%s" % (
            original_file, six_copy, diff_output.decode("utf-8")))

if __name__ == "__main__":
    fix = "--fix" in sys.argv
    check_all_six_modules_in_sync(fix)
