from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

try:
    import jsonc
except ModuleNotFoundError as e:
    raise ImportError(
        "Missing dependency 'json-with-comments' (imported as 'jsonc').\n"
        f"Install it with:\n  {sys.executable} -m pip install json-with-comments\n"
        "Or add it to your project's requirements."
    ) from e

from configure import configure_ocr_model

working_dir: Path = Path(__file__).parent.parent.resolve()
install_path: Path = working_dir / "install"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install NTEToolbox with MaaFramework and GUI"
    )
    parser.add_argument("--version", required=True, help="Version tag, e.g., v1.0.0")
    parser.add_argument(
        "--os",
        required=True,
        choices=["win", "macos", "linux", "android"],
        help="Target OS",
    )
    parser.add_argument(
        "--arch",
        required=True,
        choices=["aarch64", "x86_64"],
        help="Target architecture",
    )
    parser.add_argument(
        "--gui", required=True, choices=["mfaa", "mxu"], help="GUI type (mfaa or mxu)"
    )
    return parser.parse_args()


args: argparse.Namespace = parse_args()
version: str = args.version
os_name: str = args.os
arch: str = args.arch
gui: str = args.gui


def get_dotnet_platform_tag() -> str:
    """自动检测当前平台并返回对应的dotnet平台标签"""
    if os_name == "win" and arch == "x86_64":
        return "win-x64"
    if os_name == "win" and arch == "aarch64":
        return "win-arm64"
    if os_name == "macos" and arch == "x86_64":
        return "osx-x64"
    if os_name == "macos" and arch == "aarch64":
        return "osx-arm64"
    if os_name == "linux" and arch == "x86_64":
        return "linux-x64"
    if os_name == "linux" and arch == "aarch64":
        return "linux-arm64"
    # argparse 已限制选项，但保留防御代码
    print("Unsupported OS or architecture.")
    sys.exit(1)


def install_deps() -> None:
    if not (working_dir / "deps" / "bin").exists():
        print('Please download the MaaFramework to "deps" first.')
        print('请先下载 MaaFramework 到 "deps"。')
        sys.exit(1)

    if os_name == "android":
        shutil.copytree(
            working_dir / "deps" / "bin",
            install_path,
            dirs_exist_ok=True,
        )
        shutil.copytree(
            working_dir / "deps" / "share" / "MaaAgentBinary",
            install_path / "MaaAgentBinary",
            dirs_exist_ok=True,
        )
        return

    ignore_patterns = shutil.ignore_patterns(
        "*MaaDbgControlUnit*",
        "*MaaThriftControlUnit*",
        "*MaaRpc*",
        "*MaaHttp*",
        "plugins",
        "*.node",
        "*MaaPiCli*",
    )

    match gui:
        case "mfaa":
            target_dir: Path = (
                install_path / "runtimes" / get_dotnet_platform_tag() / "native"
            )
            shutil.copytree(
                working_dir / "deps" / "bin",
                target_dir,
                ignore=ignore_patterns,
                dirs_exist_ok=True,
            )
            shutil.copytree(
                working_dir / "deps" / "share" / "MaaAgentBinary",
                install_path / "libs" / "MaaAgentBinary",
                dirs_exist_ok=True,
            )
            shutil.copytree(
                working_dir / "deps" / "bin" / "plugins",
                install_path / "plugins" / get_dotnet_platform_tag(),
                dirs_exist_ok=True,
            )
        case "mxu":
            target_dir: Path = install_path / "maafw"
            shutil.copytree(
                working_dir / "deps" / "bin",
                target_dir,
                ignore=ignore_patterns,
                dirs_exist_ok=True,
            )
        case _:
            raise ValueError(f"不允许的值: --gui {gui}")


def install_resource() -> None:
    configure_ocr_model()

    shutil.copytree(
        working_dir / "assets" / "resource",
        install_path / "resource",
        dirs_exist_ok=True,
    )
    shutil.copy2(
        working_dir / "assets" / "interface.json",
        install_path,
    )

    with (install_path / "interface.json").open("r", encoding="utf-8") as f:
        interface: dict = jsonc.load(f)

    interface["version"] = version

    with (install_path / "interface.json").open("w", encoding="utf-8") as f:
        jsonc.dump(interface, f, ensure_ascii=False, indent=4)


def install_chores() -> None:
    shutil.copy2(
        working_dir / "README.md",
        install_path,
    )
    shutil.copy2(
        working_dir / "LICENSE",
        install_path,
    )


def install_agent() -> None:
    shutil.copytree(
        working_dir / "agent",
        install_path / "agent",
        dirs_exist_ok=True,
    )


if __name__ == "__main__":
    install_deps()
    install_resource()
    install_chores()
    install_agent()

    print(f"Install to {install_path} successfully.")
