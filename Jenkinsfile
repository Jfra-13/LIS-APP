pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

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

        stage('Instalar Dependencias') {
            steps {
                echo "📦 Instalando dependencias Python..."
                bat """
                    python -m pip install --upgrade pip
                    pip install -r requirements.txt
                """
            }
        }

        stage('Validar Código (Lint)') {
            steps {
                echo "🔍 Ejecutando validación de código con Flake8..."
                bat """
                    flake8 src/admision src/core --max-line-length=120 --statistics
                """
            }
        }

        stage('Formateo de Código (Black)') {
            steps {
                echo "🎨 Verificando formateo de código con Black..."
                bat """
                    black --check --line-length=120 src/admision src/core
                """
            }
        }

        stage('Ejecutar Tests + Cobertura') {
            steps {
                echo "🧪 Ejecutando suite de tests con pytest + cobertura..."
                bat """
                    cd src
                    pytest --cov=admision --cov=core --cov-report=html --cov-report=term-missing --cov-fail-under=80 -v
                    cd ..
                """
            }
        }

        stage('Performance Testing (< 1.5s)') {
            steps {
                echo "⚡ Validando performance de vistas (< 1.5s)..."
                bat """
                    cd src
                    pytest admision/tests.py::PacienteCreateViewTests::test_response_time_menor_1_5_segundos -v
                    cd ..
                """
            }
        }

        stage('Pruebas de Integración') {
            steps {
                echo "🔗 Ejecutando pruebas de integración..."
                bat """
                    cd src
                    pytest admision/tests.py::PacienteListViewTests -v
                    pytest admision/tests.py::PacienteCreateViewTests -v
                    pytest admision/tests.py::PacienteUpdateViewTests -v
                    pytest admision/tests.py::PacienteDeleteViewTests -v
                    cd ..
                """
            }
        }
    }

    post {
        always {
            echo "📊 Generando reporte HTML de cobertura..."
            publishHTML([
                reportDir: 'src/htmlcov',
                reportFiles: 'index.html',
                reportName: '📈 Coverage Report',
                keepAll: true,
                alwaysLinkToLastBuild: true
            ])
        }

        success {
            echo "✅ BUILD EXITOSO"
            echo "  ✓ Cobertura ≥ 80%"
            echo "  ✓ Todos los tests pasaron"
            echo "  ✓ Performance validado (< 1.5s)"
        }

        failure {
            echo "❌ BUILD FALLIDO"
            echo "  Verifica los logs arriba para más detalles"
            echo "  Posibles causas:"
            echo "    - Tests fallaron"
            echo "    - Cobertura < 80%"
            echo "    - Performance > 1.5s"
            echo "    - Errores de linting (Flake8)"
            echo "    - Errores de formateo (Black)"
        }

        unstable {
            echo "⚠️ BUILD INESTABLE - Revisa los warnings"
        }
    }
}