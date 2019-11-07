# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Outputter to generate Rust code for metrics.
"""

import enum
import json

from . import metrics
from . import util
from collections import defaultdict


def rust_datatypes_filter(value):
    """
    A Jinja2 filter that renders Rust literals.
    """

    class RustEncoder(json.JSONEncoder):
        def iterencode(self, value):
            if isinstance(value, list):
                yield "vec!["
                first = True
                for subvalue in value:
                    if not first:
                        yield ", "
                    yield from self.iterencode(subvalue)
                    first = False
                yield "]"
            elif isinstance(value, dict):
                raise NotImplementedError
            elif isinstance(value, enum.Enum):
                yield (f"{value.__class__.__name__}::{util.Camelize(value.name)}")
            elif isinstance(value, set):
                raise NotImplementedError
            elif isinstance(value, str):
                yield from super().iterencode(value)
                yield ".to_string()"
            else:
                yield from super().iterencode(value)

    return "".join(RustEncoder().iterencode(value))


def type_name(obj):
    """
    Returns the Rust type to use for a given metric or ping object.
    """
    return class_name(obj.type)


def class_name(obj_type):
    """
    Returns the Rust class name for a given metric or ping type.
    """
    if obj_type == "ping":
        raise NotImplementedError
    if obj_type.startswith("labeled_"):
        raise NotImplementedError
    return f"{util.Camelize(obj_type)}Metric"


def output_rust(objs, output_dir, options={}):
    """
    Given a tree of objects, output Rust code to `output_dir`.

    :param objects: A tree of objects (metrics and pings) as returned from
    `parser.parse_objects`.
    :param output_dir: Path to an output directory to write to.
    """
    template = util.get_jinja2_template(
        "rust.jinja2",
        filters=(
            ("rust", rust_datatypes_filter),
            ("type_name", type_name),
            ("class_name", class_name),
        ),
    )

    # The object parameters to pass to constructors
    extra_args = [
        "allowed_extra_keys",
        "bucket_count",
        "category",
        "denominator",
        "disabled",
        "histogram_type",
        "include_client_id",
        "lifetime",
        "memory_unit",
        "name",
        "range_max",
        "range_min",
        "send_in_pings",
        "time_unit",
        "values",
    ]

    # Since rust can declare packages and sub-packages inline,
    # we just output everything into one big file. This makes
    # it easy to deal with in cargo build scripts.
    filepath = output_dir / "metrics.rs"

    obj_types = []
    has_labeled_metrics = False

    for category_key, category_val in objs.items():

        obj_types.extend(set(class_name(obj.type) for obj in category_val.values()))
        has_labeled_metrics = has_labeled_metrics or any(
            getattr(metric, "labeled", False) for metric in category_val.values()
        )

    if has_labeled_metrics:
        raise NotImplementedError

    with open(filepath, "w", encoding="utf-8") as fd:
        import sys; print("OBJS", objs, file=sys.stderr)
        fd.write(
            template.render(
                categories=objs,
                obj_types=obj_types,
            )
        )
        # Jinja2 squashes the final newline, so we explicitly add it
        fd.write("\n")
