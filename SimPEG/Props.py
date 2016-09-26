from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import properties
import numpy as np

from . import Maps
from . import Utils


class Mapping(properties.Property):

    info_text = 'a SimPEG Map'

    @property
    def prop(self):
        return getattr(self, '_prop', None)

    @prop.setter
    def prop(self, value):
        assert isinstance(value, PhysicalProperty)
        value._mapping = self  # Skip the setter
        self._prop = value

    @property
    def reciprocal(self):
        if self.prop and self.prop.reciprocal:
            return self.prop.reciprocal.mapping

    @property
    def reciprocal_prop(self):
        if self.prop and self.prop.reciprocal:
            return self.prop.reciprocal

    def clear_props(self, instance):
        if self.prop:
            instance._set(self.prop.name, None)
        if self.reciprocal_prop:
            instance._set(self.reciprocal_prop.name, None)
        if self.reciprocal:
            instance._set(self.reciprocal.name, None)

    def validate(self, instance, value):
        if value is None:
            return None
        if not isinstance(value, Maps.IdentityMap):
            self.error(instance, value)
        return value

    def get_property(self):

        scope = self

        def fget(self):
            value = self._get(scope.name)
            if value is not None:
                return value
            if scope.reciprocal is None:
                return None
            reciprocal = self._get(scope.reciprocal.name)
            if reciprocal is None:
                return None
            return Maps.ReciprocalMap() * reciprocal

        def fset(self, value):
            value = scope.validate(self, value)
            self._set(scope.name, value)
            scope.clear_props(self)

        return property(fget=fget, fset=fset, doc=scope.help)


class PhysicalProperty(properties.Property):

    info_text = 'a physical property'

    @property
    def mapping(self):
        return getattr(self, '_mapping', None)

    @mapping.setter
    def mapping(self, value):
        assert isinstance(value, Mapping)
        value._prop = self  # Skip the setter
        self._mapping = value

    reciprocal = None

    def clear_mappings(self, instance):
        if self.mapping:
            instance._set(self.mapping.name, None)
        if not self.reciprocal:
            return
        instance._set(self.reciprocal.name, None)
        if self.reciprocal.mapping:
            instance._set(self.reciprocal.mapping.name, None)

    def validate(self, instance, value):
        if value is None:
            return None
        assert isinstance(value, np.ndarray), (
            "Physical properties must be numpy arrays."
        )
        return value

    def get_property(self):

        scope = self

        def fget(self):
            default = self._get(scope.name)
            if default is not None:
                return default
            if scope.reciprocal:
                default = self._get(scope.reciprocal.name)
                if default is not None:
                    return 1.0 / default
            if scope.mapping is None and scope.reciprocal is None:
                return None
            if scope.mapping is None:
                return 1.0 / getattr(self, scope.reciprocal.name)
                return 'fun'

            mapping = getattr(self, scope.mapping.name)
            return mapping * self.model

        def fset(self, value):
            value = scope.validate(self, value)
            self._set(scope.name, value)
            scope.clear_mappings(self)

        return property(fget=fget, fset=fset, doc=scope.help)


class Derivative(properties.GettableProperty):

    physical_property = None

    @property
    def mapping(self):
        """The mapping looks through to the physical property map."""
        if self.physical_property is None:
            return None
        return self.physical_property.mapping

    def get_property(self):

        scope = self

        def fget(self):
            if scope.physical_property is None:
                return Utils.Zero()
            if scope.mapping is None:
                return Utils.Zero()
            mapping = getattr(self, scope.mapping.name)
            if mapping is None:
                return Utils.Zero()

            return mapping.deriv(self.model)

        return property(fget=fget, doc=scope.help)


def Invertible(help):

    mapping = Mapping(
        "Mapping of {} to the inversion model.".format(help)
    )

    physical_property = PhysicalProperty(
        help,
        mapping=mapping
    )

    property_derivative = Derivative(
        "Derivative of {} wrt the model.".format(help),
        physical_property=physical_property
    )

    return physical_property, mapping, property_derivative


def Reciprocal(prop1, prop2):
    prop1.reciprocal = prop2
    prop2.reciprocal = prop1


class BaseSimPEG(properties.HasProperties()):
    pass
