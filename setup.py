from setuptools import setup, find_packages

setup(
    name="bspwm-layout-manager",
    version="0.8.1",
    # System dependencies (not Python packages): bspwm, bspc, rofi, wmctrl
    description="Save and restore bspwm desktop layouts with a rofi menu",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="SamuelHenrique",
    url="https://github.com/SamuelHenriqueDeMoraisVitrio/bspwm-layout-manager",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "blm=bspwm_layout_manager.main:main",
        ],
    },
    data_files=[
        ("share/applications", ["assets/blm.desktop"]),
    ],
    classifiers=[
        "Environment :: X11 Applications",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Topic :: Desktop Environment",
    ],
)

