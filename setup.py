from distutils.core import setup

setup(
    name='gtc',
    version='1.1',
    description='experimental module to manage odoo deployments',
    author='Jan Troler',
    author_email='jan.troler@galtys.com',
    url='git@codebasehq.com:galtys/galtys/gtc.git',
    packages=['gtclib'],
    install_requires=[
        #'requests>=2.0.1',
    ],
    license='MIT',
    scripts=[
        'bin/gtc'
    ],
)
