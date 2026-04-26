import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.datasets import load_iris

# carga de datos
iris = load_iris()
df = pd.DataFrame(data=iris.data, columns=iris.feature_names)
df['species'] = iris.target
df['species'] = df['species'].map({0: 'setosa', 1: 'versicolor', 2: 'virginica'})

# variables objetivo y predictores
x = df[iris.feature_anmes]
y = df['species']

# datos entrenamiento y prueba
from sklearn.model_selection import train_test_split

x_train, x_test, y_train, y_test = train_test_split(x, y, tes_size=0.2, random_state=42)

# creación y entrenamiento del model
from sklearn.tree import DecisionTreeClassifier

# Crear y adjuntar el modelo
clf = DecisionTreeClassifier(random_state=42)
clf.fit(x_train, y_train)

plt.subplots(figsize=(8, 8))
sns.heatmap(correlation_matrix, cmap='RdYlGn', annot=True)
plt.show()
