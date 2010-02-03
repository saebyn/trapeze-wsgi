from setuptools import setup

setup(name='trapeze-wsgi',
      version='0.1.0',
      author='John Weaver',
      author_email='john@pledge4code.com',
      url='http://github.com/saebyn/trapeze-wsgi/',
      package_dir={'': 'src'},
      packages=[''],
      install_requires=['amqplib >= 0.6.1'],
      classifiers = [
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python :: 2.6',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Server',
      ],
      platforms = ('Any',),
     )

