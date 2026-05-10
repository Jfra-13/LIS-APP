pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Preparar Entorno') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    python -m pip install --upgrade pip
                    pip install -r requirements.txt
                    pip install flake8 black
                '''
            }
        }

        stage('Lint & Formateo') {
            steps {
                sh '''
                    . venv/bin/activate
                    flake8 src/
                    black --check src/
                '''
            }
        }

        stage('Pruebas Django') {
            steps {
                sh '''
                    . venv/bin/activate
                    cd src
                    python manage.py check
                    python manage.py test
                '''
            }
        }
    }

    post {
        always {
            cleanWs()
        }
        success {
            echo "PR validado correctamente."
        }
        failure {
            echo "El pipeline falló. Revisa los logs."
        }
    }
}