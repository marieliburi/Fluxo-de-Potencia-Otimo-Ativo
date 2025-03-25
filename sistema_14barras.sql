-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Tempo de geração: 25-Mar-2025 às 22:28
-- Versão do servidor: 10.4.32-MariaDB
-- versão do PHP: 8.0.30

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Banco de dados: `sistema_14barras`
--

-- --------------------------------------------------------

--
-- Estrutura da tabela `dadosbarra`
--

CREATE TABLE `dadosbarra` (
  `barra` int(11) NOT NULL,
  `tipo` int(11) NOT NULL,
  `Pg` decimal(6,3) NOT NULL,
  `Qg` decimal(6,3) NOT NULL,
  `Qmin` decimal(6,2) NOT NULL,
  `Qmax` decimal(6,2) NOT NULL,
  `Pc` decimal(6,3) NOT NULL,
  `Qc` decimal(6,3) NOT NULL,
  `bsh` decimal(6,2) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Extraindo dados da tabela `dadosbarra`
--

INSERT INTO `dadosbarra` (`barra`, `tipo`, `Pg`, `Qg`, `Qmin`, `Qmax`, `Pc`, `Qc`, `bsh`) VALUES
(1, 2, 0.000, 0.000, -99.99, 99.99, 0.000, 0.000, 0.00),
(2, 1, 0.000, 0.000, -0.40, 0.50, -0.183, 0.127, 0.00),
(3, 1, 0.000, 0.000, 0.00, 0.20, 0.942, 0.190, 0.00),
(4, 0, 0.000, 0.000, 0.00, 0.00, 0.478, -0.039, 0.00),
(5, 0, 0.000, 0.000, 0.00, 0.00, 0.076, 0.016, 0.00),
(6, 1, 0.000, 0.000, -0.06, 0.24, 0.112, 0.075, 0.00),
(7, 0, 0.000, 0.000, 0.00, 0.00, 0.000, 0.000, 0.00),
(8, 1, 0.000, 0.000, -0.06, 0.24, 0.000, 0.000, 0.00),
(9, 0, 0.000, 0.000, 0.00, 0.00, 0.295, 0.166, 0.19),
(10, 0, 0.000, 0.000, 0.00, 0.00, 0.090, 0.058, 0.00),
(11, 0, 0.000, 0.000, 0.00, 0.00, 0.035, 0.018, 0.00),
(12, 0, 0.000, 0.000, 0.00, 0.00, 0.061, 0.016, 0.00),
(13, 0, 0.000, 0.000, 0.00, 0.00, 0.135, 0.058, 0.00),
(14, 0, 0.000, 0.000, 0.00, 0.00, 0.149, 0.050, 0.00);

-- --------------------------------------------------------

--
-- Estrutura da tabela `dadoslinha`
--

CREATE TABLE `dadoslinha` (
  `Barra_Origem` int(11) NOT NULL,
  `Barra_Destino` int(11) NOT NULL,
  `g` decimal(10,8) NOT NULL,
  `b` decimal(10,8) NOT NULL,
  `bsh` decimal(6,4) NOT NULL,
  `tap` decimal(6,4) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Extraindo dados da tabela `dadoslinha`
--

INSERT INTO `dadoslinha` (`Barra_Origem`, `Barra_Destino`, `g`, `b`, `bsh`, `tap`) VALUES
(1, 2, 4.99913160, -15.26308652, 0.0264, 1.0000),
(1, 5, 1.02589745, -4.23498368, 0.0246, 1.0000),
(2, 3, 1.13501919, -4.78186315, 0.0219, 1.0000),
(2, 4, 1.68603315, -5.11583833, 0.0187, 1.0000),
(2, 5, 1.70113967, -5.19392740, 0.0170, 1.0000),
(3, 4, 1.98597571, -5.06881698, 0.0173, 1.0000),
(4, 5, 6.84098066, -21.57855398, 0.0064, 1.0000),
(4, 7, 0.00000000, -4.78194338, 0.0000, 1.0225),
(4, 9, 0.00000000, -1.79797907, 0.0000, 1.0320),
(5, 6, 0.00000000, -3.96793905, 0.0000, 1.0730),
(6, 11, 1.95502856, -4.09407434, 0.0000, 1.0000),
(6, 12, 1.52596744, -3.17596397, 0.0000, 1.0000),
(6, 13, 3.09892740, -6.10275545, 0.0000, 1.0000),
(7, 8, 0.00000322, -5.67697983, 0.0000, 1.0000),
(7, 9, 0.00000000, -9.09008272, 0.0000, 1.0000),
(9, 10, 3.90204955, -10.36539413, 0.0000, 1.0000),
(9, 14, 1.42400549, -3.02905046, 0.0000, 1.0000),
(10, 11, 1.88088475, -4.40294375, 0.0000, 1.0000),
(12, 13, 2.48902459, -2.25197463, 0.0000, 1.0000),
(13, 14, 1.13699416, -2.31496348, 0.0000, 1.0000);

--
-- Índices para tabelas despejadas
--

--
-- Índices para tabela `dadosbarra`
--
ALTER TABLE `dadosbarra`
  ADD PRIMARY KEY (`barra`);

--
-- Índices para tabela `dadoslinha`
--
ALTER TABLE `dadoslinha`
  ADD PRIMARY KEY (`Barra_Origem`,`Barra_Destino`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
