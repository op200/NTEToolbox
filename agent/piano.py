import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, override

import ms3
from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction

if TYPE_CHECKING:
    from maa.context import Context
    from maa.job import Job

KEY_LIST = [
    # 低音 Z-M
    *(0x5A, 0x58, 0x43, 0x56, 0x42, 0x4E, 0x4D),
    # 中音 A-J
    *(0x41, 0x53, 0x44, 0x46, 0x47, 0x48, 0x4A),
    # 高音 Q-U
    *(0x51, 0x57, 0x45, 0x52, 0x54, 0x59, 0x55),
]
MIDI__KEY: dict[int, int] = {
    # 低音
    60: 0x5A,
    62: 0x58,
    64: 0x43,
    65: 0x56,
    67: 0x42,
    69: 0x4E,
    71: 0x4D,
    # 中音
    72: 0x41,
    74: 0x53,
    76: 0x44,
    77: 0x46,
    79: 0x47,
    81: 0x48,
    83: 0x4A,
    # 高音
    84: 0x51,
    86: 0x57,
    88: 0x45,
    89: 0x52,
    91: 0x54,
    93: 0x59,
    95: 0x55,
}
LOW_PITCH_OVERFLOW_LINE, HIGH_PITCH_OVERFLOW_LINE = 59, 96
key_map: list[int] = [0x5A] * (LOW_PITCH_OVERFLOW_LINE + 1)
_val = MIDI__KEY[LOW_PITCH_OVERFLOW_LINE + 1]
for i in range(LOW_PITCH_OVERFLOW_LINE + 1, HIGH_PITCH_OVERFLOW_LINE):
    if i in MIDI__KEY:
        _val = MIDI__KEY[i]
    key_map.append(_val)
key_map += [0x55] * (128 - HIGH_PITCH_OVERFLOW_LINE)


@AgentServer.custom_action("piano_play")
class Piano_play(CustomAction):
    @override
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        controller = context.tasker.controller

        param = json.loads(argv.custom_action_param)
        assert isinstance(param, dict)

        mscz_path: Path | None = param.get("mscz_path")
        if mscz_path is None and (
            mscz_file_list := [p for p in Path.cwd().iterdir() if p.suffix == ".mscz"]
        ):
            mscz_path = mscz_file_list[0]
        if mscz_path is None:
            print("当前目录下没有 mscz 文件")
            return False
        mscz_path = Path(mscz_path)

        if not mscz_path.is_file():
            print(f'文件 "{mscz_path}" 不存在')
            return False

        if mscz_path.suffix != ".mscz":
            print(f'输入的文件 "{mscz_path}" 不是 .mscz')
            return False

        try:
            score = ms3.Score(mscz_path)
        except Exception as e:
            print(f"加载乐谱失败: {e}")
            return False

        notes = score.mscx.notes()
        if notes is None or notes.empty:
            print("没有 notes")
            return False

        # 1. 固定使用序号为 1 的声部（即总谱中最上方的乐器）
        if "staff" not in notes.columns:
            print("无法找到 'staff' 列，请检查 ms3 版本或文件结构")
            return False

        target_staff = 1
        part_notes = notes[notes["staff"] == target_staff].copy()
        if part_notes.empty:
            print(f"声部 {target_staff} 中没有音符，请检查乐谱是否包含该声部")
            return False
        print(f"使用声部: {target_staff}")

        # 按四分音符起始时间排序
        part_notes = part_notes.sort_values("quarterbeats")

        # 2. 使用最新 API 获取 BPM
        bpm = float(param.get("bpm", 120))
        try:
            # 优先使用 ms3 提供的 tempo 方法 (忽略 Pylance 的静态检查)
            tempo_df = score.mscx.tempo()  # type: ignore[attr-defined]
            if tempo_df is not None and not tempo_df.empty:
                bpm = float(tempo_df["bpm"].iloc[0])
                print(f"速度读取成功 (tempo API): {bpm} BPM")
            else:
                # 回退方案：尝试从 measures 中获取
                measures = score.mscx.measures()
                if measures is not None and "tempo" in measures.columns:
                    tempo_series = measures["tempo"].dropna()
                    if not tempo_series.empty:
                        bpm = float(tempo_series.iloc[0])
                        print(f"速度读取成功 (measures): {bpm} BPM")
                    else:
                        print("未找到速度标记，使用默认 120 BPM")
                else:
                    print("未找到速度信息，使用默认 120 BPM")
        except Exception as e:
            print(f"获取速度异常，使用默认 {bpm} BPM: {e}")
        quarter_sec: float = 60 / bpm

        # 3. 按起始时间分组（处理同一时刻的和弦）
        grouped = part_notes.groupby("quarterbeats")

        start_real = time.time()
        all_midi_list: list[int] = [
            note.get("midi", -1) for _, group in grouped for _, note in group.iterrows()
        ]
        if -1 in all_midi_list:
            print("存在无值 midi")
        midi_min, midi_max = min(all_midi_list), max(all_midi_list)
        midi_range = max(1, midi_max - midi_min)
        print("midi pre:", midi_min, midi_max, midi_range)
        if midi_min <= LOW_PITCH_OVERFLOW_LINE:
            print("警告: 低音溢出")
        if midi_max >= HIGH_PITCH_OVERFLOW_LINE:
            print("警告: 高音溢出")

        for qb, group in grouped:
            # 计算该时间点应该发生的真实时间
            target_real: float = start_real + qb * quarter_sec  # pyright: ignore[reportAssignmentType, reportOperatorIssue]
            now = time.time()
            if target_real > now:
                time.sleep(target_real - now)
            else:
                print("超时:", target_real, now, target_real - now)

            # 收集当前时间点所有要按的键
            key_codes: set[int] = set()
            midi_list = []
            for _, note in group.iterrows():
                midi = note.get("midi")
                midi_list.append(midi)
                assert midi is not None
                key_code: int = key_map[midi]
                key_codes.add(key_code)

            print(len(key_codes), midi_list)

            post_job_list: list[Job] = []
            for key_code in key_codes:
                post_job_list.append(controller.post_click_key(key_code))
            for job in post_job_list:
                job.wait()

        return True
