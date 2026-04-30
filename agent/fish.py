import time
from typing import TYPE_CHECKING, override

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction

if TYPE_CHECKING:
    from maa.context import Context

MAX_RANGE = 60
GY_ROI = [400, 40, 500, 18]


@AgentServer.custom_action("fish_溜鱼")
class Fish_溜鱼(CustomAction):
    @override
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        controller = context.tasker.controller

        for _ in range(MAX_RANGE):
            img = controller.post_screencap().get(wait=True)

            greem_reco_detail = context.run_recognition(
                "匹配绿色",
                img,
                pipeline_override={
                    "匹配绿色": {
                        "recognition": {
                            "type": "ColorMatch",
                            "param": {
                                "roi": GY_ROI,
                                "lower": [32, 178, 160],
                                "upper": [60, 244, 197],
                            },
                        }
                    }
                },
            )
            if greem_reco_detail is None:
                print(f"识别绿色错误: {greem_reco_detail}")
                return True
            gbox = greem_reco_detail.box
            if gbox is None:
                # print("识别不到绿色")
                return True

            yellow_reco_detail = context.run_recognition(
                "匹配黄色",
                img,
                pipeline_override={
                    "匹配黄色": {
                        "recognition": {
                            "type": "ColorMatch",
                            "param": {
                                "roi": GY_ROI,
                                "lower": [216, 189, 80],
                                "upper": [253, 252, 186],
                            },
                        }
                    }
                },
            )
            if yellow_reco_detail is None:
                print(f"识别黄色错误: {yellow_reco_detail}")
                return True
            ybox = yellow_reco_detail.box
            if ybox is None:
                # print("识别不到黄色")
                return True

            green_x = gbox.x + gbox.w // 2
            yellow_x = ybox.x + ybox.w // 2
            diff = green_x - yellow_x

            key = (
                0x41  # A
                if diff < 0
                else 0x44  # D
            )
            controller.post_key_down(key).wait()
            time.sleep(min(0.6, max(0.02, abs(diff) / 200)))
            controller.post_key_up(key).wait()

        print(f"超出 {MAX_RANGE} 次循环")
        return True
