import re
from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from typing import Union, NamedTuple, Literal, Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Grid, Horizontal
from textual.events import DescendantBlur
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Button, Input


class NumberSpinner(Widget):
    DEFAULT_CSS = """

    """

    @dataclass
    class ButtonSpin(Message):
        """
        The transient number is the number that potentially this is increasing or decreasing to, however the final
        number may be different, due to the applied constraints. This is provided to allow changing what the end result
        may be.
        """
        number_spinner: "NumberSpinner"
        direction: Literal["up", "down"]
        transient_number: int

        @property
        def control(self) -> "NumberSpinner":
            return self.number_spinner

    @dataclass
    class NumberChanged(Message):
        number_spinner: "NumberSpinner"
        number: int

        @property
        def control(self) -> "NumberSpinner":
            return self.number_spinner

    def __init__(self, min_val: int, max_val: int, initial_value: Optional[int] = None, **kwargs):
        """
        Provides an input box with an up and down box. Restricted to integers that are constrained to min/max values.
        :param min_val:
        :param max_val:
        :param initial_value:
        :param kwargs:

        :keyword id: ID of the NumberSpinner
        :keyword classes: classes for the NumberSpinner
        """
        super().__init__(**kwargs)
        self.min = min_val
        self.max = max_val

        value = initial_value if initial_value is not None else self.min
        input_params = dict(
            classes="num_spin_input",
            value=str(value)
        )
        self.input = Input(**input_params)
        if not self.number_valid():
            self.input.value = str(self.min)

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Button("−", classes="int_change_btn down")
            yield self.input
            yield Button("+", classes="int_change_btn up")

    @on(Button.Pressed, ".int_change_btn")
    def _up_down_btn(self, event: Button.Pressed):
        current_value = self.value
        if event.button.has_class("up"):
            current_value += 1
            if current_value <= self.max:
                self.value = current_value
            self.post_message(self.ButtonSpin(number_spinner=self, direction="up", transient_number=current_value))
        else:
            current_value -= 1
            if current_value >= self.min:
                self.value = current_value
            self.post_message(self.ButtonSpin(number_spinner=self, direction="down", transient_number=current_value))

    @on(Input.Changed)
    def _typed_anything(self, event: Input.Changed):
        result = re.sub(r"\D*", "", event.value)
        if len(event.input.value) != len(result):
            event.input.value = result
            event.input.cursor_position -= 1
        else:
            if not self.input.has_focus and self.number_valid():
                self.constrain_value()
            self.post_message(self.NumberChanged(number_spinner=self, number=self.value))

    @on(DescendantBlur, ".num_spin_input")
    def _leave_input(self):
        if not len(self.input.value):
            self.input.value = self.min
        else:
            self.constrain_value()

    def constrain_value(self):
        """
        If the internal value is outside the permitted values then it will be constrained.
        """
        if not len(self.input.value):
            return
        if self.value > self.max:
            self.set_value_no_msg(self.max)
        if self.value < self.min:
            self.set_value_no_msg(self.min)
        self.input.cursor_position = len(self.input.value)

    def set_value_no_msg(self, value: int):
        self.input.value = str(value)

    @property
    def value(self):
        try:
            return int(self.input.value)
        except ValueError:
            return self.min

    @value.setter
    def value(self, value: int):
        self.input.value = str(value)
        self.post_message(self.NumberChanged(number_spinner=self, number=self.value))

    def number_valid(self):
        return self.min <= self.value <= self.max


class DateTuple(NamedTuple):
    year: int
    month: int
    day: int


class BasicDatePicker(Grid):
    label = reactive("Input")

    @dataclass
    class Changed(Message):
        date_picker: "BasicDatePicker"
        date_part: str
        value: int

        @property
        def control(self) -> "BasicDatePicker":
            return self.date_picker

    def __init__(self, label: str, min_year: int = 2010, initial_value: Optional[date] = None, id_: str | None = None,
                 disabled=False):
        if id_ is not None:
            super().__init__(id=id_, disabled=disabled)
        else:
            super().__init__()
        self.label = label

        init_day = initial_value.day if initial_value is not None else date.today().day
        init_month = initial_value.month if initial_value is not None else date.today().month
        init_year = initial_value.year if initial_value is not None else date.today().year

        self.day = NumberSpinner(1, 31, init_day, classes="day")
        self.month = NumberSpinner(1, 12, init_month, classes="month")
        self.year = NumberSpinner(min_year, date.today().year + 1, init_year, classes="year")

    def compose(self) -> ComposeResult:
        yield Label(self.label, classes="form_label")
        with Horizontal():
            yield self.day
            yield self.month
            yield self.year

    @property
    def highest_day(self):
        if self.month.value > 12:
            self.month.value = 12
        return monthrange(self.year.value, self.month.value)[1]

    @on(NumberSpinner.ButtonSpin)
    def _on_spin(self, event: NumberSpinner.ButtonSpin):
        spinner = event.number_spinner
        if spinner.has_class("year"):
            return
        if spinner.has_class("month") and event.transient_number > spinner.max and self.year.value <= self.year.max:
            self.year.value += 1
            self.month.value = self.month.min
        elif spinner.has_class("day") and self.month.value == 12 and event.transient_number == self.highest_day + 1:
            self.month.value = 1
            self.day.value = 1
            self.year.value += 1
        elif spinner.has_class("month") and event.transient_number < spinner.min and self.year.value >= self.year.min:
            self.year.value -= 1
            self.month.value = self.month.max
        elif spinner.has_class("day") and event.transient_number > spinner.max and self.month.value <= self.month.max:
            self.month.value += 1
            self.day.value = self.day.min
        elif spinner.has_class("day") and event.transient_number == 0 and self.month.value == 1:
            if self.year.value != self.year.min:
                self.month.value = 12
                self.year.value -= 1
                self.day.value = self.day.max
            else:
                self.month.value = 1
                self.day.value = 1
        elif spinner.has_class("day") and event.transient_number < spinner.min and self.month.value >= self.month.min:
            self.month.value -= 1
            self.day.value = self.day.max

    @on(NumberSpinner.NumberChanged)
    def _on_change(self, event: NumberSpinner.NumberChanged):
        if event.number_spinner.has_class("day"):
            date_part = "day"
        elif event.number_spinner.has_class("month"):
            date_part = "month"
        else:
            date_part = "year"
        self.post_message(self.Changed(self, date_part, event.number))

    @on(NumberSpinner.NumberChanged, ".month,.year")
    def validate(self):
        self.day.max = self.highest_day
        self.day.constrain_value()

    @property
    def date(self):
        try:
            return date(self.year.value, self.month.value, self.day.value)
        except ValueError:
            return None

    @date.setter
    def date(self, value: Union[date, DateTuple]):
        self.day.value = value.day
        self.month.value = value.month
        self.year.value = value.year
