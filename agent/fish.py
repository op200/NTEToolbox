import time
from typing import TYPE_CHECKING, override

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction

if TYPE_CHECKING:
    from maa.context import Context


@AgentServer.custom_action("fish_溜鱼")
class Fish_溜鱼(CustomAction):
    @override
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        controller = context.tasker.controller

        img = controller.post_screencap().get(wait=True)
        yellow_reco_detail = context.run_recognition(
            "匹配黄色",
            img,
            pipeline_override={
                "匹配黄色": {
                    "recognition": {
                        "type": "ColorMatch",
                        "param": {
                            "roi": [400, 40, 500, 18],
                            "lower": [216, 189, 80],
                            "upper": [253, 252, 186],
                        },
                    }
                }
            },
        )

        if yellow_reco_detail is None:
            print("识别不到黄色")
            return True

        green_box = argv.box
        yellow_box = yellow_reco_detail.box

        if yellow_box is None:
            print("识别到黄色但是没有位置")
            return True

        green_x = green_box.x + green_box.w // 2
        yellow_x = yellow_box.x + yellow_box.w // 2
        diff = green_x - yellow_x

        key = (
            0x41  # A
            if diff < 0
            else 0x44  # D
        )
        controller.post_key_down(key).wait()
        time.sleep(abs(diff) / 200)
        controller.post_key_up(key).wait()

        return True
