import json
from datetime import datetime
from typing import Literal

import pytest

from chatkit.server import diff_widget
from chatkit.types import WidgetItem
from chatkit.widgets import Card, Text, WidgetRoot


@pytest.mark.parametrize(
    "before, after, expected",
    [
        (Card(children=[]), Card(children=[]), []),
        (
            Card(children=[Text(id="text", value="Hello", streaming=True)]),
            Card(children=[Text(id="text", value="Hello, world!", streaming=True)]),
            ["widget.streaming_text.value_delta"],
        ),
        (
            Card(children=[Text(id="text", value="Hello", streaming=True)]),
            Card(children=[Text(id="text", value="Hello, world!", streaming=False)]),
            ["widget.root.updated"],
        ),
        (
            Card(children=[Text(value="Hello")]),
            Card(children=[Text(value="world!")]),
            ["widget.root.updated"],
        ),
    ],
)
def test_diff(
    before: WidgetRoot,
    after: WidgetRoot,
    expected: list[
        Literal[
            "widget.streaming_text.value_delta",
            "widget.root.updated",
        ]
    ],
):
    diff = diff_widget(before, after)
    assert len(diff) == len(expected)
    for i in range(len(diff)):
        assert diff[i].type == expected[i]


def test_json_dump_excludes_none_fields():
    widget = Card(children=[Text(value="Hello")])

    json_str = widget.model_dump_json()
    assert isinstance(json_str, str)
    data = json.loads(json_str)

    # Top-level widget should include type and exclude None-valued fields.
    assert data["type"] == "Card"
    assert "key" not in data
    assert "padding" not in data
    assert "status" not in data
    assert "collapsed" not in data

    # Children should be serialized with None fields omitted as well.
    assert isinstance(data["children"], list)
    assert len(data["children"]) == 1

    text_dump = data["children"][0]
    assert text_dump["type"] == "Text"
    assert text_dump["value"] == "Hello"
    assert "italic" not in text_dump
    assert "streaming" not in text_dump
    assert "color" not in text_dump
    assert "key" not in text_dump


def test_json_dump_excludes_none_fields_nested():
    widget = Card(children=[Text(value="Hello")])
    widget_item = WidgetItem(
        thread_id="1", widget=widget, id="1", created_at=datetime.now()
    )

    json_str = widget_item.model_dump_json()
    assert isinstance(json_str, str)
    data = json.loads(json_str)

    # Top-level widget should include type and exclude None-valued fields.
    widget_dump = data["widget"]
    assert widget_dump["type"] == "Card"
    assert "key" not in widget_dump
    assert "padding" not in widget_dump
    assert "status" not in widget_dump
    assert "collapsed" not in widget_dump

    # Children should be serialized with None fields omitted as well.
    assert isinstance(widget_dump["children"], list)
    assert len(widget_dump["children"]) == 1

    text_dump = widget_dump["children"][0]
    assert text_dump["type"] == "Text"
    assert text_dump["value"] == "Hello"
    assert "italic" not in text_dump
    assert "streaming" not in text_dump
    assert "color" not in text_dump
    assert "key" not in text_dump
