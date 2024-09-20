# Copyright 2024 The KerasHub Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Script to create (and optionally install) a `.whl` archive for KerasHub.

Usage:

1. Create a `.whl` file in `dist/`:

```
python3 pip_build.py
```

2. Also install the new package immediately after:

```
python3 pip_build.py --install
```
"""

import argparse
import datetime
import os
import pathlib
import re
import shutil

hub_package = "keras_hub"
nlp_package = "keras_nlp"
build_directory = "tmp_build_dir"
dist_directory = "dist"
to_copy = ["setup.py", "setup.cfg", "README.md"]


def ignore_files(_, filenames):
    return [f for f in filenames if "_test" in f]


def update_version(build_path, package, version, is_nightly=False):
    """Export Version and Package Name."""
    package_name = package.replace("_", "-")
    if is_nightly:
        date = datetime.datetime.now()
        version += f".dev{date.strftime('%Y%m%d%H')}"
        package_name = f"{package}-nightly"

    with open(build_path / "setup.py") as f:
        setup_contents = f.read()
    with open(build_path / "setup.py", "w") as f:
        setup_contents = setup_contents.replace(
            "name=", f'name="{package_name}",  # '
        )
        setup_contents = setup_contents.replace(
            "VERSION = ", f'VERSION = "{version}"  # '
        )
        f.write(setup_contents)

    # Make sure to export the __version__ string
    version_utils = build_path / package / "src" / "version_utils.py"
    if os.path.exists(version_utils):
        with open(version_utils) as f:
            contents = f.read()
        with open(version_utils, "w") as f:
            contents = re.sub(
                "\n__version__ = .*\n",
                f'\n__version__ = "{version}"\n',
                contents,
            )
            f.write(contents)


def copy_source_to_build_directory(root_path, package):
    # Copy sources (`keras_hub/` directory and setup files) to build
    # directory
    shutil.copytree(
        root_path / package,
        root_path / build_directory / package,
        ignore=ignore_files,
    )
    for fname in to_copy:
        shutil.copy(root_path / fname, root_path / build_directory / fname)


def build_wheel(build_path, dist_path, __version__):
    # Build the package
    os.chdir(build_path)
    os.system("python3 -m build")

    # Save the dist files generated by the build process
    if not os.path.exists(dist_path):
        os.mkdir(dist_path)
    for fpath in (build_path / dist_directory).glob("*.*"):
        shutil.copy(fpath, dist_path)

    # Find the .whl file path
    for fname in os.listdir(dist_path):
        if __version__ in fname and fname.endswith(".whl"):
            whl_path = dist_path / fname
            print(f"Build successful. Wheel file available at {whl_path}")
            return whl_path
    print("Build failed.")
    return None


def build(root_path, is_nightly=False, keras_nlp=True):
    if os.path.exists(build_directory):
        raise ValueError(f"Directory already exists: {build_directory}")

    try:
        whls = []
        build_path = root_path / build_directory
        dist_path = root_path / dist_directory
        os.mkdir(build_path)

        from keras_hub.src.version_utils import __version__  # noqa: E402

        copy_source_to_build_directory(root_path, hub_package)
        update_version(build_path, hub_package, __version__, is_nightly)
        whl = build_wheel(build_path, dist_path, __version__)
        whls.append(whl)

        if keras_nlp:
            build_path = root_path / build_directory / nlp_package
            dist_path = root_path / nlp_package / dist_directory

            copy_source_to_build_directory(root_path, nlp_package)
            update_version(build_path, nlp_package, __version__, is_nightly)
            whl = build_wheel(build_path, dist_path, __version__)
            whls.append(whl)

        return whls
    finally:
        # Clean up: remove the build directory (no longer needed)
        os.chdir(root_path)
        shutil.rmtree(root_path / build_directory)


def install_whl(whls):
    for path in whls:
        print(f"Installing wheel file: {path}")
        os.system(f"pip3 install {path} --force-reinstall --no-dependencies")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--install",
        action="store_true",
        help="Whether to install the generated wheel file.",
        default=False,
    )
    parser.add_argument(
        "--nightly",
        action="store_true",
        help="Whether to generate nightly wheel file.",
        default=False,
    )
    parser.add_argument(
        "--keras_nlp",
        action="store_true",
        help="Whether to build the keras-nlp shim package.",
        default=True,
    )
    args = parser.parse_args()
    root_path = pathlib.Path(__file__).parent.resolve()
    whls = build(root_path, args.nightly, args.keras_nlp)
    if whls and args.install:
        install_whl(whls)
