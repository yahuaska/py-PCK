from distutils.core import setup

setup(
    name='py-PCK',
    version='1.0',
    packages=['pck'],
    url='https://github.com/yahuaska/py-PCK',
    license='GNU GPL v2.0',
    author='yahuaska',
    author_email='ringo.working@gmail.com',
    requires=[
        'PIL',
    ],
    platforms='Any',
    long_description='Python class for manipulating PCK images from X-Com: Apocalypse. Based on code from OpenApoc and \
    ported from C++.',
    description='Python class for manipulating PCK images from X-Com: Apocalypse. Based on code from OpenApoc and \
    ported from C++.'
)