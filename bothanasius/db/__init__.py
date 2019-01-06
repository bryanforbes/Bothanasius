from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Union, List

import re
import pendulum
import datetime
from sqlalchemy import types
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql.base import ischema_names, PGTypeCompiler
from sqlalchemy.sql import expression

if TYPE_CHECKING:
    DateTimeBase = types.TypeDecorator[pendulum.DateTime]
    LtreeBase = types.UserDefinedType['Ltree']
    LQUERYBase = types.TypeEngine[str]
    LTXTQUERYBase = types.TypeEngine[str]
else:
    DateTimeBase = types.TypeDecorator
    LtreeBase = types.UserDefinedType
    LQUERYBase = types.TypeEngine
    LTXTQUERYBase = types.TypeEngine


class DateTime(DateTimeBase):
    impl = types.DateTime

    def process_bind_param(
        self, value: Optional[pendulum.DateTime], dialect: Any
    ) -> Optional[datetime.datetime]:
        return (
            datetime.datetime.fromtimestamp(value.int_timestamp)
            if value is not None
            else value
        )

    def process_result_value(
        self, value: Optional[datetime.datetime], dialect: Any
    ) -> Optional[pendulum.DateTime]:
        return pendulum.instance(value, 'local') if value is not None else value


path_matcher = re.compile(r'^[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)*$')


class Ltree(object):
    """
    Ltree class wraps a valid string label path. It provides various
    convenience properties and methods.

    ::

        from sqlalchemy_utils import Ltree

        Ltree('1.2.3').path  # '1.2.3'


    Ltree always validates the given path.

    ::

        Ltree(None)  # raises TypeError

        Ltree('..')  # raises ValueError


    Validator is also available as class method.

    ::

        Ltree.validate('1.2.3')
        Ltree.validate(None)  # raises ValueError


    Ltree supports equality operators.

    ::

        Ltree('Countries.Finland') == Ltree('Countries.Finland')
        Ltree('Countries.Germany') != Ltree('Countries.Finland')


    Ltree objects are hashable.


    ::

        assert hash(Ltree('Finland')) == hash('Finland')


    Ltree objects have length.

    ::

        assert len(Ltree('1.2'))  2
        assert len(Ltree('some.one.some.where'))  # 4


    You can easily find subpath indexes.

    ::

        assert Ltree('1.2.3').index('2.3') == 1
        assert Ltree('1.2.3.4.5').index('3.4') == 2


    Ltree objects can be sliced.


    ::

        assert Ltree('1.2.3')[0:2] == Ltree('1.2')
        assert Ltree('1.2.3')[1:] == Ltree('2.3')


    Finding longest common ancestor.


    ::

        assert Ltree('1.2.3.4.5').lca('1.2.3', '1.2.3.4', '1.2.3') == '1.2'
        assert Ltree('1.2.3.4.5').lca('1.2', '1.2.3') == '1'


    Ltree objects can be concatenated.

    ::

        assert Ltree('1.2') + Ltree('1.2') == Ltree('1.2.1.2')
    """

    path: List[str]

    def __init__(
        self, path_or_ltree: Union[Ltree, str, List[str]]  # noqa: F821
    ) -> None:
        if isinstance(path_or_ltree, Ltree):
            self.path = path_or_ltree.path
        else:
            if isinstance(path_or_ltree, str):
                path_or_ltree = path_or_ltree.split('.')

            if not isinstance(path_or_ltree, list):
                raise TypeError(
                    "Ltree() argument must be a string, list of strings, or an Ltree, "
                    "not '{0}'".format(type(path_or_ltree).__name__)
                )

            self.validate('.'.join(path_or_ltree))
            self.path = path_or_ltree

    @classmethod
    def validate(cls, path: str) -> None:
        if path_matcher.match(path) is None:
            raise ValueError("'{0}' is not a valid ltree path.".format(path))

    def __len__(self) -> int:
        return len(self.path)

    def index(self, other: Union[Ltree, str, List[str]]) -> int:  # noqa: F821
        subpath = Ltree(other).path
        for index, _ in enumerate(self.path):
            if self.path[index : len(subpath) + index] == subpath:
                return index
        raise ValueError('subpath not found')

    def descendant_of(self, other: Union[Ltree, str, List[str]]) -> bool:  # noqa: F821
        """
        is left argument a descendant of right (or equal)?

        ::

            assert Ltree('1.2.3.4.5').descendant_of('1.2.3')
        """
        subpath = self[: len(Ltree(other))]
        return subpath == other

    def ancestor_of(self, other: Union[Ltree, str, List[str]]) -> bool:  # noqa: F821
        """
        is left argument an ancestor of right (or equal)?

        ::

            assert Ltree('1.2.3').ancestor_of('1.2.3.4.5')
        """
        subpath = Ltree(other)[: len(self)]
        return subpath == self

    def __getitem__(self, key: Union[int, slice]) -> Ltree:  # noqa: F821
        if isinstance(key, (int, slice)):
            return Ltree(self.path[key])

        raise TypeError(
            'Ltree indices must be integers, not {0}'.format(key.__class__.__name__)
        )

    def lca(
        self, *others: Union[Ltree, str, List[str]]  # noqa: F821
    ) -> Optional[Ltree]:  # noqa: F821
        """
        Lowest common ancestor, i.e., longest common prefix of paths

        ::

            assert Ltree('1.2.3.4.5').lca('1.2.3', '1.2.3.4', '1.2.3') == '1.2'
        """
        other_parts = [Ltree(other).path for other in others]
        for index, element in enumerate(self.path):
            if any(
                (
                    other[index] != element or len(other) <= index + 1
                    for other in other_parts
                )
            ):
                if index == 0:
                    return None
                return Ltree(self.path[0:index])
        return None

    def __add__(self, other: Union[Ltree, str, List[str]]) -> Ltree:  # noqa: F821
        return Ltree(self.path + Ltree(other).path)

    def __radd__(self, other: Union[Ltree, str, List[str]]) -> Ltree:  # noqa: F821
        return Ltree(other) + self

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Ltree):
            return self.path == other.path
        elif isinstance(other, (str, list)):
            return self.path == other
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash(self.path)

    def __ne__(self, other: Any) -> bool:
        return not (self == other)

    def __repr__(self) -> str:
        return '%s(%r)' % (self.__class__.__name__, self.path)

    def __unicode__(self) -> str:
        return '.'.join(self.path)

    def __str__(self) -> str:
        return self.__unicode__()

    def __contains__(self, label: str) -> bool:
        return label in self.path


class LtreeType(types.Concatenable, LtreeBase):
    """Postgresql LtreeType type.

    The LtreeType datatype can be used for representing labels of data stored
    in hierarchial tree-like structure. For more detailed information please
    refer to http://www.postgresql.org/docs/current/static/ltree.html

    ::

        from sqlalchemy_utils import LtreeType


        class DocumentSection(Base):
            __tablename__ = 'document_section'
            id = sa.Column(sa.Integer, autoincrement=True)
            path = sa.Column(LtreeType)


        section = DocumentSection(name='Countries.Finland')
        session.add(section)
        session.commit()

        section.path  # Ltree('Countries.Finland')


    .. note::
        Using :class:`LtreeType`, :class:`LQUERY` and :class:`LTXTQUERY` types
        may require installation of Postgresql ltree extension on the server
        side. Please visit http://www.postgres.org for details.
    """

    class comparator_factory(types.Concatenable.Comparator):  # type: ignore
        def ancestor_of(self, other: Any) -> Any:
            if isinstance(other, list):
                return self.op('@>')(expression.cast(other, ARRAY(LtreeType)))
            else:
                return self.op('@>')(other)

        def descendant_of(self, other: Any) -> Any:
            if isinstance(other, list):
                return self.op('<@')(expression.cast(other, ARRAY(LtreeType)))
            else:
                return self.op('<@')(other)

        def lquery(self, other: Any) -> Any:
            if isinstance(other, list):
                return self.op('?')(expression.cast(other, ARRAY(LQUERY)))
            else:
                return self.op('~')(other)

        def ltxtquery(self, other: Any) -> Any:
            return self.op('@')(other)

    def bind_processor(self, dialect: Any) -> Any:
        def process(value: Any) -> Any:
            if value:
                return value.path

        return process

    def result_processor(self, dialect: Any, coltype: Any) -> Any:
        def process(value: Any) -> Any:
            return self._coerce(value)

        return process

    def literal_processor(self, dialect: Any) -> Any:
        def process(value: Any) -> Any:
            value = value.replace("'", "''")
            return "'%s'" % value

        return process

    __visit_name__ = 'LTREE'

    def _coerce(self, value: Any) -> Any:
        if value:
            return Ltree(value)

    def coercion_listener(
        self, target: Any, value: Any, oldvalue: Any, initiator: Any
    ) -> Any:
        return self._coerce(value)


class LQUERY(LQUERYBase):
    """Postresql LQUERY type.
    See :class:`LTREE` for details.
    """

    __visit_name__ = 'LQUERY'


class LTXTQUERY(LTXTQUERYBase):
    """Postresql LTXTQUERY type.
    See :class:`LTREE` for details.
    """

    __visit_name__ = 'LTXTQUERY'


ischema_names['ltree'] = LtreeType
ischema_names['lquery'] = LQUERY
ischema_names['ltxtquery'] = LTXTQUERY


def visit_LTREE(self: Any, type_: Any, **kw: Any) -> str:
    return 'LTREE'


def visit_LQUERY(self: Any, type_: Any, **kw: Any) -> str:
    return 'LQUERY'


def visit_LTXTQUERY(self: Any, type_: Any, **kw: Any) -> str:
    return 'LTXTQUERY'


PGTypeCompiler.visit_LTREE = visit_LTREE
PGTypeCompiler.visit_LQUERY = visit_LQUERY
PGTypeCompiler.visit_LTXTQUERY = visit_LTXTQUERY
