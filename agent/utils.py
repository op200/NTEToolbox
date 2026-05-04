from typing import TYPE_CHECKING, override

from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition, RectType

if TYPE_CHECKING:
    import numpy as np
    from maa.context import Context

DEFAULT_RESOLUTION = (1280, 720)


@AgentServer.custom_recognition("启动测试")
class Adswq(CustomRecognition):
    @override
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> RectType | CustomRecognition.AnalyzeResult | None:
        controller = context.tasker.controller

        img: np.typing.NDArray = controller.post_screencap().get(wait=True)

        h, w = img.shape[:2]
        if (w, h) != DEFAULT_RESOLUTION:
            print(
                f"分辨率非 {DEFAULT_RESOLUTION[0]} x {DEFAULT_RESOLUTION[1]}: {w} x {h}"
            )
        if w * 9 != h * 16:
            print(f"分辨率 {w} x {h} 不是 16:9")
            return None

        return [0, 0, w, h]
