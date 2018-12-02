# -*- coding: utf-8 -*-
import inspect
from typing import Optional, Any, List, Text, Dict, Union

from prompt_toolkit.layout import FormattedTextControl
from prompt_toolkit.validation import Validator, ValidationError

from questionary.constants import (SELECTED_POINTER, INDICATOR_SELECTED,
                                   INDICATOR_UNSELECTED)


class Choice(object):

    def __init__(self,
                 title: Text,
                 value: Any,
                 disabled: Optional[Text] = None,
                 is_initially_selected: bool = False,
                 shortcut_key: Optional[Text] = None):
        self.disabled = disabled
        self.value = value
        self.title = title
        self.is_initially_selected = is_initially_selected

        if shortcut_key is not None:
            self.shortcut_key = str(shortcut_key)
        else:
            self.shortcut_key = None

    @staticmethod
    def build(c: Union[Text, 'Choice', Dict[Text, Any]]) -> 'Choice':
        """Create a choice object from different representations."""

        if isinstance(c, Choice):
            return c
        elif isinstance(c, str):
            return Choice(c, c)
        else:
            return Choice(c.get('name'),
                          c.get('value', c.get('name')),
                          c.get('disabled', None),
                          c.get('checked'),
                          c.get('key'))


class Separator(Choice):
    """Used to space/separate choices group."""

    default_separator = '-' * 15

    def __init__(self, line: Optional[Text] = None):
        self.line = line or self.default_separator
        super(Separator, self).__init__(self.line, None, "-")


class InquirerControl(FormattedTextControl):
    SHORTCUT_KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
                     'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j',
                     'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
                     'u', 'v', 'w', 'x', 'y', 'z']

    def __init__(self,
                 choices: List[Union[Text, Choice, Dict[Text, Any]]],
                 default: Optional[Any] = None,
                 use_indicator: bool = True,
                 use_shortcuts: bool = False,
                 **kwargs):

        self.use_indicator = use_indicator
        self.use_shortcuts = use_shortcuts
        self.default = default

        self.pointed_at = None
        self.is_answered = False
        self.choices = []
        self.selected_options = []

        self._init_choices(choices, default)
        self._assign_shortcut_keys()

        super(InquirerControl, self).__init__(self._get_choice_tokens,
                                              **kwargs)

    def _is_selected(self, choice):
        return ((choice.is_initially_selected or
                 choice.value == self.default and
                 self.default is not None) and
                not choice.disabled)

    def _assign_shortcut_keys(self):
        available_shortcuts = self.SHORTCUT_KEYS[:]

        # first, make sure we do not double assign a shortcut
        for c in self.choices:
            if c.shortcut_key is not None:
                if c.shortcut_key in available_shortcuts:
                    available_shortcuts.remove(c.shortcut_key)
                else:
                    raise ValueError("Invalid shortcut '{}'"
                                     "for choice '{}'. Shortcuts "
                                     "should be single characters or numbers. "
                                     "Make sure that all your shortcuts are "
                                     "unique.".format(c.shortcut_key, c.title))

        shortcut_idx = 0
        for c in self.choices:
            if c.shortcut_key is None and not c.disabled:
                c.shortcut_key = available_shortcuts[shortcut_idx]
                shortcut_idx += 1

            if shortcut_idx == len(available_shortcuts):
                break  # fail gracefully if we run out of shortcuts

    def _init_choices(self, choices, default=None):
        # helper to convert from question format to internal format
        self.choices = []

        for i, c in enumerate(choices):
            choice = Choice.build(c)

            if self._is_selected(choice):
                self.selected_options.append(choice.value)

            if self.pointed_at is None and not choice.disabled:
                # find the first (available) choice
                self.pointed_at = i

            self.choices.append(choice)

    @property
    def choice_count(self):
        return len(self.choices)

    def _get_choice_tokens(self):
        tokens = []

        def append(index, choice):
            # use value to check if option has been selected
            selected = (choice.value in self.selected_options)

            if index == self.pointed_at:
                tokens.append(("class:pointer",
                               " {} ".format(SELECTED_POINTER)))
                tokens.append(("[SetCursorPosition]", ""))
            else:
                tokens.append(("", "   "))

            if isinstance(choice, Separator):
                tokens.append(("class:separator", "{}".format(choice.title)))
            elif choice.disabled:  # disabled
                tokens.append(("class:selected" if selected else "",
                               "- {} ({})".format(choice.title,
                                                  choice.disabled)))
            else:
                if self.use_shortcuts and choice.shortcut_key is not None:
                    shortcut = "{}) ".format(choice.shortcut_key)
                else:
                    shortcut = ""

                if selected:
                    if self.use_indicator:
                        indicator = INDICATOR_SELECTED + " "
                    else:
                        indicator = ""

                    tokens.append(("class:selected",
                                   "{}{}{}".format(indicator,
                                                   shortcut,
                                                   choice.title)))
                else:
                    if self.use_indicator:
                        indicator = INDICATOR_UNSELECTED + " "
                    else:
                        indicator = ""

                    tokens.append(("",
                                   "{}{}{}".format(indicator,
                                                   shortcut,
                                                   choice.title)))

            tokens.append(("", "\n"))

        # prepare the select choices
        for i, c in enumerate(self.choices):
            append(i, c)

        if self.use_shortcuts:
            tokens.append(("",
                           '  Answer: {}'
                           ''.format(self.get_pointed_at().shortcut_key)))
        else:
            tokens.pop()  # Remove last newline.
        return tokens

    def is_selection_a_separator(self):
        selected = self.choices[self.pointed_at]
        return isinstance(selected, Separator)

    def is_selection_disabled(self):
        return self.choices[self.pointed_at].disabled

    def is_selection_valid(self):
        return (not self.is_selection_disabled() and
                not self.is_selection_a_separator())

    def select_previous(self):
        self.pointed_at = (
                (self.pointed_at - 1) % self.choice_count)

    def select_next(self):
        self.pointed_at = (
                (self.pointed_at + 1) % self.choice_count)

    def get_pointed_at(self):
        return self.choices[self.pointed_at]

    def get_selected_values(self):
        # get values not labels
        return [c
                for c in self.choices
                if (not isinstance(c, Separator) and
                    c.value in self.selected_options)]


def build_validator(validate) -> Optional[Validator]:
    if validate:
        if inspect.isclass(validate) and issubclass(validate, Validator):
            return validate()
        elif callable(validate):
            class _InputValidator(Validator):
                def validate(self, document):
                    verdict = validate(document.text)
                    if verdict is not True:
                        if verdict is False:
                            verdict = 'invalid input'
                        raise ValidationError(
                            message=verdict,
                            cursor_position=len(document.text))

            return _InputValidator()
    return None