import os
import sys
from urllib.parse import urlparse

from networksecurity.exception.exception import NetworkSecurityException
from networksecurity.logging.logger import logging

from networksecurity.entity.artifact_entity import DataTransformationArtifact, ModelTrainerArtifact
from networksecurity.entity.config_entity import ModelTrainerConfig

from networksecurity.utils.ml_utils.model.estimator import NetworkModel
from networksecurity.utils.main_utils.utils import save_object, load_object
from networksecurity.utils.main_utils.utils import load_numpy_array_data, evaluate_models
from networksecurity.utils.ml_utils.metric.classification_metric import get_classification_score

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    AdaBoostClassifier,
    GradientBoostingClassifier,
    RandomForestClassifier,
)

import mlflow
import mlflow.sklearn
import dagshub

# dagshub.init() sets the MLflow tracking URI for you (mlflow=True),
# so no manual set_tracking_uri / set_registry_uri is needed.
dagshub.init(repo_owner='amit-netzen', repo_name='network-security', mlflow=True)


class ModelTrainer:
    def __init__(self, model_trainer_config: ModelTrainerConfig,
                 data_transformation_artifact: DataTransformationArtifact):
        try:
            self.model_trainer_config = model_trainer_config
            self.data_transformation_artifact = data_transformation_artifact
        except Exception as e:
            raise NetworkSecurityException(e, sys)

    def track_mlflow(self, best_model, best_model_name, train_metric, test_metric):
        """Log train + test metrics and the model in a single MLflow run."""
        tracking_url_type_store = urlparse(mlflow.get_tracking_uri()).scheme

        with mlflow.start_run():
            mlflow.log_param("best_model", best_model_name)

            mlflow.log_metric("train_f1_score", train_metric.f1_score)
            mlflow.log_metric("train_precision", train_metric.precision_score)
            mlflow.log_metric("train_recall", train_metric.recall_score)

            mlflow.log_metric("test_f1_score", test_metric.f1_score)
            mlflow.log_metric("test_precision", test_metric.precision_score)
            mlflow.log_metric("test_recall", test_metric.recall_score)

            # Model registry does not work with the local file store
            # This model was trained in this script, so it is safe to trust the
            # tree-node type that skops flags when serializing tree-based models.
            trusted_types = ["sklearn.tree._tree.Tree"]

            if tracking_url_type_store != "file":
                mlflow.sklearn.log_model(
                    best_model,
                    name="model",
                    registered_model_name=best_model_name,
                    skops_trusted_types=trusted_types,
                )
            else:
                mlflow.sklearn.log_model(
                    best_model,
                    name="model",
                    skops_trusted_types=trusted_types,
                )

    def train_model(self, X_train, y_train, x_test, y_test):
        models = {
            "Random Forest": RandomForestClassifier(verbose=1),
            "Decision Tree": DecisionTreeClassifier(),
            "Gradient Boosting": GradientBoostingClassifier(verbose=1),
            "Logistic Regression": LogisticRegression(verbose=1),
            "AdaBoost": AdaBoostClassifier(),
        }
        params = {
            "Decision Tree": {
                'criterion': ['gini', 'entropy', 'log_loss'],
            },
            "Random Forest": {
                'n_estimators': [8, 16, 32, 128, 256],
            },
            "Gradient Boosting": {
                'learning_rate': [.1, .01, .05, .001],
                'subsample': [0.6, 0.7, 0.75, 0.85, 0.9],
                'n_estimators': [8, 16, 32, 64, 128, 256],
            },
            "Logistic Regression": {},
            "AdaBoost": {
                'learning_rate': [.1, .01, .001],
                'n_estimators': [8, 16, 32, 64, 128, 256],
            },
        }

        # NOTE: evaluate_models must fit each model in place (set_params with the
        # best params, then .fit) so that models[best_model_name] is trained below.
        model_report: dict = evaluate_models(
            X_train=X_train, y_train=y_train,
            X_test=x_test, y_test=y_test,
            models=models, param=params,
        )

        # Best model name and score
        best_model_name = max(model_report, key=lambda name: model_report[name])
        best_model_score = model_report[best_model_name]
        logging.info(f"Best model: {best_model_name} (score={best_model_score})")
        best_model = models[best_model_name]

        y_train_pred = best_model.predict(X_train)
        classification_train_metric = get_classification_score(y_true=y_train, y_pred=y_train_pred)

        y_test_pred = best_model.predict(x_test)
        classification_test_metric = get_classification_score(y_true=y_test, y_pred=y_test_pred)

        # Track the experiment with MLflow (one run, both train and test metrics)
        self.track_mlflow(best_model, best_model_name,
                          classification_train_metric, classification_test_metric)

        preprocessor = load_object(
            file_path=self.data_transformation_artifact.transformed_object_file_path
        )

        model_dir_path = os.path.dirname(self.model_trainer_config.trained_model_file_path)
        os.makedirs(model_dir_path, exist_ok=True)

        # Save an *instance* (preprocessor + model), not the class itself
        network_model = NetworkModel(preprocessor=preprocessor, model=best_model)
        save_object(self.model_trainer_config.trained_model_file_path, object=network_model)

        # Model pusher
        os.makedirs("final_model", exist_ok=True)
        save_object("final_model/model.pkl", object=best_model)

        # Model trainer artifact
        model_trainer_artifact = ModelTrainerArtifact(
            trained_model_file_path=self.model_trainer_config.trained_model_file_path,
            train_metric_artifact=classification_train_metric,
            test_metric_artifact=classification_test_metric,
        )
        logging.info(f"Model trainer artifact: {model_trainer_artifact}")
        return model_trainer_artifact

    def initiate_model_trainer(self) -> ModelTrainerArtifact:
        try:
            train_file_path = self.data_transformation_artifact.transformed_train_file_path
            test_file_path = self.data_transformation_artifact.transformed_test_file_path

            # Loading training array and testing array
            train_arr = load_numpy_array_data(train_file_path)
            test_arr = load_numpy_array_data(test_file_path)

            x_train, y_train, x_test, y_test = (
                train_arr[:, :-1],
                train_arr[:, -1],
                test_arr[:, :-1],
                test_arr[:, -1],
            )

            return self.train_model(x_train, y_train, x_test, y_test)

        except Exception as e:
            raise NetworkSecurityException(e, sys)