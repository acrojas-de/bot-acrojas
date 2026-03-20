@echo off
echo 🚀 Deploy en curso...

git status

git add .

git diff --cached --quiet
if %errorlevel%==0 (
    echo ⚠️ No hay cambios para subir
) else (
    git commit -m "auto deploy"
    git push
    echo ✅ Deploy enviado a Railway
)

pause