pipeline {
    agent any

    stages {
        stage('Validar Conexión Git') {
            steps {
                echo "✅ Jenkins logró leer el Jenkinsfile sin errores de sintaxis."
            }
        }

        stage('Validar Entorno del Servidor (Windows)') {
            steps {
                echo "Verificando qué herramientas tiene instaladas Jenkins por dentro..."
                // Usamos 'bat' en lugar de 'sh' para sistemas Windows
                bat "git --version"
                bat "python --version"
                bat "docker --version"
            }
        }
    }
}