pipeline {
    agent any

    stages {
        stage('Validar Conexión Git') {
            steps {
                echo "✅ Jenkins logró leer el Jenkinsfile sin errores de sintaxis."
            }
        }

        stage('Validar Entorno del Servidor') {
            steps {
                echo "Verificando qué herramientas tiene instaladas Jenkins por dentro..."
                sh "git --version"
                sh "python3 --version || echo 'ALERTA: Python3 NO está instalado'"
                sh "docker --version || echo 'ALERTA: Docker NO está instalado'"
            }
        }
    }
}