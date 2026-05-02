import enum
import itertools
import json
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal, LiteralString, NamedTuple, override

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction

if TYPE_CHECKING:
    from maa.context import Context
    from maa.job import Job

type Key_name = Literal["Z", "X", "C", "V", "B", "N", "M","A", "S", "D", "F", "G", "H", "J", "Q", "W", "E", "R", "T", "Y", "U"]  # fmt: off
KN__CODE: Final[dict[Key_name, int]] = {
    # 低音 Z-M
    **{"Z": 0x5A, "X": 0x58, "C": 0x43, "V": 0x56, "B": 0x42, "N": 0x4E, "M": 0x4D},  # noqa: PIE800
    # 中音 A-J
    **{"A": 0x41, "S": 0x53, "D": 0x44, "F": 0x46, "G": 0x47, "H": 0x48, "J": 0x4A},  # noqa: PIE800
    # 高音 Q-U
    **{"Q": 0x51, "W": 0x57, "E": 0x45, "R": 0x52, "T": 0x54, "Y": 0x59, "U": 0x55},  # noqa: PIE800
}

LOW_PITCH_OVERFLOW_LINE, HIGH_PITCH_OVERFLOW_LINE = 59, 96


DEFAULT_KN__MIDI: Final[dict[Key_name, int]] = {
    **{"Z": 60, "X": 62, "C": 64, "V": 65, "B": 67, "N": 69, "M": 71},  # noqa: PIE800
    **{"A": 72, "S": 74, "D": 76, "F": 77, "G": 79, "H": 81, "J": 83},  # noqa: PIE800
    **{"Q": 84, "W": 86, "E": 88, "R": 89, "T": 91, "Y": 93, "U": 95},  # noqa: PIE800
}

CTRL_CHANGE_KN__MIDI: Final[dict[Key_name, int]] = {  # -1
    kn: DEFAULT_KN__MIDI[kn] - 1
    for kn in itertools.chain(
        ("C", "M"),
        ("D", "J"),
        ("E", "U"),
    )
}
SHIFT_CHANGE_KN__MIDI: Final[dict[Key_name, int]] = {  # +1
    kn: DEFAULT_KN__MIDI[kn] + 1
    for kn in itertools.chain(
        ("Z", "V", "B"),
        ("A", "F", "G"),
        ("Q", "R", "T"),
    )
}


@dataclass(slots=True, kw_only=True, frozen=True)
class Key:
    class Mode(enum.Enum):
        always = enum.auto()

        only_ctrl = enum.auto()
        no_ctrl = enum.auto()

        only_shift = enum.auto()
        no_shift = enum.auto()

    mode: Mode
    code: int


MIDI_SUFFIX_SET: Final[set[LiteralString]] = {".mid", ".midi"}


@AgentServer.custom_action("piano_play")
class Piano_play(CustomAction):
    @override
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        import music21
        import music21.common.types

        controller = context.tasker.controller

        class NoteEvent(NamedTuple):
            """用于存储音符事件的简易结构"""

            quarterbeats: music21.common.types.OffsetQL
            midi: int
            velocity: int  # 暂未使用，但可从 MIDI 中提取

        param = json.loads(argv.custom_action_param)
        assert isinstance(param, dict)
        print(param)

        piano_mode = param.get("piano_mode")
        if piano_mode not in {"21", "36"}:
            print("钢琴模式必须是 21 或 36")
            return False
        print(f"钢琴模式: {piano_mode}")

        timeout_mode = param.get("timeout_mode")
        if timeout_mode not in {"同步时轴", "速率不变"}:
            print("超时模式必须是 同步时轴 或 速率不变")
            return False
        print(f"超时模式: {timeout_mode}")

        midi__key: dict[int, Key] = {
            midi: Key(
                mode=(
                    Key.Mode.no_ctrl
                    if kn in CTRL_CHANGE_KN__MIDI
                    else Key.Mode.no_shift
                    if kn in SHIFT_CHANGE_KN__MIDI
                    else Key.Mode.always
                ),
                code=code,
            )
            for kn, midi in DEFAULT_KN__MIDI.items()
            if (code := KN__CODE[kn])
        }

        if piano_mode == "36":
            midi__key_ctrl = {
                midi: Key(mode=Key.Mode.only_ctrl, code=KN__CODE[kn])
                for kn, midi in CTRL_CHANGE_KN__MIDI.items()
            }
            midi__key_shift = {
                midi: Key(mode=Key.Mode.only_shift, code=KN__CODE[kn])
                for kn, midi in SHIFT_CHANGE_KN__MIDI.items()
            }
            midi__key |= midi__key_ctrl | midi__key_shift

        key_map: list[Key] = [midi__key[DEFAULT_KN__MIDI["Z"]]] * (
            LOW_PITCH_OVERFLOW_LINE + 1
        )
        """midi -> key 的 list index 版"""
        _val = midi__key[LOW_PITCH_OVERFLOW_LINE + 1]
        for i in range(LOW_PITCH_OVERFLOW_LINE + 1, HIGH_PITCH_OVERFLOW_LINE):
            if i in midi__key:
                _val = midi__key[i]
            key_map.append(_val)
        key_map += [midi__key[DEFAULT_KN__MIDI["U"]]] * (128 - HIGH_PITCH_OVERFLOW_LINE)

        midi_path: Path | None = (
            None if (v := param.get("midi_path")) is None else Path(v)
        )
        if midi_path is None:
            if midi_file_list := [
                p for p in Path.cwd().iterdir() if p.suffix in MIDI_SUFFIX_SET
            ]:
                midi_path = midi_file_list[0]
            else:
                print("当前目录下没有 midi 文件")
                return False
        elif midi_path.suffix not in MIDI_SUFFIX_SET:
            print(f"输入的文件后缀不属于 {MIDI_SUFFIX_SET}")
            return False

        if not midi_path.is_file():
            print(f'文件 "{midi_path}" 不存在')

        try:
            midi_converted = music21.converter.parse(midi_path)
        except Exception as e:
            print(f"加载 MIDI 文件失败: {e}")
            raise

        if isinstance(midi_converted, music21.stream.Opus):
            target_part = midi_converted.scores.parts[0]
        elif isinstance(midi_converted, music21.stream.Score):
            target_part = midi_converted.parts[0]
        elif isinstance(midi_converted, music21.stream.Part):
            target_part = midi_converted
        else:
            raise TypeError("读取到的数据类型不正确")

        print(
            f"使用声部: {target_part.partName if hasattr(target_part, 'partName') else '单轨'}"
        )

        # 4. 提取所有音符事件（包含全局四分音符位置）
        notes_events: list[NoteEvent] = []
        for el in target_part.recurse().notesAndRests:
            if not el.isNote and not el.isChord:
                continue

            # 获取全局四分音符长度单位位置
            measure = el.getContextByClass("Measure")
            quarterbeats = (
                el.offset if measure is None else measure.offset + el.offset
            )  # 不应该发生，但容错

            if el.isNote:
                assert isinstance(el, music21.note.Note)
                if el.volume.velocity is not None:
                    notes_events.append(
                        NoteEvent(
                            quarterbeats=quarterbeats,
                            midi=el.pitch.midi,
                            velocity=el.volume.velocity if el.volume else 64,
                        )
                    )
            elif el.isChord:
                assert isinstance(el, music21.chord.Chord)
                if el.volume.velocity is not None:
                    for pitch in el.pitches:
                        notes_events.append(
                            NoteEvent(
                                quarterbeats=quarterbeats,
                                midi=pitch.midi,
                                velocity=el.volume.velocity if el.volume else 64,
                            )
                        )

        if not notes_events:
            print("没有音符")
            return False

        # 5. 获取速度
        bpm = float(param.get("bpm") or 120)
        try:
            # 尝试从乐谱中提取第一个速度标记
            for el in midi_converted.recurse().getElementsByClass("MetronomeMark"):
                bpm = el.number
                print(f"速度读取成功: {bpm} BPM")
                break
            else:
                print(f"未找到速度标记，使用指定或默认 {bpm} BPM")
        except Exception as e:
            print(f"获取速度异常，使用 {bpm} BPM: {e}")
        quarter_sec: float = 60 / bpm

        # 6. 按 quarterbeats 分组音符（处理同时触发）

        grouped: dict[music21.common.types.OffsetQL, list[NoteEvent]] = defaultdict(
            list
        )
        for ne in sorted(notes_events, key=lambda x: x.quarterbeats):
            grouped[ne.quarterbeats].append(ne)

        # 7. 音高范围检查
        all_midi = [ne.midi for ne in notes_events]
        midi_min, midi_max = min(all_midi), max(all_midi)
        print(f"midi 范围: {midi_min} - {midi_max}, 跨度: {midi_max - midi_min}")
        if midi_min <= LOW_PITCH_OVERFLOW_LINE:
            print("警告: 低音溢出")
        if midi_max >= HIGH_PITCH_OVERFLOW_LINE:
            print("警告: 高音溢出")

        # 8. 开始按时间顺序模拟按键
        start_real = time.time()
        timeout: float = 0
        timeout_total: float = 0
        for qb in sorted(grouped.keys()):
            target_real = start_real + qb * quarter_sec
            now = time.time()
            timeout = target_real + timeout_total - now
            if timeout_mode == "同步时轴":
                if target_real > now:
                    time.sleep(target_real - now)
                else:
                    print(f"超时: {round((now - target_real) * 1000):>7,}ms")
            else:  # noqa: PLR5501
                if timeout >= 0:
                    time.sleep(timeout)
                else:
                    timeout_total = now - target_real
                    print(
                        f"超时: {round((-timeout) * 1000):>5,}ms  {round(timeout_total * 1000):>7,}ms"
                    )

            # 收集当前时间点的所有按键
            keys: set[Key] = {key_map[ne.midi] for ne in grouped[qb]}

            post_job_list: list[Job] = []

            if all(
                k.mode not in {Key.Mode.only_ctrl, Key.Mode.only_shift} for k in keys
            ):
                for key in keys:
                    post_job_list.append(controller.post_click_key(key.code))
                for job in post_job_list:
                    job.wait()

            else:
                key_list_always = [k for k in keys if k.mode == Key.Mode.always]
                key_list_ctrl = [
                    k for k in keys if k.mode in {Key.Mode.only_ctrl, Key.Mode.no_shift}
                ]
                key_list_shift = [
                    k for k in keys if k.mode in {Key.Mode.only_shift, Key.Mode.no_ctrl}
                ]

                # region: Shift and Always
                if key_list_shift:
                    controller.post_key_down(0x10).wait()

                    for key in itertools.chain(key_list_shift, key_list_always):
                        post_job_list.append(controller.post_click_key(key.code))
                    for job in post_job_list:
                        job.wait()

                    controller.post_key_up(0x10).wait()
                # endregion

                # region: Ctrl
                if key_list_ctrl:
                    controller.post_key_down(0x11).wait()

                    post_job_list.clear()
                    for key in itertools.chain(
                        key_list_ctrl, () if key_list_shift else key_list_always
                    ):
                        if key.mode in {Key.Mode.only_ctrl, Key.Mode.no_shift}:
                            post_job_list.append(controller.post_click_key(key.code))
                    for job in post_job_list:
                        job.wait()

                    controller.post_key_up(0x11).wait()
                # endregion

        return True
