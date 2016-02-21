# Copyright (c) 2016 Mert Bora ALPER <bora@boramalper.org>

from collections import OrderedDict, Counter
import collections.abc as abc
import inspect
import typing


class AmbiguousMethods(Exception):
    pass


class NoApplicableMethods(Exception):
    pass


class _RegistryEntry:
    def __init__(self, function,
                 is_method,
                 parameters,
                 standard_pars, standard_default,
                 allow_keyword,
                 keyword_pars, keyword_default):

        self.function = function
        self.is_method = is_method
        self.parameters = parameters
        self.standard_pars = standard_pars
        self.standard_default = standard_default
        self.allow_keyword = allow_keyword
        self.keyword_pars = keyword_pars
        self.keyword_default = keyword_default


class _Registry:
    def __init__(self):
        self.registry = {}

    def register(self, entry):
        if entry.function.__qualname__ not in self.registry:
            self.registry[entry.function.__qualname__] = []

        self.registry[entry.function.__qualname__].append(entry)

    def __getitem__(self, function_name):
        return self.registry[function_name]


_registry = _Registry()


# get an item by its index from an OrderedDict
def _OD_get(od: OrderedDict, index):
    return [item[1] for item in od.items()][index]


def overload(function: typing.Callable[..., typing.Any]):
    # TODO: Dirty hack. Are there any other way to detect whether something is function or method?
    # If function is a method (i.e. first parameter is either self or cls), set is_method to True so that we'll skip
    # checking it
    if type(function) is type(_registry.register):
        is_method = True
    else:
        is_method = False

    f_name = function.__qualname__
    f_parameters = inspect.signature(function).parameters

    # Standard Parameters are the parameters that can be supplied either positionally, or as a keyword.
    # For example:
    #     def f(a, b):
    #         pass
    #     f(5, 4)    # Both a and b are supplied positionally
    #     f(5, b=2)  # a is supplied positionally, b is supplied as a keyword
    standard_pars = OrderedDict()
    for name, parameter in list(f_parameters.items())[is_method:]:
        if parameter.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
            standard_pars[name] = parameter

    # Standard Parameters that have a default value, so they don't have to supplied.
    standard_default = OrderedDict()
    for name, parameter in standard_pars.items():
        if parameter.default is not inspect.Parameter.empty:
            standard_default[name] = parameter

    # Keyword Parameters are the parameters that can be supplied only as a keyword. They shouldn't be confused with
    # **kwargs!
    # For example:
    #     def f(a, b, *, c):
    #         pass
    #     f(1, c=4, b=3)
    # In the example above, both a and b are Standard Parameters, but a is supplied positionally and b is supplied as a
    # keyword; c is a Keyword Parameter, that means, it can only be supplied as a keyword.
    keyword_pars = OrderedDict()
    for name, parameter in f_parameters.items():
        if parameter.kind == inspect.Parameter.KEYWORD_ONLY:
            keyword_pars[name] = parameter

    # Keyword Parameters that have a default value, so they don't have to supplied.
    keyword_default = OrderedDict()
    for name, parameter in keyword_pars.items():
        if parameter.default is not inspect.Parameter.empty:
            keyword_default[name] = parameter

    # Check if function accepts **kwargs
    for _, parameter in f_parameters.items():
        if parameter.kind == inspect.Parameter.VAR_KEYWORD:
            allow_keyword = True
            break
    else:
        allow_keyword = False

    # noinspection PyTypeChecker
    _registry.register(_RegistryEntry(function,
                                      is_method,
                                      f_parameters,
                                      standard_pars, standard_default,
                                      allow_keyword,
                                      keyword_pars, keyword_default, ))

    def caller(*args, **kwargs):
        possibles = []
        candidates = []

        standard_satisfied = Counter()
        keyword_satisfied = Counter()

        # Check the arguments in *args, and create a list of candidates among functions in registry
        for entry in _registry[f_name]:

            # Check if more arguments are supplied than possibly can be
            if not len(args[is_method:]) <= len(entry.standard_pars):
                continue

            for i, arg in enumerate(args[is_method:]):
                if not _isOK(arg, _OD_get(entry.standard_pars, i).annotation):
                    break
                else:
                    standard_satisfied[id(entry)] += 1
            else:
                candidates.append(entry)

        # Check the arguments in **kwargs, and create a final list of "possibles" among candidates
        for candidate in candidates:

            # There must be enough amount of kwargs for our candidate
            if not len(candidate.keyword_pars) - len(candidate.keyword_default) <= len(kwargs):
                continue

            for kwarg in kwargs:
                # The argument might be a Keyword Parameter
                if kwarg in candidate.keyword_pars:
                    if not _isOK(kwargs[kwarg], candidate.keyword_pars[kwarg].annotation):
                        break
                    else:
                        keyword_satisfied[id(candidate)] += 1

                # or The argument might be a Standard Parameter that is supplied as a keyword
                elif kwarg in list(candidate.standard_pars.keys())[len(args):]:
                    if not _isOK(kwargs[kwarg], candidate.standard_pars[kwarg].annotation):
                        break

                # Argument was already supplied in *args and also passed as a keyword argument...
                # So it can not be the function that we are looking for
                elif kwarg in list(candidate.standard_pars.keys())[:len(args)]:
                    break

                # The argument is neither a Standard nor a Keyword Parameter, so our candidate must accept
                # **kwargs.
                elif not candidate.allow_keyword:
                    break
            else:
                # All of the standard parameters are satisfied, either as an *args or **kwargs
                if standard_satisfied[id(candidate)] >= len(candidate.standard_pars) - len(candidate.standard_default)\
                   and keyword_satisfied[id(candidate)] >= len(candidate.keyword_pars) - len(candidate.keyword_default):
                    possibles.append(candidate)

        if len(possibles) > 1:
            raise AmbiguousMethods("There are {} functions that can be possibly called:\n\t{}"
                                   .format(len(possibles),
                                           "\n\t".join(['File "{}", line {}'.format(p.function.__code__.co_filename, p.function.__code__.co_firstlineno) for p in possibles])))
        elif possibles:
            return possibles[0].function(*args, **kwargs)
        else:
            raise NoApplicableMethods("Couldn't find a suitable function.")

    return caller


def _isOK(obj, hint) -> bool:  # TODO: There are still type hints we can't check, e.g. most importantly Callable
    """
    Checks whether the object is OK for a given type hint.
    :param obj:
    :param hint:
    :return:
    """

    # If there is no type hint, treat like it's typing.Any and return True
    if hint == inspect._empty:
        return True

    # For:
    #     typing.Any
    if isinstance(hint, typing.AnyMeta):
        return True

    # TODO: I'm not sure if it's supposed to be like that. The documentation of typing is not really clear.
    # For:
    #     typing.TypeVar
    if isinstance(hint, typing.TypeVar):
        for constraint in hint.__constraints__:
            if not _isOK(obj, constraint):
                break
        else:
            return True

        return False

    # For:
    #     typing.Tuple
    if isinstance(hint, typing.TupleMeta):
        if isinstance(obj, tuple):
            for i, item in enumerate(obj):
                if not isinstance(item, hint.__tuple_params__[i]):
                    break
            else:
                return True

        return False

    # TODO: We are accessing a protected member of typing, are we sure that it's the only way?
    # TODO: Also check for the return type of __reversed__ if hint is typing.Reversible. (Iterator[T_co] it should be)
    if isinstance(hint, typing._ProtocolMeta):
        abml = list(hint.__abstractmethods__)  # abml: ABstract Methods List

        for abm in abml:
            if not hasattr(obj, abm):
                break
        else:
            return True

        return False

    if isinstance(hint, typing.GenericMeta):
        if hint.__name__ == "Mapping" or hint.__name__ == "Dict":
            if isinstance(obj, abc.Mapping):
                for key in obj:
                    if not _isOK(key, hint.__parameters__[0]) or not _isOK(obj[key], hint.__parameters__[1]):
                        break
                else:
                    return True

        elif hint.__name__ == "List":
            if isinstance(obj, list):
                for i in obj:
                    if not _isOK(i, hint.__parameters__[0]):
                        break
                else:
                    return True

        elif hint.__name__ == "Iterable":
            if isinstance(obj, abc.Iterable):
                return True

        elif hint.__name__ == "Iterator":
            if isinstance(obj, abc.Iterator):
                return True

        elif hint.__name__ == "ByteString":
            if isinstance(obj, abc.ByteString):
                return True

        elif hint.__name__ == "Sequence":
            if isinstance(obj, abc.Sequence):
                return True

        else:
            raise NotImplementedError("Type hint couldn't checked: '{}'.".format(hint))

        return False

    # For:
    #     typing.Union
    #     typing.Optional  (which is equivalent to Union[X, type(None)])
    if isinstance(hint, typing.UnionMeta):
        return isinstance(obj, tuple(hint.__union_set_params__))
    elif isinstance(hint, type):
        return isinstance(obj, hint)

    raise NotImplementedError("Type hint couldn't checked: '{}'.".format(hint))
