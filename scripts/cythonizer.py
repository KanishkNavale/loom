import multiprocessing
import os
import subprocess
import sysconfig
import tomllib
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from wheel.wheelfile import WheelFile

TOML_FILE_PATH = "pyproject.toml"
CPU_COUNT = multiprocessing.cpu_count()
DIST_DIR = Path("dist")
EXCLUDED_FILES = {"__init__.py", "__version__.py"}


def read_toml() -> dict:
    with open(TOML_FILE_PATH, "rb") as f:
        data = tomllib.load(f)

    if "project" not in data:
        raise ValueError("Missing [project] section in pyproject.toml")

    return data


def collect_py_files(package_dir: str) -> list[Path]:
    return [
        Path(root) / file
        for root, _, files in os.walk(package_dir)
        for file in files
        if file.endswith(".py") and file not in EXCLUDED_FILES
    ]


def get_cython_args() -> list[str]:
    return [
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


def get_gcc_flags() -> list[str]:
    include_dirs = sysconfig.get_path("include")
    compile_flags = (sysconfig.get_config_var("CFLAGS") or "").split()
    return [
        "-shared",
        "-fPIC",
        "-march=native",
        "-mtune=native",
        "-ffast-math",
        "-funroll-loops",
        "-O3",
        "-Wno-unused-function",
        f"-I{include_dirs}",
        *compile_flags,
    ]


def build_one(args: tuple[Path, list[str], list[str], str]) -> Path:
    py_file, cython_args, extra_flags, ext_suffix = args

    c_file = py_file.with_suffix(".c")
    subprocess.run([*cython_args, str(py_file), "-o", str(c_file)], check=True)

    so_file = c_file.with_suffix("").with_suffix(ext_suffix)
    subprocess.run(
        ["gcc", *extra_flags, str(c_file), "-o", str(so_file)], check=True
    )

    return so_file


def build_extensions(py_files: list[Path]) -> list[Path]:
    print("Building extensions (cythonize + compile) ...")
    ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")
    cython_args = get_cython_args()
    extra_flags = get_gcc_flags()

    tasks = [
        (
            py_file,
            cython_args,
            extra_flags,
            ext_suffix,
        )
        for py_file in py_files
    ]

    results = []
    with ProcessPoolExecutor(max_workers=CPU_COUNT) as pool:
        futures = {pool.submit(build_one, task): task for task in tasks}

        try:
            for future in as_completed(futures):
                results.append(future.result())

        except subprocess.CalledProcessError:
            for f in futures:
                f.cancel()

            raise

    return results


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

    project = toml["project"]
    name = project["name"]
    normalized_name = name.replace("-", "_")

    if "version" in project:
        version = project["version"]

    elif (
        "tool" in toml
        and "poetry" in toml["tool"]
        and "version" in toml["tool"]["poetry"]
    ):
        version = toml["tool"]["poetry"]["version"]

    else:
        version_file = Path(package) / "__version__.py"
        version_content = version_file.read_text()

        for line in version_content.split("\n"):
            if line.startswith("__version__"):
                version = line.split("=")[1].strip().strip('"').strip("'")
                break

        else:
            raise ValueError(
                "Could not find version in pyproject.toml or __version__.py"
            )

    python_tag = get_python_tag()
    abi_tag = get_abi_tag()
    platform_tag = get_platform_tag()
    wheel_name = (
        f"{normalized_name}-{version}-{python_tag}-{abi_tag}-{platform_tag}.whl"
    )
    wheel_path = DIST_DIR / wheel_name
    dist_info = f"{normalized_name}-{version}.dist-info"

    metadata = "\n".join(
        [
            "Metadata-Version: 2.3",
            f"Name: {name}",
            f"Version: {version}",
            f"Summary: {project.get('description', '')}",
            f"License: {project.get('license', '')}",
            f"Requires-Python: {project.get('requires-python', '>=3.12')}",
            *[
                f"Requires-Dist: {dep}"
                for dep in project.get("dependencies", [])
            ],
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
    for py_file in py_files:
        c_file = py_file.with_suffix(".c")
        if c_file.exists():
            c_file.unlink()


if __name__ == "__main__":
    toml = read_toml()
    packages = (
        toml.get("tool", {})
        .get("hatch", {})
        .get("build", {})
        .get("targets", {})
        .get("wheel", {})
        .get("packages", [])
    )
    package = packages[0] if packages else toml["project"]["name"]

    py_files = collect_py_files(package)
    so_files = build_extensions(py_files)
    build_wheel(toml, so_files, package)
    clean_c_files(py_files)
