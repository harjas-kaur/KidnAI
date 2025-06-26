#this script saves the scaler and kmeans cluster files to be used in the final project
#merged_data.csv is used here again, file path may need to be changed for it to work.

import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from joblib import dump
from sklearn.model_selection import train_test_split

# Load dataset
df = pd.read_csv("../merged_file.csv")
df.ffill(inplace=True)

# Select features for scaling and PCA
X = df[['A', 'VA', 'W', 'V', 'PF']]

# Train-test split (full data for feature extraction and scaling)
X_train_full, X_test = train_test_split(X, test_size=0.2, random_state=42)

# ----- Scaling the features -----
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train_full)  # Fit and transform on training data
X_test_scaled = scaler.transform(X_test)  # Transform test data with the same scaler

# Save the scaler
dump(scaler, "scaler.joblib")
print("Scaler saved as 'scaler.joblib'.")

# ----- Apply PCA -----
pca = PCA(n_components=2)  # Example to reduce to 2 components (adjust based on needs)
X_train_pca = pca.fit_transform(X_train_scaled)  # Fit and transform training data
X_test_pca = pca.transform(X_test_scaled)  # Transform test data

# Save the PCA model
dump(pca, "pca_model.joblib")
print("PCA model saved as 'pca_model.joblib'.")

# ----- Apply KMeans Clustering -----
kmeans = KMeans(n_clusters=9, random_state=42)  # Set the number of clusters to 9
kmeans.fit(X_train_pca)  # Fit KMeans on the PCA-reduced training data

# Save the KMeans model
dump(kmeans, "kmeans_model.joblib")
print("KMeans model saved as 'kmeans_model.joblib'.")

# OPTIONAL: You can check the cluster centers to verify the results
print(f"Cluster centers: {kmeans.cluster_centers_}")
