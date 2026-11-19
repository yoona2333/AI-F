SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS `ai_family_fastapi`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE `ai_family_fastapi`;

-- 基础脚手架不预置用户、角色等业务表。
-- 各课程章节需要的数据表，会跟随对应课程逐步创建。
