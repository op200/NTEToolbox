"""解决不同执行环境的 interface 工作目录不同"""

import runpy
import sys
from pathlib import Path

MODULE_NAME = "agent"

if __name__ == "__main__":
    print(
        "import from",
        root := Path(__file__).resolve().parent.parent.parent,
    )
    sys.path.insert(0, str(root))

    del sys.modules[MODULE_NAME]
    runpy.run_module(MODULE_NAME, run_name="__main__")
