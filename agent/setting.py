import json
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Final, override

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.tasker import Tasker

from .log import log, setup_logger

if TYPE_CHECKING:
    from maa.context import Context


@AgentServer.custom_action("全局设置")
class 全局设置(CustomAction):
    @override
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        try:
            param = json.loads(argv.custom_action_param)
            if not isinstance(param, dict):
                raise TypeError("缺少 argv.custom_action_param 或类型错误")

            debug_mode_switch = param.get("debug_mode_switch")
            if debug_mode_switch is None:
                raise ValueError("debug_mode_switch 必须填值")
            debug_mode_switch = int(debug_mode_switch)
            if debug_mode_switch not in {0, 1}:
                raise ValueError("debug_mode_switch 必须是 0 或 1")

            logging_switch = param.get("logging_switch")
            if logging_switch is None:
                raise ValueError("logging_switch 必须填值")
            logging_switch = int(logging_switch)
            if logging_switch not in {0, 1}:
                raise ValueError("logging_switch 必须是 0 或 1")

            logging_switch = bool(logging_switch)
        except Exception as e:
            log.error(f"{self.__class__.__name__} 选项初始化错误: {e} {e!r}")
            return False

        if debug_mode_switch:
            log.info("开启 debug 模式")
            setup_logger("DEBUG")
            Tasker.set_debug_mode(True)
        else:
            log.debug("关闭 debug 模式")
            setup_logger("INFO")
            Tasker.set_debug_mode(False)

        maa_option_path = Path("config", "maa_option.json")
        maa_option: dict[str, int | bool] = json.loads(
            maa_option_path.read_text(encoding="utf-8")
        )
        maa_option_old: Final = deepcopy(maa_option)

        maa_option["logging"] = logging_switch

        modified: bool = False
        for k, v in maa_option_old.items():
            if (new := maa_option[k]) != v:
                log.info(f"修改 maa_option.{k}: {v} -> {new}")
                modified = True
        if modified:
            maa_option_path.write_text(
                json.dumps(maa_option, indent=4), encoding="utf-8"
            )
            log.info(f'已覆写 "{maa_option_path}"，重启后生效')

        return True
