#!/usr/bin/env python

import multiprocessing
import os
import subprocess
import sysconfig
import tomllib
from pathlib import Path

from wheel.wheelfile import WheelFile  # type: ignore[import]

from loom.logger import LoomLogger

TOML_FILE_PATH = "pyproject.toml"
CPU_COUNT = multiprocessing.cpu_count()
DIST_DIR = Path("dist")
EXCLUDED_FILES = {"__init__.py", "__version__.py"}

logger = LoomLogger("cythonizer")


def read_toml() -> dict:
    with open(TOML_FILE_PATH, "rb") as f:
        data = tomllib.load(f)
    if "project" in data:
        return data["project"]
    raise ValueError("Missing [project] section in pyproject.toml")


def collect_py_files(package_dir: str) -> list[Path]:
    return [
        Path(root) / file
        for root, _, files in os.walk(package_dir)
        for file in files
        if file.endswith(".py") and file not in EXCLUDED_FILES
    ]


def cythonize_to_c(py_files: list[Path]) -> list[Path]:
    logger.info("Cythonizing .py -> .c ...")
    base_args = [
        "cython",
        "--fast-fail",
        "-3",
        "--directive",
        "cdivision=True",
        "--directive",
        "boundscheck=True",
        "--directive",
        "wraparound=True",
        "--directive",
        "infer_types=True",
        "--directive",
        "embedsignature=True",
        "--directive",
        "binding=True",
        "--directive",
        "linetrace=False",
        "--directive",
        "profile=False",
    ]
    c_files = []
    for py_file in py_files:
        c_file = py_file.with_suffix(".c")
        subprocess.run(
            [*base_args, str(py_file), "-o", str(c_file)], check=True
        )
        c_files.append(c_file)
    return c_files


def compile_one(args: tuple[Path, Path, list[str]]) -> Path:
    c_file, so_file, flags = args
    subprocess.run(["gcc", *flags, str(c_file), "-o", str(so_file)], check=True)
    return so_file


def compile_extensions(c_files: list[Path]) -> list[Path]:
    logger.info("Compiling .c -> .so ...")
    ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")
    include_dirs = sysconfig.get_path("include")
    compile_flags = (sysconfig.get_config_var("CFLAGS") or "").split()
    extra_flags = [
        "-shared",
        "-fPIC",
        "-march=native",
        "-mtune=native",
        "-ffast-math",
        "-funroll-loops",
        "-flto",
        "-O3",
        f"-I{include_dirs}",
        *compile_flags,
    ]

    tasks = [
        (c_file, c_file.with_suffix("").with_suffix(ext_suffix), extra_flags)
        for c_file in c_files
    ]

    with multiprocessing.Pool(CPU_COUNT) as pool:
        return pool.map(compile_one, tasks)


def get_python_tag() -> str:
    v = sysconfig.get_python_version().replace(".", "")
    return f"cp{v}"


def get_abi_tag() -> str:
    soabi = sysconfig.get_config_var("SOABI") or ""
    parts = soabi.split("-")
    if len(parts) >= 2:
        return f"cp{parts[1]}"
    return get_python_tag()


def get_platform_tag() -> str:
    return sysconfig.get_platform().replace("-", "_").replace(".", "_")


def build_wheel(toml: dict, so_files: list[Path], package: str) -> Path:
    print("Assembling wheel ...")
    DIST_DIR.mkdir(exist_ok=True)

    name = toml["name"]
    version = toml["version"]
    python_tag = get_python_tag()
    abi_tag = get_abi_tag()
    platform_tag = get_platform_tag()
    wheel_name = f"{name}-{version}-{python_tag}-{abi_tag}-{platform_tag}.whl"
    wheel_path = DIST_DIR / wheel_name
    dist_info = f"{name}-{version}.dist-info"

    metadata = "\n".join(
        [
            "Metadata-Version: 2.3",
            f"Name: {name}",
            f"Version: {version}",
            f"Summary: {toml.get('description', '')}",
            f"License: {toml.get('license', '')}",
            f"Requires-Python: {toml.get('requires-python', '>=3.12')}",
            *[f"Requires-Dist: {dep}" for dep in toml.get("dependencies", [])],
        ]
    )

    wheel_metadata = "\n".join(
        [
            "Wheel-Version: 1.0",
            "Generator: cythonize_package",
            "Root-Is-Purelib: false",
            f"Tag: {python_tag}-{abi_tag}-{platform_tag}",
        ]
    )

    with WheelFile(wheel_path, "w") as wf:
        for so_file in so_files:
            wf.write(str(so_file), arcname=str(so_file))

        for init in Path(package).rglob("__init__.py"):
            wf.write(str(init), arcname=str(init))

        for ver in Path(package).rglob("__version__.py"):
            wf.write(str(ver), arcname=str(ver))

        wf.writestr(f"{dist_info}/METADATA", metadata)
        wf.writestr(f"{dist_info}/WHEEL", wheel_metadata)
        wf.writestr(f"{dist_info}/top_level.txt", f"{package}\n")

    print(f"Built: {wheel_path}")
    return wheel_path


def clean_c_files(py_files: list[Path]) -> None:
    logger.info("Cleaning up .c files ...")
    for py_file in py_files:
        c_file = py_file.with_suffix(".c")
        if c_file.exists():
            c_file.unlink()


def clean_so_files(py_files: list[Path]) -> None:
    logger.info("Cleaning up .so files ...")
    ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")
    for py_file in py_files:
        so_file = py_file.with_suffix("").with_suffix(ext_suffix)
        if so_file.exists():
            so_file.unlink()


if __name__ == "__main__":
    toml = read_toml()
    package = toml["name"]

    py_files = collect_py_files(package)
    c_files = cythonize_to_c(py_files)
    so_files = compile_extensions(c_files)
    build_wheel(toml, so_files, package)
    clean_c_files(py_files)
    clean_so_files(py_files)
