# datos
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.datasets import load_diabetes

# carga de datos
diabetes = load_diabetes()
df = pd.DataFrame(data=diabetes.data, columns=diabetes.feature_names)
df['TARGET'] = diabetes.target

correlation_matrix = df.corr()
plt.subplots(figsize=(8, 8))
sns.heatmap(correlation_matrix, cmap='RdYlGn', annot=True)
plt.show()
