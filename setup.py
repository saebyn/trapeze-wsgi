from setuptools import setup

setup(name='trapeze-wsgi',
      version='0.1.2',
      author='John Weaver',
      author_email='john@pledge4code.com',
      description='A trapeze-compatible AMQP client that provides support for any web framework that uses the WSGI standard.',
      url='http://github.com/saebyn/trapeze-wsgi/',
      package_dir={'': 'src'},
      packages=[''],
      install_requires=['amqplib >= 0.6.1'],
      classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.6',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Server',
      ],
      platforms=('Any',),
     )
