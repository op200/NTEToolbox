import json
import time
from typing import TYPE_CHECKING, override

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction

if TYPE_CHECKING:
    from maa.context import Context

MAX_RANGE = 120
GY_ROI = [404, 44, 478, 12]


@AgentServer.custom_action("fish_溜鱼")
class Fish_溜鱼(CustomAction):
    @override
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        controller = context.tasker.controller

        param = json.loads(argv.custom_action_param)
        assert isinstance(param, dict)

        try:
            溜鱼_midpoint_pix_range = param.get("溜鱼_midpoint_pix_range")
            溜鱼_midpoint_sleep_time = param.get("溜鱼_midpoint_sleep_time")
            if 溜鱼_midpoint_pix_range is None or 溜鱼_midpoint_sleep_time is None:
                raise ValueError("必须填值")
            溜鱼_midpoint_pix_range, 溜鱼_midpoint_sleep_time = (
                int(溜鱼_midpoint_pix_range),
                int(溜鱼_midpoint_sleep_time),
            )
            if not 0 < 溜鱼_midpoint_pix_range < 50:
                raise ValueError("溜鱼_midpoint_pix_range 值范围不正常")
            if not 0 <= 溜鱼_midpoint_sleep_time < 200:
                raise ValueError("溜鱼_midpoint_sleep_time 值范围不正常")
        except Exception as e:
            print(f"选项初始化错误: {e} {e!r}")
            return False

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

            green_x = gbox.x + gbox.w / 2
            yellow_x = ybox.x + ybox.w / 2
            diff = green_x - yellow_x

            if (diff_abs := abs(diff)) < 溜鱼_midpoint_pix_range:
                time.sleep(溜鱼_midpoint_sleep_time / 1000)
                continue

            key = (
                0x41  # A
                if diff < 0
                else 0x44  # D
            )
            controller.post_key_down(key).wait()
            time.sleep(diff_abs / 200)
            controller.post_key_up(key).wait()

        print(f"溜鱼超出 {MAX_RANGE} 次循环")
        return True
