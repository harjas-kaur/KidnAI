# THis script has used the file merged_data.csv to train out randon forest model with multioutputclassifier
#it uses optuna library to automate hyperparameter tuning
#the file path may need to be changed for this to work as it is

import pandas as pd
import numpy as np
import optuna
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.metrics import accuracy_score
from joblib import dump
from tqdm import tqdm

# Load dataset
df = pd.read_csv("../merged_file.csv")
df.ffill(inplace=True)

# Select features and labels
X = df[['A', 'VA', 'W', 'V', 'PF']]
y = df.iloc[:, 8:].astype(int)

# Train-test split (full data)
X_train_full, X_test, y_train_full, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Subsample training data for tuning
X_train_sample, _, y_train_sample, _ = train_test_split(X_train_full, y_train_full, test_size=0.8, random_state=42)

print(f"Sampled {X_train_sample.shape[0]} samples for Optuna tuning.")

# Define objective function for Optuna
def objective(trial):
    n_estimators = trial.suggest_int('n_estimators', 5, 50)
    max_depth = trial.suggest_int('max_depth', 3, 10)
    min_samples_split = trial.suggest_int('min_samples_split', 2, 10)
    min_samples_leaf = trial.suggest_int('min_samples_leaf', 1, 10)
    max_features = trial.suggest_categorical('max_features', ['sqrt', 'log2', 1, 2, 3])
    
    rf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        min_samples_leaf=min_samples_leaf,
        max_features=max_features,
        n_jobs=-1,
        random_state=42
    )
    
    model = MultiOutputClassifier(rf)
    model.fit(X_train_sample, y_train_sample)
    
    preds = model.predict(X_train_sample)
    score = accuracy_score(y_train_sample, preds)
    
    return score

# Create Optuna study
study = optuna.create_study(direction='maximize')

# Custom loop with tqdm progress bar
N_TRIALS = 20  # You can later increase this safely

print("Starting Optuna optimization with progress bar...")
with tqdm(total=N_TRIALS) as pbar:
    def callback(study, trial):
        pbar.update(1)

    study.optimize(objective, n_trials=N_TRIALS, callbacks=[callback])

print("Optimization completed.")

print("Best hyperparameters found:")
print(study.best_params)

# Train final model on FULL training data using best params
best_params = study.best_params

final_rf = RandomForestClassifier(
    n_estimators=best_params['n_estimators'],
    max_depth=best_params['max_depth'],
    min_samples_split=best_params['min_samples_split'],
    min_samples_leaf=best_params['min_samples_leaf'],
    max_features=best_params['max_features'],
    n_jobs=-1,
    random_state=42
)

final_model = MultiOutputClassifier(final_rf)
final_model.fit(X_train_full, y_train_full)

# Evaluate final model
y_pred = final_model.predict(X_test)
final_accuracy = accuracy_score(y_test, y_pred)
print(f"Final Test Accuracy: {final_accuracy:.2f}")

# Save final optimized model
dump(final_model, "optimized_random_forest_optuna_rpi.joblib", compress=3)
print("Optimized model saved as 'optimized_random_forest_optuna_rpi.joblib'.")
