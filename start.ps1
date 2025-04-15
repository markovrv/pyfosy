<#
.SYNOPSIS
��������� Python ���������� fos.py �� ������������ ���������

.DESCRIPTION
���� ������:
1. ���������� ����������� ��������� Python (venv)
2. ��������� ���������� fos.py
3. ������� ���������� ������ ����������
#>

# ��������� ����
$venvPath = ".\venv"  # ���� � ������������ ���������
$pythonApp = ".\fos.py"  # ���� � Python ����������

# ��������� ������������� ������������ ���������
if (-not (Test-Path -Path $venvPath)) {
    Write-Host "����������� ��������� �� ������� � $venvPath" -ForegroundColor Red
    Write-Host "�������� ����������� ��������� ��������: python -m venv venv"
    exit 1
}

# ��������� ������������� Python �����
if (-not (Test-Path -Path $pythonApp)) {
    Write-Host "���� ���������� �� ������: $pythonApp" -ForegroundColor Red
    exit 1
}

# ���������� ����������� ���������
try {
    $activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
    if (-not (Test-Path -Path $activateScript)) {
        Write-Host "�� ������ ������ ���������: $activateScript" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "��������� ������������ ���������..." -ForegroundColor Cyan
    . $activateScript
}
catch {
    Write-Host "������ ��������� ������������ ���������: $_" -ForegroundColor Red
    exit 1
}

# ��������� Python � ����������� ���������
try {
    $pythonPath = Join-Path $venvPath "Scripts\python.exe"
    if (-not (Test-Path -Path $pythonPath)) {
        Write-Host "Python �� ������ � ����������� ���������" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "������������ Python �� ������������ ���������: $pythonPath" -ForegroundColor Green
}
catch {
    Write-Host "������ �������� Python: $_" -ForegroundColor Red
    exit 1
}

# ��������� ����������
try {
    Write-Host "������ ���������� $pythonApp..." -ForegroundColor Cyan
    & $pythonPath $pythonApp
    
    # ���� ����� �������� ���������, ����� �������� �� �����:
    # & $pythonPath $pythonApp arg1 arg2
    
    Write-Host "���������� ��������� ������" -ForegroundColor Green
}
catch {
    Write-Host "������ ������� ����������: $_" -ForegroundColor Red
    exit 1
}

# �������������: ����������� ��������� (�� �����������, ��� ��� ��� ����� �������)
# deactivate