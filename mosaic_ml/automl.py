import random
import pynisher
import warnings
import pickle
import time

from mosaic.scenario import ListTask, ComplexScenario, ChoiceScenario
from mosaic.mosaic import Search
from mosaic.env import Env

from mosaic_ml import model
from mosaic_ml.utils import balanced_accuracy, memory_limit, time_limit

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.exceptions import ConvergenceWarning
from sklearn.model_selection import StratifiedKFold


from functools import partial

warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning)

LIST_TASK = [""]

class AutoML():
    def __init__(self, time_budget = None, time_limit_for_evaluation = None, training_log_file = "", info_training = {}):
        self.time_budget = time_budget
        self.time_limit_for_evaluation = time_limit_for_evaluation
        self.training_log_file = training_log_file
        self.info_training = info_training

    def configure_hyperparameter_space(self):
        if not hasattr(self, "X") or not hasattr(self, "y"):
            raise Exception("X, y is not defined.")

        # Data preprocessing
        list_data_preprocessing = model.get_all_data_preprocessing()
        data_preprocessing = []
        self.rules = []
        self.sampler = {}
        for dp_method in list_data_preprocessing:
            scenario, sampler_, rules_ = dp_method()
            data_preprocessing.append(scenario)
            self.rules.extend(rules_)
            self.sampler.update(sampler_)
        preprocessing = ChoiceScenario(name = "preprocessing", scenarios=data_preprocessing)

        # Classifier
        list_classifiers = model.get_all_classifier()
        classifiers = []
        for clf in list_classifiers:
            scenario, sampler_, rules_ = clf()
            classifiers.append(scenario)
            self.rules.extend(rules_)
            self.sampler.update(sampler_)
        classifier_model = ChoiceScenario(name = "classifier", scenarios=classifiers)

        # Pipeline = preprocessing + classifier
        self.start = ComplexScenario(name = "root", scenarios=[preprocessing, classifier_model], is_ordered=True)
        self.adjust_sampler()

    def adjust_sampler(self):
        for param in model.DATA_DEPENDANT_PARAMS:
            if param in self.sampler:
                self.sampler[param].value_list = [1, self.X.shape[1] - 1]

    def fit(self, X, y):
        self.X = X
        self.y = y
        self.configure_hyperparameter_space()

        @pynisher.enforce_limits(mem_in_mb=3072)
        def evaluate(config, bestconfig, X=None, y=None, info = {}):
            print("\n#####################################################")
            preprocessing = None
            classifier = None

            for name, params in config:
                if name in model.list_available_preprocessing:
                    preprocessing = model.list_available_preprocessing[name](**params)
                if  name in model.list_available_classifiers:
                    classifier = model.list_available_classifiers[name](**params)

            if preprocessing is None or classifier is None:
                raise Exception("Classifier and/or Preprocessing not found\n {0}".format(config))

            pipeline = Pipeline(steps=[("preprocessing", preprocessing), ("classifier", classifier)])

            try:
                print(pipeline) # Print algo

                skf = StratifiedKFold(n_splits=10)

                list_score = []
                for train_index, valid_index in skf.split(X, y):
                    X_train, X_valid = X[train_index], X[valid_index]
                    y_train, y_valid = y[train_index], y[valid_index]
                    with time_limit(36):
                        pipeline.fit(X_train, y_train)
                        score = balanced_accuracy(y_valid, pipeline.predict(X_valid))
                        if score < bestconfig["score"]:
                            print(">>>>>>>>>>>>>>>> Score: {0} Current best score: {1}".format(score, bestconfig["score"]))
                            return score
                        else:
                            list_score.append(score)

                score = min(list_score)

                pickle.dump(pipeline, open(info["working_directory"] + str(time.time()) + ".pkl", "wb"))
                print(">>>>>>>>>>>>>>>> New best Score: {0}".format(score))
                return score
            except Exception as e:
                raise e
                return 0

        eval_func = partial(evaluate, X=self.X, y=self.y, info = self.info_training)

        self.searcher = Search(self.start, self.sampler, self.rules, eval_func, logfile = self.training_log_file)
        with time_limit(3600):
            self.searcher.run(nb_simulation = 1000000000)
