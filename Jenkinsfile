pipeline {
    agent any // Se ejecuta en cualquier agente de Jenkins disponible

    environment {
        // Aquí podrías definir variables de entorno si tus pruebas las necesitan
        // EJ: DB_HOST = 'localhost'
    }

    stages {
        stage('Checkout') {
            steps {
                // Jenkins descarga el código de la rama actual (el PR)
                checkout scm
            }
        }

        stage('Preparar Entorno') {
            steps {
                echo "Creando entorno virtual e instalando dependencias..."
                // Suponiendo que Jenkins tiene Python 3.12 instalado
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Lint & Formateo (Flake8 / Black)') {
            steps {
                echo "Ejecutando Flake8 y Black..."
                sh '''
                    . venv/bin/activate
                    // Instala linter si no está en requirements.txt
                    pip install flake8 black
                    // Verifica la sintaxis. Si esto falla, el build falla.
                    flake8 src/
                    // Verifica el formateo (sin cambiar los archivos, solo avisa)
                    black --check src/
                '''
            }
        }

        stage('Pruebas Unitarias (Pytest)') {
            steps {
                echo "Ejecutando pruebas de Django con pytest..."
                sh '''
                    . venv/bin/activate
                    // Instala pytest-django si no está en requirements.txt
                    pip install pytest pytest-django
                    // Ejecuta los tests dentro de la carpeta src
                    cd src
                    pytest
                '''
            }
        }
    }

    // Qué hacer después de terminar el pipeline (haya fallado o pasado)
    post {
        always {
            echo "Pipeline finalizado. Limpiando espacio de trabajo..."
            cleanWs() // Borra los archivos descargados para no llenar el servidor
        }
        success {
            echo "✅ El PR está perfecto. Listo para hacer merge a main."
            // El plugin de GitHub en Jenkins (configurado más adelante)
            // enviará automáticamente el "Status: Success" a GitHub.
        }
        failure {
            echo "❌ El pipeline falló. Revisa los logs de Linting o Pytest."
        }
    }
}