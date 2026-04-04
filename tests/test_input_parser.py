from copy import deepcopy

from nxbt.controller.input import DIRECT_INPUT_IDLE_PACKET
from nxbt.controller.input import InputParser


class DummyProtocol:
    def __init__(self):
        self.button_inputs = []
        self.left_stick_inputs = []
        self.right_stick_inputs = []

    def set_button_inputs(self, *args, **kwargs):
        self.button_inputs.append(args)

    def set_left_stick_inputs(self, *args, **kwargs):
        self.left_stick_inputs.append(args[0])

    def set_right_stick_inputs(self, *args, **kwargs):
        self.right_stick_inputs.append(args[0])


def test_parse_macro_preserves_infinite_loop_marker():
    parser = InputParser(DummyProtocol())
    parser.set_controller_input(deepcopy(DIRECT_INPUT_IDLE_PACKET))

    parsed = parser.parse_macro(
        "LOOP -1\n"
        "    A 0.1s\n"
        "    0.1s\n"
    )

    assert parsed == [{
        "type": "LOOP",
        "count": -1,
        "body": ["A 0.1s", "0.1s"]
    }]


def test_set_protocol_input_requeues_infinite_loop_until_stopped():
    protocol = DummyProtocol()
    parser = InputParser(protocol)
    parser.set_controller_input(deepcopy(DIRECT_INPUT_IDLE_PACKET))
    state = {"finished_macros": []}

    parser.buffer_macro(
        "LOOP -1\n"
        "    A 0.1s\n",
        macro_id="macro-1"
    )

    parser.set_protocol_input(state=state)
    assert parser.current_macro_commands == ["A", "0.1s"]
    assert parser.current_macro
    assert state["finished_macros"] == []

    parser.macro_timer_start -= 1
    parser.set_protocol_input(state=state)
    assert parser.current_macro_commands is None
    assert parser.current_macro
    assert state["finished_macros"] == []

    parser.set_protocol_input(state=state)
    assert parser.current_macro_commands == ["A", "0.1s"]
    assert parser.current_macro

    parser.stop_macro("macro-1", state=state)
    assert parser.current_macro is None
    assert parser.current_macro_commands is None
    assert "macro-1" in state["finished_macros"]

    parser.set_protocol_input(state=state)
    assert protocol.button_inputs[-1] == (0, 0, 0)


def test_macro_completion_sends_idle_input_on_next_tick():
    protocol = DummyProtocol()
    parser = InputParser(protocol)
    parser.set_controller_input(deepcopy(DIRECT_INPUT_IDLE_PACKET))
    state = {"finished_macros": []}

    parser.buffer_macro("A 0.1s", macro_id="macro-2")

    parser.set_protocol_input(state=state)
    assert parser.current_macro_commands == ["A", "0.1s"]

    parser.macro_timer_start -= 1
    parser.set_protocol_input(state=state)
    assert parser.current_macro_commands is None
    assert "macro-2" in state["finished_macros"]

    parser.set_protocol_input(state=state)
    assert protocol.button_inputs[-1] == (0, 0, 0)
