import itertools
import json
import re
import urllib.request
from pathlib import Path
from threading import Thread
from typing import TYPE_CHECKING, override

from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition, RectType

if TYPE_CHECKING:
    import numpy as np
    from maa.context import Context

DEFAULT_RESOLUTION = (1280, 720)


REQ_HEADER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0"
}


def open_req(req: urllib.request.Request):
    proxies = urllib.request.getproxies()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxies))

    return opener.open(req)


class github:
    @classmethod
    def get_latest_release_ver(
        cls,
        release_api_url: str,
        *,
        reg: str | None = None,
    ) -> str | None:
        """失败返回 None，存在 reg 则返回 group(1)"""
        try:
            with open_req(
                urllib.request.Request(
                    url=release_api_url,
                    headers=REQ_HEADER,
                )
            ) as response:
                data: dict = json.loads(response.read().decode("utf-8"))
                ver = data.get("tag_name")
                if ver is None:
                    return None
                if isinstance(ver, str):
                    if reg is None:
                        return ver.lstrip("v")
                    _match = re.search(reg, ver)
                    if _match is None:
                        print(f"Match failed: {release_api_url} {reg} {_match}")
                        return None
                    return _match.group(1)
                raise ValueError(f"ver = {ver!r}")
        except Exception as e:
            print(
                f"'{cls.__name__}.{cls.get_latest_release_ver.__name__}' execution failed: {e}"
            )

        return None


def check_ver(new_ver_str: str, old_ver_str: str) -> bool:
    new_ver = list(re.sub(r"^\D*(\d.*\d)\D*$", r"\1", new_ver_str).split("."))
    new_ver_add_num = list(str(new_ver[-1]).split("+"))
    new_ver = (
        [int(v) for v in (*new_ver[:-1], new_ver_add_num[0])],
        [int(v) for v in new_ver_add_num[1:]],
    )

    old_ver = list(re.sub(r"^\D*(\d.*\d)\D*$", r"\1", old_ver_str).split("."))
    old_ver_add_num = list(str(old_ver[-1]).split("+"))
    old_ver = (
        [int(v) for v in (*old_ver[:-1], old_ver_add_num[0])],
        [int(v) for v in old_ver_add_num[1:]],
    )

    for i in range(2):
        for new, old in itertools.zip_longest(new_ver[i], old_ver[i], fillvalue=0):
            if new > old:
                return True
            if new < old:
                break
        else:
            continue
        break
    return False


def get_project_version() -> str | None:
    for path in itertools.chain(
        Path.cwd().iterdir(),
        p.iterdir() if (p := Path("assets")).is_dir() else (),
    ):
        if path.stem == "interface" and path.suffix.startswith(".json"):
            try:
                interface = json.loads(path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f'解码 "{path}" 失败: {e} {e!r}')
                return None
            if not isinstance(interface, dict):
                print("interface 不是 dict")
                return None
            if (ver_current := interface.get("version")) is None:
                print("interface 中没有 version")
                return None
            return ver_current
    return None


def check_release() -> None:
    for path in itertools.chain(
        Path.cwd().iterdir(),
        p.iterdir() if (p := Path("assets")).is_dir() else (),
    ):
        if path.stem == "interface" and path.suffix.startswith(".json"):
            if (ver_current := get_project_version()) is None:
                return

            ver_release = github.get_latest_release_ver(
                "https://api.github.com/repos/op200/NTEToolbox/releases/latest"
            )
            if ver_release is None:
                print("获取 Github Release 失败")
                return

            if check_ver(ver_release, ver_current):
                print(
                    f"有新版本: {ver_current} -> {ver_release}。"
                    "在此下载: https://github.com/op200/NTEToolbox/releases"
                )
            return
    print("获取 interface 文件失败")


@AgentServer.custom_recognition("启动测试")
class Adswq(CustomRecognition):
    @override
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> RectType | CustomRecognition.AnalyzeResult | None:
        Thread(target=check_release, daemon=True).start()

        controller = context.tasker.controller

        success: bool = True

        img: np.typing.NDArray = controller.post_screencap().get(wait=True)

        h, w = img.shape[:2]
        if (w, h) != DEFAULT_RESOLUTION:
            print(
                f"截图分辨率 {w} x {h} 不是 {DEFAULT_RESOLUTION[0]} x {DEFAULT_RESOLUTION[1]}"
            )
            success = False
        if w * 9 != h * 16:
            print(f"截图分辨率 {w} x {h} 不是 16:9")
            success = False

        if success is False:
            return None

        return [0, 0, w, h]
