# Don't import __future__ packages here; they make setup fail

# First, we try to use setuptools. If it's not available locally,
# we fall back on ez_setup.
try:
    from setuptools import setup
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup

with open("README.pypi.rst") as readmeFile:
    long_description = readmeFile.read()

install_requires = []
with open("requirements.txt") as requirementsFile:
    for line in requirementsFile:
        line = line.strip()
        if len(line) == 0:
            continue
        if line[0] == '#':
            continue
        pinnedVersion = line.split()[0]
        install_requires.append(pinnedVersion)

setup(
    # END BOILERPLATE
    name="ga4gh",
    description="A reference implementation of the ga4gh API",
    packages=["ga4gh", "ga4gh.datamodel", "ga4gh.templates"],
    zip_safe=False,
    url="https://github.com/ga4gh/server",
    use_scm_version={"write_to": "ga4gh/_version.py"},
    entry_points={
        'console_scripts': [
            'ga4gh_client=ga4gh.cli.client:client_main',
            'ga4gh_configtest=ga4gh.cli.configtest:configtest_main',
            'ga4gh_server=ga4gh.cli.server:server_main',
            'ga2vcf=ga4gh.cli.ga2vcf:ga2vcf_main',
            'ga2sam=ga4gh.cli.ga2sam:ga2sam_main',
            'ga4gh_repo=ga4gh.cli.repomanager:repo_main',
        ]
    },
    # BEGIN BOILERPLATE
    long_description=long_description,
    install_requires=install_requires,
    license='Apache License 2.0',
    include_package_data=True,
    author="Global Alliance for Genomics and Health",
    author_email="theglobalalliance@genomicsandhealth.org",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
    ],
    keywords=['genomics', 'reference'],
    # Use setuptools_scm to set the version number automatically from Git
    setup_requires=['setuptools_scm'],
)
