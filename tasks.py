#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from sys import platform
from os import environ
from invoke import Collection, task


@task
def clean(ctx):
    '''Delete build files, optionally cache files'''
    # Patterns for directories
    dpatterns = [
        '__pycache__',
        '.cache',
        '.pytest_cache',
    ]

    # Patterns for files
    fpatterns = [
        '*.pyc',
        '*.pyo',
    ]
    for pattern in dpatterns:
        print('Cleaning dirs "{}"'.format(pattern))
        cmd = "find . -type d -name '{}' -exec rm -r {{}} +".format(pattern)
        ctx.run(cmd)

    for pattern in fpatterns:
        print('Cleaning files "{}"'.format(pattern))
        cmd = "find . -type f -name '{}' -exec rm {{}} +".format(pattern)
        ctx.run(cmd)
    print('Cleaning finished.')


@task
def test(ctx, tb='auto'):
    '''Run tests

    To set traceback print mode use $ inv test --tb=auto/long/short/line/native/no
    '''
    ctx.run('py.test -v --color=yes --tb={} lib'.format(tb))
    print('Testing finished.')


@task
def test1(ctx, path=None, capture='n', tb='auto'):
    '''Run single (one) test
    '''
    if path is None:
        print('Use -p argument to specify single test path')
    else:
        if capture[:1].title() == 'Y':
            ctx.run('py.test -s -v --color=yes --no-print-logs --tb={} {}'.format(tb, path))
        else:
            ctx.run('py.test -v --color=yes --no-print-logs --tb={} {}'.format(tb, path))
        print('Testing finished.')


@task
def lint(ctx):
    '''Run linter'''
    test_target = [
        'datanal',
        'config',
        'lib',
        'server.py',
        'tasks.py',
    ]
    for target in test_target:
        print('Linting {}'.format(target))
        ctx.run('flake8 --exit-zero {}'.format(target))
    print('Linter finished')


@task
def cov(ctx):
    '''Export coverage to HTML file
    '''
    ctx.run('py.test -s -v --color=yes --no-print-logs --tb=no --cov-report html --cov=flib')
    print('Open html/index.html')


@task
def dupl(ctx):
    '''Find duplicates in code
    '''
    ctx.run('pylint --disable=all --enable=duplicate-code flib/')


# ====[ Tasks for docs ] ========================================

@task
def docs_clean(ctx):
    '''Clean Sphinx build files (run docs.clean)'''
    patterns = [
        'docs/dist',
        'docs/source/_autosummary',
    ]
    for pattern in patterns:
        print('Cleaning "{}"'.format(pattern))
        cmd = 'rm -rf {}'.format(pattern)
        ctx.run(cmd)
    print('Cleaning finished.')


@task(pre=[docs_clean])
def docs_build(ctx):
    '''Build Shpinx documentation (run docs.build)'''
    ctx.run('sphinx-build -W -b html ./docs/source ./docs/dist/html')


# Default collection
ns = Collection(clean, lint, test, test1, cov, dupl)

# Documentation tasks are disabled by default
docs = Collection('docs')
docs.add_task(docs_build, 'build')
docs.add_task(docs_clean, 'clean')
ns.add_collection(docs, 'docs')


# Workaround for Windows "cmd" execution
if platform == 'win32':
    ns.configure({'run': {'shell': environ['COMSPEC']}})  # This is path to cmd.exe
