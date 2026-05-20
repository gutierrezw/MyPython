from Modulos_python import (
    pd,
    joblib,
    json,
    warnings,
    np,
    UndefinedMetricWarning,
    RandomForestClassifier,
    train_test_split,
    StratifiedKFold,
    cross_val_score,
    classification_report,
    f1_score,
    roc_auc_score,
)
from Modulos_Mysql import RepositorioOportunidadesBuySell, BDsystem
from Modulos_Utilitarios import define_FileCache

# Parámetros por defecto del modelo
DEFAULT_PARAMS_SELL = {
    # Parámetros del RandomForest
    "n_estimators": 100,
    "max_depth": 10,
    "min_samples_split": 5,
    "random_state": 42,
    # Parámetros de entrenamiento
    "n_folds": 5,
    "test_size": 0.3,
    # Umbrales de predicción
    "umbral_sell": 0.65,  # Confianza mínima para recomendar venta
    "umbral_observacion": 0.35,  # Por debajo de este umbral se descarta
}

# Parámetros por defecto del modelo Buy
DEFAULT_PARAMS_BUY = {
    # Parámetros del RandomForest
    "n_estimators": 100,
    "max_depth": 10,
    "min_samples_split": 5,
    "random_state": 42,
    # Parámetros de entrenamiento
    "n_folds": 5,
    "test_size": 0.3,
    # Umbrales de predicción
    "umbral_buy": 0.65,  # Confianza mínima para recomendar compra
    "umbral_observacion": 0.35,  # Por debajo de este umbral se descarta
}


class ModeloOportunidadesSell:
    def __init__(self):
        self.modelo = None
        self.metrics = None
        self.modelo_name = "modelo_sellv01"
        self.params = DEFAULT_PARAMS_SELL.copy()

        # Cargar parámetros desde BD si existen
        self._cargar_params_bd()

        # Accesos MySql
        self.ReOportunidades = RepositorioOportunidadesBuySell()

    def _cargar_params_bd(self):
        """Carga parámetros del modelo desde tabla modelos_ia."""
        try:
            modelo_data = BDsystem.get_modelo_ia(self.modelo_name)
            if modelo_data and modelo_data.get("paramts"):
                params_bd = json.loads(modelo_data["paramts"].decode("utf-8"))
                # Actualizar solo los parámetros que existan en BD
                for key, value in params_bd.items():
                    if key in self.params:
                        self.params[key] = value
        except Exception as e:
            print(f"_cargar_params_bd(): Usando parámetros por defecto. Error: {e}")

    def convertir_dataset_entrenamiento(self, datos):
        """
        Convierte lista de (rows, columns) desde RepositorioOportunidades a DataFrame usable para entrenamiento IA.
        """
        filas, columnas = datos  # descomprimir (registros, nombres de columnas)
        registros = []

        for fila in filas:
            row_dict = dict(zip(columnas, fila))

            # Elimina columnas innecesarias para el modelo
            keys_delete = ["id", "tipo", "subtipo", "origen", "timestamp", "fecha", "estado", "nota", "enviada"]
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

            except Exception as e:
                print(f"convertir_dataset_entrenamiento(): {e}")

        return pd.DataFrame(registros)

    def aplanar_datos_tecnicos(self, df):
        """Extrae indicadores diarios, semanales y mensuales de la columna 'datos_tecnicos'"""
        try:
            registros = []
            timeframes = {"diaria": "_d", "semanal": "_w", "mensual": "_m"}
            timeMaxMin = {"diaria": "13_semanas", "semanal": "26_semanas", "mensual": "52_semanas"}

            for _, rows in df.iterrows():
                plano = {}

                # crea struct a partir de json
                fila = json.loads(rows["datos_tecnicos"])

                if not isinstance(fila, dict):
                    registros.append(plano)
                    continue

                for tf, sufijo in timeframes.items():
                    fuente = fila.get(tf, {})

                    plano[f"rsi{sufijo}"] = fuente.get("rsi")
                    plano[f"macd{sufijo}"] = fuente.get("macd")
                    plano[f"Close{sufijo}"] = fuente.get("precio_calculo")
                    plano[f"atr{sufijo}"] = fuente.get("atr")
                    plano[f"atr_pct{sufijo}"] = fuente.get("atr_pct")

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

                    # Rango porcentual: posición del precio dentro del rango max-min
                    vmax = plano.get(f"{smax}_{sufijo}", 0)
                    vmin = plano.get(f"{smin}_{sufijo}", 0)
                    close = plano.get(f"Close{sufijo}", 0)
                    rango = vmax - vmin
                    clave = {"diaria": "rango_13w_pct", "semanal": "rango_26w_pct", "mensual": "rango_52w_pct"}[tf]
                    plano[clave] = round((close - vmin) / rango, 4) if rango > 0 else None

                registros.append(plano)

            df_tecnico = pd.DataFrame(registros)
            return pd.concat([df.drop(columns=["datos_tecnicos"]), df_tecnico], axis=1)
        except Exception as e:
            print(f"aplanar_datos_tecnicos(): Error: {e}")

    def cargar_datos(self, df, usar_timeframes=["d"], umbral_columnas=0.5):
        """
        Prepara los datos de entrenamiento.
        usar_timeframes: lista con sufijos ['d', 'w', 'm'] para incluir diaria, semanal, mensual
                         Por defecto solo usa diaria ['d'] ya que es el más común
        """
        # Todas las features disponibles por timeframe
        # NOTA: fibo_alcista y fibo_bajista son dicts con múltiples niveles, no se incluyen aquí
        # ROI agregado como feature importante para decisiones de venta
        base_features = [
            "rsi",
            "macd",
            "Close",
            "atr",
            "atr_pct",
            "EMA020",
            "EMA050",
            "EMA100",
            "EMA200",
            "EMA009",
            "EMA021",
            "EMA055",
            "EMA144",
            "fibo_longico",
        ]
        # Features que no dependen de timeframe
        scalar_features = ["roi"]
        other_features = [
            "13_semanas_max_d",
            "13_semanas_min_d",
            "26_semanas_max_w",
            "26_semanas_min_w",
            "52_semanas_max_m",
            "52_semanas_min_m",
            "rango_13w_pct",
            "rango_26w_pct",
            "rango_52w_pct",
        ]

        # 1. Generar lista de columnas técnicas como antes (basado en usar_timeframes)
        columnas = [f"{col}_{suf}" for suf in usar_timeframes for col in base_features]

        # 2. Agregar features escalares (no dependen de timeframe)
        columnas.extend(scalar_features)

        # 3. contactena otras caracteriscas (solo las que coincidan con timeframes)
        for feat in other_features:
            if any(f"_{tf}" in feat for tf in usar_timeframes):
                columnas.append(feat)

        # 3. Verificamos cuáles existen en el DataFrame
        columnas = [c for c in columnas if c in df.columns]

        if not columnas:
            print(f"cargar_datos(): No se encontraron columnas válidas. Columnas en df: {list(df.columns)}")
            raise ValueError("No hay columnas válidas para entrenar el modelo")

        # 4. Eliminar columnas con demasiados NaN
        min_validos = int(len(df) * umbral_columnas)
        df = df.dropna(thresh=min_validos, axis=1)

        # 5. Ahora eliminar filas que tengan NaN en las columnas restantes importantes
        columnas_validas = [col for col in columnas if col in df.columns]

        if not columnas_validas:
            print(f"cargar_datos(): Todas las columnas fueron eliminadas por NaN")
            raise ValueError("No hay columnas válidas después de filtrar NaN")

        df = df.dropna(subset=columnas_validas + ["recomendado"])

        # 6. Solo los que han sido aprobados o rechazados
        df = df[df["recomendado"].isin([1, -1])]

        if df.empty:
            print(f"cargar_datos(): No quedan filas después del filtrado")
            raise ValueError("No hay datos para entrenar después del filtrado")

        # 7. Etiqueta binaria
        df["etiqueta"] = df["recomendado"].apply(lambda x: "sell" if x == 1 else "hold")

        return df[columnas_validas], df["etiqueta"]

    def entrenar_modelo(self, df):
        """
        Entrena el modelo usando validación cruzada estratificada.
        Los parámetros se cargan desde self.params (BD o defaults).
        """
        try:
            X, y = self.cargar_datos(df)
            warnings.filterwarnings("ignore", category=UndefinedMetricWarning)

            # Parámetros desde configuración
            n_folds = self.params.get("n_folds", 5)
            n_estimators = self.params.get("n_estimators", 100)
            max_depth = self.params.get("max_depth", 10)
            min_samples_split = self.params.get("min_samples_split", 5)
            random_state = self.params.get("random_state", 42)
            test_size = self.params.get("test_size", 0.3)

            # Validación cruzada estratificada con balanceo de clases
            cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=random_state)
            modelo = RandomForestClassifier(
                n_estimators=n_estimators,
                max_depth=max_depth,
                min_samples_split=min_samples_split,
                class_weight="balanced",
                random_state=random_state,
            )

            # Calcular métricas con cross-validation
            cv_accuracy = cross_val_score(modelo, X, y, cv=cv, scoring="accuracy")
            cv_f1 = cross_val_score(modelo, X, y, cv=cv, scoring="f1_weighted")
            cv_precision = cross_val_score(modelo, X, y, cv=cv, scoring="precision_weighted")
            cv_recall = cross_val_score(modelo, X, y, cv=cv, scoring="recall_weighted")
            cv_roc_auc = cross_val_score(modelo, X, y, cv=cv, scoring="roc_auc")

            # Entrenar modelo final con todos los datos
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, stratify=y, random_state=random_state
            )
            modelo.fit(X_train, y_train)

            self.modelo = modelo
            self.feature_names = X.columns.tolist()

            # Calcular balance de clases
            class_counts = y.value_counts()
            n_aprobadas = class_counts.get("sell", 0)
            n_rechazadas = class_counts.get("hold", 0)
            balance_ratio = (
                min(n_aprobadas, n_rechazadas) / max(n_aprobadas, n_rechazadas)
                if max(n_aprobadas, n_rechazadas) > 0
                else 0
            )

            # Guardar métricas de validación cruzada y parámetros usados
            self.metrics = {
                "precision": np.mean(cv_precision),
                "precision_std": np.std(cv_precision),
                "recall": np.mean(cv_recall),
                "recall_std": np.std(cv_recall),
                "f1_score": np.mean(cv_f1),
                "f1_std": np.std(cv_f1),
                "accuracy": np.mean(cv_accuracy),
                "accuracy_std": np.std(cv_accuracy),
                "roc_auc": np.mean(cv_roc_auc),
                "roc_auc_std": np.std(cv_roc_auc),
                "n_folds": n_folds,
                "n_samples": len(X),
                "n_aprobadas": int(n_aprobadas),
                "n_rechazadas": int(n_rechazadas),
                "balance_ratio": float(balance_ratio),
                # Parámetros del modelo usados
                "params": {
                    "n_estimators": n_estimators,
                    "max_depth": max_depth,
                    "min_samples_split": min_samples_split,
                    "test_size": test_size,
                },
            }

            # Calcular métricas adicionales en test set
            self.metricas_de_clases(X, y, y_test, X_test)

        except Exception as e:
            print("entrenar_modelo(): {}".format(e))

    def metricas_de_clases(self, X, y, y_test, X_test):
        """Agrega métricas del test set al diccionario de métricas existente"""
        # Predicciones finales
        y_pred = self.modelo.predict(X_test)

        # Calcular métricas del test set
        report = classification_report(y_test, y_pred, output_dict=True)
        f1_macro = f1_score(y_test, y_pred, average="macro")
        y_proba = self.modelo.predict_proba(X_test)[:, 1]
        roc_auc = roc_auc_score(y_test, y_proba)

        # Agregar métricas del test set (complementan las de CV)
        if self.metrics is None:
            self.metrics = {}
        self.metrics["test_precision"] = report.get("weighted avg", {}).get("precision", 0)
        self.metrics["test_recall"] = report.get("weighted avg", {}).get("recall", 0)
        self.metrics["test_f1"] = report.get("weighted avg", {}).get("f1-score", 0)
        self.metrics["test_accuracy"] = report.get("accuracy", 0)
        self.metrics["f1_macro"] = f1_macro
        self.metrics["test_roc_auc"] = roc_auc

        # Feature importance (top 10)
        self.calcular_feature_importance()

    def calcular_feature_importance(self):
        """Calcula y guarda la importancia de las features del modelo"""
        if self.modelo is None or not hasattr(self.modelo, "feature_importances_"):
            return

        importances = self.modelo.feature_importances_
        feature_names = self.modelo.feature_names_in_

        # Ordenar por importancia descendente
        indices = np.argsort(importances)[::-1]

        # Guardar top 10 features más importantes
        top_features = []
        for i in range(min(10, len(indices))):
            idx = indices[i]
            top_features.append({"feature": feature_names[idx], "importance": float(importances[idx])})

        if self.metrics is None:
            self.metrics = {}
        self.metrics["feature_importance"] = top_features

    def predecir_modelo(self, df):
        """
        Realiza predicciones sobre nuevos datos.
        Clasifica según umbrales:
        - confianza >= umbral_sell: recomendar venta
        - confianza >= umbral_observacion: observación
        - confianza < umbral_observacion: descartar
        """

        def clasificar(conf, umbral_sell, umbral_obs):
            if conf >= umbral_sell:
                return "sell"
            elif conf >= umbral_obs:
                return "observacion"
            return "descartar"

        try:
            if self.modelo is None:
                print("predecir_modelo(): Modelo no entrenado o cargado.")
                return None

            X_nuevo = df[self.modelo.feature_names_in_].copy()
            X_nuevo = X_nuevo.fillna(0)

            predicciones = self.modelo.predict(X_nuevo)
            probabilidades = self.modelo.predict_proba(X_nuevo)

            df_resultado = df.copy()
            df_resultado["prediccion"] = predicciones
            df_resultado["confianza"] = probabilidades[:, 1]

            # Umbrales desde parámetros
            umbral_sell = self.params.get("umbral_sell", 0.65)
            umbral_obs = self.params.get("umbral_observacion", 0.35)

            df_resultado["clasificacion"] = df_resultado["confianza"].apply(
                lambda c: clasificar(c, umbral_sell, umbral_obs)
            )

            # Elimina filas con NaN en roi
            df_resultado = df_resultado.dropna(subset=["roi"])

            return df_resultado
        except Exception as e:
            print(f"predecir_modelo(): {e}")
            return None

    def save_modelo(self, file="modelo_ia"):
        """Guarda el modelo y sus métricas usando define_FileCache"""
        path_modelo = define_FileCache(f"{file}.pkl")
        path_metrics = define_FileCache(f"{file}_metrics.pkl")
        joblib.dump(self.modelo, path_modelo)
        if self.metrics:
            joblib.dump(self.metrics, path_metrics)

    def load_modelo(self, file="modelo_ia"):
        """Carga el modelo y sus métricas si existen"""
        path_modelo = define_FileCache(f"{file}.pkl")
        path_metrics = define_FileCache(f"{file}_metrics.pkl")
        try:
            self.modelo = joblib.load(path_modelo)
        except FileNotFoundError:
            self.modelo = None
        try:
            self.metrics = joblib.load(path_metrics)
        except FileNotFoundError:
            self.metrics = None

    # Ordena tareas para el entrenamiento del modelo de Sell
    def run_entraminetoSell(self):
        datos = self.ReOportunidades.obtener_por_tipo(tipo="sell")
        if datos[0]:
            df = self.convertir_dataset_entrenamiento(datos)
            df = self.aplanar_datos_tecnicos(df)
            self.entrenar_modelo(df)
            self.save_modelo(file=self.modelo_name)


class ModeloOportunidadesBuy:
    """
    Modelo IA para detectar oportunidades de compra.
    Enfocado en identificar activos con precio deprimido usando RSI, EMAs y otros indicadores.
    """

    def __init__(self):
        self.modelo = None
        self.metrics = None
        self.modelo_name = "modelo_buyv01"
        self.params = DEFAULT_PARAMS_BUY.copy()

        # Cargar parámetros desde BD si existen
        self._cargar_params_bd()

        # Accesos MySql
        self.ReOportunidades = RepositorioOportunidadesBuySell()

    def _cargar_params_bd(self):
        """Carga parámetros del modelo desde tabla modelos_ia."""
        try:
            modelo_data = BDsystem.get_modelo_ia(self.modelo_name)
            if modelo_data and modelo_data.get("paramts"):
                params_bd = json.loads(modelo_data["paramts"].decode("utf-8"))
                for key, value in params_bd.items():
                    if key in self.params:
                        self.params[key] = value
        except Exception as e:
            print(f"_cargar_params_bd(): Usando parámetros por defecto. Error: {e}")

    def convertir_dataset_entrenamiento(self, datos):
        """Convierte datos desde RepositorioOportunidades a DataFrame para entrenamiento."""
        filas, columnas = datos
        registros = []

        for fila in filas:
            row_dict = dict(zip(columnas, fila))

            # Elimina columnas innecesarias
            keys_delete = ["id", "tipo", "subtipo", "origen", "timestamp", "fecha", "estado", "nota", "enviada"]
            for key in keys_delete:
                row_dict.pop(key, None)

            json_detalle = row_dict.get("json_detalle")
            if not json_detalle:
                continue

            try:
                detalle = json.loads(json_detalle)
                indicadores = detalle.get("indicadores", {})

                row_dict["datos_tecnicos"] = indicadores
                row_dict["ganancia_precio"] = detalle.get("ganancia_precio", 0)
                row_dict["ganancia_inversion"] = detalle.get("ganancia_inversion", 0)
                row_dict["dividend_yield"] = detalle.get("dividend_yield", 0)
                row_dict["score"] = detalle.get("score", 0)

                registros.append(row_dict)
            except Exception as e:
                print(f"convertir_dataset_entrenamiento(): {e}")

        return pd.DataFrame(registros)

    def aplanar_datos_tecnicos(self, df):
        """Extrae indicadores técnicos de la columna 'datos_tecnicos'."""
        try:
            registros = []
            timeframes = {"diaria": "_d", "semanal": "_w", "mensual": "_m"}
            timeMaxMin = {"diaria": "13_semanas", "semanal": "26_semanas", "mensual": "52_semanas"}

            for _, rows in df.iterrows():
                plano = {}
                fila = (
                    json.loads(rows["datos_tecnicos"])
                    if isinstance(rows["datos_tecnicos"], str)
                    else rows["datos_tecnicos"]
                )

                if not isinstance(fila, dict):
                    registros.append(plano)
                    continue

                for tf, sufijo in timeframes.items():
                    fuente = fila.get(tf, {})

                    plano[f"rsi{sufijo}"] = fuente.get("rsi")
                    plano[f"macd{sufijo}"] = fuente.get("macd")
                    plano[f"Close{sufijo}"] = fuente.get("precio_calculo")
                    plano[f"atr{sufijo}"] = fuente.get("atr")
                    plano[f"atr_pct{sufijo}"] = fuente.get("atr_pct")

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

                    # Máximos y mínimos
                    plano[f"{smax}_{sufijo}"] = fuente.get(smax, 0)
                    plano[f"{smin}_{sufijo}"] = fuente.get(smin, 0)

                    # Rango porcentual: posición del precio dentro del rango max-min
                    vmax = plano.get(f"{smax}_{sufijo}", 0)
                    vmin = plano.get(f"{smin}_{sufijo}", 0)
                    close = plano.get(f"Close{sufijo}", 0)
                    rango = vmax - vmin
                    clave = {"diaria": "rango_13w_pct", "semanal": "rango_26w_pct", "mensual": "rango_52w_pct"}[tf]
                    plano[clave] = round((close - vmin) / rango, 4) if rango > 0 else None

                registros.append(plano)

            df_tecnico = pd.DataFrame(registros)
            return pd.concat([df.drop(columns=["datos_tecnicos"]), df_tecnico], axis=1)
        except Exception as e:
            print(f"aplanar_datos_tecnicos(): {e}")
            return df

    def cargar_datos(self, df, usar_timeframes=["d"], umbral_columnas=0.5):
        """Prepara los datos de entrenamiento para Buy."""
        # Features técnicas por timeframe
        base_features = [
            "rsi",
            "macd",
            "Close",
            "atr",
            "atr_pct",
            "EMA020",
            "EMA050",
            "EMA100",
            "EMA200",
            "EMA009",
            "EMA021",
            "EMA055",
            "EMA144",
            "fibo_longico",
        ]

        # Features específicas para Buy (precio deprimido)
        scalar_features = ["ganancia_precio", "ganancia_inversion", "dividend_yield", "score"]

        other_features = [
            "13_semanas_max_d",
            "13_semanas_min_d",
            "26_semanas_max_w",
            "26_semanas_min_w",
            "52_semanas_max_m",
            "52_semanas_min_m",
            "rango_13w_pct",
            "rango_26w_pct",
            "rango_52w_pct",
        ]

        # Generar columnas
        columnas = [f"{col}_{suf}" for suf in usar_timeframes for col in base_features]
        columnas.extend(scalar_features)

        for feat in other_features:
            if any(f"_{tf}" in feat for tf in usar_timeframes):
                columnas.append(feat)

        columnas = [c for c in columnas if c in df.columns]

        if not columnas:
            print(f"cargar_datos(): No se encontraron columnas válidas.")
            raise ValueError("No hay columnas válidas para entrenar el modelo")

        # Eliminar columnas con demasiados NaN
        min_validos = int(len(df) * umbral_columnas)
        df = df.dropna(thresh=min_validos, axis=1)

        columnas_validas = [col for col in columnas if col in df.columns]

        if not columnas_validas:
            raise ValueError("No hay columnas válidas después de filtrar NaN")

        df = df.dropna(subset=columnas_validas + ["recomendado"])

        # Solo aprobados o rechazados
        df = df[df["recomendado"].isin([1, -1])]

        if df.empty:
            raise ValueError("No hay datos para entrenar después del filtrado")

        # Etiqueta binaria para Buy
        df["etiqueta"] = df["recomendado"].apply(lambda x: "buy" if x == 1 else "wait")

        return df[columnas_validas], df["etiqueta"]

    def entrenar_modelo(self, df):
        """Entrena el modelo usando validación cruzada estratificada."""
        try:
            X, y = self.cargar_datos(df)
            warnings.filterwarnings("ignore", category=UndefinedMetricWarning)

            # Parámetros desde configuración
            n_folds = self.params.get("n_folds", 5)
            n_estimators = self.params.get("n_estimators", 100)
            max_depth = self.params.get("max_depth", 10)
            min_samples_split = self.params.get("min_samples_split", 5)
            random_state = self.params.get("random_state", 42)
            test_size = self.params.get("test_size", 0.3)

            cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=random_state)
            modelo = RandomForestClassifier(
                n_estimators=n_estimators,
                max_depth=max_depth,
                min_samples_split=min_samples_split,
                class_weight="balanced",
                random_state=random_state,
            )

            # Métricas con cross-validation
            cv_accuracy = cross_val_score(modelo, X, y, cv=cv, scoring="accuracy")
            cv_f1 = cross_val_score(modelo, X, y, cv=cv, scoring="f1_weighted")
            cv_precision = cross_val_score(modelo, X, y, cv=cv, scoring="precision_weighted")
            cv_recall = cross_val_score(modelo, X, y, cv=cv, scoring="recall_weighted")
            cv_roc_auc = cross_val_score(modelo, X, y, cv=cv, scoring="roc_auc")

            # Entrenar modelo final
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, stratify=y, random_state=random_state
            )
            modelo.fit(X_train, y_train)

            self.modelo = modelo
            self.feature_names = X.columns.tolist()

            # Balance de clases
            class_counts = y.value_counts()
            n_aprobadas = class_counts.get("buy", 0)
            n_rechazadas = class_counts.get("wait", 0)
            balance_ratio = (
                min(n_aprobadas, n_rechazadas) / max(n_aprobadas, n_rechazadas)
                if max(n_aprobadas, n_rechazadas) > 0
                else 0
            )

            self.metrics = {
                "precision": np.mean(cv_precision),
                "precision_std": np.std(cv_precision),
                "recall": np.mean(cv_recall),
                "recall_std": np.std(cv_recall),
                "f1_score": np.mean(cv_f1),
                "f1_std": np.std(cv_f1),
                "accuracy": np.mean(cv_accuracy),
                "accuracy_std": np.std(cv_accuracy),
                "roc_auc": np.mean(cv_roc_auc),
                "roc_auc_std": np.std(cv_roc_auc),
                "n_folds": n_folds,
                "n_samples": len(X),
                "n_aprobadas": int(n_aprobadas),
                "n_rechazadas": int(n_rechazadas),
                "balance_ratio": float(balance_ratio),
                "params": {
                    "n_estimators": n_estimators,
                    "max_depth": max_depth,
                    "min_samples_split": min_samples_split,
                    "test_size": test_size,
                },
            }

            self.metricas_de_clases(X, y, y_test, X_test)

        except Exception as e:
            print(f"entrenar_modelo(): {e}")

    def metricas_de_clases(self, X, y, y_test, X_test):
        """Agrega métricas del test set."""
        y_pred = self.modelo.predict(X_test)

        report = classification_report(y_test, y_pred, output_dict=True)
        f1_macro = f1_score(y_test, y_pred, average="macro")
        y_proba = self.modelo.predict_proba(X_test)[:, 1]
        roc_auc = roc_auc_score(y_test, y_proba)

        if self.metrics is None:
            self.metrics = {}
        self.metrics["test_precision"] = report.get("weighted avg", {}).get("precision", 0)
        self.metrics["test_recall"] = report.get("weighted avg", {}).get("recall", 0)
        self.metrics["test_f1"] = report.get("weighted avg", {}).get("f1-score", 0)
        self.metrics["test_accuracy"] = report.get("accuracy", 0)
        self.metrics["f1_macro"] = f1_macro
        self.metrics["test_roc_auc"] = roc_auc

        self.calcular_feature_importance()

    def calcular_feature_importance(self):
        """Calcula importancia de features."""
        if self.modelo is None or not hasattr(self.modelo, "feature_importances_"):
            return

        importances = self.modelo.feature_importances_
        feature_names = self.modelo.feature_names_in_

        indices = np.argsort(importances)[::-1]

        top_features = []
        for i in range(min(10, len(indices))):
            idx = indices[i]
            top_features.append({"feature": feature_names[idx], "importance": float(importances[idx])})

        if self.metrics is None:
            self.metrics = {}
        self.metrics["feature_importance"] = top_features

    def predecir_modelo(self, df):
        """Realiza predicciones para oportunidades de compra."""

        def clasificar(conf, umbral_buy, umbral_obs):
            if conf >= umbral_buy:
                return "buy"
            elif conf >= umbral_obs:
                return "observacion"
            return "descartar"

        try:
            if self.modelo is None:
                print("predecir_modelo(): Modelo no entrenado o cargado.")
                return None

            X_nuevo = df[self.modelo.feature_names_in_].copy()
            X_nuevo = X_nuevo.fillna(0)

            predicciones = self.modelo.predict(X_nuevo)
            probabilidades = self.modelo.predict_proba(X_nuevo)

            df_resultado = df.copy()
            df_resultado["prediccion"] = predicciones
            df_resultado["confianza"] = probabilidades[:, 1]

            umbral_buy = self.params.get("umbral_buy", 0.65)
            umbral_obs = self.params.get("umbral_observacion", 0.35)

            df_resultado["clasificacion"] = df_resultado["confianza"].apply(
                lambda c: clasificar(c, umbral_buy, umbral_obs)
            )

            return df_resultado
        except Exception as e:
            print(f"predecir_modelo(): {e}")
            return None

    def save_modelo(self, file="modelo_ia"):
        """Guarda el modelo y métricas."""
        path_modelo = define_FileCache(f"{file}.pkl")
        path_metrics = define_FileCache(f"{file}_metrics.pkl")
        joblib.dump(self.modelo, path_modelo)
        if self.metrics:
            joblib.dump(self.metrics, path_metrics)

    def load_modelo(self, file="modelo_ia"):
        """Carga el modelo y métricas."""
        path_modelo = define_FileCache(f"{file}.pkl")
        path_metrics = define_FileCache(f"{file}_metrics.pkl")
        try:
            self.modelo = joblib.load(path_modelo)
        except FileNotFoundError:
            self.modelo = None
        try:
            self.metrics = joblib.load(path_metrics)
        except FileNotFoundError:
            self.metrics = None

    def run_entrenamientoBuy(self):
        """Ejecuta el entrenamiento del modelo Buy."""
        datos = self.ReOportunidades.obtener_por_tipo(tipo="buy")
        if datos[0]:
            df = self.convertir_dataset_entrenamiento(datos)
            df = self.aplanar_datos_tecnicos(df)
            self.entrenar_modelo(df)
            self.save_modelo(file=self.modelo_name)


if __name__ == "__main__":
    AiSell = ModeloOportunidadesSell()
    AiSell.run_entraminetoSell()
