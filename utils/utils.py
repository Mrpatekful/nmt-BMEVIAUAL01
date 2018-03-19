from functools import wraps

import time
import pickle
import os.path
import inspect
import numpy


class Component:
    """
    The base class for the components of the API.
    """

    interface = None

    abstract = True

    def properties(self):
        """
        Convenience function for retrieving the properties of an instances, with their values.
        :return:
        """
        return {
            name: getattr(self, name) for (name, _) in
            inspect.getmembers(type(self), lambda x: isinstance(x, property))
            if name != 'optimizers' and name != 'state'
        }


class ParameterSetter:
    """
    This class handles the initialization of the given object's parameters.
    """

    @staticmethod
    def pack(cls_interface):
        """
        Packs the parameters of the decorated function.
        :param cls_interface: dict, interface of the instance.
        """
        def pack_wrapper(func):
            """
            Decorator for the functions, that require parameter packing.
            """
            def wrapper(*args, **kwargs):
                flattened_interface = create_leaf_dict(cls_interface)
                packed_parameters = create_intersection(kwargs, flattened_interface)

                if len(packed_parameters) > 0:
                    free_parameters = subtract_dict(kwargs, packed_parameters)

                    return func(*args, ParameterSetter(kwargs), **free_parameters)

                else:
                    return func(*args, **kwargs)

            return wrapper

        return pack_wrapper

    def __init__(self, param_dict):
        """
        An instance of a ParameterSetter class.
        :param param_dict: dict, containing the key value pairs of the object's parameters.
        """
        self._param_dict = param_dict

    def initialize(self, instance, subset=None):
        """
        This function creates the attributes of an instances. The instance must have an interface() method,
        that describes the required attributes.
        :param instance: instance, that will be initialized with the parameters, stored in the parameter dict.
        :param subset: dict, subset of the parameter setter's param dict, that specifies the subset
                       that should be created for the instance. If None, all of the parameters will be
                       initialized, that are stored in the param dict.
        """
        params = create_leaf_dict(instance.interface)

        if subset is not None:
            if isinstance(subset, dict):
                params = create_intersection(params, subset)
                self._param_dict = subtract_dict(self._param_dict, params)

            else:
                raise ValueError('Error: \' subset \' parameter must be a dictionary.')

        for parameter in params:
            instance.__dict__['_' + parameter] = self._param_dict[parameter]

    def extract(self, parameter_dict):
        """
        Extracts a set of parameters from the parameter dictionary of the setter object. The extracted parameters
        are then removed from the parameter setter's dictionary.
        :param parameter_dict: dict, subset of parameters to be extracted. It is typically an interface of an instance.
        :return: dict, extracted parameters.
        """
        extracted_parameters = create_intersection(self._param_dict, parameter_dict)
        self._param_dict = subtract_dict(self._param_dict, extracted_parameters)

        return extracted_parameters


def subclasses(base_cls):
    """
    Discovers the inheritance tree of a given class. The class must have an abstract() method. A class of the
    hierarchy will only be the part of the returned classes, if it's abstract() method returns False.
    :param base_cls: type, root of the inheritance hierarchy.
    :return: dict, classes that are part of the hierarchy, with their str names as keys, and type references as values.
    """
    def get_hierarchy(cls):
        sub_classes = {sub_cls.__name__: sub_cls for sub_cls in cls.__subclasses__()}
        hierarchy = {}
        for sub_cls_name in sub_classes:
            hierarchy = {**hierarchy, **get_hierarchy(sub_classes[sub_cls_name])}

        return {**hierarchy, **{name: sub_classes[name] for name in sub_classes if not sub_classes[name].abstract}}

    return get_hierarchy(base_cls)


def copy_dict_hierarchy(dictionary, fill_value=None):
    """
    Copies the a dictionary, that may have multiple embedded dictionaries. The values
    of the dictionary are replaced with the provided fill value.
    :param dictionary: dict, which structure will be copied.
    :param fill_value: the value that will be used to fill the copied dictionary.
    :return: dict, the copied dictionary.
    """
    new_dict = dict(zip(dictionary.keys(), [fill_value] * len(dictionary.keys())))
    for key in [k for k in dictionary.keys() if isinstance(dictionary[k], dict)]:
        new_dict[key] = copy_dict_hierarchy(dictionary[key])

    return new_dict


def merge_dicts(create_dict, iterable):
    """
    Merges multiple dictionaries, which are created by the output of a function and
    an iterable. The function is applied to the values of the iterable, that creates dictionaries
    :param create_dict: function, that given a parameter, outputs a dictionary.
    :param iterable: iterable, on which the function will be applied.
    :return: dict, the created dictionary.
    """
    merged_dict = {}
    for dictionary in map(create_dict, iterable):
        merged_dict = {**merged_dict, **dictionary}

    return merged_dict


def create_leaf_dict(dictionary):
    """
    Creates a flattened dictionary, from a dictionary, that has multiple dictionaries as
    values.
    :param dictionary: dict, that may have multiple layers of dictionaries as values.
    :return: dict, the flattened dictionary.
    """
    leaf_dict = {}
    for key in dictionary:
        if isinstance(dictionary[key], dict):

            leaf_dict = {**leaf_dict, **create_leaf_dict(dictionary[key])}

        else:

            leaf_dict = {**leaf_dict, key: dictionary[key]}

    return leaf_dict


def reduce_parameters(func, parameters):
    """
    Reduce a set of parameters, given in a form of dictionary, to the
    set of parameters, that are required by the function.
    :param func: Function, that requires a subset of parameters given as second argument.
    :param parameters: dict, a set of parameters, that yields a subset of parameters,
                       that is required by the func parameter.
    :return: dict, the subset of parameters for the 'func' function.
    """
    func_params = {}
    for parameter in inspect.signature(func).parameters.keys():
        func_params[parameter] = parameters[parameter]

    return func_params


def create_intersection(whole_dict, sub_dict):
    """
    Reduces a dictionary to have the same keys as an another dict.
    :param whole_dict: dict, the dictionary to be reduced.
    :param sub_dict: dict, the dictionary with the required keys.
    :return: dict, the reduced dict.
    """
    reduced_dict = {}
    for parameter in sub_dict.keys():
        if whole_dict.get(parameter, None) is None:

            return {}

        reduced_dict[parameter] = whole_dict[parameter]

    return reduced_dict


def subtract_dict(whole_dict, sub_dict):
    """
    Creates a dictionary with a set of keys, that only present in the 'greater' dictionary.
    :param whole_dict: dict, the dictionary to be reduced.
    :param sub_dict: dict, the dictionary with the required keys.
    :return: dict, the reduced dict.
    """
    reduced_dict = {}
    for parameter in [key for key in whole_dict.keys() if key not in sub_dict.keys()]:
        reduced_dict[parameter] = whole_dict[parameter]

    return reduced_dict


def execute(func, iterable, params=None):
    if params is None:
        params = {}
    for element in iterable:
        getattr(element, func)(**params)


def print_validation_format(self, **kwargs):
    """
    Convenience function for printing the parameters of the function, to the standard output.
    The parameters must be provided as keyword arguments. Each argument must contain a 2D
    array containing word ids, which will be converted to the represented words from the
    dictionary of the language, used by the reader instance.
    """
    id_batches = numpy.array(list(kwargs.values()))
    expression = ''
    for index, ids in enumerate(zip(*id_batches)):
        expression += '{%d}:\n' % index
        for param in zip(kwargs, ids):
            expression += ('> [%s]:\t%s\n' % (param[0], '\t'.join(sentence_from_ids(self._corpora.source_vocabulary,
                                                                                    param[1]))))
        expression += '\n'
    print(expression)


def ids_from_sentence(vocabulary, sentence):
    """
    Convenience method, for converting a sequence of words to ids.
    :param vocabulary: Language, object of the language to use the look up of.
    :param sentence: string, a tokenized sequence of words.
    :return: list, containing the ids (int) of the sentence in the same order.
    """
    return [vocabulary(word.rstrip()) for word in sentence.split(' ') if word.rstrip() != '']


def sentence_from_ids(vocabulary, ids):
    """
    Convenience method, for converting a sequence of ids to words.
    :param vocabulary: Language, object of the language to use the look up of.
    :param ids: ids, representations of words.
    :return: list, containing the ids (int) of the sentence in the same order.
    """
    return [vocabulary(word_id) for word_id in ids]


def logging(logger):
    """
    Decorator for the functions to get logs from. The function which is decorated
    with logging must return its values as a dictionary.
    :param logger: Logger object, which handles the data.
    :return: wrapper of the function.
    """
    def log_wrapper(func):
        """
        Wraps the wrapper of the function.
        :param func: the decorated function.
        :return: wrapper
        """
        @wraps(func)
        def wrapper(*args, **kwargs):

            return logger(*args, func=func, **kwargs)

        return wrapper

    return log_wrapper


class Logger:
    """
    Logger class for saving the progress of training.
    """

    def __init__(self,
                 params,
                 dump_interval=1000):
        """
        A logger instance. Instantiation should happen as a parameter of logging decorator.
        :param params: tuple, name of the input parameters, which will be logged.
        :param dump_interval: int, number of iteration, between two log dumps.
        """
        self._log_dir = None
        self._id = 1
        self._params = params
        self._dump_interval = dump_interval
        self._log_dict = {}

    def __call__(self, *args, func, **kwargs):
        """
        Invocation of a logger object will execute the given function, record the time required
        for this operation, and then save the results and given input parameters to the log dictionary.
        :param args: arguments of the function, which will be executed.
        :param func: function to be executed.
        :param kwargs: keyword arguments of the function to be executed.
        :return: result of the execution.
        """
        exec_time = time.time()
        result = func(*args, **kwargs)
        exec_time = time.time() - exec_time
        self._save_log({
            'exec_time': exec_time,
            **{param: kwargs[param] for param in self._params},
            **result
        })

        return result

    def _save_log(self, log):
        """
        Saves the log to the log dictionary. When the log id reaches the dump interval, the
        dictionary is serialized, and then deleted from the memory.
        :param log: dict, the log to be saved.
        """
        self._log_dict[self._id] = log
        if self._id % self._dump_interval == 0:
            self._dump_log()
        self._id += 1

    def _dump_log(self):
        """
        Serializes the log dictionary.
        """
        pickle.dump(obj=self._log_dict,
                    file=open(os.path.join(self.log_dir, 'iter_%d-%d' %
                                           (self._id-self._dump_interval, self._id)), 'wb'))
        del self._log_dict
        self._log_dict = {}

    @property
    def log_dir(self):
        """
        Property for the logging directory.
        :return: str, location of the logs.
        """
        if self._log_dir is None:
            raise ValueError('Log directory has not been defined.')
        return self._log_dir

    @log_dir.setter
    def log_dir(self, log_dir):
        """
        Setter for the directory of the logging directory.
        """
        self._log_dir = log_dir
