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
        yellow_reco_detail = context.run_recognition(
            "匹配黄色",
            argv.reco_detail.raw_image,
            pipeline_override={
                "匹配黄色": {
                    "recognition": {
                        "type": "ColorMatch",
                        "param": {
                            "roi": [400, 40, 500, 18],
                            "lower": [230, 213, 122],
                            "upper": [254, 249, 170],
                        },
                    }
                }
            },
        )

        if yellow_reco_detail is None:
            print("识别不到黄色")
            return False

        green_box = argv.box
        yellow_box = yellow_reco_detail.box

        if yellow_box is None:
            print("识别到黄色但是没有位置")
            return False

        green_x = green_box.x + green_box.w // 2
        yellow_x = yellow_box.x + yellow_box.w // 2

        click_job = context.tasker.controller.post_click_key(
            0x41  # A
            if green_x < yellow_x
            else 0x44  # D
        )
        click_job.wait()

        return True
