<#
.SYNOPSIS
Запускает Python приложение fos.py из виртуального окружения

.DESCRIPTION
Этот скрипт:
1. Активирует виртуальное окружение Python (venv)
2. Запускает приложение fos.py
3. Ожидает завершения работы приложения
#>

# Указываем пути
$venvPath = ".\venv"  # Путь к виртуальному окружению
$pythonApp = ".\fos.py"  # Путь к Python приложению

# Проверяем существование виртуального окружения
if (-not (Test-Path -Path $venvPath)) {
    Write-Host "Виртуальное окружение не найдено в $venvPath" -ForegroundColor Red
    Write-Host "Создайте виртуальное окружение командой: python -m venv venv"
    exit 1
}

# Проверяем существование Python файла
if (-not (Test-Path -Path $pythonApp)) {
    Write-Host "Файл приложения не найден: $pythonApp" -ForegroundColor Red
    exit 1
}

# Активируем виртуальное окружение
try {
    $activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
    if (-not (Test-Path -Path $activateScript)) {
        Write-Host "Не найден скрипт активации: $activateScript" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Активация виртуального окружения..." -ForegroundColor Cyan
    . $activateScript
}
catch {
    Write-Host "Ошибка активации виртуального окружения: $_" -ForegroundColor Red
    exit 1
}

# Проверяем Python в виртуальном окружении
try {
    $pythonPath = Join-Path $venvPath "Scripts\python.exe"
    if (-not (Test-Path -Path $pythonPath)) {
        Write-Host "Python не найден в виртуальном окружении" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Используется Python из виртуального окружения: $pythonPath" -ForegroundColor Green
}
catch {
    Write-Host "Ошибка проверки Python: $_" -ForegroundColor Red
    exit 1
}

# Запускаем приложение
try {
    Write-Host "Запуск приложения $pythonApp..." -ForegroundColor Cyan
    & $pythonPath $pythonApp
    
    # Если нужно передать аргументы, можно добавить их здесь:
    # & $pythonPath $pythonApp arg1 arg2
    
    Write-Host "Приложение завершило работу" -ForegroundColor Green
}
catch {
    Write-Host "Ошибка запуска приложения: $_" -ForegroundColor Red
    exit 1
}

# Дополнительно: деактивация окружения (не обязательно, так как это новый процесс)
# deactivate