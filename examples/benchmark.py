import argparse
import sys

sys.path.insert(0, '/home/tau/hrakotoa/Code/mosaic_project/mosaic_ml')
sys.path.append('.')

from update_metadata_util import load_task

import scipy

from mosaic_ml.automl import AutoML

from sklearn.preprocessing import Imputer
from sklearn.preprocessing import StandardScaler

import os

parser = argparse.ArgumentParser()
parser.add_argument('--working-directory', type=str, required=True)
parser.add_argument('--time-limit', type=int, required=True)
parser.add_argument('--per-run-time-limit', type=int, required=True)
parser.add_argument('--task-id', type=int, required=True)
parser.add_argument('--task-type', choices=['classification', 'regression'],
                    required=True)
parser.add_argument('-s', '--seed', type=int, required=True)
parser.add_argument('--unittest', action='store_true')
args = parser.parse_args()

working_directory = args.working_directory
time_limit = args.time_limit
per_run_time_limit = args.per_run_time_limit
task_id = args.task_id
task_type = args.task_type
seed = args.seed
is_test = args.unittest

tmp_dir = os.path.join(working_directory, str(task_id))
try:
    os.makedirs(tmp_dir + '/')
    os.makedirs(tmp_dir + '/images/')
except:
    pass

info = {
    "working_directory": tmp_dir + '/',
    "images_directory": tmp_dir + "/images"
}

X_train, y_train, X_test, y_test, cat = load_task(task_id)
imp = Imputer(missing_values="NaN", strategy="median")
imp.fit(X_train)

X_train = imp.transform(X_train)
X_test = imp.transform(X_test)

if not scipy.sparse.issparse(X_train):
    scaler = StandardScaler()
    scaler.fit(X_train)
    X_train = scaler.transform(X_train)
    X_test = scaler.transform(X_test)
else:
    scaler = StandardScaler(with_mean=False)
    scaler.fit(X_train)
    X_train = scaler.transform(X_train)
    X_test = scaler.transform(X_test)

autoML = AutoML(training_log_file="{0}/result.txt".format(tmp_dir), info_training=info)
autoML.fit(X_train, y_train)
"""
os.chdir(info["working_directory"])
for file in glob.glob("*.pkl"):
    pipeline = pickle.load(open(file, "rb"))
    pipeline.fit(X_train, y_train)
    score = balanced_accuracy(y_test, pipeline.predict(X_test))
    with open("{0}/validation.txt".format(tmp_dir), "a+") as f:
        f.write("{0},{1}\n".format(file, score))
"""
