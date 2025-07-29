@echo off
echo ========================================
echo    AVBook 爬虫系统启动脚本
echo ========================================

cd /d "%~dp0"

echo 1. 激活虚拟环境...
call new_venv\Scripts\activate

echo 2. 检查MySQL服务...
net start mysql8 2>nul
if %errorlevel% neq 0 (
    echo MySQL服务已在运行或启动失败
) else (
    echo MySQL服务启动成功
)

echo 3. 检查系统状态...
python system_status.py

echo 4. 启动Django开发服务器...
start "Django Server" cmd /k "new_venv\Scripts\activate && python backend\manage.py runserver 0.0.0.0:8000"

echo 5. 等待Django服务器启动...
timeout /t 5 /nobreak >nul

echo 6. 启动定时任务调度器...
start "Scheduler" cmd /k "new_venv\Scripts\activate && python backend\manage.py schedule_crawler run --daemon"

echo 7. 等待服务启动完成...
timeout /t 3 /nobreak >nul

echo 8. 打开管理界面...
start http://localhost:8000/admin/

echo ========================================
echo    系统启动完成！
echo ========================================
echo.
echo 🌐 访问地址:
echo    Django管理后台: http://localhost:8000/admin/
echo    API接口: http://localhost:8000/api/
echo.
echo 🚀 常用命令:
echo    查看状态: python system_status.py
echo    手动爬取: python backend\manage.py crawl_avmoo --pages=5
echo    查看任务: python backend\manage.py schedule_crawler list
echo.
echo 按任意键退出...
pause >nul
