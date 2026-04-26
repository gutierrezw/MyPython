import pandas as pd
import os
import joblib
import json
import warnings

from sklearn.exceptions import UndefinedMetricWarning
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, f1_score, roc_auc_score
from Modulos_Mysql import RepositorioOportunidadesBuySell


class ModeloOportunidadesSell:
    def __init__(self):
        self.modelo = None
        self.path = os.getcwd()
        self.modelo_name = 'modelo_sellv01'

        # Accesos MySql ----------------------------------------------------------------------------------------------
        self.ReOportunidades = RepositorioOportunidadesBuySell()

    def convertir_dataset_entrenamiento(self, datos):
        """
        Convierte lista de (rows, columns) desde RepositorioOportunidades a DataFrame usable para entrenamiento IA.
        """
        filas, columnas = datos  # descomprimir (registros, nombres de columnas)
        registros = []

        for fila in filas:
            row_dict = dict(zip(columnas, fila))

            # Elimina columnas innecesarias para el modelo
            keys_delete = ['id', 'tipo', 'subtipo', 'origen', 'timestamp', 'fecha', 'estado', 'nota', 'enviada']
            for key in keys_delete:
                row_dict.pop(key, None) 

            json_detalle = row_dict.get("json_detalle")
            if not json_detalle:
                continue

            try:
                detalle = json.loads(json_detalle)

                # Limpieza de indicadores si vienen como string
                indicadores = detalle.get("indicadores", {})
              
                row_dict["datos_tecnicos"] = indicadores
                row_dict["profit"] = detalle.get("profit")
                row_dict["roi"] = detalle.get("roi")

                registros.append(row_dict)

            except (EncodingWarning, Exception) as e:
                print(f"convertir_dataset_entrenamiento(): {e}")
    
        return pd.DataFrame(registros)
      
    def aplanar_datos_tecnicos(self, df):
        """Extrae indicadores diarios, semanales y mensuales de la columna 'datos_tecnicos'"""
        try:
            registros = []
            timeframes = {"diaria": "_d", "semanal": "_w", "mensual": "_m" }
            timeMaxMin = {"diaria": "13_semanas", "semanal": "26_semanas", "mensual": "52_semanas" }

            for _, rows in df.iterrows():
                plano = {}

                # crea struct a partir de json
                fila = json.loads(rows['datos_tecnicos'])
                                          
                if not isinstance(fila, dict):
                    registros.append(plano)
                    continue

                for tf, sufijo in timeframes.items():
                    fuente = fila.get(tf, {})

                    plano[f"rsi{sufijo}"] = fuente.get("rsi")
                    plano[f"macd{sufijo}"] = fuente.get("macd")
                    plano[f"Close{sufijo}"] = fuente.get("precio_calculo")

                    # construye string para extraer Maximos y Minimos
                    smax = timeMaxMin[tf] + "_max"
                    smin = timeMaxMin[tf] + "_min"

                    # EMAs largos
                    emas_largos = fuente.get("ema(20,50,100,200)", {})
                    for k, v in emas_largos.items():
                        plano[f"{k}{sufijo}"] = v

                    # EMAs cortos
                    emas_cortos = fuente.get("ema(09,21,055,144)", {})
                    for k, v in emas_cortos.items():
                        plano[f"{k}{sufijo}"] = v

                    # Fibonacci
                    fibo = fuente.get("retroceso_fibonacci", {})
                    plano[f"fibo_longico{sufijo}"] = fibo.get("longico")
                    
                    # Aplanar retroceso alcista
                    fibo_alcista = fibo.get("tendencia alcista", {})
                    for nivel, valor in fibo_alcista.items():
                        nivel_limpio = nivel.strip().replace("%", "").replace(".", "_")
                        col_name = f"fibo_alcista_{nivel_limpio}{sufijo}"
                        plano[col_name] = valor 
                    
                    # Aplanar retroceso bajista
                    fibo_bajista = fibo.get("tendencia_bajista", {})
                    for nivel, valor in fibo_bajista.items():
                        nivel_limpio = nivel.strip().replace("%", "").replace(".", "_")
                        col_name = f"fibo_bajista_{nivel_limpio}{sufijo}"
                        plano[col_name] = valor

                    # Maximo y minimos
                    plano[f"{smax}_{sufijo}"] = fuente.get(smax, 0)
                    plano[f"{smin}_{sufijo}"] = fuente.get(smin, 0)

                registros.append(plano)

            df_tecnico = pd.DataFrame(registros)
            return pd.concat([df.drop(columns=["datos_tecnicos"]), df_tecnico], axis=1)
        except (EncodingWarning, Exception) as e:
            print(f"aplanar_datos_tecnicos(): Error: {e}")

    def cargar_datos(self, df, usar_timeframes=["d", "w", "m"], umbral_columnas=0.5):
        """
        Prepara los datos de entrenamiento.
        usar_timeframes: lista con sufijos ['d', 'w', 'm'] para incluir diaria, semanal, mensual
        """
        # Todas las features disponibles por timeframe
        base_features = ['rsi', 'macd', 'Close', 
                        'EMA020', 'EMA050', 'EMA100', 'EMA200',
                        'EMA009', 'EMA021', 'EMA055', 'EMA144',
                        'fibo_longico', 'fibo_alcista', 'fibo_bajista'
        ]
        other_features = ['13_semanas_max_d', '13_semanas_min_d',
                          '26_semanas_max_w', '26_semanas_min_w'
                          '52_semanas_max_m', '52_semanas_min_m'
        ]

        # 1. Generar lista de columnas técnicas como antes (basado en usar_timeframes)
        columnas = [f"{col}_{suf}" for suf in usar_timeframes for col in base_features]
       
        # 2. contactena otras caracteriscas
        columnas.extend(other_features)

        # 3. Verificamos cuáles existen en el DataFrame
        columnas = [c for c in columnas if c in df.columns]

        # 4. Eliminar columnas con demasiados NaN
        min_validos = int(len(df) * umbral_columnas)
        df = df.dropna(thresh=min_validos, axis=1)

        # 5. Ahora eliminar filas que tengan NaN en las columnas restantes importantes
        columnas_validas = [col for col in columnas if col in df.columns]
        df = df.dropna(subset=columnas_validas + ["recomendado"])
     
        # 6. Solo los que han sido aprobados o rechazados
        df = df[df['recomendado'].isin([1, -1])]

        # 7. Etiqueta binaria
        df['etiqueta'] = df['recomendado'].apply(lambda x: "Display/Opportunity" if x == 1 else "Hide/Opportunity")

        return df[columnas_validas], df['etiqueta']
    
    def entrenar_modelo(self, df):
        try:
            X, y = self.cargar_datos(df)

            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, stratify=y, random_state=42)
            modelo = RandomForestClassifier(n_estimators=100, random_state=42)
            modelo.fit(X_train, y_train)

            self.modelo = modelo
            self.feature_names = X.columns.tolist()
            warnings.filterwarnings("ignore", category=UndefinedMetricWarning)

            self.metricas_de_clases(X, y, y_test, X_test)

        except (EncodingWarning, Exception) as e:
            print('entrenar_modelo(): {}'.format(e))

    def metricas_de_clases(self, X, y, y_test, X_test):

        # Predicciones finales
        y_pred = self.modelo.predict(X_test)
        
        print("📊 Reporte de entrenamiento:")
        print(classification_report(y_test, y_pred))
        print("Distribución etiquetas:", y.value_counts())
        print("=" * 50)

        # Equilibra precisión y recall, y el promedio macro da el mismo peso a ambas clases "F1-score (macro)"
        f1_macro = f1_score(y_test, y_pred, average="macro")
        print("F1-macro:", f1_macro)
    
        # Mide la capacidad de distinguir entre clases, independientemente del umbral
        y_proba = self.modelo.predict_proba(X_test)[:, 1]
        roc_auc = roc_auc_score(y_test, y_proba)
        print("ROC-AUC:", roc_auc)   

    def predecir_modelo(self, df):
        try:
            if self.modelo is None:
                raise ValueError("⚠️ Modelo no entrenado o cargado.")

            X_nuevo = df[self.modelo.feature_names_in_].copy()
            X_nuevo = X_nuevo.fillna(0)

            predicciones = self.modelo.predict(X_nuevo)
            probabilidades = self.modelo.predict_proba(X_nuevo)

            df_resultado = df.copy()
            df_resultado["prediccion"] = predicciones
            df_resultado["confianza"] = probabilidades[:, 1]
            
            # elimina las filas con NaN
            df_resultado = df_resultado.dropna(subset=['roi'])

            return df_resultado
        except (EncodingWarning, Exception) as e:
            print('predecir_modelo(): {}'.format(e))

    def save_modelo(self, file='modelo_ia'):
        path = path = os.path.join(self.path, 'tmp', f'{file}.pkl')
        joblib.dump(self.modelo, path)

    def load_modelo(self, file='modelo_ia'):
        path = path = os.path.join(self.path, 'tmp', f'{file}.pkl')
        self.modelo = joblib.load(path)

    # Ordena tareas para el entrenamiento del modelo de Sell
    def run_entraminetoSell(self):
        datos = self.ReOportunidades.obtener_por_tipo(tipo='sell')
        if datos[0]:
            df = self.convertir_dataset_entrenamiento(datos)
            df = self.aplanar_datos_tecnicos(df)
            self.entrenar_modelo(df)
            self.save_modelo(file=self.modelo_name)

if __name__ == '__main__':
    
    AiSell = ModeloOportunidadesSell()
    AiSell.run_entraminetoSell()
