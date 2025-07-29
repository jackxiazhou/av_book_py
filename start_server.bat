@echo off
echo ========================================
echo    🎬 AVBook Python版本 - 启动脚本
echo ========================================
echo.

cd /d "%~dp0"

echo 📊 检查数据库状态...
backend\venv\Scripts\python.exe backend\manage.py check_data
echo.

echo 🚀 启动Django开发服务器...
echo 服务器地址: http://localhost:8000
echo 管理后台: http://localhost:8000/admin/ (admin/admin123)
echo API文档: http://localhost:8000/api/docs/
echo.
echo 按 Ctrl+C 停止服务器
echo ========================================

backend\venv\Scripts\python.exe backend\manage.py runserver 0.0.0.0:8000
