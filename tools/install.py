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

working_dir = Path(__file__).parent.parent.resolve()
install_path = working_dir / Path("install")
version = (len(sys.argv) > 1 and sys.argv[1]) or "v0.0.1"

# 解析命令行参数: version os arch --gui <mfaa|mxu>
if len(sys.argv) < 6:
    print("Usage: python install.py <version> <os> <arch> --gui <mfaa|mxu>")
    print("Example: python install.py v1.0.0 win x86_64 --gui mfaa")
    sys.exit(1)

os_name = sys.argv[2]
arch = sys.argv[3]

gui = None
if "--gui" in sys.argv:
    idx = sys.argv.index("--gui")
    if idx + 1 < len(sys.argv):
        gui = sys.argv[idx + 1]
if gui not in ("mfaa", "mxu"):
    print("Error: You must specify --gui mfaa or --gui mxu.")
    sys.exit(1)


def get_dotnet_platform_tag():
    """自动检测当前平台并返回对应的dotnet平台标签"""
    if os_name == "win" and arch == "x86_64":
        platform_tag = "win-x64"
    elif os_name == "win" and arch == "aarch64":
        platform_tag = "win-arm64"
    elif os_name == "macos" and arch == "x86_64":
        platform_tag = "osx-x64"
    elif os_name == "macos" and arch == "aarch64":
        platform_tag = "osx-arm64"
    elif os_name == "linux" and arch == "x86_64":
        platform_tag = "linux-x64"
    elif os_name == "linux" and arch == "aarch64":
        platform_tag = "linux-arm64"
    else:
        print("Unsupported OS or architecture.")
        print("available parameters:")
        print("version: e.g., v1.0.0")
        print("os: [win, macos, linux, android]")
        print("arch: [aarch64, x86_64]")
        sys.exit(1)

    return platform_tag


def install_deps():
    if not (working_dir / "deps" / "bin").exists():
        print('Please download the MaaFramework to "deps" first.')
        print('请先下载 MaaFramework 到 "deps"。')
        sys.exit(1)

    # Android 平台仍然使用原来的全复制方式
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

    # 公共的忽略模式（移除不需要的控制单元和调试文件）
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
            # MFAA: 复制到 runtimes/<platform>/native/
            target_dir = (
                install_path / "runtimes" / get_dotnet_platform_tag() / "native"
            )
            shutil.copytree(
                working_dir / "deps" / "bin",
                target_dir,
                ignore=ignore_patterns,
                dirs_exist_ok=True,
            )
            # 复制 MaaAgentBinary
            shutil.copytree(
                working_dir / "deps" / "share" / "MaaAgentBinary",
                install_path / "libs" / "MaaAgentBinary",
                dirs_exist_ok=True,
            )
            # 复制 plugins
            shutil.copytree(
                working_dir / "deps" / "bin" / "plugins",
                install_path / "plugins" / get_dotnet_platform_tag(),
                dirs_exist_ok=True,
            )
        case "mxu":
            # MXU: 复制到 maafw/ 目录下，保持相同的过滤逻辑
            target_dir = install_path / "maafw"
            shutil.copytree(
                working_dir / "deps" / "bin",
                target_dir,
                ignore=ignore_patterns,
                dirs_exist_ok=True,
            )
            # MXU 不需要复制 MaaAgentBinary 和 plugins
        case _:
            raise ValueError(f"不允许的值: --gui {gui}")


def install_resource():
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
        interface = jsonc.load(f)

    interface["version"] = version

    with (install_path / "interface.json").open("w", encoding="utf-8") as f:
        jsonc.dump(interface, f, ensure_ascii=False, indent=4)


def install_chores():
    shutil.copy2(
        working_dir / "README.md",
        install_path,
    )
    shutil.copy2(
        working_dir / "LICENSE",
        install_path,
    )


def install_agent():
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
