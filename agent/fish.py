import functools
import json
import time
from typing import TYPE_CHECKING, Self, override

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.define import OCRResult

from .virtual_key import Win_virtual_key

if TYPE_CHECKING:
    import numpy as np
    from maa.context import Context
    from maa.controller import Controller

MAX_RANGE = 120
GY_ROI = [404, 44, 478, 12]


def get_img(controller: Controller) -> np.typing.NDArray:
    return controller.post_screencap().get(wait=True)


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
            img: np.typing.NDArray = get_img(controller)

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
                time.sleep(2)  # 等待弹出获鱼界面
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
                time.sleep(2)  # 等待弹出获鱼界面
                return True

            green_x = gbox.x + gbox.w / 2
            yellow_x = ybox.x + ybox.w / 2
            diff = green_x - yellow_x

            if (diff_abs := abs(diff)) < 溜鱼_midpoint_pix_range:
                time.sleep(溜鱼_midpoint_sleep_time / 1000)
                continue

            key = (
                Win_virtual_key.A.value.code
                if diff < 0
                else Win_virtual_key.D.value.code
            )
            controller.post_key_down(key).wait()
            time.sleep((diff_abs + max(0, 溜鱼_midpoint_pix_range / 2 - 1)) / 200)
            controller.post_key_up(key).wait()

        print(f"溜鱼超出 {MAX_RANGE} 次循环")
        return True


@AgentServer.custom_action("fish_卖鱼_and_买换饵")
class Fish_卖鱼_and_买换饵(CustomAction):
    @override
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        controller = context.tasker.controller

        _get_img = functools.partial(get_img, controller=controller)

        def 检测初始状态() -> bool:
            初始状态_reco_detail = context.run_recognition("初始状态", _get_img())
            if 初始状态_reco_detail is None:
                print(f"{Fish_卖鱼_and_买换饵.__name__} 初始状态 识别错误")
                return False
            return 初始状态_reco_detail.box is not None

        class Empty_job:
            def wait(self) -> Self:
                return self

        if 检测初始状态() is False:
            print(f"{Fish_卖鱼_and_买换饵.__name__} 初始状态 识别不到")
            return False

        # region: 市场界面
        for action in (
            lambda: controller.post_click_key(Win_virtual_key.Q.value.code),
            lambda: controller.post_click(100, 280),  # 归流鱼舱
            lambda: controller.post_click(710, 645),  # 一键出售
            lambda: controller.post_click(780, 470),  # 确认
            lambda: controller.post_click(640, 640),  # 点击空白
            lambda: controller.post_click_key(Win_virtual_key.VK_ESCAPE.value.code),
        ):
            action().wait()
            time.sleep(1.5)
        # endregion

        # region: 商店界面
        controller.post_click_key(Win_virtual_key.R.value.code).wait()
        time.sleep(1.5)
        匹配万能鱼饵_reco_detail = context.run_recognition(
            "匹配万能鱼饵",
            _get_img(),
            pipeline_override={
                "匹配万能鱼饵": {
                    "recognition": {
                        "type": "OCR",
                        "param": {
                            "roi": [19, 71, 460, 610],
                        },
                    }
                }
            },
        )
        if 匹配万能鱼饵_reco_detail is None:
            print(f"{Fish_卖鱼_and_买换饵.__name__} 匹配万能鱼饵 识别错误")
            return False
        if 匹配万能鱼饵_reco_detail.box is None:
            print(f"{Fish_卖鱼_and_买换饵.__name__} 匹配万能鱼饵 识别不到")
            return False
        for ocr_res in 匹配万能鱼饵_reco_detail.all_results:
            if not isinstance(ocr_res, OCRResult):
                print("匹配万能鱼饵 OCR 结果不是 OCRResult 类型")
                return False
            if ocr_res.score < 0.9:
                continue
            if ocr_res.text == "万能鱼饵":
                controller.post_click(ocr_res.box[0], ocr_res.box[1]).wait()
                time.sleep(1.5)
                匹配万能鱼饵价格_reco_detail = context.run_recognition(
                    "匹配万能鱼饵价格",
                    _get_img(),
                    pipeline_override={
                        "匹配万能鱼饵价格": {
                            "recognition": {
                                "type": "OCR",
                                "param": {
                                    "roi": [1162, 577, 31, 31],
                                },
                            }
                        }
                    },
                )
                if 匹配万能鱼饵价格_reco_detail is None:
                    print(f"{Fish_卖鱼_and_买换饵.__name__} 匹配万能鱼饵价格 识别错误")
                    return False
                if 匹配万能鱼饵价格_reco_detail.box is None:
                    print(f"{Fish_卖鱼_and_买换饵.__name__} 匹配万能鱼饵价格 识别不到")
                    return False
                all_results = 匹配万能鱼饵价格_reco_detail.all_results
                if len(all_results) == 1:
                    if not isinstance(all_results[0], OCRResult):
                        print("匹配万能鱼饵价格 OCR 结果不是 OCRResult 类型")
                        return False
                    if all_results[0].score > 0.96 and all_results[0].text == "5":
                        for _ in range(3):  # 买 n * 99 个
                            for action in (
                                lambda: controller.post_click(1218, 636),  # 加满
                                lambda: controller.post_click(1074, 688),  # 购买
                                lambda: controller.post_click(774, 476),  # 确认
                                lambda: controller.post_click(640, 540),  # 点击空白
                            ):
                                action().wait()
                                time.sleep(1.5)

                        controller.post_click_key(  # 退出到初始
                            Win_virtual_key.VK_ESCAPE.value.code
                        ).wait()
                        time.sleep(1)
        # endregion

        # region: 换饵
        for action in (
            lambda: controller.post_click_key(Win_virtual_key.E.value.code),
            lambda: controller.post_click(496, 360),
            lambda: controller.post_click(496, 360),  # 点两次，无论如何都会进详细页面
            lambda: controller.post_click_key(Win_virtual_key.VK_ESCAPE.value.code),
            lambda: controller.post_click(780, 472),  # 更换
        ):
            action().wait()
            time.sleep(1.5)
        # endregion

        return True
