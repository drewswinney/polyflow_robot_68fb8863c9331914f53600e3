from setuptools import setup

package_name = 'webrtc'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/webrtc.launch.py']),
    ],
    install_requires=[
        'setuptools',
        'aiortc',
        'websockets',
    ],
    zip_safe=True,
    maintainer='Drew Swinney',
    maintainer_email='drew@polyflow.app',
    description='Polyflow ROS 2 node that bridges ROS topics to WebRTC signaling/data channels.',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'webrtc = webrtc.webrtc:main',  # <executable name> = <module>:<function>
        ],
    },
)
