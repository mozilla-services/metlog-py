"""
This module provides a DottedNameResolver from pyramid.path

Some parts of pyramid.path were removed to minimize the list of
dependencies.
"""

"""
  License:

  A copyright notice accompanies this license document that identifies
  the copyright holders.

  Redistribution and use in source and binary forms, with or without
  modification, are permitted provided that the following conditions are
  met:

  1.  Redistributions in source code must retain the accompanying
      copyright notice, this list of conditions, and the following
      disclaimer.

  2.  Redistributions in binary form must reproduce the accompanying
      copyright notice, this list of conditions, and the following
      disclaimer in the documentation and/or other materials provided
      with the distribution.

  3.  Names of the copyright holders must not be used to endorse or
      promote products derived from this software without prior
      written permission from the copyright holders.

  4.  If any files are modified, you must cause the modified files to
      carry prominent notices stating that you changed the files and
      the date of any change.

  Disclaimer

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ``AS IS'' AND
    ANY EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
    TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
    PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
    HOLDERS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
    EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
    TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
    DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
    ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
    TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF
    THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
    SUCH DAMAGE.
"""

import os
import pkg_resources
import sys
import imp

ignore_types = [imp.C_EXTENSION, imp.C_BUILTIN]
init_names = ['__init__%s' % x[0] for x in imp.get_suffixes() if
               x[0] and x[2] not in ignore_types]


def caller_path(path, level=2):
    if not os.path.isabs(path):
        module = caller_module(level + 1)
        prefix = package_path(module)
        path = os.path.join(prefix, path)
    return path


def caller_module(level=2, sys=sys):
    module_globals = sys._getframe(level).f_globals
    module_name = module_globals.get('__name__') or '__main__'
    module = sys.modules[module_name]
    return module


def package_name(pkg_or_module):
    """ If this function is passed a module, return the dotted Python
    package name of the package in which the module lives.  If this
    function is passed a package, return the dotted Python package
    name of the package itself."""
    if pkg_or_module is None or pkg_or_module.__name__ == '__main__':
        return '__main__'
    pkg_filename = pkg_or_module.__file__
    pkg_name = pkg_or_module.__name__
    splitted = os.path.split(pkg_filename)
    if splitted[-1] in init_names:
        # it's a package
        return pkg_name
    return pkg_name.rsplit('.', 1)[0]


def package_of(pkg_or_module):
    """ Return the package of a module or return the package itself """
    pkg_name = package_name(pkg_or_module)
    __import__(pkg_name)
    return sys.modules[pkg_name]


def caller_package(level=2, caller_module=caller_module):
    # caller_module in arglist for tests
    module = caller_module(level + 1)
    f = getattr(module, '__file__', '')
    if (('__init__.py' in f) or ('__init__$py' in f)):  # empty at >>>
        # Module is a package
        return module
    # Go up one level to get package
    package_name = module.__name__.rsplit('.', 1)[0]
    return sys.modules[package_name]


def package_path(package):
    # computing the abspath is actually kinda expensive so we memoize
    # the result
    prefix = getattr(package, '__abspath__', None)
    if prefix is None:
        prefix = pkg_resources.resource_filename(package.__name__, '')
        # pkg_resources doesn't care whether we feed it a package
        # name or a module name within the package, the result
        # will be the same: a directory name to the package itself
        try:
            package.__abspath__ = prefix
        except:
            # this is only an optimization, ignore any error
            pass
    return prefix


class _CALLER_PACKAGE(object):
    def __repr__(self):  # pragma: no cover (for docs)
        return 'pyramid.path.CALLER_PACKAGE'


CALLER_PACKAGE = _CALLER_PACKAGE()


class Resolver(object):
    def __init__(self, package=CALLER_PACKAGE):
        if package in (None, CALLER_PACKAGE):
            self.package = package
        else:
            if isinstance(package, basestring):
                try:
                    __import__(package)
                except ImportError:
                    raise ValueError(
                        'The dotted name %r cannot be imported' % (package,)
                        )
                package = sys.modules[package]
            self.package = package_of(package)

    def get_package_name(self):
        if self.package is CALLER_PACKAGE:
            package_name = caller_package().__name__
        else:
            package_name = self.package.__name__
        return package_name

    def get_package(self):
        if self.package is CALLER_PACKAGE:
            package = caller_package()
        else:
            package = self.package
        return package


class DottedNameResolver(Resolver):
    """ A class used to resolve a :term:`dotted Python name` to a package or
    module object.

    .. note:: This API is new as of Pyramid 1.3.

    The constructor accepts a single argument named ``package`` which may be
    any of:

    - A fully qualified (not relative) dotted name to a module or package

    - a Python module or package object

    - The value ``None``

    - The constant value :attr:`pyramid.path.CALLER_PACKAGE`.

    The default value is :attr:`pyramid.path.CALLER_PACKAGE`.

    The ``package`` is used when a relative dotted name is supplied to the
    :meth:`~pyramid.path.DottedNameResolver.resolve` method.  A dotted name
    which has a ``.`` (dot) or ``:`` (colon) as its first character is
    treated as relative.

    If the value ``None`` is supplied as the ``package``, the resolver will
    only be able to resolve fully qualified (not relative) names.  Any
    attempt to resolve a relative name when the ``package`` is ``None`` will
    result in an :exc:`ValueError` exception.

    If the value :attr:`pyramid.path.CALLER_PACKAGE` is supplied as the
    ``package``, the resolver will treat relative dotted names as relative to
    the caller of the :meth:`~pyramid.path.DottedNameResolver.resolve`
    method.

    If a *module* or *module name* (as opposed to a package or package name)
    is supplied as ``package``, its containing package is computed and this
    package used to derive the package name (all names are resolved relative
    to packages, never to modules).  For example, if the ``package`` argument
    to this type was passed the string ``xml.dom.expatbuilder``, and
    ``.mindom`` is supplied to the
    :meth:`~pyramid.path.DottedNameResolver.resolve` method, the resulting
    import would be for ``xml.minidom``, because ``xml.dom.expatbuilder`` is
    a module object, not a package object.

    If a *package* or *package name* (as opposed to a module or module name)
    is supplied as ``package``, this package will be used to relative compute
    dotted names.  For example, if the ``package`` argument to this type was
    passed the string ``xml.dom``, and ``.minidom`` is supplied to the
    :meth:`~pyramid.path.DottedNameResolver.resolve` method, the resulting
    import would be for ``xml.minidom``.
    """
    def resolve(self, dotted):
        """
        This method resolves a dotted name reference to a global Python
        object (an object which can be imported) to the object itself.

        Two dotted name styles are supported:

        - ``pkg_resources``-style dotted names where non-module attributes
          of a package are separated from the rest of the path using a ``:``
          e.g. ``package.module:attr``.

        - ``zope.dottedname``-style dotted names where non-module
          attributes of a package are separated from the rest of the path
          using a ``.`` e.g. ``package.module.attr``.

        These styles can be used interchangeably.  If the supplied name
        contains a ``:`` (colon), the ``pkg_resources`` resolution
        mechanism will be chosen, otherwise the ``zope.dottedname``
        resolution mechanism will be chosen.

        If the ``dotted`` argument passed to this method is not a string, a
        :exc:`ValueError` will be raised.

        When a dotted name cannot be resolved, a :exc:`ValueError` error is
        raised.

        Example:

        .. code-block:: python

           r = DottedNameResolver()
           v = r.resolve('xml') # v is the xml module

        """
        if not isinstance(dotted, basestring):
            raise ValueError('%r is not a string' % (dotted,))
        package = self.package
        if package is CALLER_PACKAGE:
            package = caller_package()
        return self._resolve(dotted, package)

    def maybe_resolve(self, dotted):
        """
        This method behaves just like
        :meth:`~pyramid.path.DottedNameResolver.resolve`, except if the
        ``dotted`` value passed is not a string, it is simply returned.  For
        example:

        .. code-block:: python

           import xml
           r = DottedNameResolver()
           v = r.maybe_resolve(xml)
           # v is the xml module; no exception raised
        """
        if isinstance(dotted, basestring):
            package = self.package
            if package is CALLER_PACKAGE:
                package = caller_package()
            return self._resolve(dotted, package)
        return dotted

    def _resolve(self, dotted, package):
        if ':' in dotted:
            return self._pkg_resources_style(dotted, package)
        else:
            return self._zope_dottedname_style(dotted, package)

    def _pkg_resources_style(self, value, package):
        """ package.module:attr style """
        if value.startswith('.') or value.startswith(':'):
            if not package:
                raise ValueError(
                    'relative name %r irresolveable without package' % (value,)
                    )
            if value in ['.', ':']:
                value = package.__name__
            else:
                value = package.__name__ + value
        return pkg_resources.EntryPoint.parse(
            'x=%s' % value).load(False)

    def _zope_dottedname_style(self, value, package):
        """ package.module.attr style """
        module = getattr(package, '__name__', None)  # package may be None
        if not module:
            module = None
        if value == '.':
            if module is None:
                raise ValueError(
                    'relative name %r irresolveable without package' % (value,)
                )
            name = module.split('.')
        else:
            name = value.split('.')
            if not name[0]:
                if module is None:
                    raise ValueError(
                        'relative name %r irresolveable without '
                        'package' % (value,)
                        )
                module = module.split('.')
                name.pop(0)
                while not name[0]:
                    module.pop()
                    name.pop(0)
                name = module + name

        used = name.pop(0)
        found = __import__(used)
        for n in name:
            used += '.' + n
            try:
                found = getattr(found, n)
            except AttributeError:
                __import__(used)
                found = getattr(found, n)  # pragma: no cover

        return found


def resolve_name(name, package=None):
    """Resolve dotted name into a python object.

    This function resolves a dotted name as a reference to a python object,
    returning whatever object happens to live at that path.  It's a simple
    convenience wrapper around pyramid's DottedNameResolver.

    The optional argument 'package' specifies the package name for relative
    imports.  If not specified, only absolute paths will be supported.
    """
    return DottedNameResolver(package).resolve(name)
