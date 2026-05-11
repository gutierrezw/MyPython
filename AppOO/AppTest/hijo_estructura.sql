-- MySQL dump 10.13  Distrib 8.0.44, for Win64 (x86_64)
--
-- Host: localhost    Database: bdinv
-- ------------------------------------------------------
-- Server version	8.0.44

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `booktrading`
--

DROP TABLE IF EXISTS `booktrading`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `booktrading` (
  `id` int NOT NULL AUTO_INCREMENT,
  `sec` int NOT NULL,
  `categoria` char(15) DEFAULT NULL,
  `divisa` char(3) DEFAULT NULL,
  `cuenta` char(10) NOT NULL,
  `simbolo` char(25) NOT NULL,
  `fechahora` datetime(6) DEFAULT NULL,
  `idtrans` char(25) NOT NULL,
  `cantidad` float DEFAULT '0',
  `preciotrans` float DEFAULT '0',
  `preciocierre` float DEFAULT '0',
  `producto` float DEFAULT '0',
  `tarifacomision` float DEFAULT '0',
  `basico` float DEFAULT '0',
  `gprealizadas` float DEFAULT '0',
  `mtmgp` float DEFAULT '0',
  `codigo` char(20) DEFAULT NULL,
  `stock` float DEFAULT '0',
  `sell` float DEFAULT '0',
  `activa` char(1) DEFAULT NULL,
  `split` float DEFAULT '0',
  `factor_cambio` float DEFAULT '1',
  `updateStamp` datetime(6) DEFAULT NULL,
  `hash_id` char(32) DEFAULT NULL,
  `indicadores` blob,
  `delisted` tinyint(1) DEFAULT '0',
  `fecha_deliste` date DEFAULT NULL,
  PRIMARY KEY (`id`,`cuenta`,`simbolo`,`sec`,`idtrans`),
  KEY `booKtrading_synbol` (`cuenta`,`simbolo`,`divisa`,`sec`) USING BTREE,
  KEY `idx_booktrading_cuenta_divisa_simbolo_activa_fechahora_sec` (`cuenta`,`divisa`,`simbolo`,`activa`,`fechahora`,`sec`),
  KEY `idx_hash_id` (`hash_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4506 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Tabla que registra las operaciones de compra y venta de activos. Basepara la construcción de diaria  y perfromance de inversión.';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `inversion`
--

DROP TABLE IF EXISTS `inversion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `inversion` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ticket` char(25) NOT NULL,
  `useraccount` char(10) NOT NULL DEFAULT 'U4214563',
  `conid` char(20) CHARACTER SET armscii8 COLLATE armscii8_general_ci DEFAULT NULL,
  `estrategia` char(3) DEFAULT '',
  `empresa` char(50) DEFAULT NULL,
  `peso` float DEFAULT '0',
  `mrkprice` float DEFAULT '0',
  `open` float DEFAULT '0',
  `dgyp` float DEFAULT '0',
  `costobase` float DEFAULT '0',
  `position` float DEFAULT '0',
  `unrealizedpnl` float DEFAULT '0',
  `dividendo` float DEFAULT '0',
  `dividendYield` float DEFAULT '0',
  `exDividendDate` date DEFAULT '9999-12-31',
  `objetivo` float DEFAULT '0',
  `deuda` float DEFAULT '0',
  `retorno` float DEFAULT '0',
  `fealta` date DEFAULT NULL,
  `febaja` date DEFAULT NULL,
  `iactiva` char(1) DEFAULT NULL,
  `tipoinv` char(10) DEFAULT 'Stock',
  `sectype` char(5) DEFAULT NULL COMMENT 'Indica el tipo de activo  en catalogo SEC',
  `sector` char(30) DEFAULT NULL,
  `factor_cambio` float DEFAULT '1',
  `divisa` char(5) DEFAULT 'USD',
  `nivelIA` char(2) DEFAULT '01',
  `region` varchar(45) DEFAULT NULL,
  `country` varchar(45) DEFAULT NULL,
  `timestamp` timestamp(6) NULL DEFAULT NULL,
  PRIMARY KEY (`id`,`ticket`,`useraccount`),
  KEY `inversion_ticket` (`ticket`,`useraccount`),
  KEY `inversion_tipoinv` (`tipoinv`,`useraccount`,`ticket`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=158 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Tabla que contiene activos de cada vehiculo de inversión';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `oportunidadesbuysell`
--

DROP TABLE IF EXISTS `oportunidadesbuysell`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `oportunidadesbuysell` (
  `id` int NOT NULL AUTO_INCREMENT,
  `symbol` varchar(25) DEFAULT NULL,
  `account` char(10) DEFAULT 'U4214563',
  `vehiculo` char(10) DEFAULT 'Stock',
  `opcion` varchar(10) DEFAULT NULL,
  `tipo` varchar(10) DEFAULT NULL,
  `subtipo` varchar(20) DEFAULT NULL,
  `origen` varchar(20) DEFAULT NULL,
  `hash_id` char(32) DEFAULT NULL,
  `json_detalle` json DEFAULT NULL,
  `timestamp` datetime DEFAULT CURRENT_TIMESTAMP,
  `fecha` date DEFAULT NULL,
  `recomendado` decimal(8,4) DEFAULT NULL,
  `estado` varchar(20) DEFAULT 'pendiente',
  `nota` text,
  `enviada` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `idx_hash_id` (`hash_id`)
) ENGINE=InnoDB AUTO_INCREMENT=542 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Tabla para almacenar las oportunidadesd de Buy & Sell  que pasara por la modelos de IA -- a afin de automatizar las decisicones para la operación del sistema \ncast(`timestamp` as date)';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `order_trader`
--

DROP TABLE IF EXISTS `order_trader`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `order_trader` (
  `id` int NOT NULL AUTO_INCREMENT,
  `account` char(10) NOT NULL,
  `vehiculo` char(10) NOT NULL,
  `conid` char(20) NOT NULL,
  `id_order` char(40) DEFAULT NULL,
  `symbol` char(25) DEFAULT NULL,
  `orderType` char(10) DEFAULT NULL,
  `price` float DEFAULT NULL,
  `side` char(4) DEFAULT NULL,
  `intent` char(10) DEFAULT NULL COMMENT 'Intent	Significado\n\n==========================\nENTRY	Apertura de posición\n\nTP1	Toma de ganancia parcial 1\n\nTP2	Toma de ganancia parcial 2\n\nEXIT	Cierre total de posición',
  `tif` char(4) DEFAULT NULL,
  `quantity` float DEFAULT NULL,
  `status` char(30) DEFAULT NULL,
  `stampPlace` timestamp(6) NULL DEFAULT NULL,
  `clientOrderId` char(40) DEFAULT NULL,
  `stampSubmit` timestamp(6) NULL DEFAULT NULL,
  `hash_id_oportunidad` char(32) DEFAULT NULL,
  PRIMARY KEY (`id`,`account`,`vehiculo`,`conid`),
  KEY `idx_account_symbol` (`account`,`symbol`),
  CONSTRAINT `chk_intent` CHECK ((`intent` in (_utf8mb4'ENTRY',_utf8mb4'TP1',_utf8mb4'TP2',_utf8mb4'EXIT')))
) ENGINE=InnoDB AUTO_INCREMENT=524 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Estructura para almacenar odenes colocadas y sy correspondiente id y status';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `diaria_performance`
--

DROP TABLE IF EXISTS `diaria_performance`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `diaria_performance` (
  `id` int NOT NULL AUTO_INCREMENT,
  `account` char(10) NOT NULL,
  `Date` date NOT NULL,
  `symbol` char(25) NOT NULL,
  `AdjClose` float DEFAULT NULL,
  `value` float DEFAULT NULL,
  `cantidad` float DEFAULT NULL,
  `costo_base` float DEFAULT NULL,
  `performa` float DEFAULT NULL,
  `gyp_dia` float DEFAULT NULL,
  `nr_gyp` float DEFAULT NULL,
  `comisiones` float DEFAULT NULL,
  `dividends` float DEFAULT NULL,
  `factor_cambio` float DEFAULT '1',
  PRIMARY KEY (`id`,`Date`,`account`,`symbol`),
  UNIQUE KEY `diaria_performance_symbol` (`account`,`symbol`,`Date`) USING BTREE,
  KEY `diaria_performance_date` (`account`,`Date`,`symbol`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=85704 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `performa_inversion`
--

DROP TABLE IF EXISTS `performa_inversion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `performa_inversion` (
  `id` int NOT NULL AUTO_INCREMENT,
  `idcuenta` char(10) NOT NULL,
  `vehiculo` char(10) NOT NULL,
  `fechaclose` date NOT NULL,
  `referencia` char(10) NOT NULL,
  `p_referencia` float DEFAULT NULL,
  `p_vehiculo` float DEFAULT NULL,
  `gyp_dia` float DEFAULT NULL,
  `nr_gyp` float DEFAULT NULL,
  `value` float DEFAULT NULL,
  `costo_base` float DEFAULT NULL,
  `dividends` float DEFAULT NULL,
  `timestamp` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`,`idcuenta`,`vehiculo`,`fechaclose`,`referencia`),
  KEY `idx_idcuenta_vehiculo` (`idcuenta`,`vehiculo`),
  KEY `idx_fechaclose` (`fechaclose`)
) ENGINE=InnoDB AUTO_INCREMENT=4956 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Contiene desempeño del vehiculo implecado y su indice de referencia\n\nValor del portafolio=∑(Posici \no\nˊ\n n \ni\n​\n ×Precio de cierre \ni\n​\n )+Dividendos totales+Ganancias realizadas totales\nPuedes normalizar este valor respecto al día inicial:\n\nI\nˊ\nndice de desempe\nn\n˜\no\n=\nValor del portafolio en el d\nı\nˊ\na actual\nValor del portafolio en el d\nı\nˊ\na inicial\n×\n100\nI\nˊ\n ndice de desempe \nn\n˜\n o= \nValor del portafolio en el d \nı\nˊ\n a inicial\nValor del portafolio en el d \nı\nˊ\n a actual\n​\n ×100\nb. Índice ponderado por retornos\nCalcula los retornos diarios para cada acción y genera un promedio ponderado según su peso en el portafolio.\n\nFórmula:\n\nRetorno ponderado diario\n=\n∑\n(\nPosici\no\nˊ\nn\n?\n×\nPrecio de cierre\n?\nValor total del portafolio\n×\nRetorno\n?\n)\nRetorno ponderado diario=∑( \nValor total del portafolio\nPosici \no\nˊ\n n \ni\n​\n ×Precio de cierre \ni\n​\n \n​\n ×Retorno \ni\n​\n )\nEl retorno de cada acción (\nRetorno\n?\nRetorno \ni\n​\n ) se calcula como:\n\nRetorno\n?\n=\nPrecio de cierre\n?\nCosto base\n?\n−\n1\nRetorno \ni\n​\n = \nCosto base \ni\n​\n \nPrecio de cierre \ni\n​\n \n​\n −1\n';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `otros_activos`
--

DROP TABLE IF EXISTS `otros_activos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `otros_activos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `symbol` char(25) NOT NULL,
  `cuenta` char(10) DEFAULT 'B0000001',
  `idcrypto` bigint DEFAULT NULL,
  `descripcion` char(80) DEFAULT NULL,
  `base_asset` char(25) DEFAULT NULL,
  `quote_asset` char(10) DEFAULT NULL,
  `avgcost` float DEFAULT '0',
  `objetivo` float DEFAULT '0',
  `indicadores` blob,
  `fecupdate` datetime DEFAULT NULL,
  PRIMARY KEY (`id`,`symbol`),
  KEY `otros_symbol` (`symbol`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=151 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `extractos`
--

DROP TABLE IF EXISTS `extractos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `extractos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `extracto` date NOT NULL,
  `idcuenta` char(10) NOT NULL,
  `depositos` float DEFAULT NULL,
  `retiros` float DEFAULT NULL,
  `crecimiento` float DEFAULT NULL,
  `dividendos` float DEFAULT NULL,
  `perdidas` float DEFAULT NULL,
  `fee` float DEFAULT NULL,
  `comisiones` float DEFAULT NULL,
  `tax` float DEFAULT NULL,
  `cierreanterior` float DEFAULT NULL,
  `navcierre` float DEFAULT NULL,
  `costobase` float DEFAULT NULL,
  `idevengo` float DEFAULT NULL,
  `imargen` float DEFAULT NULL,
  PRIMARY KEY (`id`,`idcuenta`,`extracto`)
) ENGINE=InnoDB AUTO_INCREMENT=202 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sesion`
--

DROP TABLE IF EXISTS `sesion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sesion` (
  `id` int NOT NULL AUTO_INCREMENT,
  `vehiculo` char(10) NOT NULL,
  `fesesion` datetime DEFAULT NULL,
  `iduser` char(10) DEFAULT NULL,
  `idcuenta` char(10) DEFAULT NULL,
  `Idcuenta_principal` tinyint DEFAULT '0' COMMENT 'Indicador True --  vehiculo que prevalece en fiscalyear para el portafolio\\\\n',
  `id_transaccion` tinyint DEFAULT '0',
  `load_csv` tinyint DEFAULT '0' COMMENT 'Indicador True --  que necesita cargar CSV para procesar fin de mes\\\\\\\\n',
  `orcartera` char(50) DEFAULT NULL,
  `fiscalYear` date DEFAULT NULL,
  `fefund` date DEFAULT NULL,
  `Pinvertir` int DEFAULT NULL,
  `gypPrecio` float DEFAULT '0',
  `gainInversion` float DEFAULT '0',
  `xstrategy` char(60) DEFAULT NULL,
  `environment` varchar(45) DEFAULT NULL COMMENT 'Captura en entorno de trabajo TEST o PROD para usos de endpoint en las API',
  `userapi` blob,
  `userpass` blob,
  `private_key` blob,
  `public_key` blob,
  `port` smallint DEFAULT NULL,
  `parameters` blob COMMENT 'CAmpo para almacenar paranetros del vehiculo,   Por ejemplo: prameters  referente a la proteción de las ganancias',
  PRIMARY KEY (`id`,`vehiculo`),
  KEY `sesion_vehiculo` (`vehiculo`,`idcuenta`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `trazaplan`
--

DROP TABLE IF EXISTS `trazaplan`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `trazaplan` (
  `id` int NOT NULL AUTO_INCREMENT,
  `idcuenta` char(10) NOT NULL,
  `meta` int NOT NULL,
  `extracto` date DEFAULT NULL,
  `vision` float DEFAULT NULL,
  `costobase` float DEFAULT NULL,
  `dividendo` float DEFAULT NULL,
  `ccapital` float DEFAULT NULL,
  `trendimiento` float DEFAULT NULL,
  `tinversion` float DEFAULT NULL,
  `efectividad` float DEFAULT NULL,
  `status` char(20) DEFAULT NULL,
  `recompensa` char(20) DEFAULT NULL,
  `timestamp` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_idcuenta` (`idcuenta`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `fin_accounts`
--

DROP TABLE IF EXISTS `fin_accounts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `fin_accounts` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(80) NOT NULL,
  `type` enum('checking','credit','savings','investment','debit') NOT NULL,
  `currency` char(5) NOT NULL DEFAULT 'ARS',
  `balance` decimal(18,2) DEFAULT '0.00',
  `opening_balance` decimal(18,2) DEFAULT '0.00',
  `credit_limit` decimal(18,2) DEFAULT NULL,
  `bank_id` int NOT NULL,
  `account_number_last4` char(10) DEFAULT NULL,
  `account_ref` varchar(40) DEFAULT NULL COMMENT 'Número de cuenta completo o referencia del banco',
  `institution` varchar(80) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `short_name` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_account` (`bank_id`,`account_ref`,`currency`),
  CONSTRAINT `fin_accounts_ibfk_1` FOREIGN KEY (`bank_id`) REFERENCES `fin_banks` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=35 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `fin_exchange_rates`
--

DROP TABLE IF EXISTS `fin_exchange_rates`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `fin_exchange_rates` (
  `id` int NOT NULL AUTO_INCREMENT,
  `from_currency` char(3) NOT NULL,
  `to_currency` char(4) NOT NULL DEFAULT 'USDT',
  `rate` decimal(18,8) NOT NULL,
  `date` date NOT NULL,
  `source` enum('binance','manual') NOT NULL DEFAULT 'manual',
  `pair` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_rate_date` (`from_currency`,`to_currency`,`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `fin_statement_imports`
--

DROP TABLE IF EXISTS `fin_statement_imports`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `fin_statement_imports` (
  `id` int NOT NULL AUTO_INCREMENT,
  `account_id` int NOT NULL,
  `bank_id` int NOT NULL,
  `filename` varchar(200) DEFAULT NULL,
  `file_hash` char(64) NOT NULL COMMENT 'SHA-256 del archivo',
  `section` varchar(60) DEFAULT NULL COMMENT 'Sección dentro del PDF (ej: visa_credito, cuenta_ars)',
  `period_from` date DEFAULT NULL,
  `period_to` date DEFAULT NULL,
  `imported_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `row_count` int DEFAULT '0',
  `processed_count` int DEFAULT '0',
  `skipped_count` int DEFAULT '0',
  `status` enum('pending','processed','error') NOT NULL DEFAULT 'pending',
  `error_log` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_import` (`file_hash`,`section`),
  KEY `account_id` (`account_id`),
  KEY `bank_id` (`bank_id`),
  CONSTRAINT `fin_statement_imports_ibfk_1` FOREIGN KEY (`account_id`) REFERENCES `fin_accounts` (`id`),
  CONSTRAINT `fin_statement_imports_ibfk_2` FOREIGN KEY (`bank_id`) REFERENCES `fin_banks` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=129 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `fin_transactions`
--

DROP TABLE IF EXISTS `fin_transactions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `fin_transactions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `date` date NOT NULL,
  `type` enum('income','expense','transfer') NOT NULL,
  `amount` decimal(18,2) NOT NULL,
  `currency` char(5) NOT NULL DEFAULT 'ARS',
  `amount_usdt` decimal(18,8) DEFAULT NULL COMMENT 'Convertido a USDT al rate del día',
  `category_id` int DEFAULT NULL,
  `account_id` int NOT NULL,
  `description` varchar(300) DEFAULT NULL COMMENT 'Descripción limpia (editable)',
  `raw_description` varchar(300) NOT NULL COMMENT 'Texto original del extracto — no editar',
  `raw_description_detail` varchar(300) DEFAULT NULL COMMENT 'Segunda línea del extracto (Santander)',
  `comprobante` varchar(20) DEFAULT NULL COMMENT 'Número de referencia/cupón del banco',
  `import_id` int DEFAULT NULL,
  `classified_by` enum('rule','ai','manual','synthetic') DEFAULT NULL,
  `classification_confidence` float DEFAULT NULL,
  `is_recurring` tinyint(1) NOT NULL DEFAULT '0',
  `recurring_group_id` int DEFAULT NULL,
  `installment_current` tinyint DEFAULT NULL COMMENT 'Cuota actual (ej: 1)',
  `installment_total` tinyint DEFAULT NULL COMMENT 'Total cuotas (ej: 6)',
  `tags` varchar(200) DEFAULT NULL,
  `notes` text,
  `needs_review` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_tx` (`account_id`,`date`,`amount`,`raw_description`(150)),
  KEY `category_id` (`category_id`),
  KEY `import_id` (`import_id`),
  CONSTRAINT `fin_transactions_ibfk_1` FOREIGN KEY (`category_id`) REFERENCES `fin_categories` (`id`),
  CONSTRAINT `fin_transactions_ibfk_2` FOREIGN KEY (`account_id`) REFERENCES `fin_accounts` (`id`),
  CONSTRAINT `fin_transactions_ibfk_3` FOREIGN KEY (`import_id`) REFERENCES `fin_statement_imports` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1650 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `market`
--

DROP TABLE IF EXISTS `market`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `market` (
  `id` int NOT NULL AUTO_INCREMENT,
  `account` char(10) NOT NULL DEFAULT 'U4214563',
  `tipo` char(10) NOT NULL DEFAULT 'Dividends' COMMENT 'Tipo de activo::  Diividends y/o crecimiento  ',
  `symbol` char(10) NOT NULL,
  `lastFiscalYearEnd` date DEFAULT NULL,
  `shortName` varchar(60) DEFAULT NULL,
  `firstTradeDateEpochUtc` date DEFAULT NULL,
  `categoriaActivo` char(4) NOT NULL,
  `encartera` char(1) DEFAULT NULL,
  `favorito` tinyint(1) DEFAULT '0' COMMENT '0: no es favorito\\n1: es marcado como favorito',
  `lastPrice` float DEFAULT NULL,
  `previousClose` float DEFAULT NULL,
  `open` float DEFAULT NULL,
  `marketCap` float DEFAULT NULL,
  `monthDividendsPay` varchar(120) DEFAULT NULL,
  `dividendRate` float DEFAULT NULL,
  `dividendYield` float DEFAULT NULL,
  `exDividendDate` date DEFAULT NULL,
  `payoutRatio` float DEFAULT NULL,
  `country` varchar(45) DEFAULT NULL,
  `volume` int DEFAULT NULL,
  `sector` varchar(45) DEFAULT NULL,
  `industry` varchar(45) DEFAULT NULL,
  `website` varchar(200) DEFAULT NULL,
  `fiveYearAvgDividendYield` float DEFAULT NULL,
  `trailingAnnualDividendRate` float DEFAULT '0',
  `trailingAnnualDividendYield` float DEFAULT NULL,
  `ttmDividends` float DEFAULT NULL,
  `nextDividend` float DEFAULT NULL,
  `trazaDividends` blob,
  `lastDividendValue` float DEFAULT NULL,
  `beta` float DEFAULT NULL,
  `trailingPE` float DEFAULT NULL,
  `forwardPE` float DEFAULT NULL,
  `pegRatio` float DEFAULT NULL,
  `averageVolume` int DEFAULT NULL,
  `fiftyTwoWeekLow` float DEFAULT NULL,
  `fiftyTwoWeekHigh` float DEFAULT NULL,
  `fiftyDayAverage` float DEFAULT NULL,
  `twoHundredDayAverage` float DEFAULT NULL,
  `currency` char(6) DEFAULT NULL,
  `priceToBook` float DEFAULT NULL,
  `trailingEps` float DEFAULT NULL,
  `forwardEps` float DEFAULT NULL,
  `targetHighPrice` float DEFAULT NULL,
  `targetLowPrice` float DEFAULT NULL,
  `targetMeanPrice` float DEFAULT NULL,
  `totalDebt` float DEFAULT NULL,
  `returnOnAssets` float DEFAULT NULL,
  `returnOnEquity` float DEFAULT NULL,
  `earningsGrowth` float DEFAULT NULL,
  `revenueGrowth` float DEFAULT NULL,
  `freeCashflow` float DEFAULT NULL,
  `grossMargins` float DEFAULT NULL,
  `ebitdaMargins` float DEFAULT NULL,
  `operatingMargins` float DEFAULT NULL,
  `financialCurrency` char(6) DEFAULT NULL,
  `trailingPegRatio` float DEFAULT NULL,
  `ema200` float DEFAULT NULL,
  `ema100` float DEFAULT NULL,
  `ema50` float DEFAULT NULL,
  `ema20` float DEFAULT NULL,
  `timestamp` timestamp(6) NULL DEFAULT NULL,
  `inst_funds` int DEFAULT NULL,
  `inst_shares` bigint DEFAULT NULL,
  `inst_score` float DEFAULT NULL,
  `inst_update` datetime DEFAULT NULL,
  `inst_ownership_pct` float DEFAULT NULL,
  `insider_ownership_pct` float DEFAULT NULL,
  `inst_top_holder` varchar(120) DEFAULT NULL,
  `inst_top_holder_shares` bigint DEFAULT NULL,
  `cusip` varchar(9) DEFAULT NULL,
  `fh_count` int DEFAULT NULL,
  `fh_total_value` bigint DEFAULT NULL,
  `fh_buy_ratio` decimal(6,4) DEFAULT NULL,
  `fh_sell_ratio` decimal(6,4) DEFAULT NULL,
  `fh_call_shares` bigint DEFAULT NULL,
  `fh_put_shares` bigint DEFAULT NULL,
  `new_entrants` int DEFAULT NULL,
  `full_exits` int DEFAULT NULL,
  `delta_call_shares` bigint DEFAULT NULL,
  `delta_put_shares` bigint DEFAULT NULL,
  `analyst_rec` varchar(20) DEFAULT NULL,
  `analyst_mean` float DEFAULT NULL,
  `analyst_count` smallint DEFAULT NULL,
  `sharesOutstanding` bigint DEFAULT NULL,
  `floatShares` bigint DEFAULT NULL,
  `consenso_tag` varchar(15) DEFAULT NULL,
  `consenso_suma` tinyint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_symbol` (`symbol`),
  KEY `idx_cusip` (`cusip`)
) ENGINE=InnoDB AUTO_INCREMENT=11470 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Contiene todos los simbolos negociables de NASDAQ,  para analisis de oportunidades e indicadores de acumulación.   Tambienposeen información relevantes en cada activo.\n';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `funds`
--

DROP TABLE IF EXISTS `funds`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `funds` (
  `id` int NOT NULL AUTO_INCREMENT,
  `fund_name` varchar(200) NOT NULL,
  `cik` varchar(20) DEFAULT NULL,
  `frequency` int DEFAULT '0',
  `last_update` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_cik` (`cik`)
) ENGINE=InnoDB AUTO_INCREMENT=53944 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Tabla para almacenar los principales fondos instituciones que valorans acción de inteés ';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `fund_filings`
--

DROP TABLE IF EXISTS `fund_filings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `fund_filings` (
  `filename` varchar(200) NOT NULL,
  `cik` varchar(10) NOT NULL,
  `fund_name` varchar(200) NOT NULL,
  `filing_date` date NOT NULL,
  `accession` varchar(20) NOT NULL,
  `processed` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`filename`),
  KEY `idx_cik` (`cik`),
  KEY `idx_filing_date` (`filing_date`),
  KEY `idx_processed` (`processed`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `fund_holdings`
--

DROP TABLE IF EXISTS `fund_holdings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `fund_holdings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `fund_id` int DEFAULT NULL,
  `cusip` varchar(12) DEFAULT NULL,
  `symbol` varchar(20) DEFAULT NULL,
  `shares` bigint DEFAULT NULL,
  `value` decimal(20,2) DEFAULT NULL,
  `report_date` date DEFAULT NULL,
  `shares_prev` bigint DEFAULT NULL,
  `shares_delta` bigint DEFAULT NULL,
  `pct_change` float DEFAULT NULL,
  `operation` varchar(10) DEFAULT NULL,
  `option_type` varchar(10) NOT NULL DEFAULT 'STK',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_holding` (`fund_id`,`cusip`,`report_date`,`option_type`),
  KEY `idx_cusip` (`cusip`),
  KEY `idx_fund_date` (`fund_id`,`report_date`),
  KEY `idx_report_date` (`report_date`)
) ENGINE=InnoDB AUTO_INCREMENT=1203528 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-05-10 17:08:57
