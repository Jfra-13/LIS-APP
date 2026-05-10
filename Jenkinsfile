pipeline {

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
                    pip install -r requirements.txt
                '''
            }
        }

            steps {
                sh '''
                    . venv/bin/activate
                    flake8 src/
                    black --check src/
                '''
            }
        }

            steps {
                sh '''
                    . venv/bin/activate
                    cd src
                '''
            }
        }
    }

    post {
        always {
        }
        success {
        }
        failure {
        }
    }
}