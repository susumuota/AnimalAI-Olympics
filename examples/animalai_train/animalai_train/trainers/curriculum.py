import os
import json
import math

from .exception import CurriculumError
from animalai.envs.arena_config import ArenaConfig

import logging

logger = logging.getLogger('mlagents.trainers')


class Curriculum(object):
    def __init__(self, location, yaml_files):
        """
        Initializes a Curriculum object.
        :param location: Path to JSON defining curriculum.
        :param yaml_files: A list of configuration files for each lesson
        """
        self.max_lesson_num = 0
        self.measure = None
        self._lesson_num = 0
        # The name of the brain should be the basename of the file without the
        # extension.
        self._brain_name = os.path.basename(location).split('.')[0]

        try:
            with open(location) as data_file:
                self.data = json.load(data_file)
        except IOError:
            raise CurriculumError(
                'The file {0} could not be found.'.format(location))
        except UnicodeDecodeError:
            raise CurriculumError('There was an error decoding {}'
                                  .format(location))
        self.smoothing_value = 0
        for key in ['configuration_files', 'measure', 'thresholds',
                    'min_lesson_length', 'signal_smoothing']:
            if key not in self.data:
                raise CurriculumError("{0} does not contain a "
                                      "{1} field."
                                      .format(location, key))
        self.smoothing_value = 0
        self.measure = self.data['measure']
        self.min_lesson_length = self.data['min_lesson_length']
        self.max_lesson_num = len(self.data['thresholds'])

        configuration_files = self.data['configuration_files']
        # for key in configuration_files:
        # if key not in default_reset_parameters:
        #     raise CurriculumError(
        #         'The parameter {0} in Curriculum {1} is not present in '
        #         'the Environment'.format(key, location))
        if len(configuration_files) != self.max_lesson_num + 1:
            raise CurriculumError(
                'The parameter {0} in Curriculum {1} must have {2} values '
                'but {3} were found'.format(key, location,
                                            self.max_lesson_num + 1,
                                            len(configuration_files)))
        folder = os.path.dirname(location)
        folder_yaml_files = os.listdir(folder)
        if not all([file in folder_yaml_files for file in configuration_files]):
            raise Curriculum(
                'One or more configuration file(s) in curriculum {0} could not be found'.format(location)
            )
        self.configurations = [ArenaConfig(os.path.join(folder, file)) for file in yaml_files]

    @property
    def lesson_num(self):
        return self._lesson_num

    @lesson_num.setter
    def lesson_num(self, lesson_num):
        self._lesson_num = max(0, min(lesson_num, self.max_lesson_num))

    def increment_lesson(self, measure_val):
        """
        Increments the lesson number depending on the progress given.
        :param measure_val: Measure of progress (either reward or percentage
               steps completed).
        :return Whether the lesson was incremented.
        """
        if not self.data or not measure_val or math.isnan(measure_val):
            return False
        if self.data['signal_smoothing']:
            measure_val = self.smoothing_value * 0.25 + 0.75 * measure_val
            self.smoothing_value = measure_val
        if self.lesson_num < self.max_lesson_num:
            if measure_val > self.data['thresholds'][self.lesson_num]:
                self.lesson_num += 1
                # config = {}
                # parameters = self.data['parameters']
                # for key in parameters:
                #     config[key] = parameters[key][self.lesson_num]
                logger.info('{0} lesson changed. Now in lesson {1}'
                            .format(self._brain_name,
                                    self.lesson_num))
                return True
        return False

    def get_config(self, lesson=None):
        """
        Returns reset parameters which correspond to the lesson.
        :param lesson: The lesson you want to get the config of. If None, the
               current lesson is returned.
        :return: The configuration of the reset parameters.
        """
        if not self.data:
            return {}
        if lesson is None:
            lesson = self.lesson_num
        lesson = max(0, min(lesson, self.max_lesson_num))
        config = self.configurations[lesson]
        # parameters = self.data['parameters']
        # for key in parameters:
        #     config[key] = parameters[key][lesson]
        return config
