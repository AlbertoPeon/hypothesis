# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import django.db.models as dm
import hypothesis.extra.fakefactory as ff
from hypothesis.specifiers import one_of, sampled_from, positive_integers
from hypothesis.extra.datetime import timezone_aware_datetime
from hypothesis.internal.compat import text_type, binary_type
from hypothesis.searchstrategy.strategies import MappedSearchStrategy, \
    strategy

FIELD_MAPPINGS = {
    dm.BigIntegerField: int,
    dm.BinaryField: binary_type,
    dm.BooleanField: bool,
    dm.CharField: text_type,
    dm.DateTimeField: timezone_aware_datetime,
    dm.EmailField: ff.FakeFactory('email'),
    dm.FloatField: float,
    dm.IntegerField: int,
    dm.NullBooleanField: one_of((None, bool)),
    dm.PositiveIntegerField: positive_integers,
    dm.PositiveSmallIntegerField: positive_integers,
}


class ModelNotSupported(Exception):
    pass


def model_to_base_specifier(model):
    result = {}
    for f in model._meta.concrete_fields:
        if isinstance(f, dm.AutoField):
            continue
        if isinstance(f, dm.ForeignKey):
            mapped = f.related.parent_model
        elif getattr(f, 'choices', None):
            options = [
                c for c, _ in f.get_flatchoices()
            ]
            if not f.blank:
                options.remove('')
            mapped = sampled_from(options)
        else:
            try:
                mapped = FIELD_MAPPINGS[type(f)]
            except KeyError:
                if f.null:
                    continue
                else:
                    raise ModelNotSupported((
                        'No mapping defined for field type %s and %s is not '
                        'nullable') % (
                        type(f).__name__, f.name
                    ))
        if f.null:
            mapped = one_of((None, mapped))
        result[f.name] = mapped
    return result


class ModelStrategy(MappedSearchStrategy):

    def __init__(self, model, settings):
        self.model = model
        specifier = model_to_base_specifier(model)
        super(ModelStrategy, self).__init__(
            strategy=strategy(specifier, settings))

    def pack(self, value):
        result = self.model(**value)
        result.save()
        return result


@strategy.extend_static(dm.Model)
def define_model_strategy(model, settings):
    return ModelStrategy(model, settings)
