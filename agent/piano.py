import enum
import json
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, override

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction

if TYPE_CHECKING:
    from maa.context import Context
    from maa.job import Job

KEY_LIST: list[int] = [
    # 低音 Z-M
    # Z     X     C     V     B     N     M
    *(0x5A, 0x58, 0x43, 0x56, 0x42, 0x4E, 0x4D),
    # 中音 A-J
    # A     S     D     F     G     H     J
    *(0x41, 0x53, 0x44, 0x46, 0x47, 0x48, 0x4A),
    # 高音 Q-U
    # Q     W     E     R     T     Y     U
    *(0x51, 0x57, 0x45, 0x52, 0x54, 0x59, 0x55),
]
LOW_PITCH_OVERFLOW_LINE, HIGH_PITCH_OVERFLOW_LINE = 59, 96


@dataclass(slots=True, kw_only=True, frozen=True)
class Key:
    class Mode(enum.Enum):
        default = None
        shift = 0x10
        """高半音"""
        ctrl = 0x11
        """低半音"""

    mode: Mode
    key: int


MIDI_SUFFIX_SET: set[str] = {".mid", ".midi"}


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

        mode = param.get("piano_mode")
        if mode not in {"21", "36"}:
            print("模式必须是 21 或 36")
            return False
        print(f"模式: {mode}")

        midi__key: dict[int, Key] = {
            midi: Key(mode=Key.Mode.default, key=KEY_LIST[i])
            for i, midi in enumerate(
                (
                    *(60, 62, 64, 65, 67, 69, 71),
                    *(72, 74, 76, 77, 79, 81, 83),
                    *(84, 86, 88, 89, 91, 93, 95),
                )
            )
        }

        if mode == "36":
            midi__key |= {
                midi: Key(mode=Key.Mode.ctrl, key=KEY_LIST[i])
                for i, midi in enumerate(
                    (
                        # -1
                        *(None, None, 63, None, None, None, 70),
                        *(None, None, 75, None, None, None, 82),
                        *(None, None, 87, None, None, None, 94),
                    )
                )
                if midi is not None
            } | {
                midi: Key(mode=Key.Mode.shift, key=KEY_LIST[i])
                for i, midi in enumerate(
                    (
                        # +1
                        *(61, None, None, 66, 68, None, None),
                        *(73, None, None, 78, 80, None, None),
                        *(85, None, None, 90, 92, None, None),
                    )
                )
                if midi is not None
            }

        key_map: list[Key] = [Key(mode=Key.Mode.default, key=0x5A)] * (
            LOW_PITCH_OVERFLOW_LINE + 1
        )
        """midi -> key 的 list index 版"""
        _val = midi__key[LOW_PITCH_OVERFLOW_LINE + 1]
        for i in range(LOW_PITCH_OVERFLOW_LINE + 1, HIGH_PITCH_OVERFLOW_LINE):
            if i in midi__key:
                _val = midi__key[i]
            key_map.append(_val)
        key_map += [Key(mode=Key.Mode.default, key=0x55)] * (
            128 - HIGH_PITCH_OVERFLOW_LINE
        )

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
        for qb in sorted(grouped.keys()):
            target_real = start_real + qb * quarter_sec
            now = time.time()
            if target_real > now:
                time.sleep(target_real - now)
            else:
                print(f"超时: {round((now - target_real) * 1000)}ms")

            # 收集当前时间点的所有按键
            keys: set[Key] = set()
            for ne in grouped[qb]:
                key: Key = key_map[ne.midi]
                keys.add(key)

            keys_default = [k for k in keys if k.mode == Key.Mode.default]
            keys_shift = [k for k in keys if k.mode == Key.Mode.shift]
            keys_ctrl = [k for k in keys if k.mode == Key.Mode.ctrl]

            post_job_list: list[Job] = []
            for key in keys_default:
                post_job_list.append(controller.post_click_key(key.key))
            for job in post_job_list:
                job.wait()

            # print(len(keys), keys_default, keys_shift, keys_ctrl)

            if keys_shift:
                controller.post_key_down(0x10).wait()

                post_job_list.clear()
                for key in keys_shift:
                    post_job_list.append(controller.post_click_key(key.key))
                for job in post_job_list:
                    job.wait()

                controller.post_key_up(0x10).wait()

            if keys_ctrl:
                controller.post_key_down(0x11).wait()

                post_job_list.clear()
                for key in keys_ctrl:
                    post_job_list.append(controller.post_click_key(key.key))
                for job in post_job_list:
                    job.wait()

                controller.post_key_up(0x11).wait()

        return True
