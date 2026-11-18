-- phpMyAdmin SQL Dump
-- version 5.2.3
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Generation Time: Oct 26, 2026 at 01:48 PM
-- Server version: 8.4.10
-- PHP Version: 8.3.32

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `absensi_web`
--

-- --------------------------------------------------------

--
-- Table structure for table `attendance_records`
--

CREATE TABLE `attendance_records` (
  `id` int UNSIGNED NOT NULL,
  `user_id` int UNSIGNED NOT NULL,
  `schedule_id` int UNSIGNED NOT NULL,
  `status` enum('HADIR','TERLAMBAT') COLLATE utf8mb4_unicode_ci NOT NULL,
  `attendance_time` datetime NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `attendance_records`
--

INSERT INTO `attendance_records` (`id`, `user_id`, `schedule_id`, `status`, `attendance_time`, `created_at`) VALUES
(1, 2, 6, 'TERLAMBAT', '2026-10-21 13:35:12', '2026-10-21 06:35:12'),
(2, 2, 1, 'TERLAMBAT', '2026-10-26 08:11:43', '2026-10-26 01:11:44'),
(3, 2, 2, 'TERLAMBAT', '2026-10-26 10:16:30', '2026-10-26 03:16:31');

-- --------------------------------------------------------

--
-- Table structure for table `schedules`
--

CREATE TABLE `schedules` (
  `id` int UNSIGNED NOT NULL,
  `course` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `lecturer` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sks` tinyint UNSIGNED NOT NULL,
  `room` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `day` tinyint UNSIGNED NOT NULL,
  `start_time` time NOT NULL,
  `end_time` time NOT NULL
) ;

--
-- Dumping data for table `schedules`
--

INSERT INTO `schedules` (`id`, `course`, `code`, `lecturer`, `sks`, `room`, `day`, `start_time`, `end_time`) VALUES
(1, 'Mobile Programming', '912', 'MKU', 3, 'Lab.1', 0, '07:30:00', '10:00:00'),
(2, 'Machine Learning', '0322', 'RAP', 3, '201-A1', 0, '10:00:00', '12:30:00'),
(3, 'Kecerdasan Buatan', '0788', 'SHE', 3, '201-A1', 1, '07:30:00', '10:00:00'),
(4, 'Penelitian ilmu komputer', '0312', 'VTA', 3, '201-A1', 1, '10:00:00', '12:30:00'),
(5, 'Aljabar Linier', '0708', 'IAL', 3, '201-A1', 2, '10:00:00', '12:30:00'),
(6, 'Pengolahan Citra', '0093', 'TYS', 3, '302-A1', 2, '12:30:00', '15:00:00'),
(7, 'Manajemen Proyek Perangkat Lunak', '0100', 'RZL', 3, '302-A1', 3, '12:30:00', '15:00:00');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int UNSIGNED NOT NULL,
  `name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nim` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `face_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `name`, `nim`, `email`, `password`, `face_name`, `created_at`) VALUES
(1, 'Gilang Saputra', '15240328', 'gilang@gmail.com', '$2a$12$MeBQTutB/DlhtADYm5Vub.sLsRq5xyYKlk98Mc6q678uZcZU2JlyO', 'Gilang', '2026-10-21 03:47:34'),
(2, 'Andra Fishabegti', '15240928', 'andra@gmail.com', '$2a$12$MeBQTutB/DlhtADYm5Vub.sLsRq5xyYKlk98Mc6q678uZcZU2JlyO', 'Andra', '2026-10-21 03:47:34'),
(3, 'Pascal Aimar Fawwaz', '15240850', 'aimar@gmail.com', '$2a$12$MeBQTutB/DlhtADYm5Vub.sLsRq5xyYKlk98Mc6q678uZcZU2JlyO', 'Aimar', '2026-10-21 03:47:34');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `attendance_records`
--
ALTER TABLE `attendance_records`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_attendance_user` (`user_id`),
  ADD KEY `idx_attendance_schedule` (`schedule_id`),
  ADD KEY `idx_attendance_time` (`attendance_time`);

--
-- Indexes for table `schedules`
--
ALTER TABLE `schedules`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_schedules_code_day_start` (`code`,`day`,`start_time`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_users_nim` (`nim`),
  ADD UNIQUE KEY `uq_users_email` (`email`),
  ADD UNIQUE KEY `uq_users_face_name` (`face_name`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `attendance_records`
--
ALTER TABLE `attendance_records`
  MODIFY `id` int UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `schedules`
--
ALTER TABLE `schedules`
  MODIFY `id` int UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `attendance_records`
--
ALTER TABLE `attendance_records`
  ADD CONSTRAINT `fk_attendance_schedule` FOREIGN KEY (`schedule_id`) REFERENCES `schedules` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_attendance_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
